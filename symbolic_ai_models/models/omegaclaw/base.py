"""OmegaClaw: several fingers reach, one of them closes.

Six of the rule-based models in this repo are the same program wearing different
clothes. ``routes`` follows a structural path and weights it by a context prior;
``workspace`` runs competing codelets and weights them by a learned policy;
``brill`` picks a source to copy from and corrects the choice; ``analogy``
retrieves a case and replays the route that explained it. Read their
``node_votes`` side by side and the shared skeleton is unmistakable::

    look in a few structurally-defined places      (propose)
    decide how much each place is worth here       (control)
    turn that into a distribution and a confidence (commit)

They differ in the middle step and almost nowhere else — yet each one re-derives
the reaching, the calibration and the abstention contract for itself, and each
one got a slightly different part of it wrong at some point in this repo's
history. ``workspace`` shipped a confidence of ``0.15 + 0.75 * settled`` that
turned out to state 0.534 and deliver 0.216. ``routes`` counted successes
without counting failures. Those are not interesting mistakes; they are the same
mistake, made twice, in code that was copied rather than shared.

**OmegaClaw is that skeleton, factored out.** A *claw* is one reaching finger: a
structural operator that points at a node of the same episode and offers its
label. The subclass supplies a control policy and nothing else, so two OmegaClaw
models differ in exactly the thing being compared and share the reaching, the
evidence-gathering, the held-out calibration, the type head and the abstention
path, bit for bit.

Extension points
----------------
One is required::

    weigh(name, ctx, claim) -> float        how much this claw counts, here

Three have defaults that the three shipped subclasses deliberately do not
override, so that the comparison between them isolates control::

    claws()      -> {name: claw}            where to reach
    perceive(view, node) -> Hashable        what counts as "the same situation"
    commit(weighted) -> (votes, raw score)  how to aggregate

What the base class does for you, and why each part is here rather than in the
subclasses:

* **Evidence.** Every claw is run over the masked training views and scored
  against the answer, per context and globally. Every subclass therefore has the
  same table available and cannot accidentally measure it differently.
* **A held-out calibration.** The evidence table is fitted twice: once on four
  fifths of the episodes, whose predictions on the remaining fifth train the
  :class:`~symbolic_ai_models.calibration.ScoreCalibrator`, and once on
  everything, which is what ships. A subclass reports a raw score in ``[0, 1]``
  from ``commit`` and the base turns it into a confidence that has been measured
  rather than asserted. This is the part that was worth sharing most: it is
  fiddly, it is invisible when wrong, and it is exactly what ``workspace`` got
  wrong on its own.
* **The type head.** A claim names the node it was read off, so the same claw
  that argues for a label argues for that node's type at no extra cost.
  Abstaining on type would have scored the abstention rather than the model.

Why the claws are pointer-valued
--------------------------------
Every claw returns *another node's label*, never a remembered symbol. That makes
the whole family exactly equivariant under renaming, which is a real robustness
property — though it is worth repeating the correction recorded in
:mod:`symbolic_ai_models.models.routes`: on this curriculum 100% of scored labels
recur in training, so pointer-valued reasoning buys robustness and not accuracy,
and a model that refuses to memorise is handicapping itself for a benefit this
task does not pay. The OmegaClaw family accepts that handicap on purpose, so its
numbers should be read as the ceiling of *structure-only* reasoning under this
control policy, not as the best achievable score.

Negative results recorded here rather than hidden
-------------------------------------------------
* ``models/routes.follow`` was the obvious thing to reuse for the route-shaped
  claws, and it is not reused. It takes plain arrays and rescans the whole
  ``parent`` list on every call, so a single node costs eleven claws times
  ``O(n)`` scans; with eleven claws over four masking passes that dominated
  fitting time. :class:`Scan` caches the child lists once per view instead. The
  cost of that decision is a second implementation of ``peer`` and ``sibling``
  in this repo, which is a real cost and is why it is written down.
* The base class originally let a subclass override ``learn`` to gather its own
  statistics. Nothing needed it, and having it there meant two subclasses could
  silently be fitted on different evidence — which is the one failure this whole
  file exists to prevent. It was removed; a subclass that genuinely needs other
  statistics should not be an OmegaClaw.
"""

