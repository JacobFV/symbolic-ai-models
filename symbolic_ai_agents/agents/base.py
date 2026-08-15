"""What every agent shares, so that only the policy differs.

The counterpart of :mod:`symbolic_ai_models.models.base` and
:mod:`symbolic_ai_models.models.symbolic`, and it enforces the same bar in the
same three ways. There is no neural family here — an agent in this package is
always something that computes an action rather than learning one — so the split
is simpler, but the discipline is not.

**A distribution, not an answer.** An agent returns *preferences* — a handful of
actions it has a reason to expect, plus a **confidence** in ``[0, 1]``. The base
class turns that into a distribution over the legal actions by mixing against a
fitted prior policy::

    p(a) = (1 - confidence) · prior(a) + confidence · preference(a)

Confidence zero is abstention, and it lands the agent exactly on the prior.
Because the prior *is* the floor — the frequency of that answer string in
training, with mass shifted onto whatever the best parameter-free shortcut
picks — an agent that declines to answer scores the floor rather than scoring
chance. That is the same repair the model harness made when it discovered
several rule-based models whose mechanism beat the floor comfortably while their
score did not, purely because abstaining dropped them below the baseline they
were being compared against.

**It cannot see the answer.** An :class:`~symbolic_ai_agents.envs.base.Observation`
holds no field containing the gold action, and where it carries structure it
carries the model harness's own
:class:`~symbolic_ai_models.models.symbolic.GraphView`, in which hidden labels
are literally ``None``. An agent that wanted to cheat has nothing to read.

**It is fitted on training seeds only.** :meth:`Agent.fit` sees the training
episodes and nothing else; evaluation seeds start a million away.

What the base class does that a subclass therefore cannot get wrong
------------------------------------------------------------------
* **Forgetting refusals.** An action the environment has just refused is removed
  from the next choice, and the set is cleared when
  :attr:`~symbolic_ai_agents.envs.base.Observation.key` says a new question has
  begun. Every agent gets this identically, so
  :mod:`symbolic_ai_agents.envs.retry` measures the quality of a ranking rather
  than which author remembered to write a loop guard.
* **The prior.** Fitted once, here, from the training episodes. Two agents
  therefore fall back on the same thing and the difference between them is their
  mechanism — the same argument that makes the shared back-off in
  :mod:`symbolic_ai_models.models.symbolic` worth having.
* **Calibration.** :meth:`PolicyAgent.confidence` maps a raw internal score to
  the accuracy that score has historically earned, using the model harness's
  :class:`~symbolic_ai_models.calibration.ScoreCalibrator` on held-out training
  episodes. The measured lesson recorded there — that agents deriving confidence
  from *how much structure they found* are the badly calibrated ones — applies
  here unchanged, so the number is measured rather than asserted.
"""

from __future__ import annotations

import collections
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping, Sequence

from symbolic_ai_models.calibration import ScoreCalibrator
from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.shortcuts import SHORTCUTS, Shortcut

from ..envs.base import Environment, Move, Observation

__all__ = ["Agent", "PolicyAgent", "Decision", "Preference", "ABSTAIN",
           "LearnContext", "training_views", "held_out", "shuffled"]

#: ``({action: weight}, confidence in [0, 1])``
Preference = tuple[Mapping[str, float], float]

#: What an agent returns when it has nothing to say. The mixture then reduces
#: exactly to the prior, which is the honest reading of "I don't know" and is
#: why abstention costs nothing beyond the floor it declined to improve on.
ABSTAIN: Preference = ({}, 0.0)


@dataclass(frozen=True)
class Decision:
    """One action, how sure the agent is, and a line for the trace."""

    action: str
    confidence: float = 0.0
    why: str = ""


@dataclass
class LearnContext:
    """Everything an agent might need in order to learn, and nothing about *how*.

    The mirror of :class:`symbolic_ai_models.models.base.FitContext`, including
    the part that looks vestigial: ``steps`` is carried and ignored. Every agent
    in this package fits in one pass, exactly as every rule-based model does, and
    what the runner records is ``steps: 0`` — so a row in a comparison table
    cannot be misread as an agent that trained as long as its neighbours.

    ``envs`` is here because an agent may legitimately want to learn *from its
    own experience* rather than from the gold answers:
    :mod:`symbolic_ai_agents.agents.recall` rolls itself out on the training
    episodes and keeps what paid. Nothing forces an agent to use it.
    """

    episodes: Sequence[Episode]
    tok: SymbolTokenizer
    envs: Mapping[str, Environment] = field(default_factory=dict)

    steps: int = 0
    seed: int = 0
    #: ``(done, total, note) -> None``, for a learner with something to report
    on_step: Callable[..., None] | None = None


