"""`005`: the intermediate representation as a knob — an atomspace role source.

Read the pre-registration first
(``notes/decisions/2026-08-14-atomspace-metta-ir-preregistration.md``). It was
written before any of this existed and it predicts a **loss** on label accuracy,
with the measured reason: ``omegaclaw_reach-001`` added ``ilp``'s best
discovered operator — a typed, slot-selected sibling firing at 0.803 reliability
— and still lost, +0.226 against +0.234, because ``ilp`` is uniquely right on
only 2.2% of nodes and candidate recall climbing 82.7% -> 98.7% moved accuracy
by 0.000. Reach was never the constraint. So "we can now express more patterns"
predicts almost nothing on the head this repo leads with, and that sentence is
here so the eventual number cannot be read as whatever flatters the line.

The one thing that changes, and everything that does not
---------------------------------------------------------
This family reuses ``vsa_spec_004.RoleEmbedding`` unchanged: the cache, the
held-out knob fit against the *calibrated mixture*, the fixed softmax
temperature of 12, the gate refit, the parameter accounting. The codebook, the
cleanup, the candidate set, the pointer and the back-off are ``vsa-002``'s and
``vsa_perm-002``'s. **The only difference between a ``-005`` row and its
``-002``/``-004`` neighbour is where the role vectors come from**, which is what
makes this a controlled experiment rather than a pile of variants — the same
arithmetic that makes the ``vsa_*`` family one: the candidate score *is* the
role Gram, so replacing the role construction and touching nothing else swaps
one Gram for another.

Here the role of a node is **the set of conjunctive queries it satisfies** in
the atomspace the episode encodes to. Superposed, so

    ``<role_i, role_j> = d * (signature mass shared by i and j)``

which is ``vsa_sum-004``'s graded ladder over a different, larger index set.

What the atomspace can say that the four-tuple cannot
------------------------------------------------------
``vsa-002``'s role asserts the generator's coordinates are ``(ptype, slot,
depth, arity)``. Three groups of signature are added here and each is a
*direction the flat arrays do not have*:

``ct``/``ck`` — **downward.** The type of the child in slot ``k``. Every
    structural key in this repo — ``node_context``, the masked-node floor, the
    shared back-off, ``OmegaClaw.perceive`` — is ``(parent type, slot, depth,
    has children)``: upward, plus one bit of arity. What a node *contains* has
    never been a feature of anything here.

``sb``/``sk`` — **the typed, slot-selected sibling.** ``CLAWS`` has ``sibling0``
    and ``prev_sibling`` and no way to name which sibling, which is why
    ``omegaclaw_reach-001`` needed a new branch to reach ``ilp``'s best clause.
    Here it is ``(child $p $k $q) (child $p $j $s) (: $s $t)`` and the offset
    ``j - k`` is part of the feature: "the sibling two slots to my left, and it
    is a ``pred``".

``gp``/``gt``/``ps`` — **the path, not the position.** ``depth`` says how far
    from the root a node sits; these say what the two steps above it were and
    which slots they came down.

The knob, and why its grid deliberately contains both degenerate ends
----------------------------------------------------------------------
One knob: ``extra_weight``, the mass the three atomspace-only groups get
relative to the four hand-built coordinates. Fitted exactly as every other
``-004`` knob is — held-out *training* episodes, the log-likelihood of the
calibrated mixture, never a score, never eval.

The grid is ``(0.0, 0.25, 0.5, 1.0, 2.0, 4.0)`` and it runs to **zero on
purpose**. At ``0.0`` this model *is* ``metta_tuple-005``, i.e. ``vsa_sum-004``;
at ``4.0`` the extra queries drown the tuple. So the fit can say "the atomspace
bought nothing" in its own voice, and both ends of the grid are named degenerate
models rather than arbitrary stopping points.

``notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value.md`` is the
reason that sentence is here: ``vsa_full_gated-002`` fitted a share on a grid
that stopped at 1.0, landed on 1.0, and came out bit-identical to the unweighted
row — a whole experiment spent on a boundary reported as a fit. A knob landing
on ``0.0`` or ``4.0`` here **is reported as a boundary**, not as a value.

Cosine, and the row that does not use it
-----------------------------------------
The rich schedule gives different nodes different numbers of signatures — a node
with six children has more ``ct`` solutions than a leaf — so an unnormalised
superposition would give busy nodes a higher Gram against everyone. That is a
popularity bias, not a role. The rich rows therefore normalise each role to norm
``sqrt(d)``, making the Gram a cosine.

``metta_tuple-005`` does **not** normalise, because every node has exactly four
signatures under :data:`TUPLE_QUERIES` and switching normalisation on there
would turn the contrast against ``vsa_sum-004`` from "the query schedule" into
"the query schedule and the normalisation".

The harness check this whole line rests on
--------------------------------------------
``metta_tuple-005`` re-expresses ``vsa-002``'s four coordinates as queries over
the atomspace and changes nothing else. **Pre-registered: it should reproduce
``vsa_sum-004`` to within crosstalk** — the two draw independent random atoms
per coordinate, so they are not bit-identical, but the Gram has the same
distribution and the accuracies should agree to a few thousandths.

If they do not, the finding is about the harness and not about the IR, and
nothing else in this module may be read until that is explained. That is
``notes/lessons/2026-08-13-the-harness-moves-more-than-the-models.md`` applied
in advance rather than in hindsight: models span about 0.1 of lift here and
harness decisions span 0.15 to 2.0.

The type head, which is the other place this might pay
--------------------------------------------------------
Floor 0.860, two of nineteen models positive, **every VSA row parked at
-0.486** since ``vsa-002`` because the family's type vote is a four-feature
lookup and the floor is a six-level backed-off ladder. Nothing has attacked it.

:class:`MettaTypes` attacks it with the one direction the floor cannot read: the
multiset of a node's **child types**. A node whose children are ``char`` atoms
is a ``str`` whatever sits above it, and no key in this repo has ever looked
down. Design rule 1 — the label and type heads do not share machinery — is
satisfied by construction: this head has its own ladder, its own counts and its
own support threshold, and shares with the label head only a *derived quantity*,
which is data rather than mechanism.

Written down before the sweep: **this row should be positive on type lift**, and
if it is not, the honest reading is that the floor's six-level upward ladder
already reconstructs everything the downward direction carries. If it lands near
1.0 the reading is *not* a win — a metric that becomes trivially correct once
the representation carries it is a definition, not a result
(``notes/decisions/2026-08-14-the-ir-is-a-knob.md``), and the number to check is
whether ``str`` alone accounts for it.
"""

