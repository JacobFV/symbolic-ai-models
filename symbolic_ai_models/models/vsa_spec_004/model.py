"""Roles derived from the graph instead of drawn from a hat — and which graph
quantity turns out to be the right one.

``tests/test_vsa_perm.py`` pins the defect the whole ``vsa_*`` family inherits.
A role is the elementwise product of four independent random atoms indexed by
``(ptype, slot, depth, arity)``, so at ``d = 4096`` its inner product against
another role is ``4096 +/- 0`` on an exact tuple match and ``4 +/- 60``
otherwise. Sixty-six sigma, and nothing in between.

That matters because of an identity the algebra hands us for free. The codebook
is bipolar, so ``cb[s] ** 2 == 1`` elementwise, and a masked node's own binding
is never in the trace. Therefore::

    probe    = role(i) * trace = sum_j role(i) * role(j) * cb[label_j]
    score(s) = <cb[s], probe> = sum_{j: label_j = s} <role(i), role(j)> + noise

**The candidate score is the role Gram matrix**, exactly, up to crosstalk. Every
property of the retrieval is a property of that matrix, so replacing the role
construction and touching nothing else swaps a 0/1 partition for whatever Gram
the new construction has. The comparison is clean by arithmetic rather than by
care, and that is what makes this family a controlled experiment rather than a
pile of variants.

Which continuous structure? The measurement that decided it
-----------------------------------------------------------
The obvious construction is the **Laplacian eigenmap** — the low eigenvectors of
``L = D - A`` place structurally similar positions near each other, and "two
steps away in the tree" is what every hand-written back-off ladder in this repo
has been approximating. That was the pre-registered hypothesis
(``notes/decisions/2026-08-13-spectral-roles-preregistration.md``), and a
diagnostic run before the sweep refuted it hard enough to change the design.

On 550 masked nodes of a three-lesson slice, measuring where the answer actually
sits (slice numbers, used only to size the design — every reported result comes
from the full sweep):

============================================================  ============
question                                                       answer
============================================================  ============
the graph-**nearest** visible node carries the answer          **0.000**
hop distance to the nearest visible node that does             2, 4, 6 or 7
no visible node carries the answer at all                      0.575
a visible carrier shares the query's exact role tuple          0.140
============================================================  ============

A diffusion kernel puts its mass on hop 1. The answer is **never** at hop 1 —
the tree alternates functor and argument nodes, so a label-carrying node is
always an even number of hops from another one. Graph *proximity* is not merely
uninformative here, it is pointed at exactly the wrong nodes. Raw retrieval
accuracy, arg-max over the Gram with no gate and no back-off, on the same slice:

=========================================================  ==========
role Gram                                                  raw top-1
=========================================================  ==========
product of four random atoms (``vsa-002``)                   0.100
diffusion locality, ``t = 4`` (``vsa_spec-004``)             **0.005**
**sum** of the same four atoms (``vsa_sum-004``)             **0.185**
heat-kernel signature (``vsa_hks-004``)                      **0.149**
=========================================================  ==========

Two separate things fall out of that, and the family below is built to measure
each against the other on the full curriculum:

**Graded beats partitioned, using the very same coordinates.** Superposing the
four atoms instead of *binding* them turns ``<role_i, role_j>`` into
``d * (how many of the four coordinates agree)`` — a back-off ladder expressed
as one vector, with no graph and no eigendecomposition anywhere. That is
``vsa_sum-004``, and it is a two-character change to ``vsa-002``: ``*`` becomes
``+``.

**The graph-derived embedding that works is structural, not positional.** The
**heat-kernel signature** ``h_i(t) = sum_k exp(-t lam_k) u_k[i]^2`` is a node's
own diffusion profile: how much heat stays at ``i`` after time ``t``, read at
several ``t``. It is a spectral quantity of the graph, it is invariant under
graph automorphism, and it says two nodes are alike when they sit in *similar
local structure* — whether or not they are anywhere near each other. That is
what a role is supposed to mean, and unlike the eigenmap it does not confuse
"same kind of position" with "same place". ``vsa_hks-004`` beats the hand-built
tuple's partition using **nothing but the graph**: no ``ptype``, no ``slot``, no
``depth``, no ``arity``.

The eigenmap arm is kept and registered anyway, because a pre-registered
prediction that failed is a result and deleting it would be the kind of tidying
this repo has a rule against.

How a feature vector becomes a hypervector
-------------------------------------------
Two encodings, each chosen so the Gram is the kernel we mean:

*Linear*, for the eigenmap, whose features already carry the kernel in their
inner product. ``phi_i = psi_i / ||psi_i||`` with
``psi_i = (U[:, :m] diag(exp(-t lam / 2)))_i``, then ``role_i = sign(phi_i @ R)``
for a fixed bipolar ``R``. Gives ``<role_i, role_j> ~ d (2/pi) arcsin(K_ij)``
with ``K`` the correlation-normalised diffusion kernel: PSD, unit diagonal, no
bandwidth knob.

*Random Fourier features*, for the signature, whose features are a point in
``R^T`` and want a distance-decaying kernel over it.
``role_i = sign(cos(x_i @ W / s + b))`` with ``W`` standard normal and ``b``
uniform gives ``<role_i, role_j> ~ d (2/pi) arcsin(exp(-||x_i - x_j||^2 / 2s^2))``.

Both take ``sign`` at the end so the algebra stays bipolar and the crosstalk
statistics are *identical* to ``vsa-002``'s — the only difference between the
models is the Gram. The arcsine is monotone and therefore cannot reorder
candidates; it costs contrast, not ranking.

What is fitted, and the harness trap found on the way
------------------------------------------------------
Each construction has at most **one** knob — the eigenmap's diffusion time, the
signature's bandwidth; ``vsa_sum-004`` has none — and it is chosen on held-out
*training* episodes by the log-likelihood of the **calibrated mixture**, which
is the model that actually ships. Everything else, including the cleanup's
softmax temperature, is held at ``vsa-002``'s value, so a ``-004`` row is the
same machine with a different role Gram and nothing else.

That last sentence started life as a correction to a disaster and ended as the
ninth slice artifact in this repo's history. Both halves are worth keeping.

The first version fitted the temperature too, and on a three-lesson diagnostic
every graded construction ran to the flattest corner of the grid: 0.126 held-out
*training* accuracy at ``(knob 1.0, sharpness 12)`` became **0.040** at
``(4.0, 3)``, which is what the likelihood chose. The mechanism was legible —
*a flat softmax over a graded Gram is an episode unigram*, an excellent density
estimate and a terrible classifier — so rather than fix it in silence,
``vsa_hks_ll-004`` was registered to price the decision at full scale.

**On all 179 lessons the likelihood picks sharpness 12 by itself**, and
``vsa_hks_ll-004`` comes out bit-identical to ``vsa_hks-004``: 0.242 label,
+0.115 lift, 6.643 bits, 0.213 copy, on every digit. The trap is real on three
lessons and absent on a hundred and seventy-nine. Fixing the temperature remains
the right design — it removes a degree of freedom the ``-002`` family does not
have, which is what makes a ``-004`` row a clean contrast — but it is a *design*
argument and not, as the slice claimed, a rescue.

The controls
------------
``vsa_spec_shuf-004`` and ``vsa_hks_shuf-004`` permute the feature rows across
the episode's nodes. The multiset of coordinates is untouched, so the entire
distribution of pairwise Gram values survives *bit-identically* — same values,
same effective sharpness, same statistics into the gate — and only the
correspondence between a coordinate and the node it describes is destroyed. If a
shuffled row matches its treatment, the embedding contributed nothing. This repo
has been saved by exactly this shape of control more than once.

Every model is registered twice, with and without ``structural_fallback``,
because that shared lookup donates a memorising floor to treatment and control
alike and has flipped the sign of an effect here before.

The cost, stated rather than hidden
-----------------------------------
Per episode this pays one ``eigh`` on an ``n x n`` matrix and one ``(n x k) @
(k x d)`` projection, against ``vsa-002``'s four dictionary lookups per node. It
is the first thing in this family superlinear in *nodes*. ``scripts/vsa_dim_curve.py``
prices it: accuracy, bits and tokens/sec on one curve, with a point chosen to be
deliberately too expensive so the curve has a right-hand end.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import GraphView
from ..vsa_002.model import VSAModel, _bipolar
from ..vsa_perm_002.model import VSAPerm

__all__ = ["RoleEmbedding", "VSAAtomRoles", "VSASum", "VSASumPure",
           "VSASpectral", "VSASpectralPure", "VSASpectralShuffled",
           "VSASpectralShuffledPure", "VSASpectralMix", "VSASpectralMixPure",
           "VSAHKS", "VSAHKSPure", "VSAHKSShuffled", "VSAHKSShuffledPure",
           "VSAHKSLikelihood", "VSAHKSLikelihoodPure", "VSAHKSSum",
           "VSAHKSSumPure", "VSAPermSpectral", "VSAPermSpectralPure",
           "VSAPermHKS", "VSAPermHKSPure",
           # the refuter's rows; see the block at the foot of this module
           "NullRoles", "VSANull", "VSANullPure", "VSAHKSWide", "VSAHKSWidePure",
           "VSASpectralWidePure", "VSASpectralShuffledMatchedPure"]


def _shape_hash(parent: Sequence[int]) -> int:
    """A stable 64-bit digest of a tree's shape.

    ``hash()`` on a tuple of ints is deterministic in CPython but is not
    promised to be, and the shuffle has to be **identical between fitting and
    prediction** or the control is a different model in each phase. FNV-1a,
    written out, because that promise is worth eight lines.
    """
    h = 0xCBF29CE484222325
    for p in parent:
        v = int(p) & 0xFFFFFFFF
        for _ in range(4):
            h = ((h ^ (v & 0xFF)) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
            v >>= 8
    return h


def _laplacian_spectrum(view: GraphView) -> tuple[np.ndarray, np.ndarray]:
    """``(U, lam)`` of the normalised Laplacian of the episode's tree.

    Only parent-child edges. The ``same_label`` coreference edges in
    ``view.rel`` are visible and would be admissible, but ``relation_matrix``
    withholds them for exactly the hidden nodes being queried, so they can move
    a query's *neighbours* around and never the query itself: a confound with no
    upside. Recorded in the pre-registration note.
    """
    n = len(view)
    adjacency = np.zeros((n, n), dtype=np.float64)
    for i, p in enumerate(view.parent):
        if 0 <= p < n and p != i:
            adjacency[i, p] = adjacency[p, i] = 1.0
    degree = adjacency.sum(axis=1)
    inverse = np.zeros(n, dtype=np.float64)
    np.divide(1.0, np.sqrt(degree), out=inverse, where=degree > 0)
    laplacian = np.eye(n) - inverse[:, None] * adjacency * inverse[None, :]
    # Symmetrise against float drift: `eigh` reads one triangle, and a
    # non-symmetric input would be silently reinterpreted rather than rejected.
    lam, vec = np.linalg.eigh(0.5 * (laplacian + laplacian.T))
    return vec, np.clip(lam, 0.0, None)


class RoleEmbedding:
    """Role vectors from *something*, with the two scalars fitted honestly.

    A mixin over either VSA base class, because the same fitting code has to sit
    under ``VSAModel`` (role channel only) and under ``VSAPerm`` (role channel
    plus permutation), and a copy would let the two drift.

    A subclass supplies :meth:`_role_matrix`, an ``(n, d)`` array of role
    vectors for one view, and optionally a one-element knob grid. Everything
    else — the cache, the joint fit of ``(knob, sharpness)``, the parameter
    count, persistence — is shared.
    """

    #: Values the role construction's own knob is searched over. One element
    #: means the construction has no knob at all and nothing is fitted --
    #: ``vsa_sum-004`` is that case, and is therefore an exactly matched
    #: contrast against ``vsa-002``.
    knob_grid: tuple[float, ...] = (1.0,)
    #: Softmax temperatures, searched **only** when :attr:`fit_sharpness` is on.
    #: Off everywhere except ``vsa_hks_ll-004``, which exists to price it; see
    #: that class for the 3x accuracy swing turning it on produces.
    sharpness_grid: tuple[float, ...] = (3.0, 6.0, 12.0, 24.0, 48.0)
    fit_sharpness = False
    #: Permute the feature rows across nodes: the control. See the module doc.
    shuffle_coordinates = False
    #: Off only for a diagnostic; every registered model fits.
    fit_knobs = True
    #: How many eigenvectors the spectral constructions keep.
    n_eig_default = 32

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.n_eig = int(cfg.get("vsa_n_eig", self.n_eig_default))
        self._knob = float(cfg.get("vsa_knob", self.knob_grid[0]))
        self._proj: np.ndarray | None = None
        self._fourier: tuple | None = None
        self._cache: tuple | None = None

    # ---- encodings -------------------------------------------------------
    def _projection(self, k: int, salt: int) -> np.ndarray:
        """A fixed ``(k, d)`` matrix, regenerated from the seed, never stored.

        Same reasoning as :meth:`VSAModel.symbolic_state`, which found 177MB per
        checkpoint of regenerable noise: a matrix that is a pure function of an
        integer is an integer.
        """
        if self._proj is None or self._proj.shape[0] < k:
            self._proj = _bipolar(np.random.default_rng(self.seed + salt),
                                  max(k, self.n_eig), self._d)
        return self._proj[:k]

    def _linear_encode(self, features: np.ndarray) -> np.ndarray:
        """``sign(X R)``: Gram is ``d (2/pi) arcsin(<x_i, x_j>)``.

        For features whose *inner product* is already the kernel we mean.
        """
        out = np.sign(features @ self._projection(features.shape[1], 3))
        out = out.astype(np.float32)
        out[out == 0.0] = 1.0
        return out

    def _fourier_encode(self, features: np.ndarray) -> np.ndarray:
        """``sign(cos(X W / s + b))``: Gram is ``d (2/pi) arcsin(exp(-r^2/2s^2))``.

        For features that are a point in ``R^k`` and want a distance-decaying
        kernel over it. ``W`` standard normal and ``b`` uniform is the standard
        random-Fourier construction; ``sign`` at the end is what keeps the
        algebra bipolar and the crosstalk identical to ``vsa-002``'s.
        """
        k = features.shape[1]
        if self._fourier is None or self._fourier[0] != k:
            rng = np.random.default_rng(self.seed + 4)
            self._fourier = (
                k, rng.normal(size=(k, self._d)).astype(np.float32),
                rng.uniform(0.0, 2.0 * np.pi, size=self._d).astype(np.float32))
        _, weights, phase = self._fourier
        scale = self._knob * math.sqrt(k)
        out = np.sign(np.cos(features @ weights / scale + phase))
        out = out.astype(np.float32)
        out[out == 0.0] = 1.0
        return out

    # ---- the per-view role matrix ---------------------------------------
    def _role_matrix(self, view: GraphView) -> np.ndarray:
        raise NotImplementedError

    def _shuffled(self, view: GraphView, features: np.ndarray) -> np.ndarray:
        """Permute the feature rows, deterministically in the graph's shape."""
        if not self.shuffle_coordinates:
            return features
        rng = np.random.default_rng(
            [self.seed + 5, len(view), _shape_hash(view.parent) % (2 ** 32)])
        return features[rng.permutation(len(view))]

    def _roles_for(self, view: GraphView) -> np.ndarray:
        """``(n, d)``, cached per view and per knob.

        The cache holds the view itself, not merely its ``id``: dropping the
        reference would let the object be collected and a later view reuse the
        address, which is a silent wrong-answer bug rather than a crash.
        """
        if (self._cache is not None and self._cache[0] is view
                and self._cache[1] == self._knob):
            return self._cache[2]
        roles = self._role_matrix(view)
        self._cache = (view, self._knob, roles)
        return roles

    def _role(self, view: GraphView, node: int) -> np.ndarray:
        return self._roles_for(view)[node]

    def _atom_role(self, view: GraphView, node: int) -> np.ndarray:
        """``vsa-002``'s role: the product of four independent random atoms."""
        return super()._role(view, node)

    # ---- fitting ---------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Fit as the parent does, then fit the two scalars, then refit the gate.

        The gate maps the cleanup's peak score to a mixing weight, and moving
        either scalar moves every score, so a gate fitted under the provisional
        values is stale the moment they change. Refitting is a second pass over
        the same held-out fifth of the training episodes; threading the scalars
        into the parents' ``learn`` bodies instead would mean overriding two
        different ones, which is how this family's variants would drift apart.
        """
        super().learn(episodes, tok)
        if not self.fit_knobs:
            return
        cut = max(int(len(episodes) * 0.8), 1)
        held_out = episodes[cut:] or episodes
        self._fit_scalars(held_out, tok)
        self._fit_gate(held_out, tok)

    def _predict_context(self, view: GraphView):
        """Whatever this class's ``_label_votes`` takes as its third argument.

        ``VSAModel`` passes a trace; ``VSAReach`` passes a ``_State`` holding two
        traces and two address codebooks. The fit has to build one without
        knowing which parent it is sitting under.
        """
        builder = getattr(self, "_state", None)
        return builder(view) if builder is not None else self._trace(view)

    def _probe_for(self, view: GraphView, node: int, context) -> np.ndarray:
        builder = getattr(self, "_probe_vector", None)
        return (builder(view, node, context) if builder is not None
                else self._probe(view, node, context))

    def _fit_scalars(self, episodes: Sequence[Episode],
                     tok: SymbolTokenizer) -> None:
        """Pick the construction's knob by the held-out likelihood of the
        *deployed* model — the calibrated mixture, not the bare cleanup.

        Two corrections are baked into that sentence and both were expensive.

        **Score the model that ships.** The first version selected on the
        log-mass the *bare cleanup* put on the right symbol. A bare cleanup that
        is confident and wrong pays ``log(1e-6) = -13.8``, because a floor has to
        be there for the log to exist — but the deployed model never pays it:
        :class:`MassCalibrator` mixes the cleanup with the shared back-off, so a
        confident wrong answer costs ``log(backoff)``. Selecting on the bare
        cleanup prices a risk the model does not take. What is used instead is
        exactly the objective the calibrator already maximises, read out rather
        than thrown away::

            c(s) = argmax_c sum_i log[(1 - c) b_i + c q_i]      (the gate)
            LL   = sum_i log[(1 - c(s_i)) b_i + c(s_i) q_i]     (selected on)

        **Do not put the temperature in the same grid — on three lessons.**
        Fixing that and then fitting ``(knob, sharpness)`` jointly chose the
        degenerate corner on a three-lesson diagnostic: a flat softmax over a
        graded Gram is an *episode unigram*, a genuinely good density estimate
        and a terrible classifier. Held-out **training** episodes, three lessons,
        ``vsa_hks-004``:

        ==========  =========  ============
        knob        dev acc    mixture LL
        ==========  =========  ============
        0.5          0.123      -4.3813
        **1.0**      **0.126**  **-4.3712**
        2.0          0.126      -4.4335
        4.0          0.064      -4.5288
        ==========  =========  ============

        at sharpness 12, against 0.040 at ``(4.0, 3)`` — which is what the joint
        fit chose. **And on all 179 lessons the joint fit chooses sharpness 12
        anyway**, so ``vsa_hks_ll-004`` is bit-identical to ``vsa_hks-004``.
        The temperature is held fixed here for the design reason — it removes a
        degree of freedom the ``-002`` family does not have — and *not* because
        the slice's 3x swing survived. It did not. Ninth time.

        **Training episodes only.** The calibrator used for selection is fitted
        on the same held-out fifth it scores, which is in-sample for the gate's
        own one-dimensional shape; the gate that ships is refitted afterwards on
        a different masking draw.
        """
        from symbolic_ai_core.calibration import MassCalibrator

        sharpnesses = (self.sharpness_grid if self.fit_sharpness
                       else (self.sharpness,))
        best: tuple[float, float, float] | None = None
        original = self._knob
        try:
            for knob in self.knob_grid:
                self._knob = knob
                rows: list[tuple] = []
                for view, targets in self.training_views(
                        episodes, tok, repeats=1, seed=23,
                        max_nodes=self.cfg.max_nodes):
                    keep = [(node, int(label))
                            for node, (label, _) in targets.items()
                            if label >= 0]
                    if not keep:
                        continue
                    context = self._predict_context(view)
                    candidates = self._candidates(view)
                    for node, label in keep:
                        sims, cands = self._similarities(
                            self._probe_for(view, node, context), candidates)
                        if sims is None:
                            continue
                        rows.append((sims, cands, label,
                                     self.backoff_prob(view, node, label)))
                for sharp in sharpnesses:
                    scores, votes, backoff = [], [], []
                    for sims, cands, label, prior in rows:
                        table = self._soften(sims, cands, sharp)
                        if not table:
                            continue
                        scores.append(max(table.values()))
                        votes.append(float(table.get(label, 0.0)))
                        backoff.append(prior)
                    if not scores:
                        continue
                    gate = MassCalibrator().fit(scores, votes, backoff)
                    total = sum(
                        math.log(max((1.0 - gate(s)) * max(b, 1e-12)
                                     + gate(s) * q, 1e-12))
                        for s, q, b in zip(scores, votes, backoff))
                    total /= len(scores)
                    if best is None or total > best[0]:
                        best = (total, knob, sharp)
        finally:
            self._knob = original
            self._cache = None
        if best is not None:
            _, self._knob, self.sharpness = best
            self._cache = None

    # ---- bookkeeping -----------------------------------------------------
    def n_symbolic_parameters(self) -> int:
        """Vectors reached into, plus the two fitted scalars.

        On ``VSAModel``'s convention: a matrix regenerable from a seed costs one
        vector per row rather than its ``d`` signs. The role vectors themselves
        are computed per episode from the graph and are stored nowhere — there
        is no role table here of any size.
        """
        return super().n_symbolic_parameters() + self.n_eig + 2

    def render(self) -> str:
        return "\n".join([
            super().render(),
            f"  role embedding: {type(self).embedding_name}, "
            f"knob={self._knob:.3g}, sharpness={self.sharpness:.3g}"
            f"{' (fitted)' if self.fit_knobs else ''}"
            f"{', SHUFFLED' if self.shuffle_coordinates else ''}",
            "  (the role Gram is the candidate score; see the module docstring)"])

    embedding_name = "abstract"


# ---------------------------------------------------------------------------
# the hand-built atoms, in matrix form
# ---------------------------------------------------------------------------
class VSAAtomRoles(RoleEmbedding, VSAModel):
    """``vsa-002``'s role construction, expressed as a per-view matrix.

    **Deliberately not registered.** Nothing here fits a scalar that ``vsa-002``
    does not — ``knob_grid`` has one element and the temperature is fixed at the
    same 12 — so a registered row would be a duplicate of ``vsa-002`` under a
    second name, which is exactly the kind of thing that makes a comparison table
    stop meaning anything. It exists so that ``vsa_sum-004`` and the mixed rows
    can reach the atoms without reimplementing them.
    """

    LEARNED = VSAModel.LEARNED + ("_knob", "n_eig")
    embedding_name = "random atoms, product (= vsa-002)"

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        return np.stack([self._atom_role(view, j) for j in range(len(view))])

    def n_symbolic_parameters(self) -> int:
        # No projection matrix: this construction never encodes a feature.
        return VSAModel.n_symbolic_parameters(self) + 1


# ---------------------------------------------------------------------------
# graded, without a graph: bind by addition instead of by multiplication
# ---------------------------------------------------------------------------
@register("vsa_sum-004",
          doc="The four role atoms superposed, not bound: a graded partition.")
class VSASum(VSAAtomRoles):
    """``*`` becomes ``+``, and the hard partition becomes a back-off ladder.

    ``role = ptype + slot + depth + arity`` instead of their product, so

        ``<role_i, role_j> = d * (how many of the four coordinates agree)``

    plus a zero-mean cross term. An exact tuple match still scores highest; a
    three-of-four match scores three quarters of it where ``vsa-002`` scored
    noise. That is precisely the back-off ladder ``omegaclaw`` and the copy floor
    write out as a stack of ``if`` statements, expressed as one superposition and
    read out in one multiply.

    It is registered *before* the graph-derived rows on purpose. If the
    interpolation is what pays, this row gets it for two characters and no
    eigendecomposition, and any graph embedding has to beat **this** rather than
    beat the partition. Separating "graded helps" from "graph-derived helps" is
    the only way either claim means anything.

    Nothing at all is fitted here that is not fitted in ``vsa-002``: the knob
    grid has one element and the temperature is the same fixed 12. So this is an
    **exactly matched** contrast — one operator, ``*`` against ``+``, and no
    other difference of any kind.
    """

    embedding_name = "random atoms, superposed"

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        from symbolic_ai_core.data.graph import TYPE_TO_ID
        out = np.zeros((len(view), self._d), dtype=np.float32)
        for j in range(len(view)):
            parent = view.parent[j]
            ptype = (view.types[parent] or "mask") if parent >= 0 else "ROOT"
            out[j] = (self.roles[f"ptype:{TYPE_TO_ID.get(ptype, 0) % 32}"]
                      + self.roles[f"slot:{min(view.slot[j], 11)}"]
                      + self.roles[f"depth:{min(view.depth[j], 11)}"]
                      + self.roles[f"arity:{min(len(view.children(j)), 5)}"])
        return out


@register("vsa_sum_pure-004",
          doc="vsa_sum-004 without the shared memorising fallback.")
class VSASumPure(VSASum):
    """The graded partition, scored without the floor it would inherit."""

    structural_fallback = False


# ---------------------------------------------------------------------------
# the eigenmap: the pre-registered hypothesis, kept because it failed
# ---------------------------------------------------------------------------
class SpectralLocality(RoleEmbedding):
    """Roles from the diffusion kernel of the tree — position, not structure.

    ``phi_i = psi_i / ||psi_i||`` with
    ``psi_i = (U[:, :m] diag(exp(-t lam / 2)))_i``, encoded linearly. The Gram is
    the correlation-normalised heat kernel, and ``t`` interpolates between two
    named degenerate models: at ``t -> 0`` the identity, a partition *finer* than
    ``vsa-002``'s under which nothing is ever retrieved, and at ``t -> inf``
    all-ones, an episode unigram. Measured mean Gram by hop on 25-to-37-node
    graphs, which is what fixed the grid's endpoints::

        t      hop1    hop2    hop3    hop4
        0.25  +0.096  -0.018  -0.004  -0.003   near-identity
        1.0   +0.253  +0.017  -0.016  -0.002
        4.0   +0.685  +0.442  -0.031  -0.033
        16.0  +0.903  +0.788  +0.312  +0.192
        64.0  +1.000  +1.000  +1.000  +1.000   near-unigram

    The kernel peaks at hop 1 and the answer is never at hop 1 — see the module
    docstring's table. This construction is retained and registered because it
    was pre-registered and refuted, and a refuted prediction that quietly
    disappears is worse than one that scores badly in public.
    """

    knob_grid = (0.25, 1.0, 4.0, 16.0)
    embedding_name = "Laplacian eigenmap, diffusion locality"

    def _features(self, view: GraphView) -> np.ndarray:
        vec, lam = _laplacian_spectrum(view)
        m = min(self.n_eig, len(view))
        phi = vec[:, :m] * np.exp(-self._knob * lam[:m] / 2.0)[None, :]
        norms = np.linalg.norm(phi, axis=1, keepdims=True)
        return phi / np.maximum(norms, 1e-9)

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        return self._linear_encode(self._shuffled(view, self._features(view)))


@register("vsa_spec-004",
          doc="VSA with roles from the graph's Laplacian eigenmap.")
class VSASpectral(SpectralLocality, VSAModel):
    """The pre-registered experiment: graded roles by graph *proximity*."""

    LEARNED = VSAModel.LEARNED + ("_knob", "n_eig")


@register("vsa_spec_pure-004",
          doc="vsa_spec-004 without the shared memorising fallback.")
class VSASpectralPure(VSASpectral):
    """The eigenmap alone, without the memorising floor every row inherits."""

    structural_fallback = False


@register("vsa_spec_shuf-004",
          doc="Control: vsa_spec-004 with the spectral coordinates shuffled.")
class VSASpectralShuffled(VSASpectral):
    """The same coordinates, attached to the wrong nodes.

    Permuting ``phi``'s rows permutes the Gram, so the multiset of pairwise
    similarities is bit-identical — same values, same effective sharpness, same
    statistics into the gate. Only the correspondence between a coordinate and
    the node it describes dies. A control that also changed the score
    distribution would confound the two and a null from it would mean nothing.
    """

    shuffle_coordinates = True


@register("vsa_spec_shuf_pure-004",
          doc="The shuffled eigenmap control without the shared fallback.")
class VSASpectralShuffledPure(VSASpectralShuffled):
    """The control at the same setting as ``vsa_spec_pure-004``."""

    structural_fallback = False


@register("vsa_spec_mix-004",
          doc="VSA with the four role atoms bound, plus eigenmap roles.")
class VSASpectralMix(VSASpectral):
    """``role = atoms + eigenmap``: an exact-tuple match with locality under it.

    Pre-registered as the row most likely to win, on the reasoning that a
    superposition gives a back-off ladder where a product gives a partition. The
    diagnostic that reordered this module says it will not: locality is pointed
    at the wrong nodes, so what sits under the exact-tuple match is noise with
    structure rather than noise. Kept because the prediction was written down.
    """

    embedding_name = "eigenmap + bound atoms"

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        spectral = super()._role_matrix(view)
        return spectral + np.stack([self._atom_role(view, j)
                                    for j in range(len(view))])


@register("vsa_spec_mix_pure-004",
          doc="vsa_spec_mix-004 without the shared memorising fallback.")
class VSASpectralMixPure(VSASpectralMix):
    """The mix, scored without the floor it would otherwise inherit."""

    structural_fallback = False


# ---------------------------------------------------------------------------
# the heat-kernel signature: structure from the graph, not position in it
# ---------------------------------------------------------------------------
class HeatKernelSignature(RoleEmbedding):
    """Roles from each node's own diffusion profile — a spectral *role*.

    ``h_i(t) = sum_k exp(-t lam_k) u_k[i]^2`` is how much heat remains at ``i``
    at time ``t``: small ``t`` sees the node's immediate branching, large ``t``
    sees where it sits in the whole graph. Read at eight log-spaced times it is a
    point in ``R^8``, and it is the standard structural descriptor from spectral
    geometry — invariant under graph automorphism, and equal for two nodes that
    occupy the *same kind of position* however far apart they are.

    That is what a role is supposed to mean, and it is what the eigenmap gets
    wrong: the eigenmap says "near me", the signature says "like me". Nothing in
    it is hand-built — no parent type, no slot, no depth, no arity — so a row
    that beats ``vsa_randfit-004`` is the graph supplying a role decomposition
    that a human wrote down by hand in ``vsa-002``.

    The signature is logged (it spans orders of magnitude) and z-scored per
    episode across nodes, so the encoder's bandwidth means the same thing on a
    twelve-node and a hundred-node graph. Then random Fourier features, whose
    kernel decays with distance in signature space; the bandwidth is the fitted
    knob.
    """

    knob_grid = (0.5, 1.0, 2.0, 4.0)
    signature_times = (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
    embedding_name = "heat-kernel signature"

    def _features(self, view: GraphView) -> np.ndarray:
        vec, lam = _laplacian_spectrum(view)
        squared = vec ** 2
        signature = np.stack(
            [np.log(squared @ np.exp(-t * lam) + 1e-12)
             for t in self.signature_times], axis=1)
        signature -= signature.mean(axis=0, keepdims=True)
        return (signature
                / (signature.std(axis=0, keepdims=True) + 1e-9)).astype(np.float32)

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        return self._fourier_encode(self._shuffled(view, self._features(view)))


@register("vsa_hks-004",
          doc="VSA with roles from each node's heat-kernel signature.")
class VSAHKS(RoleEmbedding, VSAModel):
    """The graph writing its own role decomposition.

    Nothing hand-built enters this model's roles. If it clears
    ``vsa_randfit-004`` on the full curriculum, the claim is that the four
    coordinates ``vsa-002`` asserts are the generator's — parent type, slot,
    depth, arity — are recoverable from the graph's spectrum, *and* recoverable
    in a form that interpolates where the hand-built conjunction cannot.

    What would refute it: landing at or below ``vsa_randfit-004``, or landing
    level with ``vsa_hks_shuf-004``. The second is the one that matters — a
    shuffled signature has the same values in the same distribution attached to
    the wrong nodes, so if it scores the same, the graded Gram was doing the work
    and the graph was decoration.
    """

    LEARNED = VSAModel.LEARNED + ("_knob", "n_eig")

    _features = HeatKernelSignature._features
    _role_matrix = HeatKernelSignature._role_matrix
    knob_grid = HeatKernelSignature.knob_grid
    signature_times = HeatKernelSignature.signature_times
    embedding_name = HeatKernelSignature.embedding_name


@register("vsa_hks_pure-004",
          doc="vsa_hks-004 without the shared memorising fallback.")
class VSAHKSPure(VSAHKS):
    """The signature alone. The row to read for what the embedding is worth."""

    structural_fallback = False


@register("vsa_hks_shuf-004",
          doc="Control: vsa_hks-004 with the signatures shuffled across nodes.")
class VSAHKSShuffled(VSAHKS):
    """The control that decides whether the graph mattered.

    Same signatures, same Gram values, same distribution, wrong nodes. If this
    matches ``vsa_hks-004`` then the finding is about graded Grams and not about
    graphs, and the module docstring is wrong. That is the outcome this row
    exists to be able to report.
    """

    shuffle_coordinates = True


@register("vsa_hks_shuf_pure-004",
          doc="The shuffled signature control without the shared fallback.")
class VSAHKSShuffledPure(VSAHKSShuffled):
    """The control at the same setting as ``vsa_hks_pure-004``."""

    structural_fallback = False


@register("vsa_hks_ll-004",
          doc="vsa_hks-004 with the softmax temperature fitted as well.")
class VSAHKSLikelihood(VSAHKS):
    """Price the harness decision, instead of discovering it in a debugger.

    Every other row here holds the cleanup's softmax temperature at ``vsa-002``'s
    fixed 12, so the ``-004`` family fits nothing the ``-002`` family does not
    beyond a single construction knob. This row adds the temperature to the same
    held-out-likelihood fit — which is the *more* principled thing to do by every
    argument in ``ROADMAP.md``'s design rule 4, and which on held-out training
    episodes moved accuracy from 0.126 to 0.040.

    The mechanism is worth stating because it will recur. A flat softmax over a
    graded Gram is an **episode unigram**: it puts mass on symbols in proportion
    to how often they appear among the visible nodes. That is a genuinely good
    density estimate, so the likelihood wants it, and it is a terrible classifier,
    so the accuracy collapses. It is this repo's oldest measured fact —
    ``label_acc`` and ``label_bits`` rank these models close to inversely —
    showing up as a *fitting* decision rather than as a reporting one.

    Pre-registered: this row should beat ``vsa_hks-004`` on ``label_bits`` and
    lose to it on ``label_acc``. If it loses on both, the temperature is simply
    mis-fitted. If it *matches*, the slice that produced the 0.126-to-0.040
    number was the misleading thing and that is worth knowing too.

    **Measured, all 179 lessons: it matches, on every digit.** 0.242 label,
    +0.115 lift, 6.643 bits, 0.213 copy, +0.009 renaming — identical to
    ``vsa_hks-004``, because the likelihood picks sharpness 12 unprompted. The
    third pre-registered outcome, and the honest reading is the unflattering
    one: the harness trap this row was registered to expose is a three-lesson
    artifact. It is kept registered because the *next* graded construction may
    have a Gram on a different scale, and then the grid will matter again — but
    nothing here should be cited for a temperature effect, because there is not
    one at full scale.
    """

    fit_sharpness = True
    embedding_name = "heat-kernel signature, temperature fitted"


@register("vsa_hks_ll_pure-004",
          doc="vsa_hks_ll-004 without the shared memorising fallback.")
class VSAHKSLikelihoodPure(VSAHKSLikelihood):
    """The calibration comparison without the shared floor under either row."""

    structural_fallback = False


@register("vsa_hks_sum-004",
          doc="Heat-kernel signature roles superposed with the four atoms.")
class VSAHKSSum(VSAHKS):
    """Both graded roles at once: what the graph found, plus what a human wrote.

    ``role = signature + (ptype + slot + depth + arity)``, each channel
    contributing its own graded Gram. If the two describe the same structure,
    this lands between them and the honest reading is redundancy; if they
    describe different structure it should clear both. Equal strength, which is
    a choice and not a fit — ``vsa_full_gated-002`` is the precedent for what
    fitting the balance would cost and for why an unfitted equal share is
    reported as such.
    """

    embedding_name = "heat-kernel signature + superposed atoms"

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        return super()._role_matrix(view) + VSASum._role_matrix(self, view)


@register("vsa_hks_sum_pure-004",
          doc="vsa_hks_sum-004 without the shared memorising fallback.")
class VSAHKSSumPure(VSAHKSSum):
    """Both graded roles, scored without the shared floor."""

    structural_fallback = False


# ---------------------------------------------------------------------------
# on top of the family's best row
# ---------------------------------------------------------------------------
@register("vsa_perm_spec-004",
          doc="vsa_perm-002 with eigenmap roles in its role channel.")
class VSAPermSpectral(SpectralLocality, VSAPerm):
    """The pre-registered eigenmap, beside the permutation channel."""

    LEARNED = VSAPerm.LEARNED + ("_knob", "n_eig")


@register("vsa_perm_spec_pure-004",
          doc="vsa_perm_spec-004 without the shared memorising fallback.")
class VSAPermSpectralPure(VSAPermSpectral):
    """Against ``vsa_perm_pure-002``'s 0.337 at a -0.003 renaming drop."""

    structural_fallback = False