class Agent:
    """The interface every policy answers to.

    Three methods matter. ``act(obs) -> Decision`` says what the agent does;
    ``observe(move)`` tells it what came of it; ``fit(ctx)`` says how it came to
    behave that way. Whether the decision came from a lookup table, from a
    shortcut, or from a symbolic model wrapped out of the other package is
    exactly the question this repo is asking — so the runner does none of it and
    only supplies the episodes, the environments and the budget.
    """

    #: registry name, set by ``@register``
    name: str = ""
    #: printed in comparison tables next to the score
    family: str = "rule-based"
    summary: str = ""

    def __init__(self, extra: Mapping[str, Any] | None = None) -> None:
        self.extra: dict[str, Any] = dict(extra or {})
        self.tok: SymbolTokenizer | None = None
        #: The environment this agent is currently acting in, installed by
        #: :meth:`begin`. An agent is allowed to know where it is — that is what
        #: makes :meth:`~symbolic_ai_agents.envs.base.Environment.context_key`
        #: reachable — and is *not* allowed to call
        #: :meth:`~symbolic_ai_agents.envs.base.Environment.oracle`, which is a
        #: fitting-time facility and is checked by the leak test.
        self.env: Environment | None = None
        self._refused: set[str] = set()
        self._key = ""
        self._fitted = False

    def get(self, key: str, default: Any) -> Any:
        return self.extra.get(key, default)

    # ---- the loop -------------------------------------------------------
    def begin(self, env: Environment, obs: Observation) -> None:
        """A new episode starts. Subclasses extend; they must call ``super()``."""
        self.env = env
        self._refused = set()
        self._key = obs.key

    def act(self, obs: Observation) -> Decision:
        raise NotImplementedError

    def observe(self, move: Move) -> None:
        """Record what happened. Refusals are tracked here for every agent.

        An action that was taken and refused is not offered again while the same
        question is being asked. The environment says which question that is
        through ``obs.key``, so an agent does not have to guess when to forget —
        and :mod:`symbolic_ai_agents.envs.repair`, which moves to a new node
        every step, gets the right behaviour without knowing this exists.
        """
        if move.obs.key != self._key:
            self._refused = set()
            self._key = move.obs.key
        if move.step.correct is False:
            self._refused.add(move.action)

    # ---- learning -------------------------------------------------------
    def fit(self, ctx: LearnContext) -> None:
        """Learn from ``ctx.episodes``. Subclasses decide what that means."""
        self.tok = ctx.tok
        self._fitted = True

    def n_parameters(self) -> int:
        """How many discrete things this agent learned.

        Reported for the same reason the model harness reports it: "a table with
        34 entries" is a model size, and printing zero would be worse than
        either number.
        """
        return 0

    def render(self) -> str:
        """What the agent knows, as text, when that is short enough to read."""
        return f"{self.name}: {self.summary}"


