"""Where a corpus keeps its information, and whether a symbolic model can reach it.

`.old/docs/limiting-language-analysis.tex` argues that the useful description of
a linguistic system is not its rules but its *asymptotic* observables — how the
possibility space grows, how far correlations reach, which distinctions survive
scale. Two of those observables decide whether the symbolic-LM bet is viable at
all, so they are measured here rather than assumed:

**Mutual information at separation d**, ``I(d) = I(x_t; x_{t+d})``. The decay
regime is the whole question. Exponential decay with correlation length ``xi``
means a finite context suffices and counting methods are near-optimal beyond a
few ``xi``. Power-law decay means no characteristic scale and hierarchy is doing
real work. A *non-decaying floor* means neither: it is the signature of a latent
variable held constant across the whole sequence, which is the best case for a
symbolic model because a finite latent can be identified and bound rather than
approximated.

**Effective rank** of the context-to-next-symbol matrix — the operational form
of "how large is the symbol state space really". If it is small, a minimal
sufficient statistic for prediction is small, and an exact symbolic machine is
affordable.

Why the null control is not optional
------------------------------------
The plug-in estimator ``sum p(x,y) log [p(x,y) / p(x)p(y)]`` is **biased
upward**, by roughly ``(|X|-1)(|Y|-1) / (2 N ln 2)`` bits for ``N`` samples. On
this curriculum that is order *one bit* — comparable to the entire effect being
measured. The first version of this measurement reported "``I(d)`` plateaus at
2.35 bits at ``d=128``, a constant-latent signature" from the raw plug-in
numbers alone, with no control. That reading may have been almost entirely
estimator bias, and there was no way to tell from the numbers reported.

So every curve is measured against **two** nulls, and needing two is the whole
subtlety. A shuffle *within* each sequence destroys order while leaving that
sequence's own symbol composition intact — so it is a null for distance
structure and is **not** a null for a sequence-level latent, because a constant
latent is precisely what it preserves. A test written to check the constant-
latent case caught this: the within-shuffle reproduced the effect exactly, 1.997
against 1.997. Reporting ``raw - within`` alone would therefore have concluded
that a corpus dominated by a per-sequence latent has *no* structure at all.

The second null draws each sequence's tokens from the pooled global
distribution, keeping only the lengths. That destroys order and composition
together, so it is the pure estimator floor. The three curves decompose::

    raw    - within  =  order structure          (falls off with d)
    within - global  =  sequence-latent structure (flat in d)
    global           =  plug-in bias             (what noise alone scores)

Which is more informative than the single corrected number this module was first
written to produce, and is the reason the constant-latent reading of the
curriculum can be stated at all rather than merely asserted.

This is the same discipline the rest of the repo applies to accuracy: a number
without a floor is not a result.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

__all__ = ["MICurve", "mutual_information", "mi_curve", "effective_rank",
           "DISTANCES"]

#: Log-spaced, so exponential and power-law decay are distinguishable by eye
#: over the same number of points.
DISTANCES = (1, 2, 4, 8, 16, 32, 64, 128)


@dataclass
class MICurve:
    """``I(d)`` on the data and against both nulls. See the module docstring."""

    distances: tuple[int, ...]
    raw: dict[int, float] = field(default_factory=dict)
    within: dict[int, float] = field(default_factory=dict)
    glob: dict[int, float] = field(default_factory=dict)
    n_pairs: dict[int, int] = field(default_factory=dict)

    def order(self, d: int) -> float:
        """Structure that depends on the arrangement, not the composition."""
        return self.raw.get(d, float("nan")) - self.within.get(d, float("nan"))

    def latent(self, d: int) -> float:
        """Structure carried by what the sequence is *about*, flat in ``d``."""
        return self.within.get(d, float("nan")) - self.glob.get(d, float("nan"))

    def table(self) -> str:
        head = (f"{'d':>5}{'I(d)':>9}{'within':>9}{'global':>9}"
                f"{'order':>9}{'latent':>9}{'pairs':>10}")
        lines = [head, "-" * len(head)]
        for d in self.distances:
            if d not in self.raw:
                continue
            lines.append(
                f"{d:>5}{self.raw[d]:>9.3f}{self.within[d]:>9.3f}"
                f"{self.glob[d]:>9.3f}{self.order(d):>9.3f}"
                f"{self.latent(d):>9.3f}{self.n_pairs[d]:>10}")
        return "\n".join(lines)


def mutual_information(pairs: Sequence[tuple[int, int]]) -> float:
    """Plug-in mutual information in bits. Biased upward; see the module note."""
    n = len(pairs)
    if n < 2:
        return float("nan")
    joint: collections.Counter = collections.Counter(pairs)
    left: collections.Counter = collections.Counter(a for a, _ in pairs)
    right: collections.Counter = collections.Counter(b for _, b in pairs)
    total = 0.0
    for (a, b), c in joint.items():
        p_xy = c / n
        total += p_xy * math.log2(p_xy * n * n / (left[a] * right[b]))
    return total


def _pairs_at(sequences: Sequence[Sequence[int]], d: int
              ) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for seq in sequences:
        out.extend((seq[i], seq[i + d]) for i in range(len(seq) - d))
    return out


def mi_curve(sequences: Sequence[Sequence[int]],
             distances: Iterable[int] = DISTANCES, *,
             seed: int = 0, min_pairs: int = 500) -> MICurve:
    """``I(d)`` with a shuffled null at every distance.

    Sequences are kept separate — pairs never straddle a boundary — because the
    question is how far dependence reaches *within* an utterance. Concatenating
    documents would manufacture a document-identity latent and produce a floor
    that says nothing about language.

    The null permutes tokens **within each sequence**, so it preserves each
    sequence's own symbol distribution and length, and destroys only the order.
    A weaker null that shuffled globally would also destroy the between-sequence
    composition differences and would understate the floor.
    """
    rng = np.random.default_rng(seed)

    # Null 1: order destroyed, per-sequence composition kept.
    within = []
    for seq in sequences:
        arr = np.array(seq)
        rng.shuffle(arr)
        within.append(arr.tolist())

    # Null 2: composition destroyed too. Tokens are drawn from the pooled
    # corpus, so no sequence keeps a subject of its own and the only structure
    # left is the global unigram — which is the estimator's own floor.
    pool = np.array([s for seq in sequences for s in seq])
    glob = [rng.choice(pool, size=len(seq), replace=True).tolist()
            for seq in sequences]

    curve = MICurve(distances=tuple(distances))
    for d in curve.distances:
        pairs = _pairs_at(sequences, d)
        if len(pairs) < min_pairs:
            continue
        curve.raw[d] = mutual_information(pairs)
        curve.within[d] = mutual_information(_pairs_at(within, d))
        curve.glob[d] = mutual_information(_pairs_at(glob, d))
        curve.n_pairs[d] = len(pairs)
    return curve


def effective_rank(sequences: Sequence[Sequence[int]], *, vocab: int,
                   min_count: int = 5) -> tuple[float, int, float]:
    """``(exp(entropy of the singular-value spectrum), contexts, top-50 mass)``.

    The entropy of the normalised spectrum is used rather than a threshold count
    because a hard cutoff invents a decision the data does not support. Rows are
    the previous symbol, columns the next; a context seen fewer than
    ``min_count`` times is dropped, since its row is a delta function and would
    inflate the rank with pure noise.
    """
    counts = np.zeros((vocab, vocab), dtype=np.float64)
    for seq in sequences:
        for a, b in zip(seq, seq[1:]):
            if 0 <= a < vocab and 0 <= b < vocab:
                counts[a, b] += 1.0
    keep = counts.sum(axis=1) >= min_count
    matrix = counts[keep]
    if not matrix.size:
        return float("nan"), 0, float("nan")
    matrix = matrix / matrix.sum(axis=1, keepdims=True)
    singular = np.linalg.svd(matrix, compute_uv=False)
    share = singular / singular.sum()
    entropy = float(-(share * np.log(share + 1e-12)).sum())
    return math.exp(entropy), int(matrix.shape[0]), float(share[:50].sum())