@register("vsa_perm_hks-004",
          doc="vsa_perm-002 with heat-kernel signature roles.")
class VSAPermHKS(RoleEmbedding, VSAPerm):
    """The question the plain contrast cannot answer.

    ``vsa_perm-002`` reached +0.227 label lift by adding a *positional* channel
    beside the role channel, because relative node offset was information the
    role atoms did not encode at all. A signature-based role encodes structural
    equivalence, which is a different axis again. So: do the two compose, or was
    permutation already supplying whatever reach a better role could supply?

    Written down before the sweep, because this is the row most likely to be a
    null and nulls are the easiest thing to explain away afterwards. If it lands
    level with ``vsa_perm-002``, the reading is that the two mechanisms are
    substitutes and the cheaper one wins on cost — which makes the embedding a
    negative result with a price attached, and that is worth reporting.
    """

    LEARNED = VSAPerm.LEARNED + ("_knob", "n_eig")

    _features = HeatKernelSignature._features
    _role_matrix = HeatKernelSignature._role_matrix
    knob_grid = HeatKernelSignature.knob_grid
    signature_times = HeatKernelSignature.signature_times
    embedding_name = HeatKernelSignature.embedding_name


@register("vsa_perm_hks_pure-004",
          doc="vsa_perm_hks-004 without the shared memorising fallback.")