from __future__ import annotations

import collections
import hashlib
import math
from typing import Sequence

import numpy as np

from symbolic_ai_atomspace import (ROLE_QUERIES, TUPLE_QUERIES, RoleQuery,
                                   child_type_key, role_signatures,
                                   view_to_atomspace)
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer

from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, Votes
from ..vsa_002.model import VSAModel, _bipolar
from ..vsa_perm_002.model import VSAPerm
from ..vsa_spec_004.model import RoleEmbedding, _shape_hash

__all__ = ["AtomSpaceRoles", "TupleRoles", "MettaTuple", "MettaTuplePure",
           "Metta", "MettaPure", "MettaGated", "MettaGatedPure",
           "MettaShuffled", "MettaShuffledPure", "MettaPerm", "MettaPermPure",
           "DownwardTypes", "MettaTypes", "MettaTypesPure"]

#: Signature prefixes that are the four coordinates ``vsa-002`` asserts. Every
#: other prefix is something only the atomspace can say, and is what
#: ``extra_weight`` scales. Written as a frozenset of two-character prefixes
#: because the signatures themselves carry values after the colon.
HAND_BUILT = frozenset({"pt", "sl", "dp", "ar"})


def _atom_seed(signature: str) -> int:
    """A stable 64-bit seed for one signature.

    ``hash()`` on a string is salted per process. A role atom drawn from it
    would differ between the fitting process and the prediction process of the
    same model, which is the determinism failure
    ``tests/test_models.py::test_fitting_is_stable_across_processes`` exists to
    catch, and ``blake2b`` is eight lines cheaper than discovering it there.
    """
    return int.from_bytes(
        hashlib.blake2b(signature.encode("utf-8"), digest_size=8).digest(), "big")


