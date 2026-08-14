"""Separating *balance* from *provenance* in a seeded class layer.

Three seeding experiments in this repo are nulls, and the second of them came
with a mechanism rather than a shrug. ``synthex_class-002`` gives the model the
curriculum's own ground-truth node type for every symbol and **loses** to
``sha256(symbol) % k`` at matched cardinality. The reason found at the time was
not that the ontology is wrong — it is exact — but that it is *skewed*: on the
full curriculum **75.6% of symbols are ``ident``**, so a context built from
neighbour classes puts three quarters of every pair in one cell and cannot
discriminate. The hash partition is uniform by construction and therefore
carries more bits about a symbol than the true ontology does.

Nobody had separated the two. ``synthex_class-002`` differs from
``synthex_random-002`` in **both** provenance (semantic vs meaningless) and
balance (1.35 bits vs 2.81 bits), so its gap is unattributable. This module
supplies the two missing cells of the 2x2:

===================  ==========================  ==========================
\\                    skewed (curated profile)    balanced (uniform)
===================  ==========================  ==========================
curated provenance   ``synthex_class-002``       ``synthex_balanced-003``
no provenance        ``synthex_skewrand-003``    ``synthex_random-002``
===================  ==========================  ==========================

With all four scored under one config the two main effects come apart:

* **balance**   = (balanced + random) - (class + skewrand)
* **provenance** = (class + balanced) - (skewrand + random)

``synthex_random-003`` is the same construction as ``synthex_random-002`` with a
salt, so the arbitrary draw the control happens to sit on can be re-drawn and the
comparison read against a noise band rather than against zero.

The rebalancing, chosen before any score was seen
-------------------------------------------------
**Equal-frequency binning that respects curated boundaries.** Of the three
defensible rebalancings, only this one can reach the target:

* *merge-to-target-entropy* cannot. Merging never splits the giant class, so the
  entropy is capped at ``H(0.756, 0.244) = 0.80`` bits against a target of
  ``log2(7) = 2.81``. It is arithmetically unable to match the control.
* *recursive split on a structural feature* imports information the ontology does
  not contain — depth, frequency, parent type — and would make a win
  unattributable all over again. Provenance would no longer be held fixed.
* *equal-frequency binning* splits only within a curated class and merges only
  whole curated classes, so **every bin is either a subset of one curated class
  or a union of whole curated classes**. That is the most curated information a
  partition of this cardinality and this entropy can carry.

Concretely, with ``k`` = the number of distinct curated classes:

1. Apportion ``k`` slots to the curated classes by symbol count, largest
   remainder (Hamilton), ties by class id.
2. A class holding ``s >= 1`` slots is split into ``s`` sub-buckets by
   ``sha256(salt|symbol) % s``. The sub-buckets are semantically identical to
   each other and each is *pure*: membership still determines the curated class.
3. A class holding no slot is kept **whole** — never split — and dropped into
   whichever bin is smallest at that moment, largest leftover class first.

The honest caveat, and it is the finding in embryo: a partition where 75.6% of
symbols share a class **cannot be balanced from inside the ontology**. Step 2 is
arbitrary by necessity, so ``synthex_balanced-003`` is curated-where-it-can-be
and hash-where-it-must-be. The mutual information ``I(assignment; curated type)``
is reported beside every entropy so how much provenance survived is a number and
not a claim.
"""

from __future__ import annotations

import collections
import hashlib
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..registry import register
from ..synthex_002.model import SynthexClassModel, SynthexCurated

__all__ = ["SynthexBalanced", "SynthexSkewRandom", "SynthexRandomSalted",
           "SynthexBalancedPure", "SynthexSkewRandomPure",
           "SynthexRandomPure", "SynthexCuratedPure",
           "rebalance", "skew_matched_random", "uniform_random",
           "assignment_stats"]


def _digest(symbol: int, salt: str) -> int:
    """Deterministic across processes. ``hash()`` is salted per interpreter and
    would make every row here irreproducible while looking fine in one session."""
    return int(hashlib.sha256(f"{salt}{symbol}".encode()).hexdigest(), 16)