from __future__ import annotations

import collections
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Hashable, Mapping, Sequence

from ...calibration import ScoreCalibrator
from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["OmegaClaw", "Claim", "Scan", "Weighted", "CLAWS"]


@dataclass(frozen=True)
class Claim:
    """What one claw came back holding.

    ``strength`` is the claw's own conviction *before* any evidence — a peer
    match is a sharper thing than "the commonest label at this depth", and that
    is a property of the operator rather than of the corpus. It is shared by
    every subclass so that a control policy is compared against the same priors.
    """

    symbol: int
    source: int = -1
    strength: float = 1.0


#: ``(scan, node) -> Claim | None``. A claw that finds nothing returns ``None``
#: and is not counted as having fired, which is what keeps its reliability an
#: estimate of "right when it speaks" rather than "right about everything".
Claw = Callable[["Scan", int], "Claim | None"]

#: ``(name, claim, weight)`` — what ``commit`` is handed.
Weighted = tuple[str, Claim, float]


class Scan:
    """A :class:`GraphView` with the lookups a claw needs precomputed.

    Claws are run eleven times per hidden node, four times per training
    episode, for every model in the family — so anything that costs ``O(n)``
    inside a claw costs ``O(n)`` a few million times. Children, the label index
    and the per-depth and per-slot tallies are each built once per view here.

    It holds no answer that the view does not: hidden labels are ``None`` in
    ``labels`` and stay ``None`` in every index built from it.
    """

    def __init__(self, view: GraphView) -> None:
        self.view = view
        self.labels = view.labels
        self.parent = view.parent
        self.slot = view.slot
        self.depth = view.depth
        n = len(view)
        self.n = n

        kids: list[list[int]] = [[] for _ in range(n)]
        for i in range(n):
            p = view.parent[i]
            if 0 <= p < n:
                kids[p].append(i)
        self._children = kids

        by_label: dict[int, list[int]] = {}
        for i in range(n):
            label = view.labels[i]
            if label is not None:
                by_label.setdefault(label, []).append(i)
        self._by_label = by_label

        # Aggregate tallies, keyed by the two groupings the aggregate claws use.
        # Built by ascending node index so that `most_common` breaks ties by
        # position, which is stable across processes; a set-derived order would
        # not be.
        self._by_depth: dict[int, collections.Counter] = {}
        self._by_slot: dict[tuple, collections.Counter] = {}
        for i in range(n):
            label = view.labels[i]
            if label is None:
                continue
            self._by_depth.setdefault(view.depth[i], collections.Counter())[label] += 1
            self._by_slot.setdefault(self.slot_key(i), collections.Counter())[label] += 1
        self._shapes: dict[int, tuple] = {}

    # ---- structure ----------------------------------------------------
    def children(self, i: int) -> list[int]:
        return self._children[i] if 0 <= i < self.n else []

    def siblings(self, i: int) -> list[int]:
        p = self.parent[i]
        return [] if p < 0 else [j for j in self._children[p] if j != i]

    def child_at_slot(self, i: int, s: int) -> int | None:
        for j in self.children(i):
            if self.slot[j] == s:
                return j
        return None

    def with_label(self, label: int) -> list[int]:
        return self._by_label.get(label, [])

    def slot_key(self, i: int) -> tuple:
        p = self.parent[i]
        return ((self.view.types[p] or "mask") if p >= 0 else "ROOT",
                min(self.slot[i], 6))

    def commonest_at_depth(self, i: int) -> tuple[int, int] | None:
        return self._commonest(self._by_depth.get(self.depth[i]))

    def commonest_in_slot(self, i: int) -> tuple[int, int] | None:
        return self._commonest(self._by_slot.get(self.slot_key(i)))

    def _commonest(self, counts: collections.Counter | None) -> tuple[int, int] | None:
        """``(commonest label, a node carrying it)``, or nothing.

        The tallies are built from *visible* nodes only, so the node being asked
        about never contributes to its own answer — the removal step an earlier
        version did here was dead code and is gone.
        """
        if not counts:
            return None
        symbol, _ = counts.most_common(1)[0]
        carriers = self.with_label(symbol)
        return (symbol, carriers[0]) if carriers else None

    def shape(self, root: int, limit: int = 24) -> tuple:
        """The subtree under ``root`` as ``(type, slot)`` pairs, labels dropped.

        Cached, because the mirror claw asks for the same subtree's shape once
        per candidate sibling and the shapes do not change within a view.
        """
        cached = self._shapes.get(root)
        if cached is not None:
            return cached
        out: list[tuple] = []
        stack = [root]
        while stack and len(out) < limit:
            node = stack.pop()
            out.append(((self.view.types[node] or "mask"),
                        -1 if node == root else min(self.slot[node], 6)))
            stack.extend(reversed(self.children(node)))
        shape = tuple(out)
        self._shapes[root] = shape
        return shape


