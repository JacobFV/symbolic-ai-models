"""A verifier-guided hypothesis frontier: propose, verify exactly, refine on what is left.

Batzoglou's *Hypothesis Frontier* (arXiv:2608.10843, 2026-08-11) proposes
first-order formulas with a language model, scores each one against the data
with an **exact verifier**, keeps the best, and uses the *remaining errors* to
aim the next round of generation. The LLM is not the reasoner; it is a proposal
distribution over symbolic programs, and exact computation decides which
proposals survive.

Here the proposal distribution is enumeration. Not a concession — the hypothesis
space this task admits is small enough to walk, the box runs a real training job
that must keep the GPU, and an enumerator makes the **verifier** the only thing
that decides what survives, which is the part of the paper worth importing.

Why this model exists, and it is one measurement
------------------------------------------------

The derivability arm plants a rule the whole registry is unable to *state*.
``derive:wordnet`` does not draw an object's attribute; it follows from the
object's kind through a six-pair map fixed corpus-wide. A one-symbol lookup
walks that channel at **1.000** against a blind marginal of **0.167**, and
``RESEARCH_LOG.md`` records that of twenty models fifteen score exactly 0.000 on
the derived non-copyable bucket and five score 0.145-0.155.

Reading ``runs/derive179-*/derived_split.json`` says something sharper: four of
those five agree to **nine decimal places**, and every non-zero row is identical
between the treatment and the ``-shuffled`` arm. That is the shared back-off
wearing five models' names — see
``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md``.
**Not one model produces a correct derived fill from its own machinery.**

The reason is syntactic. Every rule-based model here concludes either a **copy**
— the label of a node reached by some structural path — or a **constant**.
``ilp-001`` is a real FOIL search and genuinely induces the relational *chain*,
but its clause head still binds ``L`` to another node's label; it searches
better over the same conclusions. The planted rule has a third form::

    label(X) = m(label(Y))      Y the kind sibling, m a finite corpus-wide map

which is neither. ``ilp`` scoring exactly 0.000 beside a search that demonstrably
works is the cleanest evidence available that the failure is **expressive, not
procedural**.

What a hypothesis is
--------------------

A pair ``(guard, resolver)``.

The **guard** is a conjunction over symbol-free structural atoms of the target —
parent type, parent label, slot, depth, sibling count, has-children — and
candidates are drawn from the subset *lattice* rather than from a ladder
somebody wrote down. That matters here: the criticism this model levels at
``ruleinduce`` is that its conclusions came from a written list, and answering it
with a written list of conditions would be the same mistake one surface over.

The **resolver** has three forms and only the third is new:

``copy:P``
    the label at structural path ``P``. Renaming-invariant, and what every
    pointer in this repo already does.
``const``
    the modal label under the guard. Memorises a *slot*.
``map:P``
    a learned finite map from the label at ``P`` to the answer. Memorises a
    *relation between symbols*, and is the only form that can state the planted
    rule.

The verifier is held out, and that is the load-bearing choice
-------------------------------------------------------------

A map fitted and scored on the same fills verifies at 1.000 by construction: it
is a lookup of the answers it was built from. So training episodes are split
into two folds **by episode index** — the same episode lands in the same fold
under every mask repeat, so a repeat cannot leak across the boundary — resolver
tables are fitted on one fold and scored on the other, in both directions, and a
hypothesis survives only on that cross-fitted precision. Tables are refitted on
everything afterwards: estimation on held-out data, deployment on all of it.

Without this the model would score high on ``derive:wordnet`` *and* on
``derive:wordnet-perm`` and prove nothing. With it the control's mechanism is
internal and inspectable rather than asserted, and it was inspected: the rule
that answers the derived bucket in the treatment is

    [slot=1, nsib=4] -> map:sib@2   p=0.659  n=2300  |m|=399

whose entries at the six planted kinds are ``shoe->lace, body->abdomen,
ship->bay, garment->arm, building->annex, auto->buffer`` — **all six recovered
verbatim**. Under the per-episode permutation that rule's held-out precision
collapses and **the rule is simply not in the fitted model**.

What is *not* true, and this sentence used to say it was: the model does not
abstain in the control. It keeps 355 other map rules, nearly the same set as the
treatment's 356, and on the derived bucket a different map fires and is wrong at
chance — 0.072, below that arm's own blind marginal of 0.143. Verification
removes the rule that was carrying the channel; it does not silence the model.

The ``-shuffled`` arm is the check that this instrument reads *derivability* and
never *meaning*: the same guard survives with the same support and the same
table size, its six entries are the scrambled graph's values, they agree with
real WordNet **zero** times out of six, and the score ties the treatment to three
decimals.

Residual guidance, and simplification
-------------------------------------

Round one proposes guards of at most one atom from every fill. Later rounds
widen the lattice — two atoms, then three — **only where the frontier is still
wrong**, which is the paper's move and what separates this from one greedy pass.
A guard is admitted only if its support *among the residual fills* clears the
threshold, so the expensive part of the lattice is paid for exactly where the
errors are.

Simplification is by construction rather than by a second pass. The lattice
contains every generalisation of every hypothesis, and the ranking breaks ties by
description length — guard atoms plus table entries — so the shortest formula
with a given verified precision is the one that survives. A ``map`` that happens
to be the identity therefore never beats the ``copy`` saying the same thing more
briefly. That is the paper's "compress without changing predictions", obtained by
ordering rather than by editing.

What this model is not
----------------------

It is not renaming-invariant where a ``map:`` fires, and it cannot be. Naming a
symbol no visible node carries requires storing an association between symbol
identities across episodes; a renaming-invariant model stores no symbol
identities. So the fifteen models scoring exactly 0.000 on the derived
non-copyable bucket are a *theorem* rather than a failure — the same shape as
``notes/lessons/2026-08-15-a-floor-outside-the-models-hypothesis-class.md`` — and
taking this channel has renaming-variance as its price. Whether that price buys
anything a slot-memoriser does not is what ``derive:wordnet-perm`` answers, which
is why the control is the load-bearing arm and not the treatment.
"""

from __future__ import annotations

import collections
import itertools
import math
from typing import Any, Sequence

import numpy as np

from symbolic_ai_core.calibration import MassCalibrator
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["FrontierModel", "GUARD_KEYS", "PATHS", "MAP_PATHS"]

#: The atoms a guard may conjoin, in a fixed order, so a guard is a tuple of
#: ``(index, value)`` pairs and two guards over the same keys compare directly.
#: Each is readable at a hidden node: ``phead`` is the *parent's* label, never
#: the target's, and is ``None`` when the parent is itself masked.
GUARD_KEYS = ("ptype", "phead", "slot", "depth", "nsib", "kids")

#: Structural paths a resolver may read a visible neighbour through. Siblings
#: are addressed **by slot**, not by position: the slot is what the generator
#: binds an argument to, and a positional index moves when a sibling is masked.
PATHS: tuple[tuple, ...] = (
    ("parent",), ("gparent",), ("prev",),
    ("sib", 0), ("sib", 1), ("sib", 2), ("sib", 3),
    ("psib", 0), ("psib", 1), ("psib", 2),
)

