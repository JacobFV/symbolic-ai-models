"""A workspace engine: infer what is being asked, then decide how to think about it.

Every other model here has one fixed way of working. ``analogy`` always aligns,
``ilp`` always resolves clauses, ``ngram`` always counts — the strategy is the
model. This one has no single strategy. It looks at the episode, works out what
kind of question it is being asked, **partitions its memory accordingly**, and
then runs a set of competing operators over that partition, committing only when
they agree.

The architecture is Hofstadter and Mitchell's Copycat, with a debt to Hearsay-II's
blackboard and to SOAR's impasse-driven subgoaling:

**Inferring the objective.** Nothing tells the engine what the task is. It reads
the term tree, walks up from the hidden node to the top-level field it lives
under, and derives a *goal signature* — which region it is in, what its parent
is, which slot it fills, whether a structurally parallel region exists elsewhere
in the episode. On ``unification`` that signature says "you are in ``pattern``,
and there is a parallel region called ``fact``", which is the whole content of
the problem, arrived at without the word *unification* appearing anywhere.

**Partitioning memory.** The workspace is not a fixed set of slots. The episode's
top-level fields become regions, so an episode with a scene and a query gets two
and a proof with six steps gets six, and correspondences are only ever built
*between* regions. The partition is a property of the input.

**Manipulating it.** Codelets are small competing operators — mirror a parallel
region, copy a peer, repeat what fills this slot elsewhere in the same region —
each proposing a filler with a strength. Agreement between codelets lowers the
**temperature**; a cold workspace has settled and commits sharply, a hot one
stays diffuse and defers to the prior. That is Copycat's central device, and it
is what lets the engine say "I have no idea" in a way that costs it only the
back-off.

What ``fit`` learns is not the answer to anything. It learns a **policy**: which
codelet to trust for which inferred goal signature. So the model is a mapping
from *kinds of problem it discovered on its own* to *ways of working*, and
``render()`` prints it — which is the artifact worth having, because it is a
readable account of how the engine decided to carve up the task.

Temperature here is deterministic. Copycat anneals stochastically, and that
matters for its search; here reproducibility matters more, so temperature is
computed from how much the codelets agree rather than sampled. The role is the
same — it governs how sharply the workspace commits — and saying so is better
than quietly keeping a random seed that changes every score.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ...calibration import ScoreCalibrator
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["WorkspaceModel", "Region", "Proposal"]


@dataclass
class Region:
    """One partition of the workspace: a top-level field and everything under it."""

    label: int | None
    root: int
    nodes: list[int] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.nodes)


@dataclass
class Proposal:
    """A filler a codelet argues for, how hard it argues, and where it looked.

    ``source`` is the node the proposal was read off. Keeping it means the same
    codelet that argues for a label argues for a type as well, at no extra cost
    — the workspace already found the corresponding position, and abstaining on
    the type question would have scored the abstention rather than the engine.
    """

    symbol: int
    strength: float
    codelet: str
    source: int = -1


@dataclass
class Goal:
    """What the engine worked out it is being asked, from structure alone."""

    region: int | None            # the top-level field the hidden node is under
    parent_type: str
    slot: int
    has_parallel: bool            # another region with the same shape
    has_peer: bool
    n_regions: int

    def signature(self) -> tuple:
        return (self.region, self.parent_type, min(self.slot, 4),
                self.has_parallel, self.has_peer, min(self.n_regions, 4))


@register("workspace", doc="Copycat-style workspace: infers the goal, partitions memory, runs competing codelets.")
class WorkspaceModel(RuleBasedModel):
    """Infer the objective, carve the workspace, let codelets compete."""

    LEARNED = ("policy", "prior", "rounds", "confidence_map")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.rounds = int(cfg.get("rounds", 3))
        # Set from measured wall clock, never from eval lift. The cap bounds
        # runtime and nothing else, so the rule is "the largest value fitting
        # 300s on the full curriculum", well under synth's 1,500s which this
        # sweep already tolerates. The old value was a guessed constant.
        # Uncapped: 26s over all 179 lessons against 17s at the old 4,000. The cap was
        # buying four seconds and costing 0.095 of label lift.
        self.max_examples = int(cfg.get("max_examples", 200_000))
        #: ``goal signature -> {codelet: how often it was right}``
        self.policy: dict[tuple, collections.Counter] = {}
        #: ``goal signature -> how many times it was seen``
        self.prior: collections.Counter = collections.Counter()
        self.confidence_map = ScoreCalibrator()

    # ---- the codelets ---------------------------------------------------
    def _codelets(self) -> dict[str, Callable]:
        return {"mirror": _mirror, "peer": _peer, "echo": _echo,
                "parent": _parent, "sibling": _sibling, "frame": _frame}

    # ---- fitting ---------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Learn which way of working pays off for which inferred goal.

        Not which answer is right — the answers do not survive the episode. The
        policy is over *strategies*, keyed by signatures the engine derived for
        itself, which is what lets it transfer to an episode whose vocabulary it
        has never seen.
        """
        # The policy is fitted twice: once on a four-fifths slice, whose
        # predictions on the held-out fifth are what the confidence map is
        # measured against, and once on everything, which is what actually
        # ships. Calibrating on the episodes the policy was fitted from would
        # certify the overconfidence rather than remove it. Fitting the final
        # policy on more data than the map was measured with biases the
        # confidence *down*, which is the safe direction.
        cut = max(int(len(episodes) * 0.8), 1)
        held_out_policy, held_out_prior = self._fit_policy(episodes[:cut], tok)
        self.policy, self.prior = self._fit_policy(episodes, tok)
        self._calibrate(episodes[cut:] or episodes, tok,
                        held_out_policy, held_out_prior)

    def _fit_policy(self, episodes: Sequence[Episode], tok: SymbolTokenizer
                    ) -> tuple[dict, collections.Counter]:
        """Which codelet pays off for which inferred goal."""
        policy: dict = collections.defaultdict(collections.Counter)
        prior: collections.Counter = collections.Counter()
        seen = 0
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            regions = _partition(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0 or seen >= self.max_examples:
                    continue
                seen += 1
                goal = _infer_goal(view, node, regions)
                key = goal.signature()
                prior[key] += 1
                for name, codelet in self._codelets().items():
                    proposal = codelet(view, node, regions, goal)
                    if proposal is not None and proposal.symbol == label_id:
                        policy[key][name] += 1
        return {k: v for k, v in policy.items()}, prior

    def _calibrate(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
                   policy: dict, prior: collections.Counter) -> None:
        """Learn what a settled workspace is actually worth.

        The old confidence was ``0.15 + 0.75 * (1 - temperature)``: it rose as
        the codelets agreed. Agreement and correctness are not the same thing,
        and measured, the gap was large — 0.534 stated against 0.216 delivered.
        """
        scores: list[float] = []
        correct: list[bool] = []
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes,
                                                 repeats=1, seed=7):
            regions = _partition(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                support, settled = self._support(view, node, regions,
                                                 policy, prior)
                if not support:
                    continue
                scores.append(settled)
                correct.append(max(support, key=lambda k: support[k]) == label_id)
        self.confidence_map = ScoreCalibrator().fit(scores, correct)

    # ---- running the workspace -------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        regions = _partition(view)
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            out[i] = self._run(view, i, regions)
        return out

    def _support(self, view: GraphView, node: int, regions: list[Region],
                 policy: dict, prior: collections.Counter
                 ) -> tuple[collections.Counter, float]:
        """Run the codelets and return their weighted support and how settled it is."""
        goal = _infer_goal(view, node, regions)
        key = goal.signature()
        learned = policy.get(key) or collections.Counter()
        seen = max(prior.get(key, 0), 1)
        support: collections.Counter = collections.Counter()
        proposals: list[Proposal] = []
        for name, codelet in self._codelets().items():
            proposal = codelet(view, node, regions, goal)
            if proposal is None:
                continue
            trust = (learned.get(name, 0) + 0.5) / (seen + 1.0)
            proposals.append(proposal)
            support[proposal.symbol] += proposal.strength * trust
        if not support:
            return support, 0.0
        return support, 1.0 - _temperature(proposals, support)

    def _run(self, view: GraphView, node: int,
             regions: list[Region]) -> tuple[Votes, Votes]:
        goal = _infer_goal(view, node, regions)
        key = goal.signature()
        learned = self.policy.get(key) or collections.Counter()
        seen = max(self.prior.get(key, 0), 1)

        support: collections.Counter = collections.Counter()
        types: collections.Counter = collections.Counter()
        proposals: list[Proposal] = []
        for name, codelet in self._codelets().items():
            proposal = codelet(view, node, regions, goal)
            if proposal is None:
                continue
            # A codelet's voice is its own strength times how often this kind of
            # problem rewarded it before. A codelet never yet useful here is not
            # silenced, only quiet.
            trust = (learned.get(name, 0) + 0.5) / (seen + 1.0)
            proposals.append(proposal)
            support[proposal.symbol] += proposal.strength * trust
            if proposal.source >= 0 and view.types[proposal.source] is not None:
                types[TYPE_TO_ID[view.types[proposal.source]]] += \
                    proposal.strength * trust

        if not support:
            return ABSTAIN, ABSTAIN

        temperature = _temperature(proposals, support)
        # A cold workspace commits: sharpen the distribution as it settles.
        sharpened = {s: w ** (1.0 / max(temperature, 0.15))
                     for s, w in support.items()}
        settled = 1.0 - temperature
        confidence = (self.confidence_map(settled) if self.confidence_map.fitted
                      else min(0.15 + 0.75 * settled, 0.9))
        for _ in range(self.rounds - 1):
            temperature *= 0.8                    # further settling, bounded
        type_votes = ((dict(types), min(confidence, 0.85)) if types else ABSTAIN)
        return (sharpened, confidence), type_votes

    def n_symbolic_parameters(self) -> int:
        return sum(len(v) for v in self.policy.values()) + len(self.prior)

    def render(self) -> str:
        """The policy: for each kind of problem it found, how it decided to work."""
        lines = [f"=== {len(self.policy)} inferred goal signatures ===",
                 "(region, parent type, slot, parallel?, peer?, regions)"
                 "  ->  codelet: hit rate"]
        rows = sorted(self.policy.items(), key=lambda kv: -self.prior.get(kv[0], 0))
        for key, counter in rows[:20]:
            seen = max(self.prior.get(key, 0), 1)
            best = ", ".join(f"{name}:{count / seen:.2f}"
                             for name, count in counter.most_common(3))
            region = key[0]
            name = (self.tok.itos[region] if self.tok and region is not None
                    and region < len(self.tok.itos) else region)
            lines.append(f"  ({name!r}, {key[1]}, slot={key[2]}, par={key[3]}, "
                         f"peer={key[4]}, n={key[5]})  ->  {best or '(none)'}"
                         f"   [{seen}x]")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# inferring the objective, and carving the workspace
# ---------------------------------------------------------------------------
def _partition(view: GraphView) -> list[Region]:
    """Top-level fields become regions; everything below joins its region.

    The number of regions is whatever the episode has. That is the point: a
    scene-and-query episode gets two, a six-step proof gets six, and nothing
    about the partition was decided in advance.
    """
    roots = [i for i in range(len(view)) if view.parent[i] >= 0
             and view.parent[view.parent[i]] < 0]
    if not roots:
        roots = [0] if len(view) else []
    owner: dict[int, int] = {}
    regions = [Region(label=view.labels[r], root=r) for r in roots]
    index = {r: k for k, r in enumerate(roots)}

    for i in range(len(view)):
        node, guard = i, 0
        while node >= 0 and node not in index and guard < len(view):
            node = view.parent[node]
            guard += 1
        if node in index:
            owner[i] = index[node]
            regions[index[node]].nodes.append(i)
    return regions


def _region_of(node: int, regions: Sequence[Region]) -> Region | None:
    for region in regions:
        if node in region.nodes:
            return region
    return None


def _shape(view: GraphView, region: Region, limit: int = 24) -> tuple:
    """A region's shape: types and slots, no labels.

    The region root's *own* slot is normalised away. It says where the region
    sits among its siblings, not what the region looks like inside, and leaving
    it in means two identically shaped regions never match: on ``unification``
    the ``fact`` and ``pattern`` subtrees are the same shape in every respect
    except that one is the record's first field and the other its second, which
    was enough to stop the mirror codelet firing on the one lesson it exists for.
    """
    return tuple((view.types[i] or "mask",
                  -1 if i == region.root else min(view.slot[i], 6))
                 for i in region.nodes[:limit])


def _parallel(a: tuple, b: tuple) -> bool:
    """Whether two region shapes correspond, treating a hidden node as a wildcard.

    Exact equality is the wrong test and fails in exactly the case that matters.
    The node being asked about is masked, so its type reads ``mask`` while its
    counterpart in the other region reads ``ident`` — and the two regions the
    engine most needs to align are the one containing the question and the one
    containing its answer. A hidden slot must therefore match anything, which is
    sound: the engine is claiming the regions have the same shape, and a slot it
    cannot see is no evidence against that.
    """
    if len(a) != len(b) or not a:
        return False
    for (type_a, slot_a), (type_b, slot_b) in zip(a, b):
        if slot_a != slot_b:
            return False
        if type_a != type_b and "mask" not in (type_a, type_b):
            return False
    return True


def _infer_goal(view: GraphView, node: int, regions: Sequence[Region]) -> Goal:
    """Work out what is being asked, from the tree and nothing else."""
    here = _region_of(node, regions)
    parallel = False
    if here is not None:
        shape = _shape(view, here)
        parallel = any(other is not here and _parallel(_shape(view, other), shape)
                       for other in regions)
    p = view.parent[node]
    return Goal(
        region=here.label if here else None,
        parent_type=(view.types[p] or "mask") if p >= 0 else "ROOT",
        slot=view.slot[node],
        has_parallel=parallel,
        has_peer=_peer(view, node, regions, None) is not None,
        n_regions=len(regions),
    )


# ---------------------------------------------------------------------------
# codelets
# ---------------------------------------------------------------------------
def _mirror(view: GraphView, node: int, regions: Sequence[Region],
            goal: Goal | None) -> Proposal | None:
    """Align this region with a structurally parallel one and read across.

    The operator the workspace exists for. On an episode stating a fact and a
    pattern over the same shape, the hidden node's counterpart in the other
    region *is* the answer, and finding it needs no knowledge of what any of it
    means — only that the two regions have the same shape.
    """
    here = _region_of(node, regions)
    if here is None:
        return None
    shape = _shape(view, here)
    position = here.nodes.index(node) if node in here.nodes else -1
    if position < 0:
        return None
    for other in regions:
        if other is here or not _parallel(_shape(view, other), shape):
            continue
        if position < len(other.nodes):
            label = view.labels[other.nodes[position]]
            if label is not None:
                return Proposal(label, 1.0, "mirror", other.nodes[position])
    return None


def _peer(view: GraphView, node: int, regions: Sequence[Region],
          goal: Goal | None) -> Proposal | None:
    """The same slot of another subtree whose head matches."""
    p = view.parent[node]
    if p < 0 or view.labels[p] is None:
        return None
    head, slot = view.labels[p], view.slot[node]
    for other in range(len(view)):
        if other != p and view.labels[other] == head:
            kids = view.children(other)
            if slot < len(kids) and view.labels[kids[slot]] is not None:
                return Proposal(view.labels[kids[slot]], 0.9, "peer", kids[slot])
    return None


def _echo(view: GraphView, node: int, regions: Sequence[Region],
          goal: Goal | None) -> Proposal | None:
    """The commonest label at this depth within the same region."""
    here = _region_of(node, regions)
    if here is None:
        return None
    depth = view.depth[node]
    peers = [i for i in here.nodes if i != node and view.depth[i] == depth
             and view.labels[i] is not None]
    if not peers:
        return None
    counts = collections.Counter(view.labels[i] for i in peers)
    symbol, count = counts.most_common(1)[0]
    source = next(i for i in peers if view.labels[i] == symbol)
    return Proposal(symbol, min(0.3 + 0.1 * count, 0.7), "echo", source)


def _parent(view: GraphView, node: int, regions: Sequence[Region],
            goal: Goal | None) -> Proposal | None:
    p = view.parent[node]
    if p < 0 or view.labels[p] is None:
        return None
    return Proposal(view.labels[p], 0.35, "parent", p)


def _sibling(view: GraphView, node: int, regions: Sequence[Region],
             goal: Goal | None) -> Proposal | None:
    for j in view.siblings(node):
        if view.labels[j] is not None:
            return Proposal(view.labels[j], 0.4, "sibling", j)
    return None


def _frame(view: GraphView, node: int, regions: Sequence[Region],
           goal: Goal | None) -> Proposal | None:
    """Whatever else fills this slot anywhere in the episode."""
    slot = view.slot[node]
    peers = [i for i in range(len(view))
             if i != node and view.slot[i] == slot and view.labels[i] is not None
             and view.depth[i] == view.depth[node]]
    if not peers:
        return None
    counts = collections.Counter(view.labels[i] for i in peers)
    symbol, count = counts.most_common(1)[0]
    source = next(i for i in peers if view.labels[i] == symbol)
    return Proposal(symbol, min(0.25 + 0.05 * count, 0.6), "frame", source)


def _temperature(proposals: Sequence[Proposal],
                 support: collections.Counter) -> float:
    """How unsettled the workspace is: 0 when the codelets agree, 1 when they
    are scattered.

    The normalised entropy of the support distribution, which is exactly the
    quantity Copycat's temperature stands for — how far the workspace is from
    having made up its mind — and it falls of its own accord as agreement rises.
    """
    total = sum(support.values())
    if total <= 0 or len(support) <= 1:
        return 0.25 if proposals else 1.0
    entropy = -sum((w / total) * math.log2(w / total) for w in support.values() if w > 0)
    return max(0.0, min(entropy / math.log2(len(support)), 1.0))