# ---------------------------------------------------------------------------
# the claws
# ---------------------------------------------------------------------------
def _at(scan: Scan, target: int | None, strength: float) -> Claim | None:
    """A claim on ``target``'s label, or nothing if it has none to give."""
    if target is None or not (0 <= target < scan.n):
        return None
    label = scan.labels[target]
    return None if label is None else Claim(label, target, strength)


def claw_peer(scan: Scan, node: int) -> Claim | None:
    """The same slot of another subtree whose head matches.

    Coreference *within* the episode — the relation that makes a term tree
    analogical rather than merely hierarchical, and the strongest single
    operator every model in this repo that has one agrees on.
    """
    p = scan.parent[node]
    if p < 0 or scan.labels[p] is None:
        return None
    for other in scan.with_label(scan.labels[p]):
        if other == p:
            continue
        target = scan.child_at_slot(other, scan.slot[node])
        claim = _at(scan, target, 0.9)
        if claim is not None:
            return claim
    return None


def claw_mirror(scan: Scan, node: int) -> Claim | None:
    """Align an ancestor with a same-shaped sibling subtree and read across.

    ``peer`` needs the two subtrees to share a *head symbol*; this needs only
    that they share a *shape*, which is what an episode stating a fact and a
    pattern over the same frame provides. A hidden slot is a wildcard in the
    shape comparison, because the node being asked about is masked by
    construction and its counterpart in the other subtree is not — insisting on
    equality there would disable the claw in precisely the case it exists for.
    """
    path: list[int] = []
    cur = node
    for _ in range(4):
        p = scan.parent[cur]
        if p < 0:
            break
        path.append(scan.slot[cur])
        cur = p
        shape = scan.shape(cur)
        for other in scan.siblings(cur):
            if not _parallel(scan.shape(other), shape):
                continue
            target: int | None = other
            for step in reversed(path):
                target = scan.child_at_slot(target, step) if target is not None else None
            claim = _at(scan, target, 1.0)
            if claim is not None:
                return claim
    return None


def _parallel(a: tuple, b: tuple) -> bool:
    if len(a) != len(b) or not a:
        return False
    for (type_a, slot_a), (type_b, slot_b) in zip(a, b):
        if slot_a != slot_b:
            return False
        if type_a != type_b and "mask" not in (type_a, type_b):
            return False
    return True


def claw_parent(scan: Scan, node: int) -> Claim | None:
    return _at(scan, scan.parent[node] if scan.parent[node] >= 0 else None, 0.35)


def claw_grandparent(scan: Scan, node: int) -> Claim | None:
    p = scan.parent[node]
    g = scan.parent[p] if p >= 0 else -1
    return _at(scan, g if g >= 0 else None, 0.25)


