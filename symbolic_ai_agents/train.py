"""The harness. One fit, any policy, any environment or all of them.

The counterpart of :mod:`symbolic_ai_models.train`, and deliberately the same
shape: episodes and a vocabulary in, a fitted thing and a directory of artefacts
out, with every environment's floor computed on the same evaluation episodes the
agent is scored on.

Three things are identical to the model harness and are identical on purpose.

* **The split is by seed.** Training seeds start at zero, evaluation seeds at one
  million. That is a property of the seeds rather than of a split file, so an
  evaluation set cannot have been fitted on however the code is rearranged.
* **The vocabulary is built the same way.** :func:`build_tokenizer` is imported
  from the model harness, not re-implemented, so ``wrap`` sees exactly the
  vocabulary the model it wraps would have seen.
* **A number is never reported without its floor.** Every environment's floor is
  the best of the reference policies *run in that environment*, and every
  reported return carries a lift beside it.

One thing is different and is the whole point: what is written out is a set of
**trajectories**, not a set of predictions. ``trajectories.jsonl`` holds what the
agent actually did, step by step, which is what
:mod:`symbolic_ai_agents.trace` reads and what makes a wrong answer inspectable
rather than merely counted.

There is no ``steps`` budget. Every agent here fits in one pass, exactly as
every rule-based model does, and the summary records ``steps: 0`` so that a row
cannot be misread as a policy that trained longer than its neighbours.
"""

from __future__ import annotations

import json
import pickle
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from symbolic_ai_models.data.curriculum import (Episode, generate, read_jsonl,
                                                resolve_lessons)
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.train import TrainConfig as ModelTrainConfig
from symbolic_ai_models.train import build_tokenizer

from .agents import Agent, LearnContext, build as build_agent
from .envs import Environment, build as build_env, rollouts
from .envs.base import lift

__all__ = ["RunConfig", "run", "evaluate_agent", "load_run", "load_data",
           "make_agent", "make_envs", "save_agent"]


@dataclass
class RunConfig:
    """Everything a run is. Serialised next to the agent, so a run is
    reproducible from its own output directory and nothing else."""

    agent: str = "context"
    envs: tuple[str, ...] = ("choice", "retry", "repair", "probe")

    # data
    data: str | None = None                  # a built cache; None generates live
    lessons: str = "all"
    n_train: int = 32
    n_eval: int = 8
    language: str = "english"
    max_nodes: int = 256
    vocab_size: int = 8192
    label_vocab_fraction: float = 0.3

    # environments
    tries: int = 3
    mask_rate: float = 0.15
    max_steps: int = 8
    max_actions: int = 24
    probe_cost: float = 0.1
    max_probes: int = 6

    # the agent
    extra: dict[str, Any] = field(default_factory=dict)

    # bookkeeping
    seed: int = 0
    #: How many trajectories per environment to write out for reading. The
    #: counts are always complete; only the stored transcripts are capped.
    keep: int = 64
    out: str = "runs/agent"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["envs"] = list(self.envs)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunConfig":
        d = dict(d)
        d["envs"] = tuple(d.get("envs", ("choice", "retry", "repair", "probe")))
        unknown = set(d) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**d)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load_data(cfg: RunConfig) -> tuple[list[Episode], list[Episode]]:
    """Training and evaluation episodes, from a cache or generated live.

    Reads the same caches ``symbolic-ai-models data`` writes, so one built split
    serves both packages and the two cannot accidentally be comparing results
    drawn from different worlds.
    """
    if cfg.data:
        root = Path(cfg.data)
        return read_jsonl(root / "train.jsonl"), read_jsonl(root / "eval.jsonl")
    lessons = resolve_lessons(cfg.lessons)
    kw = dict(language=cfg.language, max_nodes=cfg.max_nodes)
    return (list(generate(lessons, n=cfg.n_train, seed0=0, **kw)),
            list(generate(lessons, n=cfg.n_eval, seed0=1_000_000, **kw)))