class VSAPermHKSPure(VSAPermHKS):
    """The equivariant row for the family's most capable combination."""

    structural_fallback = False


# ---------------------------------------------------------------------------
# rows added by an independent refuter, 2026-08-14
#
# Everything above this line was written by one agent, including every control.
# These four rows exist because three properties the module asserts about itself
# were unmeasured, and each is written down with its prediction *before* the
# sweep ran (git will say so).
#
# 1. ``vsa_null-004``: the missing reference. The finding note concludes that
#    "the gradedness of the Gram, which the shuffle preserves exactly,
#    contributes nothing on its own" -- from ``vsa_hks_shuf_pure-004`` at
#    -0.071. But there is **no row in this family with no role information at
#    all**, so "contributes nothing" has nothing to be nothing *against*. A
#    shuffled signature does not merely fail to help: it asserts, confidently
#    and gradedly, that unrelated nodes are alike. That is a different failure
#    from having no roles, and only a null row separates them.
# 2. ``vsa_hks_wide-004``: ``knob_grid = (0.5, 1.0, 2.0, 4.0)`` and **all four
#    registered HKS rows fitted 0.5** -- the bottom. By this repo's own
#    [[2026-08-14-a-boundary-optimum-is-not-a-fitted-value]] that is a failed
#    fit until re-run wider, and the lesson was applied to the eigenmap (which
#    lost) and not to the signature (which won).
# 3. ``vsa_spec_wide_pure-004``: the note's own loosest claim, that a wider
#    diffusion grid cannot rescue the eigenmap, is an argument. This measures it.
# 4. ``vsa_spec_shuf16_pure-004``: the shuffled *eigenmap* control refitted its
#    knob to 1 while its treatment fitted 16, so for that pair the "bit-identical
#    Gram multiset" property is false as run --
#    ``test_shuffling_keeps_every_gram_value_and_loses_the_correspondence``
#    cannot see it because it overwrites the control's knob with the
#    treatment's. This row pins the knob and is the matched control.
# ---------------------------------------------------------------------------
class NullRoles(RoleEmbedding):
    """No role information of any kind: i.i.d. bipolar roles, one per node.

    Every off-diagonal Gram entry is ``0 +/- 1/sqrt(d)``, so no node is ever
    retrieved as similar to another and the readout has nothing but its back-off.
    This is what "the embedding contributes nothing" actually looks like, and it
    is the row the shuffled controls should have been read against.

    The draw is seeded from the model seed and an FNV digest of the tree's shape,
    for the same reason the shuffle is: a role that changes between the fit and
    the sweep is a different model in each phase. It is also still a pure
    function of the tree, so the row stays exactly equivariant like the rest.

    **Prediction, written before the sweep.** ``vsa_null_pure-004`` lands
    **above** both shuffled rows and near the floor -- somewhere in
    ``[-0.03, +0.02]`` of label lift -- because abstaining beats retrieving the
    wrong node confidently. *Refuted if* it lands within 0.010 of
    ``vsa_hks_shuf_pure-004``'s -0.071, which would mean the shuffle destroys
    exactly the correspondence and nothing else, and the note's sentence is
    right as written.
    """

    knob_grid = (1.0,)
    embedding_name = "i.i.d. random roles (no structure at all)"

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        rng = np.random.default_rng(
            [self.seed + 6, len(view), _shape_hash(view.parent) % (2 ** 32)])
        return _bipolar(rng, len(view), self._d)


