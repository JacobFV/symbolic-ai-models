"""What a task is: a way to fill a batch, a loss, and a floor.

The floor discipline itself — ``lift``, ``empirical_floor``, and the exact
counting that ``score_block`` and ``ratio`` do — moved to
:mod:`symbolic_ai_core.floors`, because it is the repo's central methodological
commitment and is not about models. What is left here is the part that genuinely
is: a :class:`Task` is typed in terms of
:class:`~symbolic_ai_models.models.base.ModelOutput` and
:class:`~symbolic_ai_core.data.batch.SymbolicBatch`, so it cannot live below the
models package without inverting the dependency.

The moved names are re-exported from here. They were imported from this module
across the repo and on the ``omegaclaw`` branch, and the re-export costs a line
each.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence

import torch

from symbolic_ai_core.data.batch import SymbolicBatch
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from symbolic_ai_core.floors import (Totals, bits, empirical_floor, lift, ratio,
                                     score_block)

from ..models.base import ModelOutput

__all__ = ["Task", "TaskOutput", "Totals", "lift", "bits", "empirical_floor",
           "ratio", "score_block"]


@dataclass
class TaskOutput:
    """A loss to step on, plus counts to accumulate exactly.

    Counts rather than averages: a mean of per-batch means is not the mean when
    batches differ in how many targets they carry, and under dynamic padding
    they always do.
    """

    loss: torch.Tensor
    counts: dict[str, float] = field(default_factory=dict)


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
