"""A dataset is an **address space plus a replayable generator**, not a list.

The curriculum was already lazy — an episode is a pure function of
``(lesson, seed)`` — and then the trainer called ``list()`` on it and the sampler
built an index array over the whole corpus. So the generator was lazy and the
system was not, and the practical ceiling on a training set was RAM.

Here a dataset exposes:

* ``get(key)`` — build the sample at one address, without building any other;
* ``keys(split, epoch, worker, workers)`` — the addresses this worker draws.

and everything that follows is a consequence:

* a training split can be a practically unbounded key range, because nothing
  ever holds more than a bounded buffer;
* an evaluation split is a **finite pinned list**, so what was scored is a fact
  rather than a function of how long the run happened to go on;
* a checkpoint stores a cursor, and a resumed run continues at the same next
  key rather than at the same offset into a shuffled array that no longer
  exists;
* a cache is optional and cannot change the bytes, because the bytes are a pure
  function of the address.

**An epoch draws different samples, not the same ones reshuffled.** Epoch *e* of
the training split covers ordinals ``[e*block, (e+1)*block)``. That is deliberate
and it is the standing rule about never expecting performance from repetition,
moved into the addressing scheme so it cannot be forgotten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Protocol, Sequence, runtime_checkable

from .case import WorldCase, case_from_episode
from .key import SampleKey, keyed_seed, positions

__all__ = ["ReplayableDataset", "CurriculumDataset", "SplitSpec"]


@runtime_checkable
class ReplayableDataset(Protocol):
    """Anything addressable and replayable. Duck-typed, like the task protocol."""

    dataset_id: str

    def get(self, key: SampleKey) -> WorldCase: ...

    def keys(self, split: str, *, epoch: int = 0, worker: int = 0,
             workers: int = 1) -> Iterator[SampleKey]: ...


@dataclass(frozen=True)
class SplitSpec:
    """One split's slice of the address space.

    ``seed0`` is what actually keeps train and eval apart, exactly as it did
    before: evaluation seeds start at a million and training at zero, so the two
    cannot meet unless somebody asks for a million episodes per lesson. That is
    a property of the addresses rather than of a split file that could be
    regenerated wrongly.
    """

    seed0: int
    per_lesson: int              #: episodes per lesson in one epoch-block
    shuffle: bool = True
    finite: bool = False         #: an eval split is pinned and does not grow


@dataclass
class CurriculumDataset:
    """The 179-lesson curriculum, addressed rather than listed.

    Ordinal *n* factors as ``(lesson = lessons[n % L], seed = seed0 + n // L)``
    — lesson-minor, so any prefix of the stream covers every lesson rather than
    being all of lesson one. That matters because models here are trained under
    an example budget and a lesson-major prefix would train on a fraction of the
    curriculum while claiming to train on all of it.
    """

    lessons: Sequence[str]
    dataset_id: str = "curriculum"
    language: str = "english"
    curriculum: str = "base"
    max_nodes: int = 512
    splits: dict[str, SplitSpec] = field(default_factory=dict)
    _binder: object = field(default=None, repr=False)
    _lc: object = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.splits:
            # A training block of a million seeds per lesson is 179 million
            # samples per epoch, which is not a size anybody will exhaust and
            # costs nothing to declare -- the point of an address space is that
            # its size is not a memory cost.
            self.splits = {
                "train": SplitSpec(seed0=0, per_lesson=1_000_000),
                "eval": SplitSpec(seed0=1_000_000, per_lesson=16,
                                  shuffle=False, finite=True),
            }
        self._ensure_generator()

    def _ensure_generator(self) -> None:
        if self._lc is not None:
            return
        from . import curriculum as C
        from . import langdb
        langdb.ensure_for([self.language])
        self._lc = C._lc()
        self._binder = C._binder_factory(self.curriculum)

    # ---- the address space -------------------------------------------
    @property
    def n_lessons(self) -> int:
        return len(self.lessons)

    def block(self, split: str) -> int:
        return self.n_lessons * self.splits[split].per_lesson

    def address(self, split: str, ordinal: int) -> tuple[str, int]:
        """``ordinal -> (lesson_id, seed)``. The whole of the addressing."""
        spec = self.splits[split]
        lesson = self.lessons[ordinal % self.n_lessons]
        return lesson, spec.seed0 + ordinal // self.n_lessons

    def keys(self, split: str, *, epoch: int = 0, worker: int = 0,
             workers: int = 1) -> Iterator[SampleKey]:
        spec = self.splits[split]
        if spec.finite and epoch != 0:
            raise ValueError(
                f"split {split!r} is finite and pinned: it has exactly "
                f"{self.block(split)} keys and asking for epoch {epoch} would "
                f"score samples that are not in it. Evaluate the same keys "
                f"again rather than inventing new ones.")
        key = keyed_seed(self.dataset_id, split, self.language, self.curriculum)
        for ordinal in positions(block=self.block(split), epoch=epoch,
                                 worker=worker, workers=workers, key=key,
                                 shuffle=spec.shuffle):
            yield SampleKey(self.dataset_id, split, epoch, ordinal)

    # ---- the sample --------------------------------------------------
    def get(self, key: SampleKey) -> WorldCase:
        from .curriculum import episode_at
        lesson, seed = self.address(key.split, key.ordinal)
        ep = episode_at(lesson, seed, language=self.language,
                        max_nodes=self.max_nodes, make_binder=self._binder,
                        lc=self._lc)
        if ep is None:                                     # pragma: no cover
            raise RuntimeError(f"{key} produced no episode")
        return case_from_episode(ep, key, dataset_id=self.dataset_id,
                                 recipe=self.curriculum)

    def episode(self, key: SampleKey):
        """The curriculum ``Episode`` at this address, for existing consumers."""
        from .case import language_episode_view
        return language_episode_view(self.get(key))

    def __getstate__(self):
        """Do not pickle the generator handles; a worker rebuilds them."""
        d = dict(self.__dict__)
        d["_lc"] = d["_binder"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._ensure_generator()
