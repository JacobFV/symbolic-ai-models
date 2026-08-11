"""Structure mapping: answer by aligning this episode with a remembered one.

Gentner's structure-mapping theory, and Forbus's MAC/FAC retrieval, as a
predictor. The claim behind them is that analogy runs on *relational structure*
rather than on shared features: what makes two situations analogous is that the
relations line up, not that the objects look alike. On a curriculum whose
vocabulary is reinvented every episode, that is not a philosophical position but
the only thing that could possibly work — no symbol survives from one episode to
the next, and the shape of the term does.

So this model stores training graphs and, when asked about a hidden node:

1. **MAC** — a cheap filter over the whole case base, on a structural signature
   that ignores every symbol: the multiset of ``(parent type, slot, arity)``
   around the node, and the shape of the tree above it.
2. **FAC** — a greedy structural alignment against the survivors, growing a
   node-to-node mapping outward from the query along parent, slot and sibling
   edges, scored by how much of the local relational structure it puts in
   correspondence.
3. **Transfer** — the label standing at the corresponding position in the best
   analogue, carried across.

The contrast with ``evidence`` is the point of having both. That one retrieves
by *shared concepts*, within one episode, and is a bag-of-words method wearing a
symbolic hat. This one retrieves by *isomorphism*, across the training set, and
would work identically if every symbol in the corpus were replaced by a fresh
one — which is the strongest available statement of what "symbolic" is supposed
to buy.

A case base is a model with no compression at all, so the size reported is the
number of stored cases: the honest count for a method whose hypothesis is its
memory.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["AnalogyModel"]


@dataclass
class _Case:
    """One remembered node, with the structure around it and its answer."""

    labels: tuple
    types: tuple
    parent: tuple
    slot: tuple
    node: int
    label: int
    type_id: int
    signature: frozenset

    def children(self, i: int) -> list[int]:
        return [j for j, p in enumerate(self.parent) if p == i]


@register("analogy", doc="Structure mapping: retrieve an isomorphic case and transfer its answer.")
class AnalogyModel(RuleBasedModel):
    """MAC/FAC over stored graphs; the answer comes from the aligned position."""

    LEARNED = ("cases", "index", "max_cases", "candidates")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_cases = int(cfg.get("max_cases", 6000))
        self.candidates = int(cfg.get("candidates", 40))
        self.min_overlap = int(cfg.get("min_overlap", 3))
        self.cases: list[_Case] = []
        self.index: dict[tuple, list[int]] = {}

    # ---- the case base -------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.cases = []
        self.index = collections.defaultdict(list)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_len,
                                                 repeats=2):
            for node, (label_id, type_id) in targets.items():
                if len(self.cases) >= self.max_cases:
                    break
                case = _Case(
                    labels=tuple(view.labels), types=tuple(view.types),
                    parent=tuple(view.parent), slot=tuple(view.slot),
                    node=node, label=label_id, type_id=type_id,
                    signature=_signature(view, node))
                # The MAC index is keyed on structure only, so retrieval never
                # depends on a symbol that will not exist next episode.
                self.index[_coarse(view, node)].append(len(self.cases))
                self.cases.append(case)
        self.index = dict(self.index)

    # ---- prediction ----------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            label_votes, type_votes = self._map(view, i)
            out[i] = (label_votes, type_votes)
        return out

    def _map(self, view: GraphView, node: int) -> tuple[Votes, Votes]:
        pool = self.index.get(_coarse(view, node))
        if not pool:
            return ABSTAIN, ABSTAIN
        signature = _signature(view, node)

        # MAC: rank the pool by cheap signature overlap and keep a few.
        scored = sorted(
            ((len(signature & self.cases[c].signature), c) for c in pool),
            key=lambda t: -t[0])[:self.candidates]

        labels: collections.Counter = collections.Counter()
        types: collections.Counter = collections.Counter()
        best = 0.0
        for overlap, index in scored:
            if overlap < self.min_overlap:
                break
            case = self.cases[index]
            # FAC: a real alignment on the survivors, which is where the
            # structural claim is actually tested.
            score = _align(view, node, case)
            if score <= 0.0:
                continue
            transferred = _transfer(view, node, case)
            if transferred is not None:
                labels[transferred] += score
            if case.type_id >= 0:
                types[case.type_id] += score
            best = max(best, score)

        label_votes = ((dict(labels), min(0.2 + 0.6 * best, 0.88))
                       if labels else ABSTAIN)
        type_votes = ((dict(types), min(0.2 + 0.6 * best, 0.85))
                      if types else ABSTAIN)
        return label_votes, type_votes

    def n_symbolic_parameters(self) -> int:
        """A case base does not compress; its size is its memory."""
        return len(self.cases)


# ---------------------------------------------------------------------------
def _coarse(view: GraphView, node: int) -> tuple:
    """The MAC key: enough structure to filter, cheap enough to hash."""
    p = view.parent[node]
    return ((view.types[p] or "mask") if p >= 0 else "ROOT",
            min(view.slot[node], 6),
            min(len(view.children(node)), 4))


def _signature(view: GraphView, node: int) -> frozenset:
    """A symbol-free description of the neighbourhood.

    Every element is a relation or a type — no labels — so two nodes match on
    this iff their local structure matches, whatever anything is called.
    """
    p = view.parent[node]
    items = {("depth", min(view.depth[node], 6)),
             ("slot", min(view.slot[node], 6)),
             ("arity", min(len(view.children(node)), 4)),
             ("ptype", (view.types[p] or "mask") if p >= 0 else "ROOT"),
             ("nsib", min(len(view.siblings(node)), 5))}
    for k, j in enumerate(view.siblings(node)[:4]):
        items.add(("sib", k, view.types[j] or "mask"))
    for k, j in enumerate(view.children(node)[:4]):
        items.add(("kid", k, view.types[j] or "mask"))
    if p >= 0:
        g = view.parent[p]
        items.add(("gtype", (view.types[g] or "mask") if g >= 0 else "ROOT"))
        items.add(("pslot", min(view.slot[p], 6)))
    return frozenset(items)


def _align(view: GraphView, node: int, case: _Case) -> float:
    """Grow a correspondence outward from the query and score what lines up.

    Structure mapping proper: the score counts *relations* placed in
    correspondence — matching parents, matching slots, matching sibling types —
    and never counts a shared symbol, so an alignment cannot be bought with
    vocabulary.
    """
    mapping = {node: case.node}
    frontier = [(node, case.node)]
    score = 0.0
    seen = 0
    while frontier and seen < 12:
        here, there = frontier.pop()
        seen += 1
        p_here, p_there = view.parent[here], case.parent[there]
        if p_here >= 0 and p_there >= 0:
            if view.slot[here] == case.slot[there]:
                score += 1.0
            t_here = view.types[p_here] or "mask"
            t_there = case.types[p_there] or "mask"
            if t_here == t_there:
                score += 1.0
            if p_here not in mapping:
                mapping[p_here] = p_there
                frontier.append((p_here, p_there))
        kids_here, kids_there = view.children(here), case.children(there)
        if len(kids_here) == len(kids_there):
            score += 0.5
        for a, b in list(zip(kids_here, kids_there))[:3]:
            if (view.types[a] or "mask") == (case.types[b] or "mask"):
                score += 0.5
                if a not in mapping:
                    mapping[a] = b
                    frontier.append((a, b))
    return score


def _transfer(view: GraphView, node: int, case: _Case) -> int | None:
    """The answer the analogue gives.

    Two ways round, and the order matters. If the remembered answer is a symbol
    that also appears *structurally* in the query — the peer's label, the
    parent's — take the query's copy, because that is what the analogy actually
    licenses. Otherwise fall back to the remembered symbol itself, which only
    helps for the vocabulary that recurs across episodes.
    """
    if case.label < 0:
        return None
    source = _peer_label(view, node)
    if source is not None and _peer_label_of_case(case) == case.label:
        return source
    return case.label


def _peer_label(view: GraphView, node: int) -> int | None:
    p = view.parent[node]
    if p < 0 or view.labels[p] is None:
        return None
    head, slot = view.labels[p], view.slot[node]
    for other in range(len(view)):
        if other != p and view.labels[other] == head:
            kids = view.children(other)
            if slot < len(kids) and view.labels[kids[slot]] is not None:
                return view.labels[kids[slot]]
    return None


def _peer_label_of_case(case: _Case) -> int | None:
    p = case.parent[case.node]
    if p < 0 or case.labels[p] is None:
        return None
    head, slot = case.labels[p], case.slot[case.node]
    for other in range(len(case.labels)):
        if other != p and case.labels[other] == head:
            kids = case.children(other)
            if slot < len(kids) and case.labels[kids[slot]] is not None:
                return case.labels[kids[slot]]
    return None