def make_envs(cfg: RunConfig) -> dict[str, Environment]:
    """Build the named environments with this run's settings.

    Every environment-shaping knob lives in :class:`RunConfig` and is recorded
    in ``summary.json``, so :func:`symbolic_ai_agents.report.config_drift` can
    tell a reader when two rows of one table were not produced under one
    setting. A ``probe`` column at ``cost=0.0`` and one at ``cost=0.3`` are
    different experiments and a table that mixes them silently is misleading.
    """
    kwargs: dict[str, dict[str, Any]] = {
        "choice": {},
        "retry": {"tries": cfg.tries},
        "repair": {"mask_rate": cfg.mask_rate, "max_nodes": cfg.max_nodes,
                   "max_steps": cfg.max_steps, "max_actions": cfg.max_actions},
        "probe": {"cost": cfg.probe_cost, "max_probes": cfg.max_probes},
    }
    return {name: build_env(name, **kwargs.get(name, {})) for name in cfg.envs}


def make_agent(cfg: RunConfig) -> Agent:
    return build_agent(cfg.agent, dict(cfg.extra))


def make_tokenizer(cfg: RunConfig, episodes: Sequence[Episode]) -> SymbolTokenizer:
    """The model harness's own vocabulary builder, with this run's budget."""
    return build_tokenizer(
        ModelTrainConfig(vocab_size=cfg.vocab_size,
                         label_vocab_fraction=cfg.label_vocab_fraction),
        episodes)


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
def evaluate_agent(agent: Agent, envs: dict[str, Environment],
                   episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                   keep: int = 64) -> tuple[dict[str, dict[str, Any]], dict]:
    """Every environment's metrics on ``episodes``, plus the kept trajectories.

    Deterministic, including the environments' own randomness: an environment
    seeds itself from the episode, so two agents are scored on the same masked
    nodes and the same redacted lines. Without that, a two-point move could be
    an easier draw rather than a better policy — the same argument
    :func:`symbolic_ai_models.train.evaluate_model` makes for resetting the mask
    RNG per evaluation.
    """
    metrics: dict[str, dict[str, Any]] = {}
    kept: dict[str, list] = {}
    for name, env in envs.items():
        rolls = rollouts(env, agent, episodes, tok=tok, keep=keep)
        metrics[name] = env.summarize(rolls.totals)
        kept[name] = rolls.trajectories
    return metrics, kept


