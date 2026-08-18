"""Batches from an address space, with a bounded buffer and a resumable cursor.

The old sampler took a ``Sequence[Episode]``, called ``len`` on it and shuffled
an index list over the whole corpus. Both of those are the same mistake: they
need the dataset to fit in memory in order to decide what order to read it in.

Here the order comes from the keyed permutation in :mod:`.key`, evaluated one
point at a time, so nothing larger than the bucketing window is ever held. The
window is the only buffer, and its size is ``batch_size * bucket`` samples —
independent of whether the split has ten thousand addresses or ten trillion.

**Bucketing is a speed measure and changes which samples share a batch, not
which samples are seen.** That was true of the old sampler and stays true here;
it is worth restating because it is the one place where a batching decision
could quietly become a sampling decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .case import language_episode_view
from .key import SampleKey

__all__ = ["Cursor", "stream_cases", "stream_episodes", "stream_batches"]


@dataclass
class Cursor:
    """Where a stream got to. Small enough to sit in a checkpoint.

    A resumed run continues at ``consumed`` keys into ``epoch`` — the *same next
    key*, because the permutation is a pure function of ``(dataset, split,
    epoch, worker)`` and does not depend on what was drawn before it. That is
    the property a shuffled index array cannot have once it no longer exists.
    """

    split: str
    epoch: int = 0
    consumed: int = 0
    worker: int = 0
    workers: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"split": self.split, "epoch": self.epoch,
                "consumed": self.consumed, "worker": self.worker,
                "workers": self.workers}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cursor":
        return cls(**d)


def stream_cases(dataset, cursor: Cursor, *, epochs: int | None = 1
                 ) -> Iterator[tuple[SampleKey, Any]]:
    """``(key, WorldCase)`` from ``cursor`` onward, advancing it as it goes.

    ``epochs=None`` runs forever, moving to the next epoch-block when one is
    exhausted — which draws *new* samples rather than replaying the old ones.
    """
    epoch = cursor.epoch
    seen_epochs = 0
    while epochs is None or seen_epochs < epochs:
        skip = cursor.consumed if epoch == cursor.epoch else 0
        for i, key in enumerate(dataset.keys(cursor.split, epoch=epoch,
                                             worker=cursor.worker,
                                             workers=cursor.workers)):
            if i < skip:
                continue
            cursor.epoch, cursor.consumed = epoch, i + 1
            yield key, dataset.get(key)
        seen_epochs += 1
        epoch += 1
        cursor.epoch, cursor.consumed = epoch, 0
        if dataset.splits[cursor.split].finite:
            return


def stream_episodes(dataset, cursor: Cursor, *, epochs: int | None = 1):
    """The curriculum ``Episode`` view of :func:`stream_cases`."""
    for _, case in stream_cases(dataset, cursor, epochs=epochs):
        yield language_episode_view(case)


def stream_batches(dataset, cursor: Cursor, task: Any, tok: Any, *,
                   batch_size: int, bucket: int = 8,
                   epochs: int | None = 1) -> Iterator[Any]:
    """Length-bucketed batches, holding at most ``batch_size * bucket`` samples.

    Same contract as the old ``batches`` — anything with ``.name`` and
    ``.collate`` is a task — so a model written against the list-based sampler
    runs against a stream without changing a line.
    """
    window = batch_size * max(bucket, 1)
    buf: list[Any] = []
    for ep in stream_episodes(dataset, cursor, epochs=epochs):
        buf.append(ep)
        if len(buf) >= window:
            yield from _drain(buf, task, tok, batch_size)
            buf = []
    if buf:
        yield from _drain(buf, task, tok, batch_size)


def _drain(buf: list[Any], task: Any, tok: Any, batch_size: int):
    buf.sort(key=lambda e: len(e.graph) if task.name == "node" else len(e.text))
    for b in range(0, len(buf), batch_size):
        picked = buf[b:b + batch_size]
        if picked:
            yield task.collate(picked, tok)