class AtomSpaceRoles(RoleEmbedding):
    """Role vectors from the queries a node satisfies. See the module docstring.

    A mixin over either VSA base class, exactly as
    :class:`~symbolic_ai_models.models.vsa_spec_004.model.RoleEmbedding` is, so
    the same construction sits under the role-only and the permutation rows and
    the two cannot drift apart.
    """

    #: The query schedule. Swapped wholesale by ``metta_tuple-005``.
    queries: tuple[RoleQuery, ...] = ROLE_QUERIES
    #: Normalise each role row to ``sqrt(d)``, making the Gram a cosine.
    normalise = True
    #: The one knob: how much of the role the atomspace-only groups get. Both
    #: ends are named degenerate models -- see the module docstring.
    knob_grid = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
    embedding_name = "atomspace query signatures"

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: signature -> its bipolar atom. Regenerable from the signature string
        #: and therefore **not** persisted: ``vsa-002``'s codebook taught this
        #: repo that pickling regenerable noise costs 177MB per checkpoint.
        self._sig_atoms: dict[str, np.ndarray] = {}
        #: How many distinct signatures fitting reached. Snapshotted at the end
        #: of ``learn`` so the parameter count is a property of the fit and not
        #: of how much evaluation has since run through the model.
        self.n_role_atoms = 0
        #: view -> its per-node signature lists. The signatures do not depend on
        #: the knob, and the knob fit sweeps six values over the same held-out
        #: views; recomputing the queries per knob would be six times the
        #: atomspace work for an identical answer.
        self._sig_cache: tuple | None = None
        #: ``[(extra_weight, held-out mixture log-likelihood per node)]`` --
        #: the whole grid, not only its argmax. See :meth:`_fit_scalars`.
        self.knob_curve: list[tuple[float, float]] = []

    # ---- the role construction ------------------------------------------
    def _atom_for(self, signature: str) -> np.ndarray:
        atom = self._sig_atoms.get(signature)
        if atom is None:
            rng = np.random.default_rng(
                [self.seed + 6, _atom_seed(signature) % (2 ** 63)])
            atom = _bipolar(rng, 1, self._d)[0]
            self._sig_atoms[signature] = atom
        return atom

    def _signatures_for(self, view: GraphView) -> list[list[str]]:
        if self._sig_cache is not None and self._sig_cache[0] is view:
            return self._sig_cache[1]
        signatures = role_signatures(view_to_atomspace(view), len(view),
                                     self.queries)
        self._sig_cache = (view, signatures)
        return signatures

    def _role_matrix(self, view: GraphView) -> np.ndarray:
        signatures = self._signatures_for(view)
        out = np.zeros((len(view), self._d), dtype=np.float32)
        for i, sigs in enumerate(signatures):
            for sig in sigs:
                weight = 1.0 if sig[:2] in HAND_BUILT else self._knob
                if weight != 0.0:
                    out[i] += weight * self._atom_for(sig)
        out = self._shuffled(view, out)
        if self.normalise:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            out = out * (np.sqrt(self._d) / np.maximum(norms, 1e-9))
        return out.astype(np.float32)

    # ---- fitting, with the curve written down -----------------------------
    def _fit_scalars(self, episodes: Sequence[Episode],
                     tok: SymbolTokenizer) -> None:
        """The parent's fit, with the **whole likelihood curve** recorded.

        `notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value.md`
        says a fit landing on the edge of its grid is a failed fit *until you
        establish which* of two worlds produced it: the curve genuinely turns
        around there, or the grid was too narrow. An argmax alone cannot tell
        them apart — and a third possibility it also cannot exclude is that the
        objective is **flat** and the argmax is picking noise.

        All three are distinguishable from the curve, so the curve is what gets
        written down. `rules.txt` carries every point, per
        `notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-
        unattributable.md`: a parameter recorded nowhere turns a later
        four-decimal discrepancy into a bisect.

        The objective is re-derived here rather than read out of the parent,
        because exposing it would mean editing ``vsa_spec_004`` — a file a
        parallel line is also working in, and a merge conflict in the middle of
        a shared base class is a worse hazard than twenty lines here.
        ``tests/test_metta.py::test_the_recorded_curve_picks_what_the_parent_fit_picks``
        is what makes that safe: it runs both and requires the same answer, so
        a drift between the two fails loudly instead of silently reporting a
        curve for a knob that was chosen by something else.
        """
        from symbolic_ai_core.calibration import MassCalibrator

        original = self._knob
        curve: list[tuple[float, float]] = []
        try:
            for value in self.knob_grid:
                self._knob = float(value)
                self._cache = None
                rows: list[tuple] = []
                for view, targets in self.training_views(
                        episodes, tok, repeats=1, seed=23,
                        max_nodes=self.cfg.max_nodes):
                    keep = [(node, int(label))
                            for node, (label, _) in targets.items() if label >= 0]
                    if not keep:
                        continue
                    context = self._predict_context(view)
                    candidates = self._candidates(view)
                    for node, label in keep:
                        sims, cands = self._similarities(
                            self._probe_for(view, node, context), candidates)
                        if sims is None:
                            continue
                        table = self._soften(sims, cands, self.sharpness)
                        if not table:
                            continue
                        rows.append((max(table.values()),
                                     float(table.get(label, 0.0)),
                                     self.backoff_prob(view, node, label)))
                if not rows:
                    continue
                scores = [r[0] for r in rows]
                votes = [r[1] for r in rows]
                backoff = [r[2] for r in rows]
                gate = MassCalibrator().fit(scores, votes, backoff)
                total = sum(
                    math.log(max((1.0 - gate(s)) * max(b, 1e-12) + gate(s) * q,
                                 1e-12))
                    for s, q, b in zip(scores, votes, backoff)) / len(rows)
                curve.append((float(value), total))
        finally:
            self._knob = original
            self._cache = None
        self.knob_curve = curve
        if curve:
            self._knob = max(curve, key=lambda kv: kv[1])[0]
            self._cache = None

    # ---- bookkeeping -----------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        super().learn(episodes, tok)
        self.n_role_atoms = len(self._sig_atoms)

    def n_symbolic_parameters(self) -> int:
        """One vector per signature reached into, plus the base's own count.

        ``vsa-002``'s convention: a vector regenerable from a seed costs one
        vector, not its ``d`` signs. A signature's atom is a pure function of
        the signature string, so the model's role table *is* the list of
        signatures it has seen.
        """
        base = super().n_symbolic_parameters() - self.n_eig
        return base + max(self.n_role_atoms, len(self._sig_atoms))

    def render(self) -> str:
        return "\n".join([
            super().render(),
            f"  queries: {', '.join(q.name for q in self.queries)}",
            f"  extra_weight={self._knob:.3g}"
            f"{self._boundary_note()}, normalise={self.normalise}",
            f"  signature atoms: {max(self.n_role_atoms, len(self._sig_atoms))}",
            *([f"  extra_weight likelihood curve (held-out training episodes): "
               + ", ".join(f"{k:g}->{ll:.4f}" for k, ll in self.knob_curve)]
              if self.knob_curve else []),
        ])

    def _boundary_note(self) -> str:
        """Say so in the artefact when the fit landed on the edge of its grid.

        A boundary optimum is the search saying "I wanted to keep going and you
        stopped me", and it has been reported as a fitted value here twice. The
        cheapest possible guard is for the model's own ``rules.txt`` to print
        the word.
        """
        if not self.fit_knobs or len(self.knob_grid) < 2:
            return ""
        if self._knob == self.knob_grid[0]:
            return "  [BOUNDARY: bottom of the grid; extras contribute nothing]"
        if self._knob == self.knob_grid[-1]:
            return "  [BOUNDARY: top of the grid; not a fitted value]"
        return "  (interior)"