@register("vsa_null-004",
          doc="Reference: i.i.d. random roles, the row with no role information.")
class VSANull(NullRoles, VSAModel):
    """The bottom of the family, so that "contributes nothing" has a value."""

    LEARNED = VSAModel.LEARNED + ("_knob", "n_eig")


@register("vsa_null_pure-004",
          doc="vsa_null-004 without the shared memorising fallback.")
class VSANullPure(VSANull):
    """The reference row for every ``_pure`` lift in this module."""

    structural_fallback = False


@register("vsa_hks_wide-004",
          doc="vsa_hks-004 with the bandwidth grid extended past its boundary fit.")
class VSAHKSWide(VSAHKS):
    """``vsa_hks-004``'s fitted bandwidth sat on the bottom of its grid.

    ``knob`` scales the random-Fourier bandwidth: ``cos(X W / (knob sqrt k))``.
    Smaller ``knob`` means a *faster*-decaying kernel in signature space -- the
    graded signature Gram degenerating toward a partition on near-exact signature
    equality. The likelihood asked for the smallest value on offer, in all four
    registered HKS rows, and nobody extended the grid.

    **Prediction, written before the sweep.** The fit moves interior, to 0.25 or
    0.125, and label lift rises by 0.005 to 0.025 over ``vsa_hks-004``'s +0.115.
    *Refuted if* it stays pinned at 0.5, which retires the objection and makes
    the published +0.115 a genuine fitted optimum. If instead it runs to the new
    bottom as well, the reported figure is not a fit and the direction says the
    signature kernel wants to be a partition -- which sits badly beside the
    module's "graded beats partitioned" reading.
    """

    knob_grid = (0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0)