def add_lift(metrics: dict[str, dict[str, Any]],
             floors: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Attach the floor and the lift to every score that has one.

    ``return`` and ``success`` both get one, and ``label_acc`` does too where an
    environment reports it, because those are the three numbers anyone reads.
    Everything else — how many probes were bought, what share of nodes were
    recoverable — is a description of what happened rather than a score, and giving
    it a lift would invite comparing it against a floor it has no relation to.
    """
    for env, ms in metrics.items():
        floor = floors.get(env, {})
        for key in ("return", "success", "label_acc"):
            value, base = ms.get(key), floor.get(key)
            if isinstance(value, (int, float)) and isinstance(base, (int, float)):
                ms[f"{key}_floor"] = base
                ms[f"{key}_lift"] = lift(value, base)
        if floor.get("floor_by"):
            ms["floor_by"] = floor["floor_by"]
    return metrics


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------
def run(cfg: RunConfig, *, progress=None) -> dict[str, Any]:
    """Fit ``cfg.agent``, score it in every environment, write everything out."""
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    out = Path(cfg.out)
    out.mkdir(parents=True, exist_ok=True)

    train_eps, eval_eps = load_data(cfg)
    if not train_eps:
        raise ValueError("no training episodes; check `lessons` and `n_train`")
    tok = make_tokenizer(cfg, train_eps)
    tok.save(out / "tokenizer.json")

    envs = make_envs(cfg)
    if not envs:
        raise ValueError("no environments; check `envs`")
    started = time.time()

    # The floors first, so that an agent that takes a long time to fit does not
    # leave a directory whose numbers cannot be read. They do not depend on the
    # agent, which is what a floor being a floor means.
    if progress:
        progress(f"floors for {len(envs)} environments")
    floors = {name: env.floor(eval_eps, tok, train_eps, envs=envs, seed=cfg.seed)
              for name, env in envs.items()}

    agent = make_agent(cfg)
    if progress:
        progress(f"fitting {cfg.agent} on {len(train_eps)} episodes")
    agent.fit(LearnContext(episodes=train_eps, tok=tok, envs=envs, seed=cfg.seed,
                           on_step=(lambda *a: progress(" ".join(map(str, a))))
                           if progress else None))

    if progress:
        progress(f"evaluating on {len(eval_eps)} episodes")
    metrics, kept = evaluate_agent(agent, envs, eval_eps, tok, keep=cfg.keep)
    add_lift(metrics, floors)

    save_agent(out / "agent.pkl", agent, cfg, len(tok))
    _write_jsonl(out / "trajectories.jsonl", kept)
    if hasattr(agent, "render"):
        (out / "policy.txt").write_text(agent.render(), encoding="utf-8")

    summary = {
        "config": cfg.to_dict(),
        "agent": cfg.agent,
        "family": agent.family,
        # Zero, and not the number of rollouts it took to fit: an agent here is
        # fitted in one pass and never consumed a step budget, so a row in a
        # comparison table cannot be misread as one that trained longer.
        "steps": 0,
        "parameters": agent.n_parameters(),
        "n_train": len(train_eps), "n_eval": len(eval_eps),
        "vocab_size": len(tok),
        "floors": floors,
        "final": metrics,
        "seconds": time.time() - started,
    }
    _write(out / "summary.json", summary)
    _write(out / "history.json", [{"step": 0, "eval": metrics,
                                   "seconds": summary["seconds"]}])
    return summary


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------
def save_agent(path: str | Path, agent: Agent, cfg: RunConfig,
               vocab_size: int) -> None:
    """Pickle, not ``torch.save``.

    There is not a tensor in this package. An agent's learned state is counters,
    dictionaries and a calibration map, so the honest serialisation is the one
    for plain Python objects rather than a checkpoint format that would suggest
    weights are involved. ``wrap`` is the exception — it holds a model from the
    other package — and pickling reaches through to it unchanged, since a fitted
    rule-based model is plain Python too.
    """
    with Path(path).open("wb") as f:
        pickle.dump({"agent": agent, "config": cfg.to_dict(),
                     "vocab_size": vocab_size}, f)


def load_run(run_dir: str | Path) -> tuple[Agent, SymbolTokenizer, RunConfig]:
    """Reload a finished run: the agent, its vocabulary and its config."""
    root = Path(run_dir)
    with (root / "agent.pkl").open("rb") as f:
        state = pickle.load(f)
    tok = SymbolTokenizer.load(root / "tokenizer.json")
    agent: Agent = state["agent"]
    agent.tok = tok
    return agent, tok, RunConfig.from_dict(state["config"])


def _write(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _write_jsonl(path: Path, kept: dict[str, list]) -> None:
    """One line per trajectory: what was seen, what was done, what came back.

    Only the readable parts. The :class:`~symbolic_ai_models.models.symbolic.GraphView`
    an observation may carry is not written — it is large, it is derived from
    the episode, and the episode is a pure function of its seed, so anything
    that needs it can rebuild it exactly.
    """
    with path.open("w", encoding="utf-8") as f:
        for env, trajectories in kept.items():
            for traj in trajectories:
                f.write(json.dumps({
                    "env": env, "lesson_id": traj.lesson_id,
                    "instance_id": traj.instance_id,
                    "return": traj.total_reward, "solved": traj.solved,
                    "moves": [{"text": m.obs.text, "actions": list(m.obs.actions),
                               "probes": list(m.obs.probes), "action": m.action,
                               "confidence": m.confidence,
                               "reward": m.step.reward,
                               "correct": m.step.correct,
                               "feedback": m.step.feedback}
                              for m in traj.moves],
                }, ensure_ascii=False) + "\n")