# ---------------------------------------------------------------------------
# the harness check: the old assertion, in the new notation
# ---------------------------------------------------------------------------
class TupleRoles(AtomSpaceRoles):
    """``vsa-002``'s four coordinates, read off the atomspace as queries.

    Nothing new is said. ``(child $p $k $q) (: $p $t)`` yields parent type and
    slot; depth and arity are aggregates over the ``child`` relation. The row
    exists to check that saying the *old* thing in the *new* notation reproduces
    the old number — because if it does not, every other row in this module is
    measuring a harness change and not an IR.
    """

    queries = TUPLE_QUERIES
    normalise = False
    knob_grid = (1.0,)
    fit_knobs = False
    embedding_name = "atomspace queries restricted to vsa-002's four coordinates"


@register("metta_tuple-005",
          doc="Harness check: vsa-002's four coordinates as atomspace queries.")
class MettaTuple(TupleRoles, VSAModel):
    """Should reproduce ``vsa_sum-004`` to within crosstalk. See the module doc."""

    LEARNED = VSAModel.LEARNED + ("_knob", "n_eig", "n_role_atoms")


@register("metta_tuple_pure-005",
          doc="metta_tuple-005 without the shared memorising fallback.")
class MettaTuplePure(MettaTuple):
    """The conformance check at ``vsa_sum_pure-004``'s setting."""

    structural_fallback = False


