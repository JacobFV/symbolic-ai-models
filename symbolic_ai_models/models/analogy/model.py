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

The contrast with ``evidence`` was meant to be the point of having both: that
one retrieves by *shared concepts* within an episode, this one by *isomorphism*
across the training set.

**The claim is true now, and it cost most of the score.** This docstring once
said the model "would work identically if every symbol in the corpus were
replaced by a fresh one", and the renaming test in
:mod:`symbolic_ai_models.invariance` showed it did not: label accuracy fell from
0.417 to 0.036 under a permutation of the vocabulary. Retrieval and alignment
were always structural — the MAC signature and the FAC alignment read types and
slots, never a label — but the readout fell back to ``case.label``, the symbol
remembered from the training case, and that fallback carried most of the score.

What travels between two episodes is not a symbol but a **route**: the case
records that its answer stood at, say, its slot-0 sibling, and the query is read
at the same place. :func:`_explaining_routes` recovers which structural paths
would have produced the remembered answer, and :func:`_transfer` follows them in
the new episode. Where no route explains the case, the model now returns nothing
rather than a name it happens to remember.

Measured: 0.417 -> 0.173 on ordinary episodes, and 0.036 -> 0.173 under
renaming, so the delta is exactly zero. The honest accuracy of structure mapping
here is 0.173; the other 0.244 was memorisation wearing its name.

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
from ...calibration import ScoreCalibrator
from ..routes import explaining_routes, follow
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
    #: which training episode this case came from, so calibration can exclude
    #: it and measure retrieval rather than memory
    episode: int = -1

    def children(self, i: int) -> list[int]:
        return [j for j, p in enumerate(self.parent) if p == i]


