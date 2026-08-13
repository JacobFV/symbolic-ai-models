"""What a task is: a way to fill a batch, a loss, and a floor.

The floor is not decoration. ``langcurriculum`` refuses to report an accuracy
without one, on the grounds that a lesson whose answer set has two members and a
lesson whose answer set has nine are not comparable at the same score, and the
same argument applies here with more force: masked-node accuracy is dominated by
how often the answer was ``ident``, and a number that does not say so is not
telling you anything about the model.

So every task in this repo reports three things — its own score, the score of
the best thing that knows nothing but the training distribution, and the
fraction of the remaining headroom the model actually took:

    lift = (score - floor) / (ceiling - floor)

``lift`` is the number to compare across tasks and architectures. Zero is "no
better than the prior", one is perfect.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

import torch

from symbolic_ai_core.data.batch import SymbolicBatch
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..models.base import ModelOutput

__all__ = ["Task", "TaskOutput", "Totals", "lift", "bits"]


def bits(nats: float) -> float:
    """Cross-entropy in bits, which is the unit a floor is legible in."""
    return nats / math.log(2)


def lift(score: float, floor: float, ceiling: float = 1.0) -> float:
    """Fraction of the headroom above the floor that ``score`` claimed."""
    room = ceiling - floor
    return 0.0 if abs(room) < 1e-12 else (score - floor) / room


@dataclass
class TaskOutput:
    """A loss to step on, plus counts to accumulate exactly.

    Counts rather than averages: a mean of per-batch means is not the mean when
    batches differ in how many targets they carry, and under dynamic padding
    they always do.
    """

    loss: torch.Tensor
    counts: dict[str, float] = field(default_factory=dict)


class Totals(dict):
    """Summed counts across batches. ``+=`` a ``TaskOutput``'s counts into it."""

    def add(self, counts: dict[str, float]) -> "Totals":
        for k, v in counts.items():
            self[k] = self.get(k, 0.0) + v
        return self


class Task(Protocol):
    """Fill a batch, score a forward pass, say what the numbers mean."""

    name: str

    def collate(self, episodes: Sequence[Episode],
                tok: SymbolTokenizer) -> SymbolicBatch: ...

    def compute(self, out: ModelOutput, batch: SymbolicBatch) -> TaskOutput: ...

    def summarize(self, totals: Totals) -> dict[str, float]:
        """Turn accumulated counts into reportable metrics."""
        ...

    def floor(self, episodes: Sequence[Episode],
              tok: SymbolTokenizer, train: Sequence[Episode]) -> dict[str, float]:
        """The score of knowing only the training distribution."""
        ...


def _gather_targets(logits: torch.Tensor, targets: torch.Tensor
                    ) -> tuple[torch.Tensor, torch.Tensor, int]:
    """Flatten to the scored positions only. Returns ``(logits, targets, n)``."""
    flat_t = targets.reshape(-1)
    keep = flat_t >= 0
    n = int(keep.sum())
    if n == 0:
        return logits.new_zeros((0, logits.shape[-1])), flat_t.new_zeros((0,)), 0
    return logits.reshape(-1, logits.shape[-1])[keep], flat_t[keep], n


def score_block(logits: torch.Tensor, targets: torch.Tensor, prefix: str
                ) -> tuple[torch.Tensor, dict[str, float]]:
    """Cross-entropy plus exact counts for one head. Shared by both tasks."""
    lg, tg, n = _gather_targets(logits, targets)
    if n == 0:
        return logits.sum() * 0.0, {f"{prefix}_n": 0.0, f"{prefix}_nll": 0.0,
                                    f"{prefix}_correct": 0.0}
    loss = torch.nn.functional.cross_entropy(lg, tg)
    correct = float((lg.argmax(-1) == tg).sum())
    return loss, {f"{prefix}_n": float(n),
                  f"{prefix}_nll": float(loss.detach()) * n,
                  f"{prefix}_correct": correct}


def _safe(totals: Totals, num: str, den: str) -> float:
    d = totals.get(den, 0.0)
    return float(totals.get(num, 0.0) / d) if d else float("nan")


def ratio(totals: Totals, prefix: str) -> dict[str, float]:
    """The two numbers every head reports: accuracy and bits per prediction."""
    return {f"{prefix}_acc": _safe(totals, f"{prefix}_correct", f"{prefix}_n"),
            f"{prefix}_bits": bits(_safe(totals, f"{prefix}_nll", f"{prefix}_n")),
            f"{prefix}_n": float(totals.get(f"{prefix}_n", 0.0))}


def empirical_floor(counts: dict[Any, int]) -> tuple[float, float]:
    """``(majority accuracy, entropy in bits)`` of a label distribution.

    The two baselines a floor needs: the best a constant guess can do, and what
    the true distribution costs someone who knows it exactly but nothing else.
    """
    total = sum(counts.values())
    if not total:
        return 0.0, 0.0
    acc = max(counts.values()) / total
    ent = -sum((c / total) * math.log2(c / total) for c in counts.values() if c)
    return acc, ent