def claw_sibling0(scan: Scan, node: int) -> Claim | None:
    sibs = scan.siblings(node)
    return _at(scan, sibs[0] if sibs else None, 0.4)


def claw_prev_sibling(scan: Scan, node: int) -> Claim | None:
    sibs = [j for j in scan.siblings(node) if j < node]
    return _at(scan, sibs[-1] if sibs else None, 0.45)


def claw_child0(scan: Scan, node: int) -> Claim | None:
    kids = scan.children(node)
    return _at(scan, kids[0] if kids else None, 0.3)


def claw_aunt(scan: Scan, node: int) -> Claim | None:
    p = scan.parent[node]
    if p < 0:
        return None
    aunts = scan.siblings(p)
    return _at(scan, aunts[0] if aunts else None, 0.3)


def claw_prev(scan: Scan, node: int) -> Claim | None:
    """The nearest labelled node before this one in the linearisation."""
    for j in range(node - 1, -1, -1):
        if scan.labels[j] is not None:
            return _at(scan, j, 0.25)
    return None


def claw_slotmate(scan: Scan, node: int) -> Claim | None:
    """Whatever usually fills this slot under this kind of parent, here."""
    found = scan.commonest_in_slot(node)
    return None if found is None else Claim(found[0], found[1], 0.35)


def claw_echo(scan: Scan, node: int) -> Claim | None:
    """The commonest label at this depth in this episode."""
    found = scan.commonest_at_depth(node)
    return None if found is None else Claim(found[0], found[1], 0.3)


#: The default reach. Fixed and shared, so that a difference between two
#: OmegaClaw models is a difference in control and cannot be a difference in
#: what they were allowed to look at. Insertion order is the iteration order and
#: is therefore part of the model: ties in a winner-take-all commit break
#: towards the earlier claw, and that has to be reproducible across processes.
CLAWS: Mapping[str, Claw] = {
    "mirror": claw_mirror,
    "peer": claw_peer,
    "prev_sibling": claw_prev_sibling,
    "sibling0": claw_sibling0,
    "parent": claw_parent,
    "grandparent": claw_grandparent,
    "aunt": claw_aunt,
    "child0": claw_child0,
    "slotmate": claw_slotmate,
    "echo": claw_echo,
    "prev": claw_prev,
}


