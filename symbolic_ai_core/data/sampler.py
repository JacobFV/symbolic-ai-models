"""Turning episodes into batches, for whoever needs them.

This lives below both the models and the trainer because both draw batches now:
a model that owns its own learning has to be able to iterate its training data
without importing the trainer that called it.

The task is duck-typed — anything with ``.name`` and ``.collate`` will do — so
this module has no dependency on :mod:`symbolic_ai_models.tasks` and cannot
close an import cycle.
"""

from __future__ import annotations

import random
from typing import Any, Iterator, Sequence

from .batch import SymbolicBatch
from .curriculum import Episode
from .tokenizer import SymbolTokenizer

__all__ = ["batches", "cycle"]


def batches(episodes: Sequence[Episode], task: Any, tok: SymbolTokenizer, *,
            batch_size: int, rng: random.Random, shuffle: bool = True,
            bucket: int = 8) -> Iterator[SymbolicBatch]:
    """Yield batches, bucketed by length within a shuffled window.

    Episode lengths across 179 lessons vary by more than an order of magnitude,
    and batching them at random means most of a batch is padding. Sorting inside
    a window of ``bucket`` batches keeps the sampling close to uniform while
    cutting the padding sharply — it is a speed measure, and it changes which
    episodes share a batch but not which episodes are seen.
    """
    order = list(range(len(episodes)))
    if shuffle:
        rng.shuffle(order)
    window = batch_size * max(bucket, 1)
    for start in range(0, len(order), window):
        chunk = order[start:start + window]
        chunk.sort(key=lambda i: len(episodes[i].graph) if task.name == "node"
                   else len(episodes[i].text))
        for b in range(0, len(chunk), batch_size):
            picked = [episodes[i] for i in chunk[b:b + batch_size]]
            if picked:
                yield task.collate(picked, tok)


def cycle(episodes: Sequence[Episode], task: Any, tok: SymbolTokenizer, *,
          batch_size: int, rng: random.Random) -> Iterator[SymbolicBatch]:
    """An endless reshuffled stream of batches for one task."""
    while True:
        empty = True
        for batch in batches(episodes, task, tok, batch_size=batch_size, rng=rng):
            empty = False
            yield batch
        if empty:                                            # pragma: no cover
            raise RuntimeError(f"task {task.name} produced no batches")
