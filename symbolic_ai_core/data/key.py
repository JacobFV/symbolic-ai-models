"""A sample's **address**, and the permutation that orders addresses.

A dataset here is not a list. It is an *address space* plus a replayable
generator, which is the only shape that lets a practically unbounded training
stream cost the same memory as a small one. This module holds the address half:
what a sample is called, how a stream of names is ordered, and how that order is
split across workers.

Three properties everything above this module leans on:

* **A sample is a pure function of its address.** The curriculum already had
  this — an episode is a pure function of ``(lesson, seed)`` — and it is what
  makes a cache optional rather than authoritative, and what makes an
  interrupted run resume at the same next key rather than at the same offset
  into a shuffled array that no longer exists.
* **Shuffling never materialises an index.** ``random.shuffle(range(n))`` is
  where dataset-as-``Sequence`` actually bites: it needs ``n``, and ``n`` is
  supposed to be allowed to be ``10**12``. The order here comes from a keyed
  pseudo-random permutation evaluated one point at a time, so position ``i`` of
  epoch ``e`` is computable without knowing what is at position ``i - 1``.
* **Worker shards are disjoint by construction**, not by agreement. Worker ``w``
  of ``W`` takes the positions congruent to ``w`` mod ``W`` *after* permutation,
  so no two workers can draw the same key and no coordination is needed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterator

__all__ = ["SampleKey", "block_permutation", "positions", "keyed_seed"]


@dataclass(frozen=True, order=True)
class SampleKey:
    """What one sample is called.

    ``ordinal`` indexes the dataset's address space; the dataset decides what an
    ordinal means (for the language curriculum it factors into a lesson and a
    seed). ``epoch`` is part of the *name*, not a loop counter: a training
    stream may be unbounded, and epoch ``e`` selects which block of the address
    space this pass draws from, so two epochs draw different samples rather than
    re-drawing the same ones in a different order.
    """

    dataset_id: str
    split: str
    epoch: int
    ordinal: int

    def __str__(self) -> str:
        return f"{self.dataset_id}/{self.split}/{self.epoch}/{self.ordinal}"


def keyed_seed(*parts: object) -> int:
    """A 64-bit seed from a tuple of names. Stable across processes and runs.

    ``hash()`` is not: Python salts string hashing per process unless
    ``PYTHONHASHSEED`` is set, and a shuffle keyed on it would silently give a
    resumed run a different order from the one it was interrupted in.
    """
    h = hashlib.blake2b("|".join(str(p) for p in parts).encode(), digest_size=8)
    return int.from_bytes(h.digest(), "big")


def _round(value: int, key: int, r: int) -> int:
    h = hashlib.blake2b(f"{key}|{r}|{value}".encode(), digest_size=8)
    return int.from_bytes(h.digest(), "big")


def block_permutation(index: int, domain: int, key: int, *, rounds: int = 4) -> int:
    """A bijection of ``range(domain)`` onto itself, evaluated at one point.

    A four-round Feistel network over a power-of-two domain, with **cycle
    walking** for the domains that are not: if the network lands outside
    ``domain`` it is applied again, which is exact rather than approximate — a
    Feistel network is a permutation of the enclosing power of two, so the
    points inside ``domain`` that map outside form cycles that are followed
    until they come back. Cost is bounded in expectation by the padding ratio,
    at most two applications on average.

    Not cryptographic and not trying to be. What it has to be is *a
    permutation*: every index in the block appears exactly once, which is the
    property a shuffled epoch is supposed to have and a hash-and-sort does not.
    """
    if domain <= 1:
        return 0
    if not 0 <= index < domain:
        raise ValueError(f"index {index} out of domain {domain}")
    bits = max(2, (domain - 1).bit_length())
    half = (bits + 1) // 2
    mask = (1 << half) - 1
    total = 1 << (2 * half)
    x = index
    while True:
        left, right = x >> half, x & mask
        for r in range(rounds):
            left, right = right, left ^ (_round(right, key, r) & mask)
        y = ((left << half) | right) % total
        if y < domain:
            return y
        x = y                                    # cycle-walk, still a bijection


def positions(*, block: int, epoch: int, worker: int, workers: int,
              key: int, shuffle: bool = True) -> Iterator[int]:
    """The ordinals worker ``worker`` of ``workers`` draws, in order.

    Yields absolute ordinals: epoch ``e`` covers ``[e*block, (e+1)*block)``, so
    a second pass over a practically unbounded space sees *new* samples rather
    than the same ones reshuffled. That is deliberate and is the difference
    between an epoch and a replay — see
    ``notes/lessons`` on never expecting performance from repetition.
    """
    if workers < 1 or not 0 <= worker < workers:
        raise ValueError(f"worker {worker} of {workers} is not a valid shard")
    base = epoch * block
    epoch_key = keyed_seed(key, epoch)
    for i in range(worker, block, workers):
        yield base + (block_permutation(i, block, epoch_key) if shuffle else i)
