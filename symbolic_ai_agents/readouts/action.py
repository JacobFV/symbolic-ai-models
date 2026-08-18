"""``action``: the same graph emission, read as a thing to *do*.

The third member of the family in :mod:`symbolic_ai_core.readout`, and the one
that comes at the representation from a different direction on purpose. ``symbol``
and ``site`` both score a model against a target computed from the answer key;
this one hands the model's emission to an
:class:`~symbolic_ai_agents.envs.base.Environment` and asks it to *choose*. A
representation that only works for one readout has been short-circuited, and the
agent side is how that gets found out.

The symptom it was written for is documented in the module it sits beside.
:mod:`symbolic_ai_agents.agents.wrapped` says, under "Three honest limits", that
**the graph head is not used**: ``repair`` hands ``wrap`` a
:class:`~symbolic_ai_core.graphview.GraphView` and ``wrap`` ignores it, scoring
the rendered s-expression as text. That is exactly a representation reachable
through one readout and no other, and no number in the repo could have shown it,
because nothing had ever asked the graph head a question phrased as an action.

What it reads
-------------

Two channels, both of them already emitted by
:class:`~symbolic_ai_models.models.symbolic.RuleBasedModel` and neither of them
new:

``symbol``
    ``node_votes(view)[node]`` — ``({vocabulary id: weight}, confidence)``. Each
    id is spelled with ``tok.itos`` and kept if the environment offered it as a
    legal action. "Name it" restricted to a 24-way stated set instead of an
    8,192-way vocabulary.
``node``
    ``source_votes(view)[node]`` — ``({node index: weight}, confidence)``. Each
    index is resolved to *the label that node carries* (``view.word(j)``) and
    kept if that is a legal action. **The pointer read as an action**: "the
    answer here is whatever that node says" becomes "do what that node says".
``both``
    each channel normalised to unit mass and then summed, so neither can
    outvote the other by having more candidates.

Which one is used is a **knob** (``ActionReadout(channel=...)``, or
``extra.channel`` on the agent), and that is the whole reason this readout is
worth having rather than a method on the agent. Two rows differing only in the
channel measure the readout; two rows differing in the model measure the models.
Welding the channel into the code would have made only the second comparison
possible, which is the mistake the readout registry exists to stop.

Why several nodes' weight lands on one action
---------------------------------------------

Because a pointer is scored by **what it picked, never by index** — the rule
:mod:`symbolic_ai_core.readout` states once for both pointer channels and that
``_pointer_counts`` established. Several visible nodes routinely carry the same
label, so a reader that split its mass across three nodes spelling ``frank`` has
not been unsure about the answer; it has been unsure about the evidence. Their
weights are therefore **summed onto the action string**, and a pointer that
hedges between equivalent sources is as confident as one that did not.

What is deliberately not here
-----------------------------

* **No back-off of its own.** ``RuleBasedModel._forward_graph`` mixes votes
  against ``structural_fallback`` and the context prior before anything sees
  them; that happens in the *model harness's* readout and not here. In this
  package the thing an abstention falls to is
  :meth:`~symbolic_ai_agents.agents.base.PolicyAgent._prior_over` — the shared
  prior every agent falls to — so two agents differ in their mechanism and not
  in what they degrade to. Adding a second back-off here would have made
  ``graphread``'s abstention land somewhere no other agent lands, and the
  difference between the rows would then be measuring the back-off.
* **No text fallback.** A readout that quietly switched to scoring text where
  the graph was absent would produce a row that is a measurement of neither.
  Absent graph means :data:`~symbolic_ai_core.graphview.ABSTAIN_ACTION`.

The floor
---------

:func:`symbolic_ai_agents.envs.base.reference_floor`, reused rather than
re-derived. The best of ``random``, ``shortcut`` and ``context``, fitted on the
training episodes and **run in the environment**, with ``floor_by`` naming the
winner. A readout without its own fitted floor is not a result — and a *second*
floor computed near-identically beside an existing one is worse than none, since
the two drift and nothing notices. This repo has already published a lift over a
floor 0.065 too low.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from symbolic_ai_core.floors import Totals
from symbolic_ai_core.graphview import (ABSTAIN_ACTION, GraphView, Preference,
                                        Votes)
from symbolic_ai_core.readout import NODE, SYMBOL, HasChannels, Readout, register

from ..envs.base import Environment, Observation

__all__ = ["ActionReadout", "Emission", "Asked", "BOTH", "CHANNEL_CHOICES",
           "emit"]

#: Both channels, each normalised to unit mass and then summed. Not a third
#: channel of :mod:`symbolic_ai_core.readout` — it is a *setting of this
#: readout*, which is why it is spelled here and not there.
BOTH = "both"

CHANNEL_CHOICES: tuple[str, ...] = (SYMBOL, NODE, BOTH)


@dataclass(frozen=True)
class Emission:
    """A rule-based model's graph-valued output, in the shape a readout reads.

    Structurally a :class:`~symbolic_ai_core.readout.HasChannels`, which is what
    lets this readout be unit-tested against a hand-built stub instead of
    against a fitted model. ``channels[SYMBOL]`` and ``channels[NODE]`` are
    ``{node index: Votes}``; a channel the model does not emit is simply absent,
    and absent is **unscored**, never zero.
    """

    channels: Mapping[str, Mapping[int, Votes]] = field(default_factory=dict)


@dataclass(frozen=True)
class Asked:
    """One decision and what the right answer was — this readout's ``batch``.

    :meth:`~symbolic_ai_core.readout.Readout.score` takes ``(output, batch)``
    and leaves ``batch`` untyped precisely so that each readout can name the
    surface its answer space lives on: ``symbol`` consumes a ``SymbolicBatch``,
    ``site`` consumes one too, and an action lives on an environment step. The
    gold action comes from
    :meth:`~symbolic_ai_agents.envs.base.Environment.oracle` and is therefore
    available at **fitting time only** — scoring is an offline audit of the
    readout, not something the agent may do while acting.
    """

    obs: Observation
    gold: str | None = None


def emit(model: Any, view: GraphView) -> Emission:
    """Ask a rule-based model for both graph channels at once.

    Kept a free function rather than a method because it is the one part that
    knows about :mod:`symbolic_ai_models`, and a readout that could only be fed
    by that package would be a worse readout: anything that can produce
    ``{node: Votes}`` can be read here.
    """
    channels: dict[str, Mapping[int, Votes]] = {}
    node_votes = getattr(model, "node_votes", None)
    if callable(node_votes):
        labels = {i: v[0] for i, v in node_votes(view).items()}
        if labels:
            channels[SYMBOL] = labels
    source_votes = getattr(model, "source_votes", None)
    if callable(source_votes):
        pointer = source_votes(view)
        if pointer:
            channels[NODE] = pointer
    return Emission(channels=channels)


def _normalise(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {a: w / total for a, w in weights.items()} if total > 0 else {}


@register("action-001", channel=SYMBOL, prefix="action",
          doc="The graph emission read as a choice among an environment's actions.")
class ActionReadout(Readout):
    """TermGraph votes in, a preference over legal action strings out.

    ``channel`` is an instance attribute here rather than the class attribute
    :func:`~symbolic_ai_core.readout.register` sets, and deliberately so: the
    registered default names what the readout reads *unless told otherwise*, and
    the knob is what makes ``symbol`` versus ``node`` a measurement rather than
    a rewrite.
    """

    def __init__(self, channel: str = SYMBOL) -> None:
        if channel not in CHANNEL_CHOICES:
            raise ValueError(
                f"action: unknown channel {channel!r}; have {list(CHANNEL_CHOICES)}")
        #: shadows the class attribute set by ``@register``; this is the knob
        self.channel = channel

    # ---- reading --------------------------------------------------------
    def prefer(self, out: HasChannels, obs: Observation) -> Preference:
        """``({legal action: weight}, raw separation)``, or abstain.

        The second element is a **raw** score in ``[0, 1]``, not a calibrated
        confidence: how concentrated the surviving mass is, times the model's own
        stated confidence in the votes it produced. The agent passes it through
        a held-out :class:`~symbolic_ai_core.calibration.ScoreCalibrator`,
        because the measured lesson recorded there is that confidence derived
        from *how much structure was found* is the badly calibrated kind, and a
        readout has no way to know better.
        """
        view, node = obs.graph, obs.node
        if view is None or node < 0 or not obs.actions:
            return ABSTAIN_ACTION
        legal = set(obs.actions)

        parts: list[tuple[dict[str, float], float]] = []
        if self.channel in (SYMBOL, BOTH):
            got = self._symbol_votes(out, view, node, legal)
            if got is not None:
                parts.append(got)
        if self.channel in (NODE, BOTH):
            got = self._node_votes(out, view, node, legal)
            if got is not None:
                parts.append(got)
        if not parts:
            return ABSTAIN_ACTION

        merged: dict[str, float] = {}
        for weights, _ in parts:
            # Unit mass each before summing, so a channel offering twenty
            # candidates cannot outvote one offering two by sheer arithmetic.
            for action, w in _normalise(weights).items():
                merged[action] = merged.get(action, 0.0) + w
        merged = _normalise(merged)
        if not merged:
            return ABSTAIN_ACTION
        conf = sum(c for _, c in parts) / len(parts)
        return merged, min(max(max(merged.values()) * conf, 0.0), 1.0)

    def _symbol_votes(self, out: HasChannels, view: GraphView, node: int,
                      legal: set[str]) -> tuple[dict[str, float], float] | None:
        """Vocabulary ids, spelled and filtered to what the environment offered."""
        channel = out.channels.get(SYMBOL)
        if not channel or node not in channel:
            return None
        weights, conf = channel[node]
        itos = view.tok.itos
        votes: dict[str, float] = {}
        for sym, w in weights.items():
            if not 0 <= sym < len(itos) or w <= 0:
                continue
            word = itos[sym]
            if word in legal:
                votes[word] = votes.get(word, 0.0) + float(w)
        return (votes, float(conf)) if votes else None

    def _node_votes(self, out: HasChannels, view: GraphView, node: int,
                    legal: set[str]) -> tuple[dict[str, float], float] | None:
        """Node indices, resolved to the label each one carries.

        Summed onto the action string rather than kept per index — see the
        module docstring. A pointer hedging between three nodes that all say
        ``frank`` was never unsure about the answer.
        """
        channel = out.channels.get(NODE)
        if not channel or node not in channel:
            return None
        weights, conf = channel[node]
        votes: dict[str, float] = {}
        for j, w in weights.items():
            if not 0 <= j < len(view) or j == node or w <= 0:
                continue
            word = view.word(j)
            if word is not None and word in legal:
                votes[word] = votes.get(word, 0.0) + float(w)
        return (votes, float(conf)) if votes else None

    # ---- scoring --------------------------------------------------------
    def score(self, out: HasChannels, batch: Any) -> dict[str, float]:
        """Counts for one decision. ``batch`` is an :class:`Asked`.

        Three counts rather than two, because "did not speak" and "spoke wrongly"
        are different facts and one column cannot hold both — the same reason
        :class:`~symbolic_ai_core.readout.Readout` insists a model emitting
        nothing on a channel is unscored rather than scored as zero. Here the
        readout is asked about a decision that *was* posed, so the abstention is
        counted and reported as its own rate instead of being dropped.
        """
        asked: Asked = batch
        obs, gold = asked.obs, asked.gold
        if gold is None or not obs.actions:
            return {}
        votes, raw = self.prefer(out, obs)
        if not votes:
            return {"action_n": 1.0, "action_abstain": 1.0}
        # First maximum wins, in the environment's own ordering — the tie rule
        # `PolicyAgent.act` uses, so this column and the agent's own row cannot
        # disagree about which action the preference names.
        best = None
        for action in obs.actions:
            if action in votes and (best is None or votes[action] > votes[best]):
                best = action
        # Charged against uniform-over-legal at the readout's own raw score,
        # which is the agent's mixture with the prior replaced by the one
        # distribution that needs no fitting. No invented smoothing constant.
        n = len(obs.actions)
        p = (1.0 - raw) / n + raw * votes.get(gold, 0.0)
        return {"action_n": 1.0, "action_spoke": 1.0,
                "action_correct": float(best == gold),
                "action_nll": -math.log(max(p, 1e-12))}

    def summarize(self, totals: Totals) -> dict[str, float]:
        """Four numbers, and none of them is the other three.

        ``action_acc`` is accuracy **given that it spoke**; ``action_yield`` is
        the share of all posed decisions it got right, which is the quantity an
        agent's row actually reflects, since an abstention there lands on the
        prior rather than on nothing. Quoting only the first would let a readout
        that speaks 5% of the time and is right every one of those look like a
        solved problem.
        """
        n = totals.get("action_n", 0.0)
        if not n:
            return {}
        spoke = totals.get("action_spoke", 0.0)
        correct = totals.get("action_correct", 0.0)
        return {"action_acc": correct / spoke if spoke else float("nan"),
                "action_yield": correct / n,
                "action_speak": spoke / n,
                "action_bits": (totals.get("action_nll", 0.0) / spoke
                                / math.log(2)) if spoke else float("nan"),
                "action_n": float(n)}

    # ---- the floor ------------------------------------------------------
    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode], **kwargs: Any) -> dict[str, float]:
        """The environment's own reference floor, namespaced. Not a second one.

        ``kwargs`` must carry ``env``; ``envs`` and ``seed`` are passed straight
        through because :func:`~symbolic_ai_agents.envs.base.reference_floor`
        needs the reference policies fitted **exactly as the scored agent was**.
        Fitting them differently is not bookkeeping: it once produced a table in
        which ``context`` beat itself by 0.025 on ``repair``, the only positive
        number in it.

        The accuracy this readout reports is per *decision*, so the floor's
        matching quantity is the environment's own per-decision accuracy —
        ``label_acc`` where the environment reports one (``repair`` does), and
        ``success`` otherwise, which coincides with it wherever the horizon is 1.
        """
        from ..envs.base import reference_floor
        env: Environment | None = kwargs.get("env")
        if env is None:
            raise ValueError("action: floor() needs env=<Environment>; a readout "
                             "over an environment's actions has no floor without "
                             "the environment")
        got = reference_floor(env, episodes, tok, train,
                              envs=kwargs.get("envs"), seed=int(kwargs.get("seed", 0)))
        acc = got.get("label_acc")
        if not isinstance(acc, (int, float)) or acc != acc:
            acc = got.get("success", float("nan"))
        return {"action_acc": float(acc), "action_yield": float(acc),
                "action_return": float(got.get("return", float("nan"))),
                "action_floor_by": got.get("floor_by", "")}
