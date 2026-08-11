"""The training harness. One loop, any architecture, either task or both.

The loop is deliberately plain — AdamW, cosine decay, gradient clipping — because
it is a control, not a contribution. Every architecture gets the same optimiser,
the same schedule, the same data in the same order and the same number of steps,
so that a difference in the results is a difference between the architectures.

Joint training runs both objectives on every step rather than alternating
between them. Alternating makes the last task's gradient the one the model most
recently moved on, which shows up as a sawtooth in whichever metric was not
updated last and makes two runs with different task orders incomparable. Summing
weighted losses costs a second forward pass and has no such artefact.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

import numpy as np
import torch

from .data.batch import SymbolicBatch
from .data.sampler import batches
from .data.curriculum import Episode, generate, read_jsonl, resolve_lessons
from .data.tokenizer import SymbolTokenizer
from .models import Model, ModelConfig, RuleBasedModel, build
from .models.base import FitContext, autocast
from .tasks import Task, Totals, make_task
from .tasks.base import lift

__all__ = ["TrainConfig", "train", "evaluate_model", "load_run", "make_model",
           "batches", "load_data", "build_tokenizer"]


@dataclass
class TrainConfig:
    """Everything a run is. Serialised next to the weights, so a run is
    reproducible from its own output directory and nothing else."""

    model: str = "transformer"
    tasks: tuple[str, ...] = ("lm", "node")
    task_weights: dict[str, float] = field(default_factory=lambda: {"lm": 1.0, "node": 1.0})

    # data
    data: str | None = None                  # a built cache; None generates live
    lessons: str = "all"
    n_train: int = 32
    n_eval: int = 8
    language: str = "english"
    max_len: int = 512
    max_nodes: int = 256
    mask_rate: float = 0.15
    type_weight: float = 0.5
    vocab_size: int = 8192
    #: share of the vocabulary reserved for whole node labels
    label_vocab_fraction: float = 0.3

    # architecture
    d_model: int = 256
    n_layers: int = 6
    n_heads: int = 8
    d_ff: int = 1024
    dropout: float = 0.1
    extra: dict[str, Any] = field(default_factory=dict)

    # optimisation
    steps: int = 2000
    batch_size: int = 16
    lr: float = 3e-4
    min_lr_ratio: float = 0.1
    warmup: int = 100
    weight_decay: float = 0.01
    grad_clip: float = 1.0

    # bookkeeping
    eval_every: int = 250
    log_every: int = 50
    seed: int = 0
    #: Continue a partially trained run from `out/checkpoint.pt` if present.
    resume: bool = False
    device: str = "cpu"
    amp: bool = True
    out: str = "runs/run"

    def resolved_device(self) -> torch.device:
        """CPU unless a run explicitly asks otherwise.

        The default used to be ``auto``, which took the GPU whenever one
        existed. The symbolic models are pure Python and gain nothing from it,
        so all that bought was contention with whatever else was training on the
        machine. Pass ``--device cuda`` deliberately.
        """
        if self.device != "auto":
            return torch.device(self.device)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tasks"] = list(self.tasks)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TrainConfig":
        d = dict(d)
        d["tasks"] = tuple(d.get("tasks", ("lm", "node")))
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**d)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load_data(cfg: TrainConfig) -> tuple[list[Episode], list[Episode]]:
    """Training and evaluation episodes, from a cache or generated live.

    The two never overlap: evaluation seeds start at one million and training
    seeds at zero, which is a property of the seeds themselves rather than of a
    split file that could be regenerated wrongly.
    """
    if cfg.data:
        root = Path(cfg.data)
        return read_jsonl(root / "train.jsonl"), read_jsonl(root / "eval.jsonl")
    lessons = resolve_lessons(cfg.lessons)
    kw = dict(language=cfg.language, max_nodes=cfg.max_nodes)
    return (list(generate(lessons, n=cfg.n_train, seed0=0, **kw)),
            list(generate(lessons, n=cfg.n_eval, seed0=1_000_000, **kw)))


def _task_kwargs(cfg: TrainConfig, name: str) -> dict[str, Any]:
    if name == "lm":
        return {"max_len": cfg.max_len}
    return {"mask_rate": cfg.mask_rate, "type_weight": cfg.type_weight,
            "max_nodes": cfg.max_nodes, "seed": cfg.seed}


def _model_config_dict(mc: ModelConfig) -> dict[str, Any]:
    """The recorded form: plain values, so a summary stays readable JSON."""
    return {"vocab_size": mc.vocab_size, "d_model": mc.d_model,
            "n_layers": mc.n_layers, "n_heads": mc.n_heads, "d_ff": mc.d_ff,
            "dropout": mc.dropout, "max_len": mc.max_len,
            "max_nodes": mc.max_nodes, "extra": dict(mc.extra)}


def model_config(cfg: TrainConfig, vocab_size: int) -> ModelConfig:
    """The shape the model is actually built with.

    Two fields here are *derived* and appear nowhere in ``TrainConfig``:
    ``vocab_size`` comes from the fitted tokenizer, and ``max_len`` is widened to
    cover whichever surface is longer plus slack, since one positional embedding
    serves both the token sequence and the node sequence.

    It is a separate function so it can be recorded. A run used to save only its
    ``TrainConfig``, which meant a saved model could not be rebuilt from its own
    summary: ``rgt`` trained with a 328-row positional embedding while its
    summary said ``max_len = 320``, and ``load_state_dict`` refused it.
    """
    return ModelConfig(
        vocab_size=vocab_size, d_model=cfg.d_model, n_layers=cfg.n_layers,
        n_heads=cfg.n_heads, d_ff=cfg.d_ff, dropout=cfg.dropout,
        max_len=max(cfg.max_len, cfg.max_nodes) + 8, max_nodes=cfg.max_nodes,
        extra=dict(cfg.extra))


def make_model(cfg: TrainConfig, vocab_size: int) -> Model:
    return build(cfg.model, model_config(cfg, vocab_size))


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
@torch.no_grad()
def evaluate_model(model: Model, tasks: dict[str, Task],
                   episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                   batch_size: int, device: torch.device,
                   amp: bool = True) -> dict[str, dict[str, float]]:
    """Every task's metrics on ``episodes``. Deterministic, including the mask.

    The masking RNG is reset per evaluation so that two checkpoints are scored
    on the same hidden nodes. Without that, a two-point move in node accuracy
    could be an easier mask rather than a better model.
    """
    model.eval()
    out: dict[str, dict[str, float]] = {}
    for name, task in tasks.items():
        if hasattr(task, "rng"):
            task.rng = np.random.default_rng(12345)
        totals = Totals()
        for batch in batches(episodes, task, tok, batch_size=batch_size,
                             rng=random.Random(0), shuffle=False):
            batch = batch.to(device)
            with autocast(device, amp):
                result = task.compute(model(batch), batch)
            totals.add(result.counts)
        out[name] = task.summarize(totals)
    model.train()
    return out


def _add_lift(metrics: dict[str, dict[str, float]],
              floors: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Attach the floor and the lift to every accuracy that has one."""
    for task, ms in metrics.items():
        floor = floors.get(task, {})
        for key in [k for k in list(ms) if k.endswith("_acc")]:
            if key in floor:
                ms[f"{key[:-4]}_floor"] = floor[key]
                ms[f"{key[:-4]}_lift"] = lift(ms[key], floor[key])
        for key in [k for k in list(ms) if k.endswith("_bits")]:
            if key in floor:
                ms[f"{key[:-5]}_floor_bits"] = floor[key]
    return metrics


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------
def train(cfg: TrainConfig, *, progress=None) -> dict[str, Any]:
    """Run ``cfg`` to completion and write everything to ``cfg.out``.

    Both families come through here and both leave the same artefacts, so
    ``compare`` puts a decision list and a transformer in one table. What
    differs is only how the model is brought to its final state: a network takes
    ``steps`` gradient steps, a rule-based model is *fitted* once, in a single
    pass over the same training episodes.
    """
    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    device = cfg.resolved_device()
    out = Path(cfg.out)
    out.mkdir(parents=True, exist_ok=True)

    train_eps, eval_eps = load_data(cfg)
    if not train_eps:
        raise ValueError("no training episodes; check `lessons` and `n_train`")
    tok = build_tokenizer(cfg, train_eps)
    tok.save(out / "tokenizer.json")

    tasks: dict[str, Task] = {n: make_task(n, **_task_kwargs(cfg, n)) for n in cfg.tasks}
    floors = {n: t.floor(eval_eps, tok, train_eps) for n, t in tasks.items()}

    model = make_model(cfg, len(tok))
    is_rule_based = isinstance(model, RuleBasedModel)
    run_device = torch.device("cpu") if is_rule_based else device
    history: list[dict[str, Any]] = []
    started = time.time()

    def record(step: int) -> None:
        """Evaluate and append to the history. The model calls this when it has
        something worth recording; a one-pass learner never does, and the final
        evaluation below covers it either way."""
        metrics = _add_lift(evaluate_model(model, tasks, eval_eps, tok,
                                           batch_size=cfg.batch_size,
                                           device=run_device,
                                           amp=cfg.amp and not is_rule_based), floors)
        history.append({"step": step, "train_loss": dict(last_losses),
                        "eval": metrics, "seconds": time.time() - started})
        _write(out / "history.json", history)
        if progress:
            progress(max(step - 1, 0), cfg.steps, dict(last_losses), 0.0, metrics)

    last_losses: dict[str, float] = {}

    def note(step: int, total: int, losses: dict[str, float], grad: float) -> None:
        last_losses.clear()
        last_losses.update(losses)
        if progress:
            progress(step, total, losses, grad)

    # Hand over the data, the tasks and the budget. How to learn from them is
    # the model's business — see `Model.fit`.
    model.fit(FitContext(
        episodes=train_eps, tok=tok, tasks=tasks, task_weights=cfg.task_weights,
        steps=cfg.steps, batch_size=cfg.batch_size, lr=cfg.lr,
        min_lr_ratio=cfg.min_lr_ratio, warmup=cfg.warmup,
        weight_decay=cfg.weight_decay, grad_clip=cfg.grad_clip,
        eval_every=cfg.eval_every, log_every=cfg.log_every, seed=cfg.seed,
        amp=cfg.amp and not is_rule_based, device=run_device,
        checkpoint=str(out / "checkpoint.pt"), resume=cfg.resume,
        on_step=note, on_eval=record))

    if not history:                       # a learner that reported nothing
        record(cfg.steps if not is_rule_based else 0)

    # `model_config` as well as `config`: the first is what the model was built
    # with, the second what was asked for, and they differ in the two derived
    # fields. Without the first, reloading a checkpoint means guessing.
    effective = model_config(cfg, len(tok))
    checkpoint = {"model": model.state_dict(), "config": cfg.to_dict(),
                  "model_config": _model_config_dict(effective),
                  "vocab_size": len(tok)}
    if isinstance(model, RuleBasedModel):
        # A decision list is not a tensor, so `state_dict` cannot see it.
        checkpoint["symbolic_state"] = model.symbolic_state()
    torch.save(checkpoint, out / "model.pt")
    extra: dict[str, Any] = {}
    if hasattr(model, "abstention_rate"):
        extra["abstention_rate"] = float(model.abstention_rate)
    if hasattr(model, "render"):
        (out / "rules.txt").write_text(model.render(), encoding="utf-8")

    summary = {
        "config": cfg.to_dict(),
        "model_config": _model_config_dict(effective),
        "model": cfg.model,
        "family": model.family,
        "steps": 0 if is_rule_based else cfg.steps,
        "parameters": model.n_parameters(),
        "n_train": len(train_eps), "n_eval": len(eval_eps),
        "vocab_size": len(tok),
        "floors": floors,
        "final": history[-1]["eval"] if history else {},
        "seconds": time.time() - started,
        "device": str(run_device),
        **extra,
    }
    _write(out / "summary.json", summary)
    return summary