# ---------------------------------------------------------------------------
# the experiment
# ---------------------------------------------------------------------------
@register("metta-005",
          doc="Roles from the conjunctive queries a node satisfies in an atomspace.")
class Metta(AtomSpaceRoles, VSAModel):
    """The full query schedule: downward, sideways-and-typed, and the path.

    ``extra_weight`` is pinned at **1.0 — an equal share — and is not fitted**,
    which is a choice and is reported as one. ``vsa_hks_sum-004`` sets the
    precedent and :class:`MettaGated` prices the alternative.

    The reason the headline row does not fit its own knob was found in the
    wiring check and is worth stating, because it is a trap with a general
    shape. The fitted version ran the knob to **0.0** — the bottom of the grid,
    where the atomspace-only queries contribute nothing at all. A row whose fit
    switches its own treatment off is not a measurement of the treatment; it is
    a measurement of what the likelihood prefers, which is a different and also
    interesting question, and it belongs in its own row rather than silently
    replacing this one. (That observation came off a six-lesson slice and is
    used here only to size the design; every number reported is the full sweep.)

    **On 179 lessons the slice was wrong and the fit is interior at 2.0** — see
    :class:`MettaGated`. The design decision this row embodies survives the
    correction and is *better* justified by it: pinning an equal share is what
    made the treatment measurable independently of what the likelihood happened
    to want, and having both rows is what let the slice be caught rather than
    believed. But the stated reason above was, on the full curriculum, false.

    What would refute the line, written before the number landed:

    * landing level with ``metta_tuple-005`` — the extra queries bought
      expressiveness nobody needed, which is what ``omegaclaw_reach-001``
      already said and what the pre-registration predicts;
    * ``metta_gated-005``'s knob fitting to ``0.0`` on the full curriculum — the
      same conclusion reached by the likelihood rather than by the accuracy, and
      the stronger version of it;
    * landing level with ``metta_shuf-005`` — the graded Gram was doing the work
      and the *correspondence* between a signature and its node was decoration.
    """

    LEARNED = VSAModel.LEARNED + ("_knob", "n_eig", "n_role_atoms")
    knob_grid = (1.0,)
    fit_knobs = False


@register("metta_pure-005", doc="metta-005 without the shared memorising fallback.")
class MettaPure(Metta):
    """The row to read for what the IR is worth.

    The shared ``structural_fallback`` is a memorising lookup every rule-based
    model inherits, and for ``vsa-002`` it was worth +0.019 of accuracy and
    **all** of the renaming sensitivity. This row is where the equivariance
    question gets answered: no query in the schedule reads the ``label``
    relation, so the drop should be ~0.000, and if it is not, something in the
    schedule is reading vocabulary and the bits are ``ensemble-001``'s 4.77 in a
    new notation.
    """

    structural_fallback = False


@register("metta_gated-005",
          doc="metta-005 with the atomspace queries' share fitted, not assumed equal.")
