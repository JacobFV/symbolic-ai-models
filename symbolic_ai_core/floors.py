"""Floors, lift, and the counting that makes both exact.

The floor is not decoration. ``langcurriculum`` refuses to report an accuracy
without one, on the grounds that a lesson whose answer set has two members and a
lesson whose answer set has nine are not comparable at the same score, and the
same argument applies to everything measured in this repo: masked-node accuracy
is dominated by how often the answer was ``ident``, and a number that does not
say so is not telling you anything about the model.

So every score here is reported alongside the score of the best thing that knows
nothing but the training distribution, and the fraction of the remaining headroom
that was actually taken::

    lift = (score - floor) / (ceiling - floor)

``lift`` is the number to compare across tasks and architectures. Zero is "no
better than the prior", one is perfect.

This lives in the core rather than in the models package because the floor
discipline is the repo's central methodological commitment and is not about
models. ``symbolic_ai_parsers`` reaches the same conclusion from the other end:
its :mod:`~symbolic_ai_parsers.floors` fits a *constant graph per metric* by
search, which is a different floor for a different codomain, and it quotes the
same argument for needing one at all.
"""

from __future__ import annotations

import math
from typing import Any

import torch

__all__ = ["Totals", "bits", "lift", "empirical_floor", "ratio", "score_block"]


def bits(nats: float) -> float:
    """Cross-entropy in bits, which is the unit a floor is legible in."""
    return nats / math.log(2)


def lift(score: float, floor: float, ceiling: float = 1.0) -> float:
    """Fraction of the headroom above the floor that ``score`` claimed."""
    room = ceiling - floor
    return 0.0 if abs(room) < 1e-12 else (score - floor) / room


class Totals(dict):
    """Summed counts across batches. ``+=`` a ``TaskOutput``'s counts into it.

    Counts rather than averages: a mean of per-batch means is not the mean when
    batches differ in how many targets they carry, and under dynamic padding they
    always do.
    """

    def add(self, counts: dict[str, float]) -> "Totals":
        for k, v in counts.items():
            self[k] = self.get(k, 0.0) + v
        return self


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