# ---------------------------------------------------------------------------
# the three partitions
# ---------------------------------------------------------------------------
def _apportion(sizes: dict[int, int], k: int) -> dict[int, int]:
    """Hamilton's largest-remainder method. Ties break by class id, ascending."""
    total = sum(sizes.values())
    exact = {c: n * k / total for c, n in sizes.items()}
    slots = {c: int(v) for c, v in exact.items()}
    left = k - sum(slots.values())
    order = sorted(exact, key=lambda c: (-(exact[c] - slots[c]), c))
    for c in order[:max(left, 0)]:
        slots[c] += 1
    return slots


def rebalance(curated: dict[int, int], k: int, salt: str = "") -> dict[int, int]:
    """Equal-frequency bins that never cut across a curated class boundary.

    Splitting happens *inside* a curated class and merging happens *between*
    whole ones, so a bin is always a subset of one class or a union of several.
    Nothing outside the ontology is consulted except the arbitrary sub-bucket
    index, which is what the balance constraint costs.
    """
    sizes = collections.Counter(curated.values())
    slots = _apportion(dict(sizes), k)
    assignment: dict[int, int] = {}
    load = [0] * k
    nxt = 0
    for c in sorted(sizes):
        s = slots[c]
        if s < 1:
            continue
        base, nxt = nxt, nxt + s
        for symbol, cls in curated.items():
            if cls != c:
                continue
            bin_ = base + (_digest(symbol, salt) % s if s > 1 else 0)
            assignment[symbol] = bin_
            load[bin_] += 1
    # Classes too small to earn a slot stay intact and join the emptiest bin.
    leftovers = sorted((c for c in sizes if slots[c] < 1),
                       key=lambda c: (-sizes[c], c))
    members = collections.defaultdict(list)
    for symbol, cls in curated.items():
        members[cls].append(symbol)
    for c in leftovers:
        bin_ = min(range(k), key=lambda b: (load[b], b))
        for symbol in members[c]:
            assignment[symbol] = bin_
        load[bin_] += sizes[c]
    return assignment


def skew_matched_random(curated: dict[int, int], salt: str = "") -> dict[int, int]:
    """A meaningless partition wearing the curated partition's size profile.

    Symbols are ordered by their digest — a deterministic pseudo-random shuffle
    independent of anything the ontology knows — and handed out in blocks whose
    sizes are exactly the curated class sizes. Same cardinality, same entropy,
    zero mutual information with the ontology.
    """
    sizes = sorted(collections.Counter(curated.values()).values(), reverse=True)
    order = sorted(curated, key=lambda s: (_digest(s, salt), s))
    assignment: dict[int, int] = {}
    at = 0
    for cls, n in enumerate(sizes):
        for symbol in order[at:at + n]:
            assignment[symbol] = cls
        at += n
    for symbol in order[at:]:                    # rounding never bites, but
        assignment[symbol] = len(sizes) - 1      # a symbol must not go missing
    return assignment


def uniform_random(curated: dict[int, int], k: int,
                   salt: str = "") -> dict[int, int]:
    """``synthex_random-002``'s partition, with the draw exposed as a salt."""
    return {symbol: _digest(symbol, salt) % k for symbol in curated}


# ---------------------------------------------------------------------------
# what "matched balance" means as a number
# ---------------------------------------------------------------------------
def assignment_stats(assignment: dict[int, int],
                     curated: dict[int, int]) -> dict[str, float]:
    """Entropy of the class assignment, and how much of the ontology survives.

    ``entropy`` is over symbol *types*, which is the quantity the control is
    uniform in and therefore the one "matched balance" has to mean. ``mutual``
    is ``I(assignment; curated type)`` in bits: it is ``H(curated)`` for the
    curated layer itself, ~0 for any partition drawn independently of it, and
    somewhere between for a rebalancing that preserved what it could.
    """
    import math

    def h(counts) -> float:
        total = sum(counts.values())
        return -sum((v / total) * math.log2(v / total)
                    for v in counts.values() if v) if total else 0.0

    a = collections.Counter(assignment.values())
    c = collections.Counter(curated[s] for s in assignment)
    joint = collections.Counter((assignment[s], curated[s]) for s in assignment)
    return {"classes": float(len(a)),
            "entropy": h(a),
            "top_share": max(a.values()) / sum(a.values()) if a else 0.0,
            "curated_entropy": h(c),
            "mutual": h(a) + h(c) - h(joint)}