class MettaGated(Metta):
    """Does the likelihood *want* the atomspace-only queries at all?

    One knob, fitted on held-out **training** episodes by the log-likelihood of
    the calibrated mixture — the model that actually ships — exactly as every
    ``-004`` knob is. The grid is ``(0.0, 0.25, 0.5, 1.0, 2.0, 4.0)`` and both
    ends are *named degenerate models*: at ``0.0`` this row is ``metta_tuple``,
    at ``4.0`` the extras drown the four hand-built coordinates. So a boundary
    here is interpretable rather than merely a place the author stopped typing —
    which is the correction
    ``notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value.md``
    demands, and the model's own ``rules.txt`` prints the word BOUNDARY when it
    happens.

    Pre-registered, before the full sweep: **the knob lands at or near 0.0 and
    this row is indistinguishable from ``metta_tuple-005``.** That is what the
    wiring check showed and what ``omegaclaw_reach-001``'s +0.226-against-+0.234
    predicts. If instead it lands interior and beats ``metta-005``, the equal
    share was the wrong choice and the extras are worth a fraction of a role
    rather than a whole one.

    **Measured on all 179 lessons: refuted, and in the second direction.** The
    prediction above is left standing verbatim because a prediction rewritten
    after the number is not a prediction. The knob lands **interior at 2.0**,
    and the recorded curve is monotone increasing to it and then turns down::

        0 -> -4.1417   0.25 -> -4.1145   0.5 -> -4.0888
        1 -> -4.0676   2    -> -4.0639   4   -> -4.0661

    So it is not a truncated grid, not a flat objective with a noisy argmax and
    not a boundary — it is a real optimum, identical to four decimals in the
    ``_pure`` row. The likelihood prefers the atomspace-only signatures at
    *twice* the weight of the four hand-built coordinates.

    The six-lesson wiring check said 0.0. A hundred and seventy-nine lessons say
    2.0. That is the **tenth** slice inversion in this repo's history and it is
    the reason the wiring check's number was labelled a design aid rather than a
    result when it was recorded.

    What the knob buys is **bits, not accuracy**: 6.477 against
    ``metta_tuple-005``'s 6.581 and ``vsa_sum-004``'s 6.583, with label accuracy
    flat at 0.227 against 0.226 and 0.228. Exactly the split the
    pre-registration named as the only place a legitimate win could appear, and
    exactly this repo's oldest measured fact about its two label metrics.
    """

    knob_grid = AtomSpaceRoles.knob_grid
    fit_knobs = True


@register("metta_gated_pure-005",
          doc="metta_gated-005 without the shared memorising fallback.")
class MettaGatedPure(MettaGated):
    """The fitted-share row without the floor every rule-based model inherits."""

    structural_fallback = False


@register("metta_shuf-005",
          doc="Control: metta-005 with the query signatures shuffled across nodes.")
class MettaShuffled(Metta):
    """The control that decides whether the *space* mattered.

    Same signatures, same multiset, same Gram value distribution, attached to
    the wrong nodes. Only the correspondence between a query result and the node
    it describes dies — so a control that matched its treatment would say the
    finding is about graded Grams and not about atomspaces. This repo has been
    saved by exactly this shape of control more than once.
    """

    shuffle_coordinates = True


@register("metta_shuf_pure-005",
          doc="The shuffled-signature control without the shared fallback.")
class MettaShuffledPure(MettaShuffled):
    """The control at ``metta_pure-005``'s setting."""

    structural_fallback = False


@register("metta_perm-005",
          doc="vsa_perm-002's channels with atomspace-query roles.")
class MettaPerm(AtomSpaceRoles, VSAPerm):
    """The query schedule beside the permutation channel.

    ``vsa_perm_pure-002`` is the best row this repo has from the VSA family —
    0.337 label at a **-0.003** renaming drop — and it got there by adding
    *relative position*, which no role atom encodes. A query-derived role is a
    different axis again, so the pre-registered question is the one
    ``vsa_perm_hks-004`` also asks: do the two compose, or was permutation
    already supplying whatever reach a better role could supply?

    Written down because it is the row most likely to be a null and nulls are
    the easiest thing to explain away afterwards.
    """

    LEARNED = VSAPerm.LEARNED + ("_knob", "n_eig", "n_role_atoms")
    knob_grid = (1.0,)
    fit_knobs = False


@register("metta_perm_pure-005",
          doc="metta_perm-005 without the shared memorising fallback.")
class MettaPermPure(MettaPerm):
    """The equivariant row for the family's most capable combination."""

    structural_fallback = False