# ---------------------------------------------------------------------------
# the base class
# ---------------------------------------------------------------------------
class OmegaClaw(RuleBasedModel, ABC):
    """Reach with every claw, weigh what each one holds, close on one answer.

    Subclasses implement :meth:`weigh` and usually nothing else. See the module
    docstring for what that buys and what it costs.
    """

    LEARNED = ("claw_evidence", "claw_totals", "confidence_map")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_examples = int(cfg.get("max_examples", 4000))
        #: ``(context, claw) -> [times it fired, times it was right]``
        self.claw_evidence: dict[tuple, list[int]] = {}
        #: ``claw -> [times it fired, times it was right]``, over all contexts
        self.claw_totals: dict[str, list[int]] = {}
        self.confidence_map = ScoreCalibrator()

    # ---- extension points ---------------------------------------------
    def claws(self) -> Mapping[str, Claw]:
        """Where this model is allowed to reach. Defaults to :data:`CLAWS`."""
        return CLAWS

    def perceive(self, view: GraphView, node: int) -> Hashable:
        """What this model treats as "the same kind of situation".

        The default is the floor's own key — parent type, slot, depth, whether
        the node has children — deliberately. Reliability is then measured in
        exactly the cells the model is scored against, so a claw that looks good
        in a context is looking good where the comparison actually happens. A
        subclass wanting a coarser or a symbol-aware context overrides this, and
        the evidence table follows it with no other change.
        """
        p = view.parent[node]
        return ((view.types[p] or "mask") if p >= 0 else "ROOT",
                min(view.slot[node], 8), min(view.depth[node], 8),
                bool(view.children(node)))

    @abstractmethod
    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        """How much this claw's claim counts in this context. **The model.**

        Return zero to silence a claw. Everything else about an OmegaClaw model
        is shared, so this method is the entire difference between one and
        another — which is the property that makes the family's numbers
        comparable and is the reason the base class does not offer a default.
        """

    def commit(self, weighted: Sequence[Weighted]
               ) -> tuple[Mapping[int, float], float] | None:
        """Aggregate into ``(distribution, raw score in [0, 1])``, or ``None``.

        The default mixes: every claim contributes its weight to its symbol, and
        the raw score is the winner's share of the total. A share is the right
        internal score to hand the calibrator because it is a statement about
        *agreement*, which is measurable, rather than about correctness, which is
        what the calibrator is for. Returning ``None`` abstains, which lands the
        model on the shared back-off and costs it nothing beyond the prior.
        """
        support: collections.Counter = collections.Counter()
        for _, claim, weight in weighted:
            if weight > 0.0:
                support[claim.symbol] += weight
        total = float(sum(support.values()))
        if total <= 0.0:
            return None
        return dict(support), support.most_common(1)[0][1] / total

    # ---- fitting -------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Gather claw evidence, then calibrate on episodes it was not gathered from.

        Fitted twice on purpose. A confidence measured against the same
        episodes the evidence came from certifies the model's overconfidence
        instead of removing it; fitting the shipped table on *more* data than
        the map was measured with biases confidence down, which is the safe
        direction. This is ``workspace``'s discipline, moved somewhere every
        member of the family inherits it.
        """
        cut = max(int(len(episodes) * 0.8), 1)
        held_out_evidence, held_out_totals = self._gather(episodes[:cut], tok)
        self.claw_evidence, self.claw_totals = self._gather(episodes, tok)
        self._calibrate(episodes[cut:] or episodes, tok,
                        held_out_evidence, held_out_totals)

    def _gather(self, episodes: Sequence[Episode], tok: SymbolTokenizer
                ) -> tuple[dict[tuple, list[int]], dict[str, list[int]]]:
        """Run every claw over the masked training views and score it."""
        evidence: dict[tuple, list[int]] = {}
        totals: dict[str, list[int]] = {}
        claws = self.claws()
        seen = 0
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            scan = Scan(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0 or seen >= self.max_examples:
                    continue
                seen += 1
                ctx = self.perceive(view, node)
                for name, claw in claws.items():
                    claim = claw(scan, node)
                    if claim is None:
                        continue
                    right = int(claim.symbol == label_id)
                    cell = evidence.setdefault((ctx, name), [0, 0])
                    cell[0] += 1
                    cell[1] += right
                    total = totals.setdefault(name, [0, 0])
                    total[0] += 1
                    total[1] += right
        return evidence, totals

    def _calibrate(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
                   evidence: dict, totals: dict) -> None:
        """Learn what this model's raw score is actually worth, out of sample."""
        held = (self.claw_evidence, self.claw_totals)
        self.claw_evidence, self.claw_totals = evidence, totals
        scores: list[float] = []
        correct: list[bool] = []
        try:
            for view, targets in self.training_views(episodes, tok, repeats=1,
                                                     seed=7,
                                                     max_nodes=self.cfg.max_nodes):
                scan = Scan(view)
                for node, (label_id, _) in targets.items():
                    if label_id < 0:
                        continue
                    result = self._decide(view, scan, node)
                    if result is None:
                        continue
                    support, raw, _ = result
                    best = max(support, key=lambda s: (support[s], -s))
                    scores.append(raw)
                    correct.append(best == label_id)
        finally:
            self.claw_evidence, self.claw_totals = held
        self.confidence_map = ScoreCalibrator().fit(scores, correct)

    # ---- reading the evidence ------------------------------------------
    def reliability(self, name: str, ctx: Hashable = None, *,
                    smoothing: float = 2.0) -> float:
        """How often this claw was right when it fired, shrunk towards its global rate.

        Shrinkage rather than a raw rate because contexts are many and thin: the
        default ``perceive`` key produces hundreds of cells on a few thousand
        examples, and a claw that fired twice in a cell and was right both times
        is not evidence of certainty. Shrinking to the claw's own global rate —
        rather than to a constant — means a rarely-seen context inherits the
        claw's reputation, which is the closest thing to a prior that the
        evidence itself supports.
        """
        fired, right = self.claw_totals.get(name, (0, 0))
        overall = (right + 0.5) / (fired + 1.0)
        if ctx is None:
            return overall
        here_fired, here_right = self.claw_evidence.get((ctx, name), (0, 0))
        return (here_right + smoothing * overall) / (here_fired + smoothing)

    def confidence(self, raw: float) -> float:
        """The measured meaning of a raw score, or a cautious guess before fitting."""
        if self.confidence_map.fitted:
            return float(self.confidence_map(raw))
        return min(0.15 + 0.75 * max(raw, 0.0), 0.9)

    # ---- predicting -----------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        scan = Scan(view)
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            result = self._decide(view, scan, i)
            if result is None:
                out[i] = (ABSTAIN, ABSTAIN)
                continue
            support, raw, weighted = result
            confidence = self.confidence(raw)
            out[i] = ((support, confidence), self._type_votes(view, weighted,
                                                              confidence))
        return out

    def _decide(self, view: GraphView, scan: Scan, node: int
                ) -> tuple[Mapping[int, float], float, list[Weighted]] | None:
        """Reach, weigh, commit. The one path both fitting and evaluation take.

        Shared between :meth:`_calibrate` and :meth:`node_votes` on purpose: a
        confidence map fitted against a slightly different decision procedure
        than the one that ships is a map for a model that does not exist.
        """
        ctx = self.perceive(view, node)
        weighted: list[Weighted] = []
        for name, claw in self.claws().items():
            claim = claw(scan, node)
            if claim is None:
                continue
            weighted.append((name, claim, float(self.weigh(name, ctx, claim))))
        if not weighted:
            return None
        committed = self.commit(weighted)
        if committed is None:
            return None
        support, raw = committed
        if not support:
            return None
        return support, min(max(float(raw), 0.0), 1.0), weighted

    def _type_votes(self, view: GraphView, weighted: Sequence[Weighted],
                    confidence: float) -> Votes:
        """The types of the nodes the claws pointed at, weighted as they were.

        Free, and better than abstaining: a claw that found the right place to
        read a label from found the right kind of node too, and a claw that did
        not is wrong about both in the same proportion — which is what makes
        this an honest reuse of the label evidence rather than a second model.
        """
        votes: collections.Counter = collections.Counter()
        for _, claim, weight in weighted:
            if weight <= 0.0 or claim.source < 0:
                continue
            type_ = view.types[claim.source]
            if type_ is not None:
                votes[TYPE_TO_ID[type_]] += weight
        if not votes:
            return ABSTAIN
        return dict(votes), min(confidence, 0.85)

    # ---- reporting -------------------------------------------------------
    def n_symbolic_parameters(self) -> int:
        """One per context-claw cell the model can actually consult."""
        return len(self.claw_evidence) + len(self.claw_totals)

    def render(self) -> str:
        """What each claw was worth, and how much of the model is context-specific."""
        lines = [f"=== {self.name}: {len(self.claws())} claws, "
                 f"{len(self.claw_evidence)} context cells ==="]
        rows = sorted(self.claw_totals.items(), key=lambda kv: -kv[1][1])
        for name, (fired, right) in rows:
            lines.append(f"  {name:<14} fired {fired:>6}   right {right:>6}"
                         f"   rate {right / max(fired, 1):.3f}")
        if not rows:
            lines.append("  (nothing fired: the model was not fitted)")
        lines.append(f"  confidence map: "
                     f"{'fitted' if self.confidence_map.fitted else 'unfitted'}")
        return "\n".join(lines)