# ---------------------------------------------------------------------------
# the models
# ---------------------------------------------------------------------------
class _Synthex003(SynthexClassModel):
    """Everything below differs from ``synthex_class-002`` in one method only.

    ``_assign_classes`` is the single overridden hook, exactly as in the -002
    pair, so a gap between any two of these five rows is the partition and can be
    nothing else.
    """

    def _curated(self, episodes: Sequence[Episode],
                 tok: SymbolTokenizer) -> dict[int, int]:
        return SynthexCurated._assign_classes(self, episodes, tok)

    @property
    def salt(self) -> str:
        return str(self.cfg.get("class_salt", ""))

    #: Filled in by ``_assign_classes`` so a run records what it partitioned
    #: into, rather than the reader having to re-derive it.
    stats: dict[str, float] = {}

    def render(self) -> str:
        bits = "  ".join(f"{k}={v:.3f}" for k, v in sorted(self.stats.items()))
        return super().render() + f"\n  partition: {bits}"


@register("synthex_balanced-003",
          doc="Curated classes rebalanced to the control's entropy: provenance "
              "held, balance varied.")
class SynthexBalanced(_Synthex003):
    """Curated provenance, uniform balance. The experiment's point.

    If curated semantics were real and merely masked by skew, this row beats
    ``synthex_random-002``. If it only matches it, provenance contributes nothing
    that a free balanced partition does not.
    """

    def _assign_classes(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> dict[int, int]:
        curated = self._curated(episodes, tok)
        k = max(len(set(curated.values())), 2)
        self.n_classes = k
        out = rebalance(curated, k, self.salt)
        self.stats = assignment_stats(out, curated)
        return out


@register("synthex_skewrand-003",
          doc="Meaningless classes wearing the curated size profile: balance "
              "held skewed, provenance removed.")
class SynthexSkewRandom(_Synthex003):
    """The cell that makes the -002 gap readable.

    ``synthex_class-002`` differs from ``synthex_random-002`` in provenance *and*
    balance. This row removes the provenance and keeps the skew, so the
    difference between it and ``synthex_class-002`` is the value of the semantics
    at the ontology's own balance — and its difference from
    ``synthex_random-002`` is the price of the skew alone.
    """

    def _assign_classes(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> dict[int, int]:
        curated = self._curated(episodes, tok)
        self.n_classes = max(len(set(curated.values())), 2)
        out = skew_matched_random(curated, self.salt)
        self.stats = assignment_stats(out, curated)
        return out


@register("synthex_random-003",
          doc="synthex_random-002's uniform hash partition with the draw "
              "exposed, so four rows can be read against a noise band.")
class SynthexRandomSalted(_Synthex003):
    """Identical to ``synthex_random-002`` at the default empty salt.

    Registered beside it rather than in place of it because the -002 row is
    published: this one exists so the same construction can be re-drawn and the
    spread between draws measured. A difference smaller than that spread is not a
    difference.
    """

    def _assign_classes(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> dict[int, int]:
        curated = self._curated(episodes, tok)
        k = max(len(set(curated.values())), 2)
        self.n_classes = k
        out = uniform_random(curated, k, self.salt)
        self.stats = assignment_stats(out, curated)
        return out


# ---------------------------------------------------------------------------
# the same 2x2 without the shared memorising floor
# ---------------------------------------------------------------------------
# `RuleBasedModel.structural_fallback` donates a *shared* component to every
# rule-based model: an abstention lands on "the commonest label in this
# structural context" rather than on the unigram. It is a memoriser, it is where
# renaming sensitivity tends to live, and it is identical across all four cells —
# so it can only compress the differences between them, never create one. These
# four rows switch it off, which is the version of the comparison in which the
# class layer is the only thing answering.
class _Pure:
    structural_fallback = False


@register("synthex_class_pure-003",
          doc="synthex_class-002 with the shared structural fallback off.")
class SynthexCuratedPure(_Pure, SynthexCurated):
    pass


@register("synthex_balanced_pure-003",
          doc="synthex_balanced-003 with the shared structural fallback off.")
class SynthexBalancedPure(_Pure, SynthexBalanced):
    pass


@register("synthex_skewrand_pure-003",
          doc="synthex_skewrand-003 with the shared structural fallback off.")
class SynthexSkewRandomPure(_Pure, SynthexSkewRandom):
    pass


@register("synthex_random_pure-003",
          doc="synthex_random-003 with the shared structural fallback off.")
class SynthexRandomPure(_Pure, SynthexRandomSalted):
    pass
