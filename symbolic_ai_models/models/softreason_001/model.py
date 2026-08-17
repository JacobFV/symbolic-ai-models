"""A soft immediate-consequence operator, run to a fixpoint.

Every rule-based model in this repo answers a masked node with *one symbol plus
a scalar*, and the harness spends that scalar as ``(1 - c) * backoff + c *
votes``. The scalar is an afterthought in all of them: it is fitted as an argmax
accuracy, or set by a hand-written ``0.15 + 0.8 * purity``, and then asked to
serve as the weight of a two-component mixture, which is a different quantity.
``notes/lessons/2026-08-13-a-ranking-is-a-property-of-a-metric.md`` is the bill
for that — ``label_acc`` and ``label_bits`` rank these models close to inversely,
and the models that top the accuracy table sit in the middle of the bits table.

This model is the other end of the argument, adapted from SoftReason
(arXiv:2607.20402). It never forms an answer. It computes a **distribution over
conclusions** as its native output, because that is what logical closure under a
soft consequence operator produces.

The construction
----------------

Per episode, the Herbrand base is ``label(i) = v`` for each node ``i`` and each
symbol ``v`` occurring anywhere in that episode. Nothing outside the episode's
own vocabulary is derivable; inventing a symbol is the shared back-off's job,
and 88.5% of the labels the symbol head cannot score are invented ``ident``
names anyway.

Ground facts are the visible nodes, at truth 1.0. The program has one rule
schema::

    label(i) = v   <--_{r}   label(j) = v        when pattern(i, j) = pi

read as: whatever ``j`` says, ``i`` says too, with reliability ``r_pi``. The
reliability is fitted by counting — how often that structural pattern actually
joined two nodes carrying the same symbol — shrunk down a back-off ladder
towards the global rate, so a pattern seen four times does not get to claim
certainty.

The immediate-consequence operator uses the **product** t-norm on the body and
**noisy-OR** over derivations::

    t_{n+1}(i, v) = 1 - prod_j [ 1 - r_{pi(i,j)} * t_n(j, v) ]

which is monotone in ``t_n`` and bounded above by 1, so iterating it from the
ground facts converges. It is iterated to a fixpoint rather than applied once,
and that is the whole point of building it:

* **round 1** consults only the visible nodes. This is one-hop copying — what
  ``corefer`` and ``ptrgen`` already do, in different notation.
* **rounds 2+** let a *hidden* node's derived mass enter another hidden node's
  body. Two masked siblings of a masked head are joined through a conclusion
  that was itself only ever derived. Nothing else in this registry does that;
  every other pointer here scores candidates against the visible set and stops.

Noisy-OR rather than a max is deliberate and is the second half of the claim:
three mediocre routes to one conclusion should outrank one mediocre route, and
under ``max`` they are indistinguishable. Product rather than Lukasiewicz for
the body because ``max(0, a + b - 1)`` with reliabilities well under 1 derives
nothing at all and the model degenerates into an abstention.

The readout
-----------

The fixpoint mass over symbols *is* the vote table. There is no argmax step
anywhere in :meth:`node_votes`. The gate ``c`` is fitted by
:class:`~symbolic_ai_core.calibration.MassCalibrator` on episodes the rules were
not fitted from — maximising the held-out likelihood of whichever symbol turned
out to be right, which is the quantity the mixture is actually asking for, and
which credits a model for spreading belief across several plausible conclusions
instead of scoring that as being unsure.

What this model does **not** get is a unary ``label(i) = v <- context(i)`` rule.
The base class already fits exactly that lookup into the back-off every model
falls to, so voting it here would be scoring the back-off under this model's
name — see
``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md``.

The type head is ``corefer``'s backed-off structural lookup, imported rather
than re-derived, so that any difference in the label column is attributable to
the label machinery and not to one model happening to have a better type head.
Type is nearly a function of tree shape here and a consequence operator over
coreference is a poor way to ask about kind.

Registered variants, one axis each::

    softreason-001    fixpoint (up to 4 rounds), mass-calibrated gate
    softreason-onehop the same rules and the same gate, operator applied ONCE

``softreason-onehop`` is the control that makes the closure readable. Without it
there is no way to say whether iterating to a fixpoint bought anything or
whether this is a pointer with unusual arithmetic; the two rows differ in the
iteration cap and in nothing else.
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

from symbolic_ai_core.calibration import MassCalibrator
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..corefer_001.model import _relation, _type_keys
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["SoftReasonModel", "SoftReason001", "SoftReasonOneHop"]


def _pattern(view: GraphView, i: int, j: int) -> tuple:
    """The structural pattern of the ordered pair ``(i, j)``, most specific.

    Reads nothing about ``i``'s own label — which is the answer — and nothing
    about ``j``'s either, so the same pattern applies whether ``j`` is a visible
    fact or a hidden node carrying derived mass. That symmetry is what lets the
    operator iterate at all: a rule whose body could only be checked against a
    visible node would have nothing to fire on in round two.
    """
    delta = i - j
    dist = min(int(math.log2(abs(delta))) if delta else 0, 6)
    p = view.parent[i]
    ptype = (view.types[p] if p >= 0 and view.types[p] else "ROOT")
    return (_relation(view, i, j), dist, delta > 0, ptype, min(view.slot[i], 6))


def _ladder(key: tuple) -> list[tuple]:
    """``_pattern``'s back-off chain, most specific first.

    A reliability is a probability estimated from counts, and the specific
    patterns are exactly the ones with too few counts to estimate it from. The
    chain is shrinkage, not a fallback: every level contributes, weighted by how
    much evidence it has.
    """
    rel, dist, direction, ptype, slot = key
    return [key, (rel, dist, direction), (rel, direction), (rel,)]


class SoftReasonModel(RuleBasedModel):
    """Weighted implications, closed under a soft ``T_P``."""

    LEARNED = ("reliability", "global_rate", "gate_map", "type_rules",
               "n_pairs", "rounds_used")

    #: How many times the operator may be applied. The fixpoint is usually
    #: reached in two or three; the cap exists so a pathological episode cannot
    #: spin. ``softreason-onehop`` sets it to 1.
    max_rounds = 4

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_rounds = int(cfg.get("max_rounds", type(self).max_rounds))
        #: Candidate bodies scored per hidden node, nearest first in the
        #: linearisation. Truncation is by structural distance, which is
        #: content-blind and so cannot smuggle the answer in.
        self.max_bodies = int(cfg.get("max_bodies", 48))
        #: Atoms kept per node between rounds. The tail of a Herbrand base is
        #: derived mass under 1e-3 that cannot change an argmax or a bit.
        self.max_atoms = int(cfg.get("max_atoms", 16))
        #: A rule this unreliable contributes less than the numerical noise of
        #: the noisy-OR and costs a multiply per pair per round.
        self.min_reliability = float(cfg.get("min_reliability", 0.02))
        #: Fixpoint tolerance: stop when no atom moved by more than this.
        self.tol = float(cfg.get("tol", 1e-3))
        self.max_views = int(cfg.get("max_views", 4000))
        self.min_support = int(cfg.get("min_support", 5))

        #: pattern -> reliability in [0, 1]
        self.reliability: dict[tuple, float] = {}
        self.global_rate = 0.0
        self.gate_map = MassCalibrator()
        self.type_rules: dict[tuple, collections.Counter] = {}
        self.n_pairs = 0
        #: Diagnostic: how many operator rounds the last predictions needed.
        self.rounds_used: collections.Counter = collections.Counter()

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        cut = max(int(len(episodes) * 0.8), 1)
        self._fit_rules(episodes[:cut], tok)
        # The gate is fitted on episodes the rules were not fitted from. A
        # fixpoint scored on its own training episodes looks sharper than it is,
        # and the gate would then hand that sharpness the mass to act on.
        self._fit_gate(episodes[cut:] or episodes, tok)
        self._fit_types(episodes, tok)

    def _fit_rules(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """Count how often each pattern joined two nodes with the same symbol.

        Only pairs whose *body* node is visible are counted, because those are
        the only pairs where both labels are known at fitting time. The estimate
        transfers to a hidden body by construction: ``_pattern`` reads no label,
        so the pattern's meaning does not depend on which side is masked.
        """
        hits: collections.Counter = collections.Counter()
        seen: collections.Counter = collections.Counter()
        total_hit = total_seen = 0
        views = 0
        for view, targets in self.training_views(episodes, tok, repeats=2,
                                                 max_nodes=self.cfg.max_nodes):
            views += 1
            if views > self.max_views:
                break
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                for j in self._bodies(view, node):
                    if view.labels[j] is None:
                        continue
                    same = int(view.labels[j]) == int(label_id)
                    total_seen += 1
                    total_hit += same
                    for key in _ladder(_pattern(view, node, j)):
                        seen[key] += 1
                        hits[key] += same
        self.n_pairs = total_seen
        self.global_rate = total_hit / max(total_seen, 1)

        # Shrinkage down the ladder: each level starts from its parent's
        # estimate and is pulled towards its own counts by how many it has.
        # A pattern seen four times therefore states almost exactly what its
        # coarser parent states, which is the honest reading of four counts.
        prior_strength = 20.0
        for key in sorted(seen, key=len):
            parent = _ladder(key)[1] if len(key) == 5 else None
            base = self.reliability.get(parent, self.global_rate) \
                if parent is not None else self.global_rate
            n = seen[key]
            if n < self.min_support:
                continue
            self.reliability[key] = ((hits[key] + prior_strength * base)
                                     / (n + prior_strength))

    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        """Fit ``c`` as the mixture weight it is, by held-out likelihood.

        Every scorable node contributes, including the ones where the operator
        derives nothing on the truth -- those are precisely the evidence that
        the conclusion set is sometimes wrong to trust, and dropping them would
        fit a gate for a task in which closure always succeeds.
        """
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(episodes, tok, repeats=1,
                                                 seed=7,
                                                 max_nodes=self.cfg.max_nodes):
            closure = self._closure(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                mass = closure.get(node)
                if not mass:
                    continue
                total = sum(mass.values())
                if total <= 0.0:
                    continue
                scores.append(max(mass.values()) / total)
                votes.append(float(mass.get(int(label_id), 0.0)) / total)
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        self.gate_map = MassCalibrator().fit(scores, votes, backoff)

    def _fit_types(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """``corefer``'s backed-off structural lookup, imported wholesale."""
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes, tok, repeats=2,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (_, type_id) in targets.items():
                if type_id < 0:
                    continue
                for key in _type_keys(view, node, None):
                    counts[key][int(type_id)] += 1
        self.type_rules = dict(counts)

    # ---- the operator --------------------------------------------------
    def _bodies(self, view: GraphView, node: int) -> list[int]:
        """Which nodes may appear in a rule body for ``node``.

        Every other node is legal; the cap is on cost. Ordered by distance in
        the linearisation, which is a fact about shape, so the candidate set
        cannot depend on the truth values being computed and an episode cannot
        change shape between rounds.
        """
        pool = [j for j in range(len(view)) if j != node]
        if len(pool) <= self.max_bodies:
            return pool
        pool.sort(key=lambda j: (abs(j - node), j))
        return sorted(pool[:self.max_bodies])

    def _closure(self, view: GraphView) -> dict[int, dict[int, float]]:
        """Iterate ``T_P`` from the ground facts to a fixpoint.

        Returns ``{hidden node: {symbol: truth}}`` -- unnormalised soft truth
        values, which the caller normalises into the distribution it needs. The
        visible nodes are not in the result because their atoms are facts, not
        conclusions.
        """
        hidden = list(view.hidden)
        if not hidden or not self.reliability:
            return {}
        hidden_set = set(hidden)

        # Rule instances, resolved once: for each head, the bodies that can
        # reach it and with what reliability. Patterns are structural, so this
        # is constant across rounds and is the expensive part.
        rules: dict[int, list[tuple[int, float]]] = {}
        for i in hidden:
            row: list[tuple[int, float]] = []
            for j in self._bodies(view, i):
                r = self._reliability_of(view, i, j)
                if r >= self.min_reliability:
                    row.append((j, r))
            rules[i] = row

        # Ground facts. A visible node asserts its own symbol at truth 1.
        facts: dict[int, int] = {j: int(v) for j, v in enumerate(view.labels)
                                 if v is not None}
        state: dict[int, dict[int, float]] = {i: {} for i in hidden}

        rounds = 0
        for _ in range(max(self.max_rounds, 1)):
            rounds += 1
            moved = 0.0
            nxt: dict[int, dict[int, float]] = {}
            for i in hidden:
                # Noisy-OR accumulated as a product of complements, so a symbol
                # supported by several bodies is more strongly concluded than
                # one supported by the best of them alone.
                complement: dict[int, float] = {}
                for j, r in rules[i]:
                    if j in hidden_set:
                        for v, t in state[j].items():
                            body = r * t
                            if body > 0.0:
                                complement[v] = complement.get(v, 1.0) * (1.0 - body)
                    else:
                        v = facts.get(j)
                        if v is not None:
                            complement[v] = complement.get(v, 1.0) * (1.0 - r)
                mass = {v: 1.0 - c for v, c in complement.items() if c < 1.0}
                if len(mass) > self.max_atoms:
                    kept = sorted(mass.items(), key=lambda kv: (-kv[1], kv[0]))
                    mass = dict(kept[:self.max_atoms])
                old = state[i]
                for v, t in mass.items():
                    moved = max(moved, abs(t - old.get(v, 0.0)))
                for v in old:
                    if v not in mass:
                        moved = max(moved, old[v])
                nxt[i] = mass
            state = nxt
            if moved <= self.tol:
                break
        self.rounds_used[rounds] += 1
        return {i: m for i, m in state.items() if m}

    def _reliability_of(self, view: GraphView, i: int, j: int) -> float:
        """The strongest evidenced level of the pattern ladder for ``(i, j)``."""
        for key in _ladder(_pattern(view, i, j)):
            r = self.reliability.get(key)
            if r is not None:
                return r
        return self.global_rate

    # ---- prediction ----------------------------------------------------
    def _type_vote(self, view: GraphView, node: int) -> Votes:
        for key in _type_keys(view, node, None):
            counts = self.type_rules.get(key)
            if counts and sum(counts.values()) >= self.min_support:
                total = sum(counts.values())
                top, n = counts.most_common(1)[0]
                return {int(top): 1.0}, min(0.15 + 0.8 * n / total, 0.95)
        return ABSTAIN

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        """The fixpoint, emitted whole.

        There is no argmax here and that is the experiment. The conclusion mass
        goes out as the vote table -- the base class normalises it -- and the
        only scalar this model states is the gate, which is a claim about
        whether to trust the closure at all rather than a claim about which
        conclusion won.
        """
        closure = self._closure(view)
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            type_vote = self._type_vote(view, i)
            mass = closure.get(i)
            if not mass or not self.gate_map.fitted:
                out[i] = (ABSTAIN, type_vote)
                continue
            total = sum(mass.values())
            if total <= 0.0:
                out[i] = (ABSTAIN, type_vote)
                continue
            gate = float(self.gate_map(max(mass.values()) / total))
            out[i] = ((mass, gate) if gate > 0.0 else ABSTAIN, type_vote)
        return out

    def n_symbolic_parameters(self) -> int:
        return len(self.reliability) + len(self.type_rules)

    def render(self) -> str:
        rows = sorted(self.reliability.items(),
                      key=lambda kv: (-kv[1], str(kv[0])))[:20]
        lines = [f"=== {self.name}: {len(self.reliability)} weighted rules "
                 f"from {self.n_pairs} pairs, global rate "
                 f"{self.global_rate:.3f} ===",
                 f"gate: {'fitted' if self.gate_map.fitted else 'unfitted'}"]
        if self.gate_map.fitted:
            lines.append("  score -> mass: " + ", ".join(
                f"{e:.2f}->{v:.2f}"
                for e, v in zip(self.gate_map.edges, self.gate_map.values)))
        # The diagnostic that says whether the closure is decorative: if every
        # episode stops after one round, this is a pointer with odd arithmetic.
        if self.rounds_used:
            lines.append("  T_P rounds to fixpoint: " + ", ".join(
                f"{k}x{v}" for k, v in sorted(self.rounds_used.items())))
        lines.append("most reliable rule patterns:")
        lines += [f"  {str(k):<52} r={v:.3f}" for k, v in rows]
        return "\n".join(lines)


@register("softreason-001",
          doc="Soft T_P closure: weighted implications iterated to a fixpoint, "
              "emitting the conclusion distribution itself.")
class SoftReason001(SoftReasonModel):
    """The model described in this module's docstring."""


@register("softreason-onehop",
          doc="softreason with the consequence operator applied once, as a control.")
class SoftReasonOneHop(SoftReasonModel):
    """One line different: ``T_P`` is applied once instead of to a fixpoint.

    This is what makes the closure charged for its own effect. ``softreason-001``
    changes two things at once against every pointer in the registry -- the
    output being a distribution, and the derivation being iterated -- and without
    this row there is no way to say which of them moved the number. With
    ``max_rounds = 1`` no hidden node ever has mass when another hidden node's
    body reads it, so the operator sees only the ground facts and the model
    reduces to soft one-hop copying with the identical gate.
    """

    max_rounds = 1
