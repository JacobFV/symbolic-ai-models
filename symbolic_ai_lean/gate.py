"""The gating diagnostic, and the controls that say what it is measuring.

Pre-registered in ``notes/decisions/2026-08-14-lean-ir-preregistration.md``,
before any of this was written, with its verdict table fixed in advance:

===================  ===============  ==========================================
prune rate           gold survival    verdict
===================  ===============  ==========================================
< ~30%               any              the line is dead
high                 < ~95%           worse than dead — abstention on ``repair``
                                      scores *below* chance, so an over-rejecting
                                      filter is negative value
high                 high             build the model
===================  ===============  ==========================================

Why this and not a model. The pointer's measured constraint is discrimination,
not recall: candidate recall 82.7% -> 93.1% -> 98.7% moved dev copy accuracy
0.4036 -> 0.4043 -> 0.4012, i.e. by nothing. So a typechecker is worth building
only if it removes candidates **without** removing the right one, and that is
one number needing no model at all.

Four controls, because a prune rate on its own says nothing:

``arity``
    Reject a candidate iff no visible occurrence of it has the hole's number of
    children. No types, no unification, no Lean. If the kernel does not beat
    this, the kernel *is* this, and the honest report is "an arity check with
    Lean branding".
``random``
    The expected gold survival of a filter that keeps the same *number* of
    labels, chosen meaninglessly. A kernel that prunes 60% and survives 60% has
    done nothing. Same-cardinality-but-meaningless is this repo's most
    productive instrument — it corrected four separate published results.
``shifted``
    The kernel, run against **another hole of the same episode**. Cardinality,
    signature and episode identical; only the question is wrong. Gold survival
    must fall to the random level. If it does not, the filter is not reading the
    hole and the prune rate is a property of the candidate set alone.
``permuted``
    Every symbol consistently renamed. Verdicts must be **identical**, symbol
    for symbol. A filter that moves under renaming is reading vocabulary, which
    is how ``ensemble-001``'s 1.14-bit headline died (0.467 -> 0.038).

Held-out **training** episodes throughout: seeds from 500, against training's
0..19, with eval's >= 1,000,000 untouched. All 179 lessons, never a slice —
``notes/lessons/2026-08-13-slices-have-inverted-results-eight-times.md``.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from symbolic_ai_core.data.curriculum import Episode, generate, lesson_ids
from symbolic_ai_core.data.term_graph import TermGraph

from .elaborate import STRUCTURAL_TYPES, Elaboration, Mode, elaborate

__all__ = ["GateResult", "Hole", "holes_of", "run_gate", "truncate",
           "arity_accepts"]

#: Where the diagnostic's episodes start. Training draws seeds 0..n_train-1 and
#: evaluation draws from 1,000,000; this sits between them, so the diagnostic is
#: settled on held-out *training* episodes exactly as the working agreements
#: require.
HELD_OUT_SEED0 = 500


def truncate(g: TermGraph, n: int) -> TermGraph:
    """The first ``n`` nodes. Valid because ``term_graph_from_json`` is breadth-first,
    so every parent precedes its children and a prefix is a tree."""
    if n >= len(g):
        return g
    return TermGraph(labels=g.labels[:n], types=g.types[:n], parent=g.parent[:n],
                 slot=g.slot[:n], depth=g.depth[:n])


def mask_nodes(g: TermGraph, rng: np.random.Generator, mask_rate: float) -> list[int]:
    """The same rule ``collate_graph`` uses, so the holes are the ones a model
    faces: an independent draw per node, and at least one question per graph."""
    n = len(g)
    chosen = np.flatnonzero(rng.random(n) < mask_rate)
    if len(chosen) == 0 and n:
        chosen = rng.integers(0, n, size=1)
    return [int(i) for i in chosen]


@dataclass
class Hole:
    """One scored question and everything the diagnostic needs about it."""

    node: int
    gold: str
    n_cand: int
    n_cand_lab: int
    kept: dict[str, dict[str, bool]] = field(default_factory=dict)


def arity_accepts(elab: Elaboration, i: int, label: str) -> bool:
    """The floor: does any visible occurrence of ``label`` have the hole's arity?

    Generous where the evidence disagrees — a symbol seen with two different
    arities is accepted at both. That is the same direction the kernel errs in,
    so the comparison is between two filters with the same bias.
    """
    want = len(elab.children[i])
    g = elab.graph
    for j in range(len(g)):
        if j in elab.hidden or g.labels[j] != label:
            continue
        if g.types[j] in STRUCTURAL_TYPES:
            continue
        if len(elab.children[j]) == want:
            return True
    return False


def holes_of(g: TermGraph, hidden: Sequence[int]) -> list[int]:
    """Masked nodes that carry a symbol — the ones the copy head is scored on.

    ``collate_graph`` also drops out-of-vocabulary labels from ``label_acc``,
    but the pointer metrics (``copy_acc``, ``label_group``) keep them, and 88.5%
    of them are invented ``ident`` names of which 80.7% are copyable. Excluding
    them would exclude the clearest case of the thing being measured.
    """
    return [i for i in hidden
            if g.labels[i] and g.types[i] not in STRUCTURAL_TYPES]


@dataclass
class GateResult:
    """Everything the pre-registered table needs, and the controls beside it."""

    modes: list[str]
    n_episodes: int
    n_holes: int
    n_copyable: int
    n_candidates: list[int]
    prune_node: dict[str, list[float]]
    prune_label: dict[str, list[float]]
    gold_survived: dict[str, list[bool]]
    random_survival: dict[str, list[float]]
    demoted_symbols: int
    total_symbols: int
    untyped_nodes: int
    total_nodes: int
    unconstrained_checks: int
    total_checks: int
    seconds: float
    checks: int
    #: mode -> verdict -> how many candidate checks ended that way.
    reasons: dict[str, dict[str, int]] = field(default_factory=dict)
    #: mode -> (rejected here but not by the arity floor,
    #:          rejected by the arity floor but not here).
    versus_arity: dict[str, tuple[int, int]] = field(default_factory=dict)
    #: mode -> how many gold answers this mode cut, by reason.
    gold_lost: dict[str, dict[str, int]] = field(default_factory=dict)

    # -- readings ---------------------------------------------------------
    def median_prune(self, mode: str) -> float:
        return statistics.median(self.prune_node[mode]) if self.prune_node[mode] else 0.0

    def mean_prune(self, mode: str) -> float:
        v = self.prune_node[mode]
        return sum(v) / len(v) if v else 0.0

    def median_prune_label(self, mode: str) -> float:
        v = self.prune_label[mode]
        return statistics.median(v) if v else 0.0

    def survival(self, mode: str) -> float:
        v = self.gold_survived[mode]
        return sum(v) / len(v) if v else 0.0

    def matched_random(self, mode: str) -> float:
        v = self.random_survival[mode]
        return sum(v) / len(v) if v else 0.0

    def table(self) -> str:
        head = (f"{'filter':<12}{'prune (median)':>16}{'prune (mean)':>14}"
                f"{'labels pruned':>15}{'gold survival':>15}"
                f"{'matched random':>16}")
        rows = [head, "-" * len(head)]
        for m in self.modes:
            rows.append(f"{m:<12}{self.median_prune(m):>16.3f}"
                        f"{self.mean_prune(m):>14.3f}"
                        f"{self.median_prune_label(m):>15.3f}"
                        f"{self.survival(m):>15.4f}"
                        f"{self.matched_random(m):>16.4f}")
        rows.append("")
        rows.append(f"{self.n_episodes} episodes, {self.n_holes} scored holes, "
                    f"{self.n_copyable} of them copyable "
                    f"({self.n_copyable / max(self.n_holes, 1):.3f}); "
                    f"median {int(statistics.median(self.n_candidates))} "
                    f"candidate nodes per hole")
        rows.append(f"coverage: {self.total_symbols - self.demoted_symbols}"
                    f"/{self.total_symbols} symbols kept a declaration "
                    f"({1 - self.demoted_symbols / max(self.total_symbols, 1):.4f}), "
                    f"{self.total_nodes - self.untyped_nodes}/{self.total_nodes} "
                    f"nodes typed "
                    f"({1 - self.untyped_nodes / max(self.total_nodes, 1):.4f})")
        rows.append(f"cost: {self.checks} candidate checks in {self.seconds:.2f}s "
                    f"= {self.checks / max(self.seconds, 1e-9):,.0f} checks/s")
        rows.append("")
        rows.append("against the arity floor (a filter that needs no types):")
        for m in self.modes:
            if m == "arity" or m not in self.versus_arity:
                continue
            extra, missed = self.versus_arity[m]
            rows.append(f"  {m:<10} rejects {extra:>7} the floor keeps, "
                        f"keeps {missed:>7} the floor rejects")
        rows.append("")
        rows.append("why a candidate was refused:")
        for m in self.modes:
            counts = self.reasons.get(m) or {}
            if not counts:
                continue
            total = sum(counts.values())
            detail = ", ".join(f"{k} {v / max(total, 1):.3f}"
                               for k, v in sorted(counts.items(),
                                                  key=lambda kv: -kv[1]))
            rows.append(f"  {m:<10} {detail}")
        rows.append("")
        rows.append("gold answers cut, by reason:")
        for m in self.modes:
            counts = self.gold_lost.get(m) or {}
            lost = sum(counts.values())
            detail = ", ".join(f"{k} {v}" for k, v in
                               sorted(counts.items(), key=lambda kv: -kv[1]))
            rows.append(f"  {m:<10} {lost:>5} / {self.n_copyable} "
                        + (f"({detail})" if detail else ""))
        return "\n".join(rows)


#: ``hybrid`` is the ``declared`` kernel **and** the arity floor, and it is not
#: a kernel: the floor gets its extra power by reading the arity of a symbol's
#: *field* occurrences, which is a fact about a record and not about a term
#: constant. It is reported because it is informative for what a Phase 2 model
#: would have to work with, and labelled because a hybrid quoted as a kernel is
#: how a line survives its own gate.
_MODES: tuple[str, ...] = ("open", "declared", "closed", "arity", "hybrid",
                           "shifted")


def run_gate(*, lessons: Sequence[str] | None = None, n: int = 3,
             seed0: int = HELD_OUT_SEED0, mask_rate: float = 0.15,
             max_nodes: int = 128, mask_seed: int = 0,
             modes: Sequence[str] = _MODES,
             episodes: Iterable[Episode] | None = None) -> GateResult:
    """Prune rate and gold survival, per filter, over held-out training episodes."""
    if episodes is None:
        episodes = generate(list(lessons or lesson_ids()), n=n, seed0=seed0)
    episodes = list(episodes)
    rng = np.random.default_rng(mask_seed)
    shift_rng = np.random.default_rng(mask_seed + 7)

    prune_node = {m: [] for m in modes}
    prune_label = {m: [] for m in modes}
    gold_survived = {m: [] for m in modes}
    random_survival = {m: [] for m in modes}
    n_candidates: list[int] = []
    n_holes = n_copyable = 0
    demoted = total_symbols = untyped = total_nodes = 0
    unconstrained = total_checks = checks = 0
    reasons: dict[str, dict[str, int]] = {m: {} for m in modes}
    versus: dict[str, list[int]] = {m: [0, 0] for m in modes}
    gold_lost: dict[str, dict[str, int]] = {m: {} for m in modes}

    t0 = time.process_time()
    for ep in episodes:
        g = truncate(ep.graph, max_nodes)
        if not len(g):
            continue
        hidden = mask_nodes(g, rng, mask_rate)
        scored = holes_of(g, hidden)
        if not scored:
            continue

        elabs: dict[str, Elaboration] = {}
        for m in modes:
            if m in ("open", "declared", "closed"):
                elabs[m] = elaborate(g, hidden, mode=m)
        if "hybrid" in modes and "declared" not in elabs:
            elabs["declared"] = elaborate(g, hidden, mode="declared")
        # `arity` and `shifted` reuse an elaboration for its structure only.
        base = elabs.get("open") or elaborate(g, hidden, mode="open")
        total_nodes += len(g)
        total_symbols += len(base.decl) + len(base.demoted)
        demoted += len(base.demoted)
        untyped += len(base.untyped)

        for i in scored:
            gold = g.labels[i]
            cand_nodes = base.candidate_nodes(i)
            cand_labels = base.candidate_labels(i)
            if not cand_nodes:
                continue
            n_holes += 1
            n_candidates.append(len(cand_nodes))
            copyable = gold in cand_labels
            n_copyable += copyable
            other = [j for j in scored if j != i]
            shift_to = (int(shift_rng.choice(other)) if other else i)

            floor = {c: arity_accepts(base, i, c) for c in cand_labels}
            for m in modes:
                if m == "arity":
                    why = {c: ("ok" if floor[c] else "arity") for c in cand_labels}
                elif m == "hybrid":
                    e = elabs["declared"]
                    why = {c: (e.verdict(i, c) if floor[c] else "arity")
                           for c in cand_labels}
                elif m == "shifted":
                    why = {c: base.verdict(shift_to, c) for c in cand_labels}
                else:
                    e = elabs[m]
                    why = {c: e.verdict(i, c) for c in cand_labels}
                    if m == "open":
                        unconstrained += sum(
                            1 for c in cand_labels if c not in e.decl)
                        total_checks += len(cand_labels)
                verdict = {c: w == "ok" for c, w in why.items()}
                for c, w in why.items():
                    reasons[m][w] = reasons[m].get(w, 0) + 1
                    if m != "arity":
                        versus[m][0] += (not verdict[c]) and floor[c]
                        versus[m][1] += verdict[c] and not floor[c]
                if copyable and not verdict[gold]:
                    gold_lost[m][why[gold]] = gold_lost[m].get(why[gold], 0) + 1
                checks += len(cand_labels)
                kept_nodes = sum(1 for j in cand_nodes if verdict[g.labels[j]])
                kept_lab = sum(1 for c in cand_labels if verdict[c])
                prune_node[m].append(1.0 - kept_nodes / len(cand_nodes))
                prune_label[m].append(1.0 - kept_lab / len(cand_labels))
                if copyable:
                    gold_survived[m].append(bool(verdict[gold]))
                    random_survival[m].append(kept_lab / len(cand_labels))
    seconds = time.process_time() - t0

    return GateResult(
        modes=list(modes), n_episodes=len(episodes), n_holes=n_holes,
        n_copyable=n_copyable, n_candidates=n_candidates,
        prune_node=prune_node, prune_label=prune_label,
        gold_survived=gold_survived, random_survival=random_survival,
        demoted_symbols=demoted, total_symbols=total_symbols,
        untyped_nodes=untyped, total_nodes=total_nodes,
        unconstrained_checks=unconstrained, total_checks=total_checks,
        seconds=seconds, checks=checks, reasons=reasons,
        versus_arity={m: (v[0], v[1]) for m, v in versus.items()},
        gold_lost=gold_lost)