@register("analogy", doc="Structure mapping: retrieve an isomorphic case and transfer its answer.")
class AnalogyModel(RuleBasedModel):
    """MAC/FAC over stored graphs; the answer comes from the aligned position."""

    LEARNED = ("cases", "index", "max_cases", "candidates", "confidence_map")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_cases = int(cfg.get("max_cases", 6000))
        self.candidates = int(cfg.get("candidates", 40))
        self.min_overlap = int(cfg.get("min_overlap", 3))
        self.cases: list[_Case] = []
        self.index: dict[tuple, list[int]] = {}
        self.confidence_map = ScoreCalibrator()

    # ---- the case base -------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.cases = []
        self.index = collections.defaultdict(list)
        for view, targets, episode in self.training_views(
                episodes, tok, max_nodes=self.cfg.max_len, repeats=2,
                with_index=True):
            for node, (label_id, type_id) in targets.items():
                if len(self.cases) >= self.max_cases:
                    break
                case = _Case(
                    labels=tuple(view.labels), types=tuple(view.types),
                    parent=tuple(view.parent), slot=tuple(view.slot),
                    node=node, label=label_id, type_id=type_id,
                    signature=_signature(view, node), episode=episode)
                # The MAC index is keyed on structure only, so retrieval never
                # depends on a symbol that will not exist next episode.
                self.index[_coarse(view, node)].append(len(self.cases))
                self.cases.append(case)
        self.index = dict(self.index)
        self._calibrate(episodes, tok)

    def _calibrate(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """Learn what an alignment score is actually worth.

        The old confidence was ``0.2 + 0.6 * alignment_score``, which asserts
        that finding more structure means being more often right. Measured, that
        assertion was badly wrong: the model stated 0.586 and delivered 0.219,
        an ECE of 0.368 and the worst in the repo.

        So the map is fitted rather than assumed, on predictions made with the
        answering episode's own cases **excluded**. Without that exclusion the
        case base contains the very node being asked about, every alignment
        looks perfect, and the calibration would certify exactly the
        overconfidence it is meant to remove.
        """
        scores: list[float] = []
        correct: list[bool] = []
        for view, targets, episode in self.training_views(
                episodes, tok, max_nodes=self.cfg.max_len, repeats=1,
                with_index=True, seed=7):
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                votes, score = self._retrieve(view, node, exclude=episode)
                if not votes or score <= 0.0:
                    continue
                predicted = max(votes, key=lambda k: votes[k])
                scores.append(score)
                correct.append(predicted == label_id)
        self.confidence_map = ScoreCalibrator().fit(scores, correct)

    # ---- prediction ----------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            label_votes, type_votes = self._map(view, i)
            out[i] = (label_votes, type_votes)
        return out

    def _map(self, view: GraphView, node: int) -> tuple[Votes, Votes]:
        labels, best = self._retrieve(view, node)
        types = self._types(view, node)
        if not labels:
            return ABSTAIN, (types if types else ABSTAIN)
        confidence = (self.confidence_map(best) if self.confidence_map.fitted
                      else min(0.2 + 0.6 * best, 0.88))
        return (dict(labels), confidence), (types if types else ABSTAIN)

    def _types(self, view: GraphView, node: int) -> Votes | None:
        types = self._retrieve_types(view, node)
        return types

    def _retrieve(self, view: GraphView, node: int, *, exclude: int = -2
                  ) -> tuple[dict, float]:
        """Vote for labels by aligned route transfer; also return the best score."""
        pool = self.index.get(_coarse(view, node))
        if not pool:
            return {}, 0.0
        signature = _signature(view, node)

        # MAC: rank the pool by cheap signature overlap and keep a few.
        scored = sorted(
            ((len(signature & self.cases[c].signature), c) for c in pool),
            key=lambda t: -t[0])[:self.candidates]

        labels: collections.Counter = collections.Counter()
        best = 0.0
        for overlap, index in scored:
            if overlap < self.min_overlap:
                break
            case = self.cases[index]
            if case.episode == exclude:
                continue
            # FAC: a real alignment on the survivors, which is where the
            # structural claim is actually tested.
            score = _align(view, node, case)
            if score <= 0.0:
                continue
            transferred = _transfer(view, node, case)
            if transferred is not None:
                labels[transferred] += score
                best = max(best, score)
        return dict(labels), best

    def _retrieve_types(self, view: GraphView, node: int) -> Votes | None:
        pool = self.index.get(_coarse(view, node))
        if not pool:
            return None
        signature = _signature(view, node)
        scored = sorted(
            ((len(signature & self.cases[c].signature), c) for c in pool),
            key=lambda t: -t[0])[:self.candidates]
        types: collections.Counter = collections.Counter()
        best = 0.0
        for overlap, index in scored:
            if overlap < self.min_overlap:
                break
            case = self.cases[index]
            score = _align(view, node, case)
            if score > 0.0 and case.type_id >= 0:
                types[case.type_id] += score
                best = max(best, score)
        if not types:
            return None
        return dict(types), min(0.2 + 0.6 * best, 0.85)

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


def _explaining_routes(case: _Case) -> list[tuple]:
    """The routes that would have produced this case's answer from its own node.

    This is what the analogy actually transfers. The remembered *symbol* is
    worthless — the next episode will not contain it — but "the answer was my
    slot-0 sibling" is a fact about shape and travels intact.
    """
    return explaining_routes(case.labels, case.parent, case.slot, case.node,
                             case.label)


def _transfer(view: GraphView, node: int, case: _Case) -> int | None:
    """Read the query at the position the case's answer stood in.

    Previously this fell back to ``case.label`` — the symbol memorised from the
    training case — whenever the peer route did not apply, and the renaming test
    showed that fallback was carrying most of the model's score: accuracy fell
    from 0.417 to 0.036 when every symbol was permuted. Structure mapping is
    supposed to survive exactly that. It now returns nothing rather than a
    remembered name, which costs accuracy and is the honest version.
    """
    if case.label < 0:
        return None
    for route in _explaining_routes(case):
        target = follow(view.labels, view.parent, view.slot, node, route)
        if target is not None and view.labels[target] is not None:
            return view.labels[target]
    return None
