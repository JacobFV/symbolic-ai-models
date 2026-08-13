"""What an environment is: a world to act in, a reward, and a floor.

This is the counterpart of :mod:`symbolic_ai_models.tasks`, and the difference
between the two is the whole reason this package exists. A *task* hands a model
the correct history and scores one prediction against one hidden symbol. An
*environment* hands an agent an observation, takes an action back, and lets the
consequences of that action be part of the next observation. Nothing is
teacher-forced. An agent that goes wrong on step one lives with it on step two,
which is precisely the measurement the model harness cannot make and which
``ROADMAP.md`` records as a scope boundary rather than a solved problem.

Everything else is kept deliberately identical to the model harness, because
that is what makes the two comparable:

* **The episodes are the same episodes.** They come from
  :func:`symbolic_ai_models.data.curriculum.generate`, are pure functions of a
  seed, and evaluation seeds still start at one million. An environment is a way
  of *presenting* an episode, not a new data source.
* **Text in, text out.** An observation is a string plus a stated set of legal
  actions, and an action is one of those strings. There are no tensors here and
  no learned representations; this package is symbolic all the way down.
* **A score is never reported without its floor.** ``lift`` is imported from the
  model harness rather than redefined, so ``0`` means the same thing in both
  packages: no better than something that understands nothing.

The floor here is measured rather than derived. :func:`reference_floor` fits the
reference policies on the training episodes and *runs them in the environment*,
which is the only floor that is guaranteed to be the right one — a closed-form
expression for "what random guessing gets" has to be re-derived for every
environment and was wrong for two of them before this was written.

Determinism
-----------
An environment seeds itself from the episode's ``instance_id`` and its own
config, never from a caller-supplied generator. Two agents evaluated on the same
episodes therefore face bit-identical worlds — the same nodes masked, the same
lines redacted — so a two-point difference between them is a difference between
the agents. ``random.Random(str)`` is used rather than ``hash()`` because
Python salts string hashes per process, which would make a run irreproducible in
a way that is invisible until someone tries to reproduce it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.models.symbolic import GraphView
from symbolic_ai_models.tasks.base import Totals, lift

__all__ = ["Observation", "Step", "Move", "Trajectory", "Environment",
           "Totals", "lift", "FLOOR_POLICIES", "reference_floor", "summarize"]

#: The policies every environment's floor is the maximum of. They are fitted on
#: the training episodes and then *run*, in the environment, on the same
#: evaluation episodes the agents are run on.
#:
#: ``random`` is chance. ``shortcut`` is the best parameter-free cheat from
#: :mod:`symbolic_ai_models.shortcuts` — pick the longest option, the one sharing
#: most words with the question, the one written unlike the others. ``context``
#: is the structure-only lookup table that the masked-node floor in the model
#: harness is built from. All three are registered agents as well as floors,
#: which means each appears in the comparison table with a lift of zero *on the
#: environment where it is the strongest of the three*, by construction. That is
#: not a bug in the table; it is the table saying what those rows are for.
FLOOR_POLICIES: tuple[str, ...] = ("random", "shortcut", "context")


@dataclass(frozen=True)
class Observation:
    """Everything the agent is shown at one step, and nothing it is not.

    ``actions`` and ``probes`` are both legal, and the split between them is the
    point of the distinction rather than a convenience: an action in ``actions``
    **commits** — it ends the question, right or wrong — while a probe buys
    information and hands the turn back. An agent that never looks at ``probes``
    is a perfectly well-formed agent that simply never asks; an environment with
    no probes to offer leaves the tuple empty and every agent behaves as it does
    everywhere else.

    ``key`` names *which question is being asked*. It changes when the
    environment moves on to a new one, and :class:`~symbolic_ai_agents.agents.base.Agent`
    uses it to know when to forget which actions have already been refused. An
    environment that re-asks the same question keeps the key.
    """

    text: str
    actions: tuple[str, ...] = ()
    #: Actions that buy information instead of committing. Usually empty.
    probes: tuple[str, ...] = ()
    #: The masked term graph, for environments that expose structure. This is
    #: the model harness's own :class:`~symbolic_ai_models.models.symbolic.GraphView`,
    #: reused rather than re-implemented: hidden labels are literally ``None``,
    #: so an agent that wanted to read its own answer has nothing to read.
    graph: GraphView | None = None
    #: Which node of ``graph`` is being asked about, or ``-1``.
    node: int = -1
    step: int = 0
    #: Steps left before the environment gives up on this question.
    remaining: int = 1
    key: str = ""
    info: Mapping[str, Any] = field(default_factory=dict)

    @property
    def choices(self) -> tuple[str, ...]:
        """Everything that may legally be done, committing or not."""
        return self.actions + self.probes


@dataclass(frozen=True)
class Step:
    """What came back. ``next_obs`` is ``None`` exactly when ``done``."""

    reward: float
    done: bool
    #: What the environment said, in words. Shown to the agent and printed in
    #: traces; environments state refusals here rather than only in the reward,
    #: because "wrong" and "wrong, and here is which part" are different worlds.
    feedback: str = ""
    next_obs: Observation | None = None
    #: Whether this action was the right one, where that is meaningful. ``None``
    #: for probes and for steps that are neither right nor wrong.
    correct: bool | None = None
    info: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Move:
    """One complete exchange: seen, done, and what came of it.

    The confidence is recorded here rather than thrown away because a stated
    confidence that does not track being right is the same empty number the
    model harness refuses to report — see :mod:`symbolic_ai_agents.calibration`,
    which reads it straight off these.
    """

    obs: Observation
    action: str
    confidence: float
    step: Step


@dataclass
class Trajectory:
    """One episode, as it actually went."""

    env: str
    lesson_id: str
    instance_id: str
    moves: list[Move] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.moves)

    @property
    def total_reward(self) -> float:
        return sum(m.step.reward for m in self.moves)

    @property
    def solved(self) -> bool:
        """Whether this episode counts as solved.

        An environment that pays partial credit gets to say so: if its final
        step carries ``info["solved"]``, that is the answer.
        :mod:`symbolic_ai_agents.envs.repair` uses it, because "the last node
        was filled correctly" and "every node was filled correctly" are
        different claims and only the second one is a repair.

        Otherwise it is whether the last *committing* move was right.
        Deliberately not "reward > 0", and deliberately ``False`` for a
        trajectory with no committing move at all — an agent that probed until
        the horizon ran out has not solved anything.
        """
        if self.moves:
            declared = self.moves[-1].step.info.get("solved")
            if declared is not None:
                return bool(declared)
        for move in reversed(self.moves):
            if move.step.correct is not None:
                return bool(move.step.correct)
        return False

    def counts(self) -> dict[str, float]:
        """Exact counts, to be summed across episodes rather than averaged.

        Averages of averages are wrong whenever episodes differ in length, and
        under a horizon they always do — the same reason
        :class:`symbolic_ai_models.tasks.base.TaskOutput` carries counts.

        Numeric entries of every step's ``info`` are summed in alongside, which
        is how an environment reports something the base class has never heard
        of — ``fills_right``, ``revealed`` — without the base class growing a
        field per environment. ``solved`` is excluded because it is a per-episode
        verdict rather than a count, and summing it per *step* would count a
        multi-step episode several times.
        """
        probes = sum(1 for m in self.moves if m.action in m.obs.probes)
        out = {"episodes": 1.0, "return": self.total_reward,
               "solved": float(self.solved), "moves": float(len(self.moves)),
               "probes": float(probes)}
        for move in self.moves:
            for key, value in move.step.info.items():
                if key == "solved" or not isinstance(value, (int, float)):
                    continue
                out[key] = out.get(key, 0.0) + float(value)
        return out


def summarize(totals: Totals) -> dict[str, float]:
    """The four numbers every environment reports, whatever else it adds."""
    n = totals.get("episodes", 0.0)
    if not n:
        return {"return": float("nan"), "success": float("nan"),
                "moves": float("nan"), "probes": float("nan"), "n": 0.0}
    return {"return": totals.get("return", 0.0) / n,
            "success": totals.get("solved", 0.0) / n,
            "moves": totals.get("moves", 0.0) / n,
            "probes": totals.get("probes", 0.0) / n,
            "n": float(n)}


class Environment:
    """Present an episode, take an action, say what happened.

    An instance is **stateful for the length of one episode**: :meth:`reset`
    installs an episode and returns the first observation, :meth:`step` advances
    it. One instance is reused across episodes, exactly as one
    :class:`~symbolic_ai_models.tasks.base.Task` instance is reused across
    batches.

    Subclasses implement :meth:`reset` and :meth:`step`. Everything else has a
    working default, so a new environment is two methods and a docstring.
    """

    #: registry name, set by ``@register``
    name: str = ""
    #: one line, printed by ``symbolic-ai-agents envs``
    summary: str = ""
    #: The most moves one episode may take.
    horizon: int = 1
    #: Whether an agent can do better here by *using what it was told*. Printed
    #: alongside results, because a high score on a non-interactive environment
    #: is a claim about ranking and a high score on an interactive one is a
    #: claim about learning within the episode, and they are not the same claim.
    interactive: bool = False

    def reset(self, ep: Episode, *, tok: SymbolTokenizer) -> Observation:
        raise NotImplementedError

    def step(self, action: str) -> Step:
        raise NotImplementedError

    def oracle(self) -> str | None:
        """The correct committing action right now. **Fitting time only.**

        This is the environment's copy of ``batch.target_tokens``: the label an
        agent is fitted against, available on training episodes and nowhere
        else. :func:`symbolic_ai_agents.agents.base.training_views` is the only
        thing in this package that calls it, and it is called only from inside
        ``fit``.

        Rather than trust that, ``tests/test_agent_leaks.py`` replaces every
        environment's ``oracle`` with a liar during evaluation and requires that
        no agent's trajectory changes. An agent that consulted it while acting
        fails that test, in the same spirit as the two leak tests every model in
        the other package has to pass.

        ``None`` means there is nothing to be right about here — a probe step, or
        an episode with no answerable question.
        """
        return None

    # ---- optional hooks -------------------------------------------------
    def context_key(self, obs: Observation) -> tuple:
        """What counts as "the same kind of situation" here.

        The lookup-table agent keys its table on this, and so does the floor it
        defines. The default is the lesson and the step number, which is the
        coarsest thing that is always available; :mod:`symbolic_ai_agents.envs.repair`
        overrides it with the structural key the model harness's masked-node
        floor uses, so that the two floors are the same table asked the same
        question.
        """
        return (str(obs.info.get("lesson_id", "")), min(obs.step, 8))

    def summarize(self, totals: Totals) -> dict[str, float]:
        return summarize(totals)

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode], *,
              envs: "Mapping[str, Environment] | None" = None,
              seed: int = 0) -> dict[str, Any]:
        """The best of the reference policies, run here on these episodes.

        ``envs`` and ``seed`` are the ones the scored agent was fitted with, and
        passing them is not optional bookkeeping -- see :func:`reference_floor`.
        """
        return reference_floor(self, episodes, tok, train, envs=envs, seed=seed)

    # ---- helpers for subclasses ----------------------------------------
    def episode_rng(self, ep: Episode) -> random.Random:
        """A generator that depends on the episode and the config, and nothing
        else — so every agent faces the identical world."""
        return random.Random(f"{self.name}:{ep.instance_id}:{self._salt()}")

    def _salt(self) -> str:
        """Config that changes the world, folded into the seed.

        An environment whose mask rate changed but whose seed did not would
        quietly reuse the old draw for the overlapping nodes and look like a
        smaller change than it was.
        """
        return ""


def reference_floor(env: Environment, episodes: Sequence[Episode],
                    tok: SymbolTokenizer, train: Sequence[Episode], *,
                    envs: "Mapping[str, Environment] | None" = None,
                    seed: int = 0) -> dict[str, Any]:
    """Fit each reference policy on ``train``; run it on ``episodes``; take the best.

    Measured rather than derived, and that is not fastidiousness. The expected
    return of guessing without replacement under
    :mod:`symbolic_ai_agents.envs.retry`'s ``1/tries`` payout is a closed form,
    it was written down wrong, and nothing would have caught it: a floor is the
    one number in the table that nothing else is checked against. Running the
    policy cannot be wrong about what the policy scores.

    Returns the winning policy's metrics with ``floor_by`` naming it, because
    *which* cheat wins says what leaked — the same argument
    :func:`symbolic_ai_models.shortcuts.shortcut_table` makes.

    **Fit the reference policies exactly as the scored agent was fitted.** This
    took ``envs={env.name: env}`` and no seed while the run fitted its agent with
    every environment and ``cfg.seed``, so the floor was a *differently fitted
    copy* of the same policy. On the first full-curriculum sweep ``context``
    scored 0.2589 on ``repair`` against a floor of 0.2336 recorded as
    ``floor_by: context`` — a reference policy beating itself by 0.025, which was
    the only positive number in the entire table.

    A floor is the one number in a run that nothing else is checked against, so
    an asymmetry here is invisible: every lift in the agents half was measured
    against a weaker copy of its own baseline, and no test could have noticed.
    """
    from ..agents import build as build_agent
    from ..agents.base import LearnContext
    from .rollout import rollouts

    best: dict[str, float] = {}
    fit_envs = dict(envs) if envs else {env.name: env}
    for name in FLOOR_POLICIES:
        try:
            policy = build_agent(name, {})
        except KeyError:                                  # pragma: no cover
            continue
        policy.fit(LearnContext(episodes=list(train), tok=tok, envs=fit_envs,
                                seed=seed))
        metrics = env.summarize(rollouts(env, policy, episodes, tok=tok).totals)
        if not best or metrics.get("return", 0.0) > best.get("return", 0.0):
            best = {**metrics, "floor_by": name}
    return best or {"return": 0.0, "success": 0.0, "floor_by": ""}