def build_tokenizer(cfg: TrainConfig, episodes: Sequence[Episode]) -> SymbolTokenizer:
    """One vocabulary covering both surfaces, with the budget split between them.

    Text pieces alone would fill it, and that would quietly break the graph
    task: in prose a label like ``o2`` is the two pieces ``o`` and ``2``, but as
    a *node label* it has to land on a single id or the masked-node head cannot
    name it. So a share of the budget is reserved for whole labels, and without
    it the graph task would silently score only the labels that happen to be
    single English words — which is a biased and much easier subset.
    """
    import collections
    reserved = int(cfg.vocab_size * cfg.label_vocab_fraction)
    tok = SymbolTokenizer.build((ep.text for ep in episodes),
                                max_vocab=max(cfg.vocab_size - reserved, 262))
    counts: collections.Counter[str] = collections.Counter()
    for ep in episodes:
        counts.update(l for l in ep.graph.labels if l)
    for label, _ in counts.most_common():
        if len(tok.itos) >= cfg.vocab_size:
            break
        if label not in tok.stoi:
            tok.stoi[label] = len(tok.itos)
            tok.itos.append(label)
    return tok


def _write(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_run(run_dir: str | Path, device: torch.device | str = "cpu"
             ) -> tuple[Model, SymbolTokenizer, TrainConfig]:
    """Reload a finished run: the model, its vocabulary and its config."""
    root = Path(run_dir)
    ckpt = torch.load(root / "model.pt", map_location=device, weights_only=False)
    cfg = TrainConfig.from_dict(ckpt["config"])
    tok = SymbolTokenizer.load(root / "tokenizer.json")
    model = make_model(cfg, ckpt["vocab_size"]).to(device)
    model.load_state_dict(ckpt["model"])
    if isinstance(model, RuleBasedModel):
        state = ckpt.get("symbolic_state")
        if state is None:
            raise ValueError(
                f"{run_dir}: a rule-based checkpoint without its learned state. "
                "Re-run the training; the run predates symbolic persistence.")
        model.load_symbolic_state(state, tok)
    model.eval()
    return model, tok, cfg
