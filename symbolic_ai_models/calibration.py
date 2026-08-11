"""Does a model's confidence mean anything?

Every model here already states one. A network's is the probability its softmax
puts on its own top choice; a rule-based model's is the same number, arrived at
through the mixture in :mod:`symbolic_ai_models.models.symbolic`, where an
abstention lands on the back-off and a confident vote does not. Neither has ever
been checked against what actually happened.

It should be. This repo insists that an accuracy without a floor is not a
result; a confidence that does not track correctness is the same kind of empty
number, and worse, because it invites a reader to trust the wrong answers. A
model that says 0.9 and is right half the time is not merely wrong, it is
wrong in a way that cannot be noticed downstream.

So: bucket the predictions by stated confidence, and in each bucket compare the
mean confidence with the observed accuracy. Perfect calibration is the diagonal.
The summary numbers are the standard ones:

* **ECE** — expected calibration error, the bucket-weighted mean gap between
  confidence and accuracy. One number, and the one to compare.
* **MCE** — the worst single bucket, which matters more than ECE when the
  failure is concentrated somewhere a caller would actually act on.
* **overconfidence** — signed, so a model that is systematically too sure looks
  different from one that is systematically too shy. Both are miscalibrated;
  only the first is dangerous.

This is measured on the same evaluation episodes and the same masked positions
as everything else, so it is not a separate experiment that could disagree with
the headline numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import torch

from .data.curriculum import Episode
from .data.tokenizer import SymbolTokenizer

__all__ = ["Bucket", "CalibrationReport", "calibrate", "calibrate_model"]


@dataclass
class Bucket:
    """One confidence band, and what happened inside it."""

    lo: float
    hi: float
    n: int
    confidence: float
    accuracy: float

    @property
    def gap(self) -> float:
        return self.confidence - self.accuracy


@dataclass
class CalibrationReport:
    """Stated confidence against observed accuracy."""

    buckets: list[Bucket] = field(default_factory=list)
    n: int = 0
    ece: float = 0.0
    mce: float = 0.0
    overconfidence: float = 0.0
    accuracy: float = 0.0
    mean_confidence: float = 0.0

    def table(self) -> str:
        head = (f"{'confidence':<14}{'n':>7}{'stated':>9}{'actual':>9}{'gap':>9}")
        lines = [head, "-" * len(head)]
        for b in self.buckets:
            if not b.n:
                continue
            lines.append(f"{f'{b.lo:.1f}-{b.hi:.1f}':<14}{b.n:>7}"
                         f"{b.confidence:>9.3f}{b.accuracy:>9.3f}{b.gap:>+9.3f}")
        lines.append("-" * len(head))
        lines.append(f"{'overall':<14}{self.n:>7}{self.mean_confidence:>9.3f}"
                     f"{self.accuracy:>9.3f}{self.overconfidence:>+9.3f}")
        lines.append(f"ECE {self.ece:.3f}   MCE {self.mce:.3f}   "
                     f"(+gap = overconfident: says more than it delivers)")
        return "\n".join(lines)


def calibrate(confidence: np.ndarray, correct: np.ndarray,
              n_bins: int = 10) -> CalibrationReport:
    """Bucket by stated confidence; compare each bucket against what happened."""
    confidence = np.asarray(confidence, dtype=np.float64).ravel()
    correct = np.asarray(correct, dtype=np.float64).ravel()
    if confidence.size == 0:
        return CalibrationReport()

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    buckets: list[Bucket] = []
    ece = mce = 0.0
    total = confidence.size
    for lo, hi in zip(edges[:-1], edges[1:]):
        # Half-open bins, closed at the top edge, so a prediction of exactly 1.0
        # is counted rather than silently dropped.
        inside = (confidence >= lo) & ((confidence < hi) | (hi >= 1.0))
        n = int(inside.sum())
        if not n:
            buckets.append(Bucket(lo, hi, 0, float("nan"), float("nan")))
            continue
        conf = float(confidence[inside].mean())
        acc = float(correct[inside].mean())
        buckets.append(Bucket(lo, hi, n, conf, acc))
        ece += (n / total) * abs(conf - acc)
        mce = max(mce, abs(conf - acc))

    return CalibrationReport(
        buckets=buckets, n=total, ece=ece, mce=mce,
        overconfidence=float(confidence.mean() - correct.mean()),
        accuracy=float(correct.mean()), mean_confidence=float(confidence.mean()))


@torch.no_grad()
def calibrate_model(model, task, episodes: Sequence[Episode],
                    tok: SymbolTokenizer, *, n_bins: int = 10,
                    device: torch.device | str = "cpu") -> CalibrationReport:
    """Run ``task`` and score the probability the model put on its own answer.

    The same positions the task scores, so this cannot disagree with the
    headline accuracy: the confidence measured is the probability of the
    ``argmax``, and the outcome is whether that ``argmax`` was right.
    """
    was_training = model.training
    model.eval()
    batch = task.collate(episodes, tok)
    if device != "cpu":
        batch = batch.to(device)
    logits = model(batch).symbol_logits.float()
    if was_training:
        model.train()

    scored = batch.target_tokens >= 0
    if not bool(scored.any()):
        return CalibrationReport()
    probs = torch.softmax(logits, dim=-1)
    confidence, predicted = probs.max(dim=-1)
    correct = (predicted == batch.target_tokens) & scored
    return calibrate(confidence[scored].cpu().numpy(),
                     correct[scored].cpu().numpy(), n_bins=n_bins)