# ---------------------------------------------------------------------------
# the type head, which nothing has attacked
# ---------------------------------------------------------------------------
class DownwardTypes:
    """A type head keyed on what a node *contains*.

    Its own ladder, its own counts, its own support threshold. It shares with
    the label head exactly one derived quantity — the child-type multiset, which
    is a query result and therefore data — and no machinery, which is design
    rule 1 satisfied by construction rather than by discipline.

    The ladder, most specific first. ``k3`` is deliberately ``node_context``
    itself, the tuple the masked-node floor and the shared back-off both key on,
    so that when the downward keys have no support this head **degrades exactly
    to the floor's own key** rather than to some near-miss of it.
    """

    #: How many observations a rung needs before it is trusted. Deliberately the
    #: same ``min_support`` the VSA type head already uses, so the contrast is
    #: the ladder and not the threshold.
    type_rules: dict

    @staticmethod
    def _type_ladder(view: GraphView, node: int,
                     children: tuple[str, ...]) -> tuple[tuple, ...]:
        parent = view.parent[node]
        ptype = (view.types[parent] or "mask") if parent >= 0 else "ROOT"
        slot = min(view.slot[node], 8)
        depth = min(view.depth[node], 8)
        return (
            (0, ptype, slot, depth, children),
            (1, ptype, slot, children),
            (2, children, min(len(children), 5)),
            # `node_context`, verbatim: the floor's own key.
            (3, ptype, slot, depth, bool(view.children(node))),
            (4, ptype, slot),
            (5,),
        )

    def _child_types(self, view: GraphView) -> list[tuple[str, ...]]:
        cached = getattr(self, "_ct_cache", None)
        if cached is not None and cached[0] is view:
            return cached[1]
        out = child_type_key(view_to_atomspace(view), len(view))
        self._ct_cache = (view, out)
        return out

    def _fit_types(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            children = self._child_types(view)
            for node, (_, type_id) in targets.items():
                if type_id < 0:
                    continue
                for key in self._type_ladder(view, node, children[node]):
                    counts[key][int(type_id)] += 1
        self.type_rules = dict(counts)

    def _type_vote(self, view: GraphView, node: int) -> Votes:
        children = self._child_types(view)
        for key in self._type_ladder(view, node, children[node]):
            table = self.type_rules.get(key)
            if table is None or sum(table.values()) < self.min_support:
                continue
            total = sum(table.values())
            top, n = table.most_common(1)[0]
            return {int(top): 1.0}, min(0.15 + 0.8 * n / total, 0.95)
        return ABSTAIN


@register("metta_type-005",
          doc="metta-005 with a type head keyed on what a node contains.")
class MettaTypes(DownwardTypes, Metta):
    """The first attack on the type head, and the direction nobody looked in.

    Every structural key in this repo reads *upward*: parent type, slot, depth,
    and one bit for whether there are children at all. What a node contains has
    never been a feature. A node whose children are ``char`` atoms is a ``str``.

    Pre-registered: **positive type lift**, against a floor of 0.860 that every
    VSA row has sat 0.486 below since ``vsa-002``. If it is not positive, the
    reading is that the floor's six-level upward ladder already reconstructs the
    downward direction, and that is worth knowing because it would mean the type
    column is saturated rather than unattacked.

    And the guard against the flattering reading: if this lands near 1.0, that
    is a *definition* and not a result — the encoding would be carrying the
    answer — so the number to look at is whether ``str`` alone accounts for it.
    """

    LEARNED = Metta.LEARNED


@register("metta_type_pure-005",
          doc="metta_type-005 without the shared memorising fallback.")
class MettaTypesPure(MettaTypes):
    """The type head scored without the label head's shared floor underneath.

    The fallback is a *label* prior and cannot touch the type column directly,
    but ``notes/lessons/2026-08-13-the-harness-moves-more-than-the-models.md``
    records a shared calibrator once pricing the type head with the label head's
    confidence and costing three models -1.96 of type lift at once. Registering
    both settings is how that stays visible instead of being argued about.
    """

    structural_fallback = False


# Kept live: the shuffle control's determinism comes from this digest, and an
# import that a linter tidied away would silently make the control random.
_ = _shape_hash
