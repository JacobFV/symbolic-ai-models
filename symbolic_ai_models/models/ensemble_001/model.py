"""Two reasoners, combined in log space, with the combination fitted.

`ROADMAP.md` rejected ensembling and the rejection was right about the question
it asked. A *perfect selector* over the four pointers reaches 0.397 copy accuracy
against `corefer` alone at 0.306, while re-ranking `corefer`'s own candidates has
0.549 reachable — so for the **copy head**, ensembling has the smaller ceiling
and was correctly passed over.

That argument does not transfer to the **label head**, and the reason is the
finding that prompted this model. Ranked by accuracy and by bits, the models in
this repo come out close to inverted: `grammar` is 14th on label accuracy and
1st on label bits; `corefer` is 1st and 6th. Those two are not making the same
mistakes — they are barely doing the same job — and an ensemble is paid in
exactly the currency where they differ. Every ensemble the roadmap considered
was pointer-with-pointer, four models that fail on the same positions because
they read the same structure. Diversity is what an ensemble buys, and that set
had none.

The renaming column is the sharpest evidence that the diversity is real:
`corefer` loses 0.003 accuracy when every symbol in the corpus is permuted and
`grammar` loses 0.159. One is reading structure and the other is reading
vocabulary. They are the most orthogonal pair the repo has.

How the combination is expressed
--------------------------------
A geometric (log-linear) mixture, not an arithmetic one::

    p(v)  proportional to  p_a(v)^w * p_b(v)^(1-w)

Geometric because it is *conjunctive*: a symbol has to be plausible to both
models to survive, so the combination sharpens where they agree instead of
smearing across both opinions. An arithmetic mixture cannot be worse than its
best component and cannot be much better either; a product can be both, which
makes it the one worth measuring.

The awkward part is that the interface passes ``(votes, confidence)`` and the
harness turns that into ``(1 - c) * backoff + c * votes`` over 8,192 symbols.
Normalising a product over that vocabulary looked like it needed a dense pass
per node. It does not, and the reason is worth writing down because it makes the
whole thing exact rather than approximate: **outside the union of the two
models' support, both components are just scaled copies of the same back-off**,
so their product is too. Writing ``S`` for the union support and
``K = (1-c_a)^w * (1-c_b)^(1-w)``::

    v not in S:   u(v) = K * backoff(v)
    v in S:       u(v) = p_a(v)^w * p_b(v)^(1-w)
    Z           = sum_S u + K * (1 - sum_S backoff)

and then ``c = 1 - K/Z`` with ``votes(v) = (u(v) - K*backoff(v)) / Z`` reproduces
``u/Z`` exactly through the existing mixture. Only the union support is ever
touched. The algebra is checked in the tests against a dense reference rather
than trusted.

``w`` is fitted on held-out training episodes by minimising negative
log-likelihood over a grid. One parameter, so a grid is honest and a search
would be false precision — the same argument the temperature scaling in
``symbolic.py`` makes.

**What would refute this.** If the fitted ``w`` lands at 0 or 1, one model is
carrying everything and the ensemble is a slower way to run it. If it lands near
0.5 and the score sits between the two components, the product is smearing
rather than sharpening. Both are reportable outcomes and neither is a bug.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import build as build_model
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["EnsembleModel", "MixedEnsemble", "PointerEnsemble"]

#: Where ``w`` is searched. Endpoints included on purpose: "one of them is
#: carrying this entirely" has to be a reachable answer, not one the grid
#: forbids.
GRID = tuple(i / 20.0 for i in range(21))


class EnsembleModel(RuleBasedModel):
    """A geometric mixture of two fitted rule-based models."""

    LEARNED = ("weight", "member_state")
    #: ``(name, name)``. Subclasses name their pair; nothing else differs.
    members: tuple[str, str] = ("ptrgen-001", "grammar-001")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.parts = [build_model(name, cfg) for name in self.members]
        self.weight = 0.5
        self.member_state: list[dict] = []

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Fit both members on the same episodes, then fit the weight between.

        Both see the whole training set rather than half each. Splitting would
        make each member weaker than its own registered row and the comparison
        against those rows meaningless — the question is what combining *these
        two models* is worth, not what combining two smaller ones would be.
        """
        for part in self.parts:
            part.fit_on(episodes, tok)
        self._fit_weight(episodes, tok)
        self.member_state = [p.symbolic_state() for p in self.parts]

    def _fit_weight(self, episodes: Sequence[Episode],
                    tok: SymbolTokenizer) -> None:
        cut = max(int(len(episodes) * 0.8), 1)
        held_out = episodes[cut:] or episodes
        rows: list[tuple[dict, dict, int, float]] = []
        for view, targets in self.training_views(held_out, tok, repeats=1,
                                                 seed=11,
                                                 max_nodes=self.cfg.max_nodes):
            per_model = [p.node_votes(view) for p in self.parts]
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                a = per_model[0].get(node, (ABSTAIN, ABSTAIN))[0]
                b = per_model[1].get(node, (ABSTAIN, ABSTAIN))[0]
                rows.append((a, b, int(label_id),
                             self.backoff_prob(view, node, int(label_id))))
        if not rows:
            return
        best_w, best_nll = 0.5, math.inf
        for w in GRID:
            nll = 0.0
            for a, b, gold, backoff in rows:
                votes, c = self._combine(a, b, w, backoff, gold)
                total = sum(votes.values()) or 1.0
                p = (1.0 - c) * backoff + c * votes.get(gold, 0.0) / total
                nll -= math.log(max(p, 1e-12))
            if nll < best_nll:
                best_w, best_nll = w, nll
        self.weight = best_w

    # ---- the algebra ---------------------------------------------------
    def _combine(self, a: Votes, b: Votes, w: float, backoff_gold: float,
                 gold: int) -> tuple[dict[int, float], float]:
        """``(votes, c)`` reproducing the normalised product exactly.

        ``backoff_gold`` and ``gold`` are threaded through only so the gold
        symbol's back-off value is available when it lies outside the union
        support; every other symbol's back-off is read from the shared table.
        """
        table_a, c_a = a if a else ({}, 0.0)
        table_b, c_b = b if b else ({}, 0.0)
        support = set(table_a) | set(table_b)
        if not support:
            return {}, 0.0

        sum_a = float(sum(table_a.values())) or 1.0
        sum_b = float(sum(table_b.values())) or 1.0
        base = {v: float(self.symbol_backoff[v].exp()) for v in support}
        if gold not in base:
            base[gold] = backoff_gold

        k = ((1.0 - c_a) ** w) * ((1.0 - c_b) ** (1.0 - w))
        unnormalised: dict[int, float] = {}
        for v in support:
            pa = (1.0 - c_a) * base[v] + c_a * table_a.get(v, 0.0) / sum_a
            pb = (1.0 - c_b) * base[v] + c_b * table_b.get(v, 0.0) / sum_b
            unnormalised[v] = (max(pa, 1e-300) ** w) * (max(pb, 1e-300) ** (1.0 - w))

        mass_support = sum(base[v] for v in support)
        z = sum(unnormalised.values()) + k * max(1.0 - mass_support, 0.0)
        if z <= 0.0:
            return {}, 0.0
        c = 1.0 - k / z
        if c <= 0.0:
            return {}, 0.0
        votes = {v: max(unnormalised[v] - k * base[v], 0.0) / z for v in support}
        if sum(votes.values()) <= 0.0:
            return {}, 0.0
        return votes, min(c, 0.999)

    # ---- prediction ----------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        per_model = [p.node_votes(view) for p in self.parts]
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            a_label, a_type = per_model[0].get(i, (ABSTAIN, ABSTAIN))
            b_label, b_type = per_model[1].get(i, (ABSTAIN, ABSTAIN))
            votes, c = self._combine(a_label, b_label, self.weight, 0.0, -1)
            # The type head takes the member that was surer rather than a
            # product. Type is nearly a function of tree shape here and the two
            # members' type heads are not independent evidence about it; a
            # product of two copies of the same lookup is that lookup, stated
            # twice as confidently.
            type_vote = a_type if (a_type and a_type[1]) >= (b_type and b_type[1]) \
                else b_type
            out[i] = ((votes, c) if votes else ABSTAIN, type_vote or ABSTAIN)
        return out

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        """Whichever member states bindings; the first that does, wins.

        Not combined. A pointer's output is a distribution over *node indices*
        and two models' indices mean the same thing only by coincidence of the
        graph — combining them is a different piece of work than combining
        distributions over symbols, and doing it silently here would make the
        copy column uninterpretable.
        """
        for part in self.parts:
            votes = part.source_votes(view)
            if votes:
                return votes
        return {}

    # ---- bookkeeping ----------------------------------------------------
    def load_symbolic_state(self, state, tok) -> None:
        super().load_symbolic_state(state, tok)
        for part, saved in zip(self.parts, self.member_state or []):
            part.load_symbolic_state(saved, tok)

    def n_symbolic_parameters(self) -> int:
        return sum(p.n_symbolic_parameters() for p in self.parts) + 1

    def render(self) -> str:
        lines = [f"=== {self.name}: {' x '.join(self.members)} ===",
                 f"  weight w = {self.weight:.2f} on {self.members[0]}, "
                 f"{1 - self.weight:.2f} on {self.members[1]}"]
        if self.weight in (0.0, 1.0):
            lines.append("  !! the grid landed on an endpoint: one member is "
                         "carrying this entirely")
        for part in self.parts:
            lines.append(f"  --- {part.name} ---")
            lines.append("\n".join("    " + line
                                   for line in part.render().splitlines()[:6]))
        return "\n".join(lines)


@register("ensemble-001",
          doc="Geometric mixture of a structural pointer and a vocabulary model.")
class MixedEnsemble(EnsembleModel):
    """``ptrgen`` x ``grammar``: the most orthogonal pair the repo has.

    Chosen on the renaming column rather than on the leaderboard. ``ptrgen``
    loses almost nothing when every symbol is permuted and ``grammar`` loses
    0.159, so they are reading different things, and the accuracy/bits ranking
    inversion says they are also failing in different places.
    """

    members = ("ptrgen-001", "grammar-001")


@register("ensemble-pointers",
          doc="Geometric mixture of two pointers, as the diversity control.")
class PointerEnsemble(EnsembleModel):
    """``ptrgen`` x ``corefer``: the ensemble the roadmap argued against.

    Registered as the control that makes the other row mean something. These
    two are both pointers over the same features and should be highly
    correlated, so if this scores level with ``ensemble-001`` the gain is coming
    from combination as such and not from the diversity the argument rests on.
    """

    members = ("ptrgen-001", "corefer-001")
