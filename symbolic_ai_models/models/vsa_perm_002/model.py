"""Give the VSA the two operators it was missing: permutation, and a transform.

``vsa-002`` encodes an episode as ``trace = sum_j role(j) * filler(j)`` and
answers a masked node by unbinding at its role. Read carefully, that procedure
cannot work, and the diagnostic below says it does not.

Why the unbinding is not an unbinding
-------------------------------------
``VSAModel._trace`` skips every node whose label is ``None``, and the masked node
*is* the node whose label is ``None``. So the masked node's own binding was never
in the trace, and the probe is not a recall — it is entirely crosstalk::

    probe   = role(i) * trace = sum_j (role(i) * role(j)) * cb[label_j]
    score(s) = <cb[s], probe> = sum_{j: label_j = s} <role(i), role(j)> + noise

because ``cb[s] ** 2 == 1`` elementwise. And ``<role(i), role(j)>`` is not a
graded similarity: a role is a *product* of four independent atoms, so it is
``d`` when the two role tuples are identical and a zero-mean random walk
otherwise. Measured at ``d = 4096``:

===================  ==========  ======
``<role_i, role_j>``  mean        sd
===================  ==========  ======
same role tuple       **4096**    0
different tuple       4           60
===================  ==========  ======

Sixty-eight standard deviations. There is no interpolation between neighbouring
cells anywhere in this model: it is a **hard partition**, and the answer it
computes is "the commonest symbol among the visible nodes that share my exact
``(ptype, slot, depth, arity)``". That is a table lookup — precisely the
commitment ``vsa_002``'s docstring says a VSA does not make — and it is a *worse*
lookup than the floor's, because it is keyed on one conjunction with no back-off.

The consequence is the ceiling, not the ranking. On a five-lesson diagnostic
slice, a visible node sharing the query's exact role tuple exists for **37.5%**
of scored masked nodes, and where none exists the model's label accuracy is
**0.000** — 110 of 176 questions answered from pure noise. The copy head sitting
0.115 *below* a fixed-offset floor is not a defect of the pointer readout on top
of a working retrieval; the retrieval has no reach.

(Those are slice numbers and are used here only to size the design. Every number
reported as a result comes from the full-curriculum sweep.)

What is added, and why each is the textbook operator for the job
----------------------------------------------------------------
**Permutation, for sequence and relative position.** The copy floor keys on the
relative *node-index* offset ``i - source`` — and not one of ``vsa-002``'s role
atoms encodes position, so the information the floor wins on is not merely
weighted badly, it is absent. Permutation is the standard third VSA operator
alongside binding and superposition, and it is exactly what encodes order::

    seq      = sum_j rho^j( cb[label_j] )          bind position by permuting
    probe    = sum_k w_k rho^{k-i}( seq )          unbind at the learned offsets

``rho`` is a cyclic shift by one. ``w`` is a distribution over relative offsets,
counted per structural context on training episodes with the same key the copy
floor uses, so the closest structural difference from the floor is that this
**superposes the top routes instead of taking the argmax over them** — which
``vsa_perm_one-002`` below is registered to price, and it turns out to be the
smaller half. A weighted mixture of the
fillers at six different offsets is one ``d``-vector; a table would have to
enumerate them and pick.

**A holistic role transform, for the analogical step.** The query's own role is
the wrong place to look whenever the answer sits somewhere else — which the
37.5% figure says is most of the time. So learn, per context, *which roles the
answer occupies*, and superpose them into one query vector::

    Q_role(i) = role(i) + sum_t w_t role(t)
    probe     = Q_role(i) * trace

``a:b::c:?`` in one multiply, and the ``sum_t`` is the part a table cannot do:
the probe retrieves a weighted mixture of the fillers at *all* the learned routes
simultaneously, in a single elementwise product, and the cleanup grades them.

**A pointer that is cleaned up against addresses, not against fillers.**
``vsa-002``'s ``source_votes`` scores a node by the mass its *label* received, so
the pointer is a re-reading of the label head and inherits everything wrong with
it. Here each visible node has an address in each channel — ``role(j)`` in the
role channel, ``rho^j(base)`` in the position channel — and the pointer is the
ordinary VSA cleanup of the *query* against that address codebook::

    score(j) = <Q_role(i), role(j)> / d  +  <Q_pos(i), rho^j(base)> / d

which is what a pointer should be: pick the address, then read what stands there.

What it bought, on all 179 lessons
----------------------------------
``runs/vsa_reach``, the same config, the same floors and the same evaluation
seeds as every other row in this repo. The ``vsa-002`` rows reproduce their
published numbers to three decimals, so the two families are comparable. Floors:
label 0.143, type 0.860, copy 0.266; copy ceiling 0.722.

=====================  =======  ========  =========  ========  =========  ======
model                  lbl acc  lbl lift  bits lift  copy acc  copy lift  rename
=====================  =======  ========  =========  ========  =========  ======
``vsa-002``              0.219    +0.089     +0.275     0.181     -0.115   0.029
``vsa_pure-002``         0.200    +0.066     +0.259     0.181     -0.115   0.002
``vsa_addr-002``         0.219    +0.089     +0.275     0.210     -0.076   0.029
``vsa_transform-002``    0.242    +0.116     +0.286     0.254     -0.016   0.021
``vsa_perm_one-002``     0.295    +0.178     +0.292     0.301     +0.048   0.006
``vsa_perm-002``         0.326    +0.213     +0.307     0.310     +0.060   0.010
``vsa_perm_pure-002``    0.337    +0.227     +0.293     0.310     +0.060  -0.003
``vsa_full-002``         0.325    +0.212     +0.314     0.300     +0.047   0.010
``vsa_full_gated-002``   0.327    +0.215     +0.316     0.299     +0.045   0.008
``vsa_full_pure-002``    0.328    +0.216     +0.300     0.300     +0.047  -0.000
``corefer-001``          0.357    +0.250     +0.258     0.336     +0.096   0.003
=====================  =======  ========  =========  ========  =========  ======

Five things in that table, and only the first was predicted.

**The copy head crosses its floor**, -0.115 to +0.060, a swing of 0.175 — the
largest single move in this family's history and larger than the whole spread
between the four pointers this repo already had.

**The label head moves further than the copy head did**, +0.089 to +0.213,
because the two are one computation here: reaching further for a *source* is
reaching further for a *symbol*. The family was near-last on accuracy and its
best row is now 0.337 against ``corefer-001``'s 0.357, without giving up the
bits it was already good at.

**The control does not carry it, but it is not nothing either.**
``vsa_addr-002`` — the same channels, only the pointer readout changed — recovers
+0.039 of the copy deficit and stays below the floor, with its label head
untouched to three decimals. So a third of the pointer's problem was that it was
the label head read twice, and two thirds was that it could not reach. Both
halves of the diagnosis are real and the permutation is the bigger one.

**Superposing two channels is worse than the better one alone, and it is not
the arithmetic.** ``vsa_full`` loses 0.013 of copy lift against ``vsa_perm`` and
gains 0.007 of bits. The obvious defence is that a weak channel was given an
equal share of the probe, so ``vsa_full_gated-002`` fits that share on held-out
*training* episodes by held-out likelihood. It lands **interior, at 1.25** — the
likelihood does want a little more position and a little less transform — and
the row moves to +0.215 label and +0.045 copy, still short of ``vsa_perm-002``
on the head the channel was added for. Pre-registered and refuted: the role
transform is genuinely subsumed once relative position is available, not merely
mis-weighted.

**And superposing the *routes* is worth less than it looks.**
``vsa_perm_one-002`` pins ``top_k = 1``, which makes it the copy floor's own rule
— same key, arg-max offset — expressed in hypervectors, and it already reaches
+0.048 copy lift. The mixture over six routes adds +0.012 copy and +0.035 label
on top of that. So the *positional channel* is what was missing and the
superposition is a real but secondary refinement, which is the opposite emphasis
to the one this docstring was drafted with. (The single-route row still clears
the floor it is a copy of because it inherits a back-off ladder the floor does
not have, a graded cleanup and a calibrated gate.)

And one that changes what the family means: **the best rows are the exactly
equivariant ones.** ``vsa_perm_pure-002`` scores 0.337 against ``vsa_perm-002``'s
0.326 at a renaming drop of -0.003, and ``vsa_full_pure-002`` 0.328 against
0.325 at -0.000. For ``vsa-002`` the shared memorising fallback was worth +0.019
of accuracy and all of its renaming sensitivity; for a model that can reach it is
**negative**. It was compensating for a retrieval that could not find anything,
and charging the family its one distinguishing property for the service.

The variants, and which of them are controls
--------------------------------------------
``vsa_addr-002``
    ``vsa-002``'s channels exactly, with the address-based pointer. **The
    control for the readout.**
``vsa_perm-002``
    Role channel plus the permutation channel.
``vsa_transform-002``
    Role channel plus the learned role transforms.
``vsa_full-002``
    All three channels, superposed at equal strength.
``vsa_full_gated-002``
    The same, with the channel balance fitted on held-out training episodes.
    **The control for the combination null**: whether adding a weaker channel
    hurts because it contributes nothing or because it was given too much of the
    probe.
``vsa_perm_one-002``
    ``vsa_perm-002`` with ``top_k = 1``. **The control for superposition**: with
    one route it is the copy floor's own rule, keyed identically, expressed in
    hypervectors instead of a table.
``vsa_addr_pure-002``, ``vsa_perm_pure-002``, ``vsa_full_pure-002``
    The same models with ``structural_fallback`` off, so the algebra is scored
    without the memorising lookup every rule-based model inherits.

Every reaching variant fits **both** route tables regardless of which channels it
reads, so the parameter counts are identical across the family by construction
and a row cannot look cheaper merely by ignoring a channel.
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

import numpy as np

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, Votes
from ..vsa_002.model import VSAModel, _bipolar

__all__ = ["VSAReach", "VSAAddr", "VSAAddrPure", "VSAPerm", "VSAPermOne",
           "VSAPermPure", "VSATransform", "VSAFull", "VSAFullGated",
           "VSAFullPure"]


class _State:
    """Everything about one episode that every hidden node in it shares.

    Built once per :class:`GraphView`: the two superposed traces and the two
    address codebooks. Without this the role of every node would be recomputed
    for every masked node in the same graph, which is quadratic for no reason.
    """

    __slots__ = ("trace", "seq", "roles", "pos", "labels")

    def __init__(self, trace: np.ndarray, seq: np.ndarray, roles: np.ndarray,
                 pos: np.ndarray, labels: list[int | None]) -> None:
        self.trace = trace
        self.seq = seq
        self.roles = roles
        self.pos = pos
        self.labels = labels


class VSAReach(VSAModel):
    """The reaching VSA: role transforms, permutation, address cleanup.

    Subclasses switch the two new channels on and off; nothing else differs
    between them, so the sweep prices each operator on its own.
    """

    LEARNED = VSAModel.LEARNED + ("offsets", "target_roles", "pos_base",
                                  "channel_weight")

    #: Bind relative position by cyclic shift, and probe at the learned offsets.
    use_position = False
    #: Reach for the roles the answer usually occupies, not only the query's own.
    use_transform = False

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: context -> ([(offset, weight)], support)
        self.offsets: dict[tuple, tuple[list[tuple[int, float]], float]] = {}
        #: context -> ([(role tuple, weight)], support)
        self.target_roles: dict[tuple, tuple[list[tuple[tuple, float]], float]] = {}
        #: The generator of the position codebook: ``rho^j(pos_base)``.
        self.pos_base: np.ndarray | None = None
        #: How many routes to superpose. Six, because the diagnostic put ~73% of
        #: the offset mass in the top eight and the tail is noise; not tuned.
        self.top_k = int(cfg.get("vsa_routes", 6))
        #: How much of the probe the position channel gets. ``1.0`` means the
        #: two channels are simply superposed, which is the neutral choice and
        #: is what every variant here uses unless ``fit_channel_weight`` is on.
        self.channel_weight = 1.0

    #: Fit :attr:`channel_weight` on held-out *training* episodes instead of
    #: leaving the channels at equal strength. See :class:`VSAFullGated`.
    fit_channel_weight = False

    # ---- fitting -------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.codebook = self._build_codebook(episodes, tok)
        self.roles = self._build_roles()
        self.pos_base = _bipolar(np.random.default_rng(self.seed + 2), 1,
                                 self._d)[0]
        cut = max(int(len(episodes) * 0.8), 1)
        self._fit_types(episodes, tok)
        # The routes are counted on the first 80% and the mixture gate is fitted
        # on the rest. Fitting both on the same episodes would let the gate see
        # a route table that had already been shown their answers, which is the
        # leak that cost `corefer`'s symbol prior 0.035 of copy accuracy.
        self._fit_reach(episodes[:cut], tok)
        held_out = episodes[cut:] or episodes
        if self.fit_channel_weight:
            self._fit_channel_weight(held_out, tok)
        self._fit_gate(held_out, tok)

    def _fit_channel_weight(self, episodes: Sequence[Episode],
                            tok: SymbolTokenizer) -> None:
        """Pick the channel balance by held-out likelihood, not by a score.

        Design rule 4: fit against a quantity rather than an event. The target
        is the mass the cleanup puts on whichever symbol turned out to be right,
        summed over held-out training nodes — so a probe that ranks the answer
        second is credited for it, which an argmax accuracy would not be.

        A coarse grid, because there is one parameter and a search would be
        false precision. **Training episodes only**; nothing here reads eval.

        The grid runs to 3.0 rather than to 1.0, and that is a correction rather
        than a choice. The first version stopped at 1.0 — "at most an equal
        share" — and the fit landed exactly on the top of it, which made the
        model bit-identical to ``vsa_full-002`` and answered nothing: a boundary
        optimum cannot distinguish "this is the best balance" from "the grid was
        too narrow". Reported as such rather than as a null.

        The grid is swept *inside* the pass over episodes rather than around it.
        Caching a :class:`_State` per view to sweep the grid outside costs two
        ``(n, d)`` matrices per held-out episode — about 3 GB on the full
        curriculum — for a one-parameter fit, which is a memory footprint nobody
        should have to have.
        """
        grid = [step / 4.0 for step in range(0, 13)]
        totals = [0.0] * len(grid)
        seen = 0
        original = self.channel_weight
        try:
            for view, targets in self.training_views(
                    episodes, tok, repeats=1, seed=17,
                    max_nodes=self.cfg.max_nodes):
                keep = [(node, int(label))
                        for node, (label, _) in targets.items() if label >= 0]
                if not keep:
                    continue
                state = self._state(view)
                for i, weight in enumerate(grid):
                    self.channel_weight = weight
                    for node, label in keep:
                        table = self._label_votes(view, node, state)
                        totals[i] += math.log(max(table.get(label, 0.0), 1e-6))
                seen += len(keep)
        finally:
            self.channel_weight = original
        if seen:
            self.channel_weight = grid[max(range(len(grid)),
                                           key=totals.__getitem__)]

    def _role_key(self, view: GraphView, node: int) -> tuple:
        """The four atom indices a node's role is the product of."""
        from symbolic_ai_core.data.graph import TYPE_TO_ID
        parent = view.parent[node]
        ptype = (view.types[parent] or "mask") if parent >= 0 else "ROOT"
        return (TYPE_TO_ID.get(ptype, 0) % 32, min(view.slot[node], 11),
                min(view.depth[node], 11), min(len(view.children(node)), 5))

    def _role_from_key(self, key: tuple) -> np.ndarray:
        out = self.roles[f"ptype:{key[0]}"].copy()
        out *= self.roles[f"slot:{key[1]}"]
        out *= self.roles[f"depth:{key[2]}"]
        out *= self.roles[f"arity:{key[3]}"]
        return out

    @staticmethod
    def _reach_keys(view: GraphView, node: int) -> tuple:
        """A back-off ladder, most specific first.

        The head of it is ``(parent type, slot, depth)``, deliberately the very
        key ``MaskedNode._copy_floor`` uses, so that a route counted here and a
        route counted by the floor are counted over the same partition.

        Stated plainly because it is a difference and not a matched control: the
        floor has **no** ladder — one key and a single global fallback — so a row
        here that clears it is clearing it with a back-off the floor lacks as well
        as with the superposition. ``vsa_perm_one-002`` bounds how much of the
        gain the ladder and the gate can account for, at +0.048 of the +0.060.
        """
        parent = view.parent[node]
        ptype = (view.types[parent] or "mask") if parent >= 0 else "ROOT"
        return ((ptype, min(view.slot[node], 8), min(view.depth[node], 8)),
                (ptype, min(view.slot[node], 8)), (ptype,), ())

    def _fit_reach(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        """Count where the answer stood, per context, on training episodes.

        One unit of credit per *question*, split among the visible nodes that
        turned out to carry the right label — not one unit per correct source.
        Most questions have several valid antecedents and nothing says which was
        meant, and counting each of them whole would weight a question by how
        many answers it happens to have. That is design rule 2 in ``ROADMAP.md``,
        which has twice produced a confident conclusion with the wrong sign here.
        """
        offsets: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        targets_: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(
                episodes, tok, repeats=2, seed=13,
                max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                sources = [j for j in range(len(view))
                           if view.labels[j] is not None
                           and int(view.labels[j]) == int(label_id) and j != node]
                if not sources:
                    continue
                share = 1.0 / len(sources)
                keys = self._reach_keys(view, node)
                for j in sources:
                    role_key = self._role_key(view, j)
                    for key in keys:
                        offsets[key][node - j] += share
                        targets_[key][role_key] += share
        self.offsets = {k: self._top(c) for k, c in offsets.items()}
        self.target_roles = {k: self._top(c) for k, c in targets_.items()}

    def _top(self, counts: collections.Counter) -> tuple[list, float]:
        """The ``top_k`` heaviest routes, renormalised, with the raw support."""
        total = float(sum(counts.values()))
        best = counts.most_common(self.top_k)
        mass = sum(w for _, w in best) or 1.0
        return ([(route, w / mass) for route, w in best], total)

    def _lookup(self, table: dict, view: GraphView, node: int) -> list:
        for key in self._reach_keys(view, node):
            entry = table.get(key)
            if entry and entry[1] >= self.min_support:
                return entry[0]
        return []

    # ---- the algebra ----------------------------------------------------
    def _state(self, view: GraphView) -> _State:
        """The episode's two traces and two address codebooks.

        ``trace`` superposes ``role(j) * filler(j)`` as before; ``seq``
        superposes ``rho^j(filler(j))``, which is the same superposition with
        *permutation* as the binding operator instead of multiplication. Cyclic
        shift is the standard VSA encoding of order, and the reason to use it
        rather than a position atom is that the shifts of one vector are
        near-orthogonal to each other while remaining a group under composition —
        so an offset is a shift, and shifting by ``k - i`` unbinds at offset
        ``k``.
        """
        n = len(view)
        d = self._d
        trace = np.zeros(d, dtype=np.float32)
        seq = np.zeros(d, dtype=np.float32)
        roles = np.zeros((n, d), dtype=np.float32)
        pos = np.zeros((n, d), dtype=np.float32)
        for j in range(n):
            roles[j] = self._role(view, j)
            pos[j] = np.roll(self.pos_base, j)
            label = view.labels[j]
            if label is None or not (0 <= label < len(self.codebook)):
                continue
            code = self.codebook[label]
            trace += roles[j] * code
            if self.use_position:
                seq += np.roll(code, j)
        return _State(trace, seq, roles, pos, list(view.labels))

    def _role_query(self, view: GraphView, node: int) -> np.ndarray:
        """``role(i)`` plus the superposed roles the answer usually occupies.

        One vector standing for several structural routes at once. Unbinding the
        trace with it returns the weighted mixture of what stands at every one of
        them, which is the operation this whole family exists to demonstrate.
        """
        query = self._role(view, node)
        if not self.use_transform:
            return query
        routes = self._lookup(self.target_roles, view, node)
        if not routes:
            return query
        query = query / max(float(np.linalg.norm(query)), 1e-9)
        mixture = np.zeros(self._d, dtype=np.float32)
        for role_key, weight in routes:
            mixture += weight * self._role_from_key(role_key)
        norm = float(np.linalg.norm(mixture))
        if norm > 0.0:
            query = query + mixture / norm
        return query

    def _pos_query(self, view: GraphView, node: int) -> tuple[np.ndarray, list]:
        """``sum_k w_k rho^{i-k}(base)`` — the addresses the answer usually has."""
        routes = self._lookup(self.offsets, view, node) if self.use_position else []
        if not routes:
            return np.zeros(0, dtype=np.float32), []
        query = np.zeros(self._d, dtype=np.float32)
        for offset, weight in routes:
            query += weight * np.roll(self.pos_base, node - offset)
        return query, routes

    def _probe_vector(self, view: GraphView, node: int,
                      state: _State) -> np.ndarray:
        """Superpose the channels' probes, each normalised to unit length.

        The channels carry different numbers of superposed terms, so their raw
        magnitudes are not comparable and normalising first is forced.
        :attr:`channel_weight` is then how much of the probe the position channel
        gets, and it is **1.0 — plain superposition — everywhere except**
        :class:`VSAFullGated`, which fits it on held-out training episodes. It is
        never chosen by looking at a score.
        """
        probe = self._role_query(view, node) * state.trace
        norm = float(np.linalg.norm(probe))
        out = probe / norm if norm > 0.0 else probe
        _, routes = self._pos_query(view, node)
        if routes and self.channel_weight > 0.0:
            shifted = np.zeros(self._d, dtype=np.float32)
            for offset, weight in routes:
                shifted += weight * np.roll(state.seq, offset - node)
            norm = float(np.linalg.norm(shifted))
            if norm > 0.0:
                out = out + self.channel_weight * shifted / norm
        return out

    def _label_votes(self, view: GraphView, node: int,
                     state: _State) -> dict[int, float]:
        return self._cleanup(self._probe_vector(view, node, state),
                             self._candidates(view))

    def _node_scores(self, view: GraphView, node: int,
                     state: _State) -> dict[int, float]:
        """Clean the query up against the **address** codebooks, not the fillers.

        ``<Q_role(i), role(j)>`` is how much of the role query node ``j``'s
        address accounts for, and ``<Q_pos(i), rho^j(base)>`` the same in the
        position channel. A node scores as a copy source by *where it is*, and
        its label is then read off it — which is what separates a pointer from a
        second reading of the label head.

        The softmax sharpness is a set constant, not a fitted one, and it is
        harmless to the reported number: the copy head is scored on the arg-max,
        which no monotone rescaling can move. It matters only to the confidence
        the pointer states.
        """
        scores = state.roles @ self._role_query(view, node) / self._d
        pos_query, routes = self._pos_query(view, node)
        if routes and self.channel_weight > 0.0:
            scores = scores + self.channel_weight * (state.pos @ pos_query
                                                     / self._d)
        out: dict[int, float] = {}
        top = float(scores.max()) if scores.size else 0.0
        for j in range(len(view)):
            if j == node or state.labels[j] is None:
                continue
            weight = float(np.exp((scores[j] - top) * 6.0))
            if weight > 1e-3:
                out[j] = weight
        return out

    # ---- the three heads -------------------------------------------------
    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        from ...calibration import MassCalibrator
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(episodes, tok, repeats=1,
                                                 seed=7,
                                                 max_nodes=self.cfg.max_nodes):
            state = self._state(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                table = self._label_votes(view, node, state)
                if not table:
                    continue
                scores.append(max(table.values()))
                votes.append(float(table.get(int(label_id), 0.0)))
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        self.gate_map = MassCalibrator().fit(scores, votes, backoff)

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        if self.codebook is None or self.pos_base is None:
            return {}
        state = self._state(view)
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            table = self._label_votes(view, i, state)
            type_vote = self._type_vote(view, i)
            if not table or not self.gate_map.fitted:
                out[i] = (ABSTAIN, type_vote)
                continue
            gate = float(self.gate_map(max(table.values())))
            out[i] = ((table, gate) if gate > 0.0 else ABSTAIN, type_vote)
        return out

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        if self.codebook is None or self.pos_base is None:
            return {}
        state = self._state(view)
        out: dict[int, Votes] = {}
        for i in view.hidden:
            by_node = self._node_scores(view, i, state)
            if by_node:
                total = sum(by_node.values()) or 1.0
                peak = max(by_node.values()) / total
                out[i] = (by_node, min(0.15 + 0.8 * peak, 0.95))
        return out

    def n_symbolic_parameters(self) -> int:
        symbols = 0 if self.codebook is None else len(self.codebook)
        routes = sum(len(v[0]) for v in self.offsets.values())
        routes += sum(len(v[0]) for v in self.target_roles.values())
        return symbols + len(self.roles) + routes + 1

    def render(self) -> str:
        channels = ["role"]
        if self.use_position:
            channels.append("permutation")
        if self.use_transform:
            channels.append("transform")
        return "\n".join([
            f"=== {self.name}: channels {'+'.join(channels)}, d={self._d} ===",
            f"  symbols {0 if self.codebook is None else len(self.codebook)}, "
            f"role atoms {len(self.roles)}",
            f"  offset routes {len(self.offsets)} contexts, "
            f"role routes {len(self.target_roles)} contexts",
            f"  top_k {self.top_k}, channel weight {self.channel_weight:.2f}"
            f"{' (fitted)' if self.fit_channel_weight else ''}",
            f"  gate: {'fitted' if self.gate_map.fitted else 'unfitted'}",
            "  (pointer cleans up against addresses, not against fillers)"])


@register("vsa_addr-002",
          doc="VSA control: vsa-002's channels, pointer cleaned up on addresses.")
class VSAAddr(VSAReach):
    """The control, and the row that could embarrass the rest of this module.

    Identical channels to ``vsa-002`` — role only. The single difference is that
    the pointer scores a node by its *address* rather than by the mass its label
    received. If the copy head's -0.115 was a readout defect then this recovers
    it alone, the permutation story is decoration, and the module docstring above
    is wrong about where the problem is.
    """


@register("vsa_perm-002",
          doc="VSA + permutation: relative position bound by cyclic shift.")
class VSAPerm(VSAReach):
    """Adds the operator the family was missing, and the copy floor keys on."""

    use_position = True


@register("vsa_perm_one-002",
          doc="vsa_perm-002 restricted to one route: the copy floor, in vectors.")
class VSAPermOne(VSAPerm):
    """The row that decides whether superposition is doing anything at all.

    ``MaskedNode._copy_floor`` takes the **arg-max** offset for a context and
    copies from there. ``vsa_perm-002`` keys on the identical context and
    superposes the top six, so the *only* structural difference between them is
    the mixture. Pin ``top_k`` to one and the two become the same rule expressed
    in different machinery.

    So this is the control that could sink the claim. If it scores at the floor
    and ``vsa_perm-002`` scores above it, superposing the routes is what pays and
    the algebra earned its place. If it scores level with ``vsa_perm-002``, then
    the gain came from being keyed and gated differently and the mixture is
    decoration — which is the reading to report if it happens.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.top_k = 1


@register("vsa_transform-002",
          doc="VSA + holistic role transform: reach the roles the answer sits at.")
class VSATransform(VSAReach):
    """``a:b::c:?`` in one multiply, with the routes superposed into one vector."""

    use_transform = True


@register("vsa_full-002", doc="VSA with permutation and role transforms both.")
class VSAFull(VSAReach):
    """All three channels. Superposed into one probe, cleaned up once."""

    use_position = True
    use_transform = True


@register("vsa_full_gated-002",
          doc="vsa_full-002 with the channel balance fitted, not assumed equal.")
class VSAFullGated(VSAFull):
    """Is the combination null about the mechanism, or about the arithmetic?

    ``vsa_full-002`` superposes a strong channel (permutation) with a weak one
    (role transform) at equal strength and comes out *below* ``vsa_perm-002``.
    That is the third time this repo has watched a weaker signal added to a
    stronger one make the pair worse, and there are two readings: either the
    role transform genuinely contributes nothing once position is available, or
    unweighted superposition is the wrong way to combine them.

    This separates them. One scalar, fitted on **held-out training episodes** by
    maximising the log-mass the cleanup puts on the symbol that turned out to be
    right — design rule 4, a quantity rather than an event. Written down before
    the number landed:

    * If the fitted weight is interior and the row beats ``vsa_perm-002``, the
      null was arithmetic and the transform is worth keeping.
    * If it runs to the top of the grid, the likelihood wants as much position
      channel as it can get, the transform is being tolerated rather than used,
      and the honest reading of the null is that position subsumes it.

    The first run of this answered neither, because the grid stopped at 1.0 and
    the fit landed on 1.0 — which is exactly what ``vsa_full-002`` already does,
    so the two rows came out bit-identical. That is a mis-specified grid rather
    than a result, and it is recorded here because a boundary optimum reported
    as a null is a mistake this repo would otherwise make twice.
    """

    fit_channel_weight = True


@register("vsa_full_pure-002",
          doc="vsa_full-002 without the shared memorising fallback.")
class VSAFullPure(VSAFull):
    """The algebra alone, with ``structural_fallback`` off.

    Quoted beside ``vsa_full-002`` for the same reason ``vsa_pure-002`` is quoted
    beside ``vsa-002``: every rule-based model inherits a shared lookup table that
    memorises the commonest label per structural context, and it is worth a real
    slice of accuracy that nobody attributes to it.
    """

    structural_fallback = False


@register("vsa_addr_pure-002",
          doc="vsa_addr-002 without the shared memorising fallback.")
class VSAAddrPure(VSAAddr):
    """The equivariance control for the pointer readout.

    ``vsa_pure-002`` establishes that the role channel is exactly equivariant;
    this is the same channel with the address pointer bolted on, so it isolates
    whether *changing how the pointer reads the probe* costs anything. It should
    not: no symbol vector appears in ``_node_scores``, and
    ``test_the_pointer_scores_addresses_and_never_symbol_identity`` checks that
    per node rather than on average.
    """

    structural_fallback = False


@register("vsa_perm_pure-002",
          doc="vsa_perm-002 without the shared memorising fallback.")
class VSAPermPure(VSAPerm):
    """The row that prices the permutation channel's equivariance, on its own.

    Registered because the first small-fixture measurement of ``vsa_full_pure``
    came back at a **0.051** renaming drop where ``vsa_pure-002`` is 0.000, and
    the obvious explanation — superposition crosstalk, which the sequence trace
    has far more of than the role trace since every node contributes to it — was
    checked and **refuted**: raising ``d`` from 4096 to 16384 moved the drop the
    wrong way (0.051 to 0.068). Splitting the channels apart on the full
    curriculum is how the question gets an answer instead of an argument.
    """

    structural_fallback = False