#: Which paths the ``map`` form is searched over. A strict subset of
#: :data:`PATHS`, and the reason is cost rather than principle: a map's
#: cross-fit is the one resolver that cannot be reduced to a ``bincount``, so it
#: is paid for per path in Python. The five kept are the parent and the four
#: sibling slots — the relations along which this generator binds arguments of
#: one predicate, which is where a corpus-wide correspondence between two
#: symbols can live at all. ``copy`` is still searched over every path in
#: :data:`PATHS`, so a route this list omits is not lost to the model, only to
#: the map form. Widening it is a knob, not a rewrite; that it is a knob is
#: recorded here because a search space is a fitted parameter of the result.
MAP_PATHS: tuple[int, ...] = (0, 3, 4, 5, 6)

#: A path that is hidden, absent, or a type that does not exist.
MISSING = -1

#: Normal deviate for the lower confidence bound a hypothesis is ranked by.
Z = 1.96


def _lcb(correct: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Wilson lower bound on a verified precision, elementwise.

    Hypotheses are ranked by this rather than by ``correct / n``, and the reason
    is a mistake this model made on its first fit. Ranking by the point estimate
    puts ``p = 1.000`` on twelve fills ahead of ``p = 0.980`` on five thousand,
    so the rules that fire first are the ones with the least evidence behind
    them — the type head lost **1.63 lift** to exactly that, ranking a shelf of
    lucky specific rules above the general ones that were carrying it.

    A held-out precision is an estimate, and an argmax over estimates of wildly
    different variance is not a comparison. The bound prices the variance: 1.000
    on 12 becomes 0.76, 0.980 on 5,000 stays 0.976, and the well-evidenced rule
    wins the tie it should have been winning. Same argument as
    ``notes/lessons/2026-08-14-record-the-curve-not-the-argmax.md``, one level
    down — the curve here is the estimate's width, and the argmax was throwing
    it away.
    """
    n = np.maximum(n, 1e-9)
    p = correct / n
    denom = 1.0 + Z * Z / n
    centre = p + Z * Z / (2 * n)
    margin = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return np.maximum(0.0, (centre - margin) / denom)


def _guard_atoms(view: GraphView, i: int) -> tuple:
    """The six structural facts about node ``i``, in :data:`GUARD_KEYS` order."""
    p = view.parent[i]
    return (
        (view.types[p] or "mask") if p >= 0 else "ROOT",
        view.labels[p] if p >= 0 else None,
        min(view.slot[i], 8),
        min(view.depth[i], 8),
        min(len(view.siblings(i)), 4),
        bool(view.children(i)),
    )


def _path_node(view: GraphView, i: int, path: tuple) -> int:
    """Which node ``path`` reaches from ``i``, or -1 if it reaches none."""
    kind = path[0]
    p = view.parent[i]
    if kind == "parent":
        return p
    if kind == "gparent":
        return view.parent[p] if p >= 0 else -1
    if kind == "prev":
        # The nearest earlier node still visible. A weak path, kept precisely
        # because it is the only one that does not go through the tree: if a
        # result here were a positional artefact, this is the path that would
        # show it.
        for j in range(i - 1, -1, -1):
            if view.labels[j] is not None:
                return j
        return -1
    if kind == "sib":
        for j in view.siblings(i):
            if view.slot[j] == path[1]:
                return j
        return -1
    if kind == "psib" and p >= 0:
        for j in view.siblings(p):
            if view.slot[j] == path[1]:
                return j
    return -1


def _path_labels(view: GraphView, i: int) -> tuple[int, ...]:
    """The visible label at each of :data:`PATHS`, or :data:`MISSING`."""
    out = []
    for path in PATHS:
        j = _path_node(view, i, path)
        lab = view.labels[j] if j >= 0 else None
        out.append(MISSING if lab is None else int(lab))
    return tuple(out)


def _path_types(view: GraphView, i: int) -> tuple[int, ...]:
    """The same paths read as *type* ids, for the type head."""
    out = []
    for path in PATHS:
        j = _path_node(view, i, path)
        t = view.types[j] if j >= 0 else None
        out.append(MISSING if t is None else int(TYPE_TO_ID.get(t, MISSING)))
    return tuple(out)


class _Rule:
    """One surviving hypothesis: a guard, a resolver, and a verified precision.

    ``dl`` is the description length the MDL tie-break uses — guard atoms plus
    however many entries the resolver's table holds — so a ``map`` that turns out
    to be the identity never wins a tie against the ``copy`` that says the same
    thing in nothing.
    """

    __slots__ = ("guard", "form", "path", "table", "const", "precision",
                 "score", "support", "dl", "fold_table", "tol")

    def __init__(self, guard: tuple, form: str, path: int, precision: float,
                 score: float, support: int, dl: int, tol: float = 0.0) -> None:
        self.guard = guard
        self.form = form
        self.path = path
        self.table: dict[int, int] = {}
        self.const: int | None = None
        self.precision = precision
        #: The lower bound on :attr:`precision`. What the ranking uses, and what
        #: the gate is calibrated against, because it is what the evidence
        #: supports rather than what the sample happened to show.
        self.score = score
        self.support = support
        self.dl = dl
        #: The cross-fit's own tables, ``fold_table[f]`` fitted on fold ``f`` and
        #: therefore usable only to predict fold ``1 - f``. Kept so the residual
        #: driving the next round is computed out of fold like everything else;
        #: :attr:`table` is the deployed one, fitted on both.
        self.fold_table: list[dict[int, int]] = [{}, {}]
        #: Width below which two verified precisions are not treated as
        #: different. 0.0 reproduces the published ranking exactly.
        self.tol = tol

    @property
    def rank(self) -> tuple:
        """Bound on precision, then brevity, then evidence, then specificity.

        Rounded before comparison. Two hypotheses separated in the fourth decimal
        of a held-out estimate are not separated, and letting that noise choose
        between a one-atom guard and a three-atom one is how a model ends up
        carrying rules it cannot justify.
        """
        # Coarser rounding is the whole of the tolerance band: two scores
        # inside one bucket tie, and the next key -- description length -- then
        # decides. A `copy` has dl 0 and a `map` has one entry per table key, so
        # a tie resolves toward the renaming-invariant resolver.
        #
        # It exists because of what `frontier-001` does under a symbol
        # permutation: 1,031 of its map rules still fire, because the
        # permutation lands a symbol on another symbol that IS in the table, and
        # **9.4% of those firings are right**. A rule that is confidently wrong
        # is worse than one that declines, and worse again than a copy that
        # would have been right -- but rank is precision-first, so a map ahead
        # of a copy by 0.004 of held-out precision takes every fill they share.
        # `getattr`, not `self.tol`: a `__slots__` class unpickled from a
        # checkpoint written before a slot existed simply does not have it, and
        # every run under `runs/` predates this one. Reading it directly raised
        # `AttributeError` from `rank` on reload — training and scoring were
        # fine, and only reopening a published model broke, which is the same
        # shape as the `nn.Module._apply` collision. Any slot added here in
        # future needs the same treatment.
        tol = getattr(self, "tol", 0.0)
        q = (-round(self.score, 3) if tol <= 0.0
             else -math.floor(self.score / tol))
        return (q, self.dl, -self.support, len(self.guard))

    def matches(self, atoms: tuple) -> bool:
        return all(atoms[k] == v for k, v in self.guard)

    def resolve(self, path_vals: tuple[int, ...]) -> int | None:
        if self.form == "const":
            return self.const
        v = path_vals[self.path]
        if v == MISSING:
            return None
        return v if self.form == "copy" else self.table.get(v)

    def dominates(self, other: "_Rule") -> bool:
        """Whether ``other`` can never fire, this rule being ranked above it.

        A rule ranked below one whose guard is a *subset* of its own is dead
        code: the higher one matches everywhere the lower does and is consulted
        first. That is the whole of the paper's simplification pass, available
        here as a comparison because the lattice already contains every
        generalisation — nothing has to be edited to find the shorter formula,
        only recognised.

        The exception is resolvability. A ``copy`` or ``map`` declines when its
        path is hidden, so a lower rule reading a *different* path can still get
        a turn. Domination is therefore claimed only when the higher rule always
        answers (``const``) or reads the same path with at least the same table.
        """
        if not set(self.guard) <= set(other.guard):
            return False
        if self.form == "const":
            return True
        if self.form != other.form or self.path != other.path:
            return False
        return self.form == "copy" or set(other.table) <= set(self.table)

    def __repr__(self) -> str:
        guard = ", ".join(f"{GUARD_KEYS[k]}={v!r}" for k, v in self.guard) or "*"
        if self.form == "const":
            body = "const"
        else:
            path = PATHS[self.path]
            body = f"{self.form}:{path[0]}" + (
                f"@{path[1]}" if len(path) > 1 else "")
        return (f"[{guard}] -> {body}  p={self.precision:.3f} "
                f"n={self.support} dl={self.dl}")


def _modal(counts: dict[Any, collections.Counter]) -> dict[Any, int]:
    return {k: c.most_common(1)[0][0] for k, c in counts.items()}


@register("frontier-001",
          doc="Verifier-guided hypothesis frontier: guarded copy/const/map rules, cross-fit.")
class FrontierModel(RuleBasedModel):
    """Induce guarded rules, verify them out of fold, refine on the residual."""

    LEARNED = ("rules", "type_rules", "gate_map", "search_log")

    #: Guard widths each round may propose. Round one is global and cheap; the
    #: later two are the frontier and only see fills the kept rules still get
    #: wrong, which is what keeps the wide end of the lattice affordable.
    ROUNDS: tuple[tuple[int, ...], ...] = ((0, 1), (2,), (3,))

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: How often a hypothesis must fire *out of fold* before it is believed.
        #: The whole point of the map form is that it is able to memorise, so
        #: this is the number deciding whether it merely did.
        self.min_support = int(cfg.get("min_support", 12))
        #: Verified precision a hypothesis must clear. 0.5 rather than something
        #: near 1.0, deliberately: a rule right half the time is worth keeping
        #: against a back-off right a seventh of the time, and the mixture
        #: weight — not this threshold — is what prices that.
        self.min_precision = float(cfg.get("min_precision", 0.5))
        #: How much residual support a guard needs before it is *proposed*.
        #: Defaults to :attr:`min_support`, which is what every published
        #: `frontier-001` number was fitted under, so this knob changes nothing
        #: until it is set.
        #:
        #: It is separate from :attr:`min_support` because those two thresholds
        #: are answering different questions and sharing one number gates the
        #: wrong one. Verification asks "is this rule reliable", and the Wilson
        #: bound in :func:`_lcb` already prices small samples there. *Proposal*
        #: asks only "is this guard worth evaluating" — and an absolute count
        #: there means **rare structure cannot earn its own hypothesis**, because
        #: a guard specific to a phenomenon occupying 0.2% of the fills cannot
        #: clear a count fixed for a corpus of 86,805. The search does not fail
        #: to find it; the search is not permitted to consider it.
        #:
        #: Measured cost of that on the derivability arm: the derived slot is
        #: ~170 fills, no guard specific to it is ever proposed, the derivation
        #: is absorbed into `[slot=1, nsib=4]`, and 45% of the bucket abstains —
        #: the rule's own path answers 100% of it with the guard removed. See
        #: ``notes/findings/2026-08-17-the-scope-is-in-the-path-and-the-guard-costs-045.md``.
        self.propose_support = int(cfg.get("propose_support", 0)) or self.min_support
        #: How many resolver forms may survive per guard. One — the best by rank
        #: — is what every published `frontier-001` number was fitted under, so
        #: this changes nothing until it is raised.
        #:
        #: It exists because one-per-guard silently discards a resolver that is
        #: *perfect on a sub-population* whenever another is better overall. On
        #: the guard `[phead='obj', slot=1]`, which covers 80% of the derived
        #: slot, `map:sib@2` is **1.000** on the derived members and 0.179 on the
        #: rest — 0.625 overall — and `const` scores 0.993, so the map is thrown
        #: away and the derivation with it. A rule is ranked by its average over
        #: the population its guard admits, and an average cannot see a
        #: sub-population.
        self.keep_per_guard = int(cfg.get("keep_per_guard", 1))
        #: Width of the band inside which two verified precisions count as
        #: equal, so that the description-length tie-break — which prefers a
        #: renaming-invariant ``copy`` over a symbol-keyed ``map`` — gets to
        #: decide. 0.0 is the published ranking and changes nothing.
        self.rank_tolerance = float(cfg.get("rank_tolerance", 0.0))
        #: Whether rules that never get a turn are dropped before the cap.
        #: On by default and that is right for a **decision list**, where such a
        #: rule is dead code occupying a slot.
        #:
        #: It is wrong for a *soft* readout, and the reason is the point of
        #: ``frontier-vote``: a rule is unreachable exactly when a higher-ranked
        #: rule already answers its fills, so the filter removes precisely the
        #: rules that would have offered a **competing conclusion**. For a model
        #: that emits a distribution, those are the only rules that can produce
        #: any spread at all.
        self.reachability_filter = bool(cfg.get("reachability_filter", True))
        #: Whether a guard may keep more than one rule of the *same* form
        #: reading *different* paths. Off by default.
        self.keep_by_path = bool(cfg.get("keep_by_path", False))
        #: How many (form, path) rules survive per guard when it is on.
        self.keep_paths = int(cfg.get("keep_paths", 6))
        #: Cap on the rule set, applied after the reachability filter in
        #: :meth:`_useful`, so it bounds the rules that answer something
        #: rather than the rules that sort first.
        self.max_rules = int(cfg.get("max_rules", 2000))
        #: Mask repeats when collecting fills.
        self.repeats = int(cfg.get("frontier_repeats", 3))
        #: Which resolver forms the label head may propose. A knob so that
        #: ``frontier-nomap`` can be the same search with the new expressive
        #: power removed and *nothing else changed* — a control in the model's
        #: own hypothesis class, which is the only kind that isolates what a
        #: form bought. The type head is unaffected: it never had ``map``.
        self.forms = tuple(cfg.get("resolver_forms",
                                   ("const", "copy", "map")))
        self.rules: list[_Rule] = []
        self.type_rules: list[_Rule] = []
        self.gate_map = MassCalibrator()
        #: What the search did each round, so a null is readable without a rerun.
        self.search_log: list[dict[str, Any]] = []

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        atoms: list[tuple] = []
        labs: list[tuple[int, ...]] = []
        types: list[tuple[int, ...]] = []
        ans_lab: list[int] = []
        ans_type: list[int] = []
        fold: list[int] = []

        for view, targets, idx in self.training_views(
                episodes, tok, repeats=self.repeats, seed=11, with_index=True,
                max_nodes=self.cfg.max_nodes):
            for i, (label_id, type_id) in targets.items():
                if label_id is None or label_id < 0 or label_id == tok.unk_id:
                    continue
                atoms.append(_guard_atoms(view, i))
                labs.append(_path_labels(view, i))
                types.append(_path_types(view, i))
                ans_lab.append(int(label_id))
                ans_type.append(int(type_id) if type_id is not None else MISSING)
                # Split by episode, never by fill: one episode reappears under
                # every mask repeat, and a per-fill split would put two maskings
                # of one graph on opposite sides of a held-out boundary.
                fold.append(idx % 2)

        if not atoms:
            return
        self.rules = self._induce(atoms, labs, ans_lab, fold, head="label",
                                  forms=self.forms)
        keep = [n for n, a in enumerate(ans_type) if a != MISSING]
        if keep:
            self.type_rules = self._induce(
                [atoms[n] for n in keep], [types[n] for n in keep],
                [ans_type[n] for n in keep], [fold[n] for n in keep],
                head="type", forms=("const", "copy"), min_precision=0.0)
        self._fit_gate(episodes, tok)

    # -- the frontier loop ----------------------------------------------
    def _induce(self, atoms: Sequence[tuple], path_vals: Sequence[tuple],
                ans: Sequence[int], fold: Sequence[int], *, head: str,
                forms: tuple[str, ...] = ("const", "copy", "map"),
                min_precision: float | None = None) -> list[_Rule]:
        # The type head answers over eight types, not 8,192 symbols, so a rule
        # right 40% of the time there is real evidence where the same number on
        # the label head is noise. Sharing one threshold made the type head
        # abstain onto the *global* type marginal, which this repo has already
        # paid -1.950 lift for once.
        floor = self.min_precision if min_precision is None else min_precision
        n = len(atoms)
        pv = np.asarray(path_vals, dtype=np.int64)
        av = np.asarray(ans, dtype=np.int64)
        fv = np.asarray(fold, dtype=np.int64)
        fires = pv != MISSING
        copy_ok = fires & (pv == av[:, None])
        # Each guard atom coded as a small integer, so that matching a guard
        # over 100k fills is a handful of vectorised comparisons rather than a
        # Python loop per rule. The raw values are kept on the rule itself,
        # because prediction sees raw atoms and never this coding.
        codes, code_of = self._encode(atoms)

        kept: list[_Rule] = []
        residual = np.arange(n)
        seen: set[tuple] = set()

        for round_no, sizes in enumerate(self.ROUNDS):
            if residual.size < self.min_support:
                break
            fresh: list[_Rule] = []
            proposed = 0
            for size in sizes:
                for keys in itertools.combinations(range(len(GUARD_KEYS)), size):
                    got = self._sweep(keys, atoms, pv, av, fv, fires, copy_ok,
                                      residual, seen, forms, floor)
                    proposed += got[0]
                    fresh.extend(got[1])
            kept.extend(fresh)
            kept.sort(key=lambda r: r.rank)
            # Drop the rules that never get a turn *before* the cap bites. On
            # the first full fit the cap was applied to the rank order alone,
            # and round three proposed 5,410 guards of which 1,135 were kept —
            # enough high-precision, low-coverage rules to push out the general
            # ones that were carrying the answers. The residual then went
            # **up**, 57,008 -> 61,924 of 86,805, which is a frontier moving
            # backwards: a later round is supposed to be able to add nothing,
            # never to subtract. Ranking cannot see this, because rank is a
            # property of one rule and coverage is a property of the set.
            if self.reachability_filter:
                kept = self._useful(kept, codes, code_of, pv, av, fv)
            del kept[self.max_rules:]
            residual = self._residual(kept, codes, code_of, pv, av, fv)
            self.search_log.append({
                "head": head, "round": round_no, "proposed": proposed,
                "kept": len(fresh), "total": len(kept),
                "residual": int(residual.size), "fills": n,
                "forms": dict(collections.Counter(r.form for r in kept)),
            })

        for rule in kept:
            self._refit(rule, codes, code_of, pv, av)
        # Pruning goes after the refit because domination between two ``map``
        # rules is a question about their deployed tables.
        kept = self._prune(kept)
        if self.search_log:
            self.search_log[-1]["after_prune"] = len(kept)
        return kept

    @staticmethod
    def _encode(atoms: Sequence[tuple]) -> tuple[np.ndarray, list[dict]]:
        """Guard atoms as integer columns, plus the value -> code maps."""
        n, k = len(atoms), len(GUARD_KEYS)
        codes = np.zeros((k, n), dtype=np.int64)
        code_of: list[dict] = [dict() for _ in range(k)]
        for j in range(k):
            table = code_of[j]
            col = codes[j]
            for i in range(n):
                v = atoms[i][j]
                c = table.get(v)
                if c is None:
                    c = table[v] = len(table)
                col[i] = c
        return codes, code_of

    def _sweep(self, keys: tuple[int, ...], atoms: Sequence[tuple],
               pv: np.ndarray, av: np.ndarray, fv: np.ndarray,
               fires: np.ndarray, copy_ok: np.ndarray, residual: np.ndarray,
               seen: set[tuple], forms: tuple[str, ...], floor: float,
               ) -> tuple[int, list[_Rule]]:
        """Every guard over ``keys`` at once, verified in one pass per resolver.

        Grouping is the whole reason this is affordable. A per-guard verifier
        walks each guard's members once per resolver, and the guards of one key
        subset partition the fills, so the cost is (number of guards) x (fills
        per guard) x (resolvers) — the same total, times the number of guards,
        for the table-valued resolvers. Keying the count tables by *group* makes
        it one pass over the fills per resolver for the whole subset, whatever
        the number of guards.
        """
        n = len(atoms)
        gid = np.zeros(n, dtype=np.int64)
        index: dict[tuple, int] = {}
        for i in range(n):
            a = atoms[i]
            key = tuple(a[k] for k in keys)
            g = index.get(key)
            if g is None:
                g = index[key] = len(index)
            gid[i] = g
        n_groups = len(index)
        support = np.bincount(gid[residual], minlength=n_groups)
        cand = support >= self.propose_support
        guards = {g: tuple(zip(keys, vals)) for vals, g in index.items()}
        for g in np.flatnonzero(cand):
            if guards[int(g)] in seen:
                cand[g] = False
        if not cand.any():
            return 0, []
        for g in np.flatnonzero(cand):
            seen.add(guards[int(g)])

        # Only fills belonging to a candidate group take part in the Python
        # passes below. In the later rounds the residual is small, so this is
        # what keeps the wide end of the lattice from costing a full sweep.
        take = np.flatnonzero(cand[gid])
        # ``{group: {form: best rule of that form}}``. Keyed by form, not by
        # group alone, so that :attr:`keep_per_guard` can decide how many
        # survive — see ``FrontierBothModel``.
        best: dict[int, dict[str, _Rule]] = collections.defaultdict(dict)
        by_path: dict[int, dict[tuple, _Rule]] | None = (
            {} if self.keep_by_path else None)

        if "copy" in forms:
            for p in range(len(PATHS)):
                f = np.bincount(gid, weights=fires[:, p], minlength=n_groups)
                c = np.bincount(gid, weights=copy_ok[:, p], minlength=n_groups)
                self._offer(best, guards, cand, c, f, "copy", p, 0, None, floor, by_path)

        if "const" in forms:
            c, f, dl, tables = self._cross_fit(gid, fv, av, take, None, n_groups)
            self._offer(best, guards, cand, c, f, "const", 0, dl, tables, floor, by_path)

        if "map" in forms:
            for p in MAP_PATHS:
                c, f, dl, tables = self._cross_fit(gid, fv, av, take, pv[:, p],
                                                   n_groups)
                self._offer(best, guards, cand, c, f, "map", p, dl, tables, floor, by_path)

        out: list[_Rule] = []
        for per_form in best.values():
            ranked = sorted(per_form.values(), key=lambda r: r.rank)
            out.extend(ranked[:self.keep_per_guard])
        if by_path is not None:
            keep = {id(r) for r in out}
            for per in by_path.values():
                ranked = sorted(per.values(), key=lambda r: r.rank)
                out.extend(r for r in ranked[:self.keep_paths]
                           if id(r) not in keep)
        return int(cand.sum()), out

    def _cross_fit(self, gid: np.ndarray, fv: np.ndarray, av: np.ndarray,
                   take: np.ndarray, key: np.ndarray | None, n_groups: int):
        """Per group: correct, fired, table size, and the two tables themselves.

        ``key`` is ``None`` for ``const`` — one entry per group — and the
        resolver's input otherwise, which makes this one routine for both. Each
        fold is predicted by the table fitted on the other, so a table that only
        reproduces the fills it was built from fires and is wrong. That is
        exactly what has to happen in ``derive:wordnet-perm``, and it is the
        whole reason a map is allowed into the hypothesis language at all.
        """
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for i in take:
            k = 0 if key is None else int(key[i])
            if k == MISSING:
                continue
            counts[(int(gid[i]), int(fv[i]), k)][int(av[i])] += 1
        tables: dict[int, list[dict[int, int]]] = collections.defaultdict(
            lambda: [{}, {}])
        for (g, f, k), c in counts.items():
            tables[g][f][k] = c.most_common(1)[0][0]
        correct = np.zeros(n_groups)
        fired = np.zeros(n_groups)
        for i in take:
            k = 0 if key is None else int(key[i])
            if k == MISSING:
                continue
            g = int(gid[i])
            pred = tables[g][1 - int(fv[i])].get(k)
            if pred is None:
                continue
            fired[g] += 1
            correct[g] += pred == int(av[i])
        dl = np.zeros(n_groups)
        for g, pair in tables.items():
            dl[g] = len(pair[0]) + len(pair[1])
        return correct, fired, dl, tables

    def _offer(self, best: dict[int, _Rule], guards: dict[int, tuple],
               cand: np.ndarray, correct: np.ndarray, fired: np.ndarray,
               form: str, path: int, dl, tables, floor: float,
               by_path: dict[int, dict[tuple, _Rule]] | None = None) -> None:
        """Keep this resolver for each candidate guard it beats the current one on."""
        scores = _lcb(correct, fired)
        for g in np.flatnonzero(cand & (fired >= self.min_support)):
            g = int(g)
            precision = correct[g] / fired[g]
            if precision < floor:
                continue
            cost = int(dl[g]) if isinstance(dl, np.ndarray) else int(dl)
            rule = _Rule(guards[g], form, path, float(precision),
                         float(scores[g]), int(fired[g]), cost + len(guards[g]),
                         self.rank_tolerance)
            if tables is not None:
                rule.fold_table = [dict(tables[g][0]), dict(tables[g][1])]
            if by_path is not None:
                # Keyed by (form, path), so two `map` rules reading *different*
                # neighbours both survive under one guard. Keeping one per form
                # is not enough: at `[slot=1, nsib=2]` every surviving rule is
                # `map:sib@0`, and the derived fills need `map:sib@2`, which
                # loses a competition *within* the map form.
                by_path.setdefault(g, {})
                cur = by_path[g].get((form, path))
                if cur is None or rule.rank < cur.rank:
                    by_path[g][(form, path)] = rule
            current = best[g].get(form)
            if current is None or rule.rank < current.rank:
                best[g][form] = rule

    # -- what the frontier still gets wrong ------------------------------
    def _match(self, rule: _Rule, codes: np.ndarray,
               code_of: list[dict]) -> np.ndarray | None:
        """Boolean mask of the fills this rule's guard fires on."""
        mask: np.ndarray | None = None
        for k, v in rule.guard:
            code = code_of[k].get(v)
            if code is None:
                return None
            hit = codes[k] == code
            mask = hit if mask is None else (mask & hit)
        return np.ones(codes.shape[1], dtype=bool) if mask is None else mask

    def _resolve_many(self, rule: _Rule, idx: np.ndarray, pv: np.ndarray,
               fv: np.ndarray | None = None) -> np.ndarray:
        """This rule's prediction at each fill in ``idx``; ``MISSING`` where it declines.

        Not named ``_apply``. It was, and ``nn.Module._apply`` is what
        ``.to(device)`` calls to walk a module's tensors — so shadowing it left
        training and evaluation working perfectly and made the fitted model
        **impossible to load back**. Nothing in the sweep noticed: three arms ran
        green, wrote their summaries, and the failure surfaced only in the
        analysis script that reopens them. See
        ``notes/lessons/2026-08-16-a-private-name-on-a-torch-module-is-not-private.md``.

        With ``fv`` given, each fill is answered by the table fitted on the fold
        it is *not* in. The residual has to be computed that way or the frontier
        aims at the wrong thing: on the first fit this method used the deployed
        table, which is empty until :meth:`_refit` runs, so every ``map`` and
        ``const`` rule silently declined and rounds two and three were steered by
        a residual in which only the copy rules existed. The visible symptom was
        a residual that stopped moving after round one.
        """
        if rule.form == "const" and fv is None:
            return np.full(idx.size, rule.const if rule.const is not None
                           else MISSING, dtype=np.int64)
        vals = (np.zeros(idx.size, dtype=np.int64) if rule.form == "const"
                else pv[idx, rule.path])
        if rule.form == "copy":
            return vals
        out = np.full(idx.size, MISSING, dtype=np.int64)
        for n, v in enumerate(vals):
            if v == MISSING:
                continue
            table = (rule.table if fv is None
                     else rule.fold_table[1 - int(fv[idx[n]])])
            got = table.get(int(v))
            if got is not None:
                out[n] = got
        return out

    def _residual(self, kept: Sequence[_Rule], codes: np.ndarray,
                  code_of: list[dict], pv: np.ndarray, av: np.ndarray,
                  fv: np.ndarray) -> np.ndarray:
        """Fills no kept rule already answers correctly, rules taken in rank order.

        The rules are consulted the way prediction consults them — highest rank
        first, first one that resolves wins — so this is the set of fills the
        *model* gets wrong rather than the set some rule gets wrong. Predictions
        are out of fold, so a rule cannot clear a fill off the frontier by having
        memorised it.
        """
        n = codes.shape[1]
        decided = np.zeros(n, dtype=bool)
        right = np.zeros(n, dtype=bool)
        for rule in kept:
            mask = self._match(rule, codes, code_of)
            if mask is None:
                continue
            idx = np.flatnonzero(mask & ~decided)
            if not idx.size:
                continue
            pred = self._resolve_many(rule, idx, pv, fv)
            live = pred != MISSING
            hit = idx[live]
            decided[hit] = True
            right[hit] = pred[live] == av[hit]
        return np.flatnonzero(~right)

    def _useful(self, kept: Sequence[_Rule], codes: np.ndarray,
                code_of: list[dict], pv: np.ndarray, av: np.ndarray,
                fv: np.ndarray) -> list[_Rule]:
        """The rules that actually answer a fill, consulted in rank order.

        A rule ranked below others that already cover everything it matches is
        not wrong, it is unreachable — and it still occupies one of the
        ``max_rules`` slots, which is how a later round was able to evict the
        rules doing the work. Filtering by reachability before the cap makes the
        cap bite on rules that matter instead of on rules that happen to sort
        late.
        """
        n = codes.shape[1]
        decided = np.zeros(n, dtype=bool)
        out: list[_Rule] = []
        for rule in kept:
            mask = self._match(rule, codes, code_of)
            if mask is None:
                continue
            idx = np.flatnonzero(mask & ~decided)
            if not idx.size:
                continue
            pred = self._resolve_many(rule, idx, pv, fv)
            live = pred != MISSING
            if not live.any():
                continue
            decided[idx[live]] = True
            out.append(rule)
        return out

    @staticmethod
    def _prune(kept: list[_Rule]) -> list[_Rule]:
        """Drop rules that a higher-ranked generalisation makes unreachable."""
        out: list[_Rule] = []
        for rule in kept:
            if not any(k.dominates(rule) for k in out):
                out.append(rule)
        return out

    def _refit(self, rule: _Rule, codes: np.ndarray, code_of: list[dict],
               pv: np.ndarray, av: np.ndarray) -> None:
        """Fit the deployed table on both folds, the precision having come from one.

        Estimating and deploying a table on the same fills is the failure the
        cross-fit exists to stop. Refitting *after* the estimate is fixed is not
        that: nothing about which hypotheses survived depends on this pass.
        """
        if rule.form == "copy":
            return
        mask = self._match(rule, codes, code_of)
        if mask is None:
            return
        idx = np.flatnonzero(mask)
        counts: dict[int, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for i in idx:
            k = 0 if rule.form == "const" else int(pv[i, rule.path])
            if k == MISSING:
                continue
            counts[k][int(av[i])] += 1
        table = _modal(counts)
        if rule.form == "const":
            rule.const = table.get(0)
        else:
            rule.table = table

    # ---- the gate -----------------------------------------------------
    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        """Price the vote as a mixture weight, not as an argmax accuracy.

        ``ptrgen-001`` against ``ptrgen-argmax`` measured this at +0.017 label
        lift and 0.58 bits for one method, so a new model fitting its gate the
        old way would start 0.58 bits behind for no reason. The score handed to
        the calibrator is the firing rule's verified precision — the model's own
        statement about how far it should be believed.
        """
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(
                episodes, tok, repeats=1, seed=7, max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id is None or label_id < 0:
                    continue
                vals = _path_labels(view, node)
                rule = self._fire(self.rules, _guard_atoms(view, node), vals)
                if rule is None:
                    continue
                scores.append(rule.score)
                votes.append(1.0 if rule.resolve(vals) == int(label_id) else 0.0)
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        if scores:
            self.gate_map = MassCalibrator().fit(scores, votes, backoff)

    # ---- prediction ---------------------------------------------------
    @staticmethod
    def _fire(rules: Sequence[_Rule], atoms: tuple,
              path_vals: tuple) -> _Rule | None:
        for rule in rules:
            if rule.matches(atoms) and rule.resolve(path_vals) is not None:
                return rule
        return None

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            atoms = _guard_atoms(view, i)
            vals = _path_labels(view, i)
            label_vote: Votes = ABSTAIN
            rule = self._fire(self.rules, atoms, vals)
            if rule is not None:
                gate = (float(self.gate_map(rule.score))
                        if self.gate_map.fitted else rule.score)
                pred = rule.resolve(vals)
                if pred is not None and gate > 0.0:
                    label_vote = ({int(pred): 1.0}, gate)
            # The type head gets its own rules and its own confidence. Sharing
            # the label head's is the mistake this repo has paid for four times,
            # most expensively as -1.96 type lift on three models at once.
            tvals = _path_types(view, i)
            trule = self._fire(self.type_rules, atoms, tvals)
            type_vote: Votes = ABSTAIN
            if trule is not None:
                tpred = trule.resolve(tvals)
                if tpred is not None:
                    type_vote = ({int(tpred): 1.0},
                                 min(0.15 + 0.8 * trule.score, 0.95))
            out[i] = (label_vote, type_vote)
        return out

    # ---- reporting ----------------------------------------------------
    def n_symbolic_parameters(self) -> int:
        return sum(r.dl for r in self.rules) + sum(r.dl for r in self.type_rules)

    def render(self) -> str:
        """The surviving hypotheses, and — first — which forms survived at all.

        The form census is the point rather than decoration. Whether a ``map:``
        rule survived verification is what separates "the derivation was induced"
        from "the score moved", and it is a property of the *fitted model* rather
        than an inference from a table downstream of it. In
        ``derive:wordnet-perm`` it is predicted to read zero on the derived
        guards.
        """
        lines = []
        for head, rules in (("label", self.rules), ("type", self.type_rules)):
            census = collections.Counter(r.form for r in rules)
            lines.append(f"{head}: {len(rules)} rules  " + ", ".join(
                f"{f}={census.get(f, 0)}" for f in ("const", "copy", "map")))
        for entry in self.search_log:
            lines.append(
                f"  round {entry['round']} [{entry['head']}]: "
                f"{entry['proposed']} guards, {entry['kept']} kept, "
                f"{entry['residual']}/{entry['fills']} fills still wrong")
        lines.append("top label hypotheses:")
        lines += [f"  {r!r}" for r in self.rules[:20]]
        maps = [r for r in self.rules if r.form == "map"]
        lines.append(f"surviving map rules: {len(maps)}")
        for r in maps[:6]:
            shown = ", ".join(
                f"{self.tok.itos[k] if self.tok else k}->"
                f"{self.tok.itos[v] if self.tok else v}"
                for k, v in list(r.table.items())[:8])
            lines.append(f"  {r!r}\n      |m|={len(r.table)}  {shown}")
        return "\n".join(lines)


@register("frontier-002",
          doc="frontier with the proposal gate separated from the verification gate.")
class FrontierRareModel(FrontierModel):
    """One number different from ``frontier-001``: what it takes to *propose*.

    ``frontier-001`` uses one threshold for two questions. Verification asks "is
    this rule reliable", and :func:`_lcb` already prices a small sample there.
    Proposal asks only "is this guard worth evaluating", and an absolute count
    there means a guard specific to a phenomenon occupying 0.2% of the fills
    cannot clear a number fixed for a corpus of 86,805 — so **the search is not
    permitted to consider it**, which is a different failure from not finding it.

    Measured consequence on ``frontier-001``: no guard specific to the derived
    slot is ever proposed, the derivation is absorbed into ``[slot=1, nsib=4]``,
    that guard misses 45% of the derived positions, and they abstain. Strip the
    guard off its own winning rule and the same path and table answer **100%**
    of the bucket.

    So this variant drops the proposal gate to 2 and leaves the verification
    gate at 12. **Predicted before running:** ``acc | derived, not copyable``
    rises above ``frontier-001``'s 0.532 in ``derive:wordnet``, stays at the
    blind marginal in ``derive:wordnet-perm``, and the pooled table barely moves
    — the derived slot is 0.20% of positions, so a pooled change of more than
    ~0.003 would mean something other than the derivation moved. Refuted if the
    derived bucket does not rise, which would say the guard was never what was
    limiting recall.

    Registered beside ``frontier-001`` rather than editing it, so one sweep
    prints both rows against the same floors.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.propose_support = int(cfg.get("propose_support", 2))


@register("frontier-003",
          doc="frontier keeping the best rule of each resolver form per guard, not one overall.")
class FrontierBothModel(FrontierModel):
    """One number different again: how many resolvers survive per guard.

    ``frontier-001`` keeps the single best resolver for each guard. That is what
    discards the derivation. On ``[phead='obj', slot=1]`` — the guard covering
    80% of the derived slot — the chosen resolver is ``const`` at score 0.993,
    and ``map:sib@2``, which is **1.000 on the derived members** and 0.179 on the
    rest, is thrown away for being 0.625 on average.

    A rule is ranked by its average over the population its guard admits, and an
    **average cannot see a sub-population**. Keeping one rule per *form* rather
    than one per guard lets both survive and lets the ordering decide which
    fires, which is a decision the ordering can make per fill and the average
    cannot.

    **Predicted before running:** ``acc | derived, not copyable`` rises above
    ``frontier-001``'s 0.532 in ``derive:wordnet``; the control stays at the
    blind marginal; the pooled table moves by less than ~0.003, because the
    derived slot is 0.20% of positions. Refuted if the bucket does not move,
    which would mean the discarded map was not what was missing and the cause is
    somewhere I have not looked — this is the fourth candidate, and the first
    three were the proposal gate, the rank ordering and the guard language, each
    built and each refuted.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.keep_per_guard = int(cfg.get("keep_per_guard", 3))


@register("frontier-004",
          doc="frontier-003 plus a tolerance band that resolves near-ties toward the copy.")
class FrontierTolerantModel(FrontierBothModel):
    """Treat precisions within a band as equal and let brevity break the tie.

    Rank is precision-first, so a ``map`` ahead of a ``copy`` by a few
    thousandths of held-out precision takes every fill the two share. That is
    the right call on the training distribution and the wrong one under a symbol
    permutation, where the map's table keys are stale: measured on
    ``frontier-001``, 1,031 map rules still fire after a renaming — the
    permutation lands symbols on other symbols the table happens to hold — and
    **9.4% of those firings are correct**.

    A band makes near-ties resolve on description length instead, and a ``copy``
    has none. It is the same idea as
    ``notes/lessons/2026-08-14-record-the-curve-not-the-argmax.md``: a difference
    inside the noise of a held-out estimate is not a difference, and letting it
    choose is how a model ends up carrying rules it cannot justify.

    **Predicted before running:** ``renamed`` rises above ``frontier-003``'s
    0.2149 and plain ``label_acc`` falls — this trades exactly the quantity the
    band is defined on. Refuted if plain accuracy is unchanged *and* renamed does
    not move, which would mean no near-ties between forms exist and the band is
    inert. A large drop in plain accuracy for no renamed gain refutes it the
    other way.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.rank_tolerance = float(cfg.get("rank_tolerance", 0.05))


@register("frontier-soft",
          doc="frontier-003's rules read as a conclusion mass instead of a decision list.")
class FrontierSoftModel(FrontierBothModel):
    """Every matching rule votes, weighted by what it verified at.

    The two live findings of the last two days, put together. `SoftReason`'s
    transferable part turned out to be **emitting the closure as a distribution**
    rather than the fixpoint it was named for — ``softreason-onehop`` is second
    of twenty-six on ``label_bits`` for that one change. `frontier-003`'s is that
    keeping the renaming-invariant rules alongside the memorising ones is worth
    6.2x the equivariance for 0.0002 of accuracy.

    `frontier-001` is eleventh of twenty-four on bits precisely because it is a
    decision list: the highest-ranked matching rule fires, its whole vote lands
    on one symbol, and when it is wrong the mass on the truth is whatever the
    back-off had. Being unsure between two candidates and being wrong are the
    same observation to it. So here the rule set is read as a **weighted
    conclusion set** instead — every matching rule that resolves contributes
    ``score ** sharpness`` to its own prediction, and the gate is fitted on how
    peaked the result is.

    Nothing about the induction changes. Same guards, same cross-fit, same
    lattice, same rules — only the readout, which is what makes the comparison
    against ``frontier-003`` a measurement of the readout and of nothing else.

    **Predicted before running:** ``label_bits`` improves substantially against
    ``frontier-003``'s 7.445, because that number is made of exactly the
    behaviour this removes. ``label_acc`` moves little and in either direction —
    weighting cannot reorder a single rule's vote, it can only reorder which rule
    wins a contested fill. Refuted if bits do not improve, which would say the
    decision list was not what was costing them.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        #: Exponent on each rule's verified score. Higher is closer to
        #: winner-takes-all, so this knob interpolates back toward
        #: ``frontier-003``'s decision list and makes the readout comparison a
        #: curve rather than two points.
        self.sharpness = float(cfg.get("vote_sharpness", 4.0))
        #: How many matching rules may vote. Bounded because prediction walks
        #: the rule list per hidden node.
        self.max_voters = int(cfg.get("max_voters", 24))

    def _mass(self, atoms: tuple, vals: tuple) -> dict[int, float]:
        mass: dict[int, float] = collections.defaultdict(float)
        seen = 0
        for rule in self.rules:
            if seen >= self.max_voters:
                break
            if not rule.matches(atoms):
                continue
            pred = rule.resolve(vals)
            if pred is None:
                continue
            seen += 1
            mass[int(pred)] += max(rule.score, 0.0) ** self.sharpness
        return dict(mass)

    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        """Fitted on how peaked the mass is, which is what it is now claiming."""
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(
                episodes, tok, repeats=1, seed=7, max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id is None or label_id < 0:
                    continue
                mass = self._mass(_guard_atoms(view, node), _path_labels(view, node))
                total = sum(mass.values())
                if total <= 0.0:
                    continue
                scores.append(max(mass.values()) / total)
                votes.append(mass.get(int(label_id), 0.0) / total)
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        if scores:
            self.gate_map = MassCalibrator().fit(scores, votes, backoff)

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            atoms = _guard_atoms(view, i)
            mass = self._mass(atoms, _path_labels(view, i))
            total = sum(mass.values())
            label_vote: Votes = ABSTAIN
            if total > 0.0 and self.gate_map.fitted:
                gate = float(self.gate_map(max(mass.values()) / total))
                if gate > 0.0:
                    label_vote = ({k: v / total for k, v in mass.items()}, gate)
            tvals = _path_types(view, i)
            trule = self._fire(self.type_rules, atoms, tvals)
            type_vote: Votes = ABSTAIN
            if trule is not None:
                tpred = trule.resolve(tvals)
                if tpred is not None:
                    type_vote = ({int(tpred): 1.0},
                                 min(0.15 + 0.8 * trule.score, 0.95))
            out[i] = (label_vote, type_vote)
        return out


@register("frontier-vote",
          doc="frontier-soft keeping the rules a decision list would discard as unreachable.")
class FrontierVoteModel(FrontierSoftModel):
    """The diversity term, in the one place the search was destroying it.

    [[2026-08-17-verification-and-diversity-are-in-tension]] measured that on
    **52.7%** of fills every rule that fires proposes the same symbol, median
    top-share 1.0000 — so ``frontier-soft``'s distribution readout has nothing to
    spread mass over, and its ``vote_sharpness`` curve is flat across a
    sixteen-fold range because of it.

    The note ended with the prediction that keeping rules *because they disagree*
    should move bits. This is the cheapest version of that, and it is a deletion
    rather than an addition: :meth:`_useful` drops rules that never get a turn,
    and a rule never gets a turn exactly when a higher-ranked rule already
    answers its fills — which is to say, the filter removes the alternatives. It
    is the correct filter for a decision list and the wrong one for a vote.

    **Predicted before running:** the share of fills whose voting rules propose a
    single symbol falls well below 0.527, and ``label_bits`` improves on
    ``frontier-soft``'s 7.061. Refuted if bits do not move — which would say the
    diagnosis is wrong and the gap to ``softreason-onehop``'s 6.148 is about what
    a closure *computes* rather than how many conclusions it holds. Accuracy is
    expected to move little: the rules being restored rank below the ones that
    were already deciding, so they can only outvote them in aggregate.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.reachability_filter = bool(cfg.get("reachability_filter", False))


@register("frontier-005",
          doc="frontier-soft keeping one rule per (form, path) per guard, not per form.")
class FrontierPathModel(FrontierSoftModel):
    """The sixth candidate, and the first with the evidence gathered *first*.

    ``notes/lessons/2026-08-17-i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective.md``
    says: before disabling a stage, show that what it removes differs from what
    it keeps. Done, and this is what it showed.

    The derived fills ``frontier-001`` misses differ from the ones it answers in
    **exactly one guard atom** — ``nsib=2`` against ``nsib=4``, with ptype, slot,
    depth and kids identical. So the derived slot comes in two object layouts and
    the model has a rule for one of them. At ``[slot=1, nsib=2]`` it holds five
    rules and **every one is** ``map:sib@0``; what those fills need is
    ``map:sib@2``, which the empty-guard test showed answers **100%** of the
    bucket.

    ``keep_per_guard`` does not reach this, and that is why ``frontier-003`` was
    a null on the bucket: it keeps one rule per *form*, and ``map:sib@0`` and
    ``map:sib@2`` are the same form. The competition that discards the right
    resolver happens **inside** the map form, between two paths.

    So: keep one rule per ``(form, path)``. And on the **soft** readout rather
    than the decision list, deliberately — ``map:sib@0`` scores 0.883 and would
    fire first, so under first-match-wins the extra rule never gets a turn. Only
    a vote lets the right answer compete with the wrong one.

    **Predicted before running:** ``acc | derived, not copyable`` rises above the
    0.531546 that five previous candidates left untouched — this is the first
    variant built after locating the discarded rule rather than guessing at a
    stage. Refuted if it stays at 0.531546, which would mean the extra rule is
    kept and still outvoted, and the readout weighting is the next thing to look
    at rather than the rule set.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.keep_by_path = bool(cfg.get("keep_by_path", True))


@register("frontier-006",
          doc="the conjunction: a lower proposal gate AND one rule per (form, path).")
class FrontierConjunctionModel(FrontierBothModel):
    """Two fixes that are each necessary and neither sufficient, applied together.

    Six candidates were tested one at a time and all six were nulls. Two of them
    turn out to be halves of one cause, and single-factor ablation cannot find a
    conjunctive cause — it reports both halves as nulls, which is exactly what
    happened.

    The guard the derived ``nsib=2`` fills need is the **two-atom**
    ``[slot=1, nsib=2]``. Every kept rule with those two atoms carries a third
    that excludes them — ``ptype='list'``, ``depth=3``, ``depth=5``,
    ``kids=True``, ``phead='<unk>'`` — while the fills are
    ``ptype='pred', phead='obj', depth=4, kids=False``. So two things have to be
    true at once and neither alone does anything:

    * the two-atom guard has to be **proposed**. Guard size decides the round
      (:attr:`ROUNDS` is ``((0,1), (2,), (3,))``), so a size-2 guard gets exactly
      one chance, in round one, against the residual left by round zero. If its
      residual support misses the bar there it is never reconsidered.
      ``frontier-002`` lowered that gate alone: null.
    * ``map:sib@2`` has to **survive under it**. ``map:sib@0`` scores higher on
      that guard's whole population, and one-rule-per-form discards the other
      path. ``frontier-005`` fixed that alone: null, and worse.

    Decision-list readout deliberately, not the vote: the vote costs 0.089 on
    this bucket on its own (0.532 -> 0.443, measured), so mixing it in would
    confound the conjunction with a known-harmful third change.

    **Predicted before running:** ``acc | derived, not copyable`` rises above
    0.531546 — the number six previous candidates left untouched to six decimals.
    Refuted if it stays there, which would mean the two-atom guard is absent for
    a third reason again and the honest answer is still "unknown".

    A risk worth stating: with a decision list, ``map:sib@0`` outranks
    ``map:sib@2`` and fires first, so the ``nsib=2`` fills may go from abstaining
    to being *confidently wrong*, which would show as the bucket falling rather
    than rising. That is a real possible outcome of this design and not a
    surprise if it happens.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.keep_by_path = bool(cfg.get("keep_by_path", True))
        self.propose_support = int(cfg.get("propose_support", 2))


@register("frontier-007",
          doc="the conjunction, with the precision floor lowered so a general guard can keep a rule.")
class FrontierFloorModel(FrontierConjunctionModel):
    """Eighth candidate, and the first located by logging the search itself.

    Instrumenting every resolver ``_offer`` sees at ``[slot=1, nsib=2]`` — the
    guard the abstaining derived fills need — settles it. For the **label** head
    not one resolver clears ``min_precision = 0.5``: the best are
    ``map:parent`` at 0.201 and ``copy:sib@0`` at 0.118. So the guard produces no
    label rule at all, ``_useful`` and ``_prune`` then remove what little is
    left, and the fills fall through to ``[slot=1] -> map:sib@3``, which cannot
    resolve for a two-sibling object and abstains.

    (The six high-precision resolvers an earlier trace showed surviving at this
    guard were the **type** head's. ``_offer`` runs for both heads and the trace
    did not separate them — worth recording, because that conflation is what
    made a scratch recomputation look like it contradicted the model when it
    agreed with it exactly.)

    A *specialisation* of the guard does keep a map — ``[ptype='list', slot=1,
    nsib=2] -> map:sib@0`` at 0.912 — because narrowing the population
    concentrates the relation. The derived fills are ``ptype='pred'``, and no
    specialisation covering them survived. **One global precision floor cannot
    serve both ends of the lattice**: it is generous at a narrow guard and
    prohibitive at a broad one, and the phenomena that live at broad guards are
    exactly the ones no narrow guard names.

    **Predicted before running:** with the floor at 0.2 a label rule survives at
    ``[slot=1, nsib=2]`` and ``acc | derived, not copyable`` rises above the
    0.531546 that seven candidates left untouched. The control must stay near the
    blind marginal; if the treatment rises *and the control rises with it*, the
    floor is admitting noise rather than the relation and the result is void.
    Refuted if the bucket does not move, in which case the honest answer after
    eight candidates is that I should stop guessing and characterise the
    population instead.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.min_precision = float(cfg.get("min_precision", 0.2))


@register("frontier-nomap",
          doc="frontier with the map form removed: the control in its own hypothesis class.")
class FrontierNoMapModel(FrontierModel):
    """The same search, the same verifier, the same gate — copy and const only.

    ``frontier-001``'s claim is that the registry could not *state* the planted
    rule, not that it could not search for one. That claim is only testable
    against a model differing in the hypothesis language and in nothing else:
    same guards, same lattice, same cross-fit, same residual rounds, same MDL
    ordering, same calibrator. Anything else — comparing against ``ilp`` or
    ``corefer`` — confounds the resolver set with the whole rest of the design,
    which is the mistake
    ``notes/lessons/2026-08-15-a-floor-outside-the-models-hypothesis-class.md``
    is about.

    Predicted before running: **0.000 on the derived non-copyable bucket**, for
    the same reason fifteen registered models score exactly that — a copy cannot
    produce a symbol no visible node carries, and a ``const`` under a guard that
    cannot see the kind sibling's label cannot tell the six kinds apart. If it
    scores above the blind marginal there, the expressiveness argument is wrong
    and ``frontier-001``'s result needs a different explanation.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.forms = ("const", "copy")