@register("vsa_hks_wide_pure-004",
          doc="vsa_hks_wide-004 without the shared memorising fallback.")
class VSAHKSWidePure(VSAHKSWide):
    """The equivariant row: against ``vsa_hks_pure-004``'s +0.107."""

    structural_fallback = False


@register("vsa_spec_wide_pure-004",
          doc="vsa_spec_pure-004 with the diffusion-time grid extended upward.")
class VSASpectralWidePure(VSASpectralPure):
    """The measurement the finding note says it did not run.

    ``vsa_spec_pure-004`` fitted ``t = 16``, the top of ``(0.25, 1, 4, 16)``. The
    note argues that extending the grid can only move further toward "the
    embedding contributes nothing", since ``t -> inf`` is the all-ones kernel.
    An argument is not a measurement and the note says so itself.

    **Prediction, written before the sweep.** The fit lands at 64 or above and
    label lift stays below the floor, within 0.02 of the published -0.044.
    *Refuted if* the row clears the floor at any ``t``, which would mean the
    eigenmap was never refuted -- only under-searched.
    """

    knob_grid = (4.0, 16.0, 64.0, 256.0, 1024.0)


@register("vsa_spec_shuf16_pure-004",
          doc="The eigenmap's shuffled control at its treatment's fitted knob.")
class VSASpectralShuffledMatchedPure(VSASpectralShuffledPure):
    """The matched control the eigenmap pair never actually had.

    ``vsa_spec_pure-004`` fitted ``t = 16``; ``vsa_spec_shuf_pure-004`` refitted
    to ``t = 1``. Two different kernels, so for that pair the "the shuffle
    preserves the Gram's value multiset bit-identically" property -- the whole
    reason a shuffle is a control rather than a different model -- is **false as
    run**. Pinning the grid to the single value 16 restores it.

    **Prediction, written before the sweep.** Matched, the shuffled eigenmap
    lands *worse* than the -0.089 the refitted one scored, because the refit was
    free to escape toward a kernel that suits misattributed coordinates. *Refuted
    if* it beats ``vsa_spec_pure-004``'s -0.044, which would say the eigenmap's
    residual signal is not the correspondence either.
    """

    knob_grid = (16.0,)