class PolicyAgent(Agent):
    """Preferences in, one legal action out, with the prior underneath.

    Subclasses implement :meth:`prefer` and usually :meth:`learn`. Everything
    else — the mixture, the refusals, the prior, the calibration — is settled
    here, which is what makes two agents differ in their mechanism and nothing
    else.
    """

    #: Whether an abstention falls back on the fitted prior. On by default, for
    #: the reason in the module docstring. :mod:`symbolic_ai_agents.agents.random_agent`
    #: turns it off, because a floor that quietly consulted the best shortcut
    #: would not be chance and the table needs one row that is.
    use_prior = True

    #: Attribute names holding what this agent learned. Everything here is plain
    #: Python, so persistence is a pickle of these plus the shared prior — see
    #: :func:`symbolic_ai_agents.train.save_agent`. Leaving it empty means an
    #: agent reloads unfitted and cannot act.
    LEARNED: tuple[str, ...] = ()

    def __init__(self, extra: Mapping[str, Any] | None = None) -> None:
        super().__init__(extra)
        #: answer string -> how often it was the gold answer in training
        self.action_prior: dict[str, float] = {}
        self.prior_floor = 1e-3
        #: the best parameter-free cheat on the training episodes, and how often
        #: it was right on episodes it was *not* chosen on
        self.shortcut: Shortcut | None = None
        self.shortcut_purity = 0.0
        self.confidence_map = ScoreCalibrator()

    # ---- fitting --------------------------------------------------------
    def fit(self, ctx: LearnContext) -> None:
        """Fit the shared prior, then whatever the subclass learns.

        The prior first and on the same episodes, so a subclass that consults it
        during :meth:`learn` sees the prior it will see at evaluation rather
        than an unfitted one — the same ordering
        :meth:`symbolic_ai_models.models.symbolic.RuleBasedModel.fit` uses for
        its parser.
        """
        self.tok = ctx.tok
        self._fit_prior(ctx.episodes)
        self.learn(ctx.episodes, ctx.tok)
        self._fitted = True

    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Read the training episodes and build whatever this agent reasons with."""

    def _fit_prior(self, episodes: Sequence[Episode]) -> None:
        """Two things: which answers are common, and which cheat works here.

        Both are measured on the training episodes and both are shared by every
        agent, so a difference between two agents is a difference in
        :meth:`prefer`.

        The shortcut's weight is its **purity** — how often it was right on
        episodes it was not selected on — rather than a constant. A flat weight
        was what the model harness tried first for the structural equivalent of
        this, and it cost the two best models several points of lift because a
        confident-but-ambiguous prior outranked a good vote. Purity settles it
        with data: a cheat that works speaks loudly, one that does not steps
        aside.
        """
        usable = [e for e in episodes if e.choices]
        counts: collections.Counter[str] = collections.Counter(
            e.answer.strip() for e in usable)
        total = sum(counts.values()) + 1.0
        self.action_prior = {k: v / total for k, v in counts.items()}
        self.prior_floor = 1.0 / total

        if len(usable) < 8:
            self.shortcut, self.shortcut_purity = None, 0.0
            return
        cut = max(int(len(usable) * 0.8), 1)
        fitting, held = usable[:cut], usable[cut:] or usable
        best, best_score = None, -1.0
        for shortcut in SHORTCUTS:
            hits = sum(shortcut.pick(e.prompt, list(e.choices)).strip()
                       == e.answer.strip() for e in fitting)
            score = hits / len(fitting)
            if score > best_score:
                best, best_score = shortcut, score
        # Purity measured on episodes the choice was *not* made from. The
        # in-sample version is a maximum over nine rules fitted on the same
        # data, so it overstates — and since this mass is the prior's own
        # confidence, overstating it makes a well-calibrated agent overconfident
        # without changing a single prediction.
        assert best is not None
        purity = sum(best.pick(e.prompt, list(e.choices)).strip()
                     == e.answer.strip() for e in held) / len(held)
        self.shortcut = best
        self.shortcut_purity = min(max(purity, 0.0), 0.9)

    # ---- the extension point --------------------------------------------
    def prefer(self, obs: Observation) -> Preference:
        """``({action: weight}, confidence)``. **The agent.**

        Weights need not be normalised and may name actions that are not legal
        here; those are dropped. Returning :data:`ABSTAIN` lands on the prior.
        """
        return ABSTAIN

    def confidence(self, raw: float) -> float:
        """The measured meaning of a raw score, or a cautious guess before fitting."""
        if self.confidence_map.fitted:
            return float(self.confidence_map(raw))
        return min(0.15 + 0.75 * max(raw, 0.0), 0.9)

    # ---- acting ---------------------------------------------------------
    def act(self, obs: Observation) -> Decision:
        legal = [a for a in obs.choices if a not in self._refused]
        if not legal:
            # Everything has been refused, which the horizon should have
            # prevented. Fall back to the full set rather than crashing: a
            # crashed agent scores nothing and a repeated wrong answer scores
            # zero, and only one of those is a measurement.
            legal = list(obs.choices)
        if not legal:
            return Decision(action="", confidence=0.0, why="no legal action")

        table, raw = self.prefer(obs)
        votes = {a: float(w) for a, w in table.items() if a in set(legal) and w > 0}
        conf = min(max(float(raw), 0.0), 1.0) if votes else 0.0
        prior = self._prior_over(obs, legal)

        mass = sum(votes.values()) or 1.0
        mixed = {a: (1.0 - conf) * prior.get(a, 0.0)
                    + conf * votes.get(a, 0.0) / mass for a in legal}
        # First maximum wins, so "no signal" resolves by the environment's own
        # ordering for every agent alike. Breaking ties on the action string
        # would make unrelated agents agree by accident — the argument
        # `symbolic_ai_models.shortcuts._argmax` makes about inflated floors.
        best = legal[0]
        for action in legal[1:]:
            if mixed[action] > mixed[best]:
                best = action
        total = sum(mixed.values()) or 1.0
        return Decision(action=best, confidence=mixed[best] / total,
                        why=self.explain(obs, best, votes, conf))

    def explain(self, obs: Observation, action: str,
                votes: Mapping[str, float], conf: float) -> str:
        """One line for the trace. Overridden by agents with more to say."""
        if not votes:
            source = f"prior ({self.shortcut.name})" if self.shortcut else "prior"
            return f"abstained -> {source}"
        return f"{len(votes)} preferences at {conf:.2f}"

    def shortlist(self, obs: Observation, options: Sequence[str],
                  max_actions: int) -> list[str]:
        """The ``max_actions`` candidates worth paying for, ranked by the prior.

        Lifted here from :class:`~symbolic_ai_agents.agents.wrapped.WrappedModel`,
        where it began, because a *second* agent now needs the identical
        handicap and two near-copies of a shortlist rule would be the same
        mistake :func:`~symbolic_ai_agents.envs.base.reference_floor` records
        about two near-copies of a floor: they drift, and nothing notices. The
        point of the rule is that it is **agent-independent** — ranked by the
        shared prior rather than by anything the caller knows — so two agents
        given the same cap face the same eight strings and the difference
        between their rows is their mechanism.

        ``max_actions <= 0`` means no cap, which is the honest spelling of "this
        agent does not pay per candidate".
        """
        opts = list(options)
        if max_actions <= 0 or len(opts) <= max_actions:
            return opts
        prior = self._prior_over(obs, opts)
        return sorted(opts, key=lambda a: (-prior.get(a, 0.0),
                                           opts.index(a)))[:max_actions]

    def _prior_over(self, obs: Observation, legal: Sequence[str]) -> dict[str, float]:
        """The floor, as a distribution over exactly these actions.

        Answer frequency, normalised, with :attr:`shortcut_purity` of the mass
        moved onto whatever the best cheat picks. With ``use_prior`` off this is
        uniform, which is what makes ``random`` a real chance baseline rather
        than a quietly informed one.
        """
        if not self.use_prior:
            return {a: 1.0 / len(legal) for a in legal}
        base = {a: self.action_prior.get(a.strip(), self.prior_floor)
                for a in legal}
        total = sum(base.values()) or 1.0
        out = {a: v / total for a, v in base.items()}
        if self.shortcut is not None and self.shortcut_purity > 0.0 and obs.actions:
            try:
                picked = self.shortcut.pick(obs.text, list(obs.actions))
            except (ValueError, IndexError):              # pragma: no cover
                return out
            if picked in out:
                share = self.shortcut_purity
                out = {a: v * (1.0 - share) for a, v in out.items()}
                out[picked] += share
        return out

    # ---- calibration ----------------------------------------------------
    def calibrate_on(self, scores: Sequence[float],
                     correct: Sequence[bool]) -> None:
        """Fit :attr:`confidence_map` from held-out outcomes.

        The caller supplies the outcomes because only it knows which episodes
        were held out. A map fitted on the episodes the agent was fitted from
        certifies its overconfidence instead of removing it — stated at length
        in :class:`symbolic_ai_models.calibration.ScoreCalibrator`, and true here
        for the same reason.
        """
        self.confidence_map = ScoreCalibrator().fit(list(scores), list(correct))

    def n_parameters(self) -> int:
        return len(self.action_prior) + (1 if self.shortcut else 0)


# ---------------------------------------------------------------------------
# fitting-time access to the answers
# ---------------------------------------------------------------------------
def training_views(env: Environment, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> "Iterator[tuple[Observation, str | None]]":
    """``(observation, correct action)`` pairs, teacher-forced through ``env``.

    The counterpart of
    :meth:`symbolic_ai_models.models.symbolic.RuleBasedModel.training_views`,
    and it exists for the same reason: an agent that fits its statistics on
    *whole* observations and is then asked about the ones it will actually face
    has a train/test mismatch. So fitting goes through the very environment
    evaluation goes through, and whatever an agent can read here it can read
    when it is scored.

    Teacher-forced on purpose. The environment is advanced with the correct
    action at every step, so the observations are the ones that follow a perfect
    history — which is exactly what a *training set* is, and exactly what
    :mod:`symbolic_ai_agents.envs.repair` then removes at evaluation time. An
    agent fitted here and scored there is being asked whether what it learned
    survives its own mistakes, which is the question this package is for.

    **This is the only place the answers are available.** It reads
    :meth:`~symbolic_ai_agents.envs.base.Environment.oracle`, which is legal
    during ``fit`` on training episodes and is cheating anywhere else. Rather
    than ask agents not to peek, ``tests/test_agent_leaks.py`` checks it
    empirically: an agent's decisions must be bit-identical when every
    environment's ``oracle`` is replaced by a liar.
    """
    for ep in episodes:
        obs = env.reset(ep, tok=tok)
        for _ in range(max(env.horizon, 1)):
            gold = env.oracle()
            yield obs, gold
            if gold is None:
                break
            step = env.step(gold)
            if step.done or step.next_obs is None:
                break
            obs = step.next_obs


def held_out(episodes: Sequence[Episode], fraction: float = 0.8
             ) -> tuple[Sequence[Episode], Sequence[Episode]]:
    """Split training episodes for a two-pass fit. Never touches evaluation."""
    cut = max(int(len(episodes) * fraction), 1)
    return episodes[:cut], (episodes[cut:] or episodes)


def shuffled(episodes: Sequence[Episode], seed: int = 0) -> list[Episode]:
    """A stable shuffle, for agents that learn from their own rollouts and
    should not see one lesson's episodes in a block."""
    out = list(episodes)
    random.Random(seed).shuffle(out)
    return out
