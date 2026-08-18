"""What an answer rests on, and how to tell later that it still holds.

`possible_answers_scoped` established the mechanism this generalises: a
computation already declares its dependencies **by reading them**, so a mapping
that records reads recovers the dependency set with no annotation and no static
analysis of the query. There it recorded reads over *conflicts*. Here it records
reads over *facts*, which is the substrate-wide version and the only claim of
this repo's that survived contact with a realistic retrieval opponent — an ideal
retriever certifies determinacy in four rounds but has no stopping rule and
over-fetches 46x.

The thing to be careful about is what a certificate is actually worth, because
the obvious answer is wrong. A read-set certificate lets you re-check an answer
without recomputing it, so its value is

    (cost of recomputation) / (cost of revalidation)  x  (fraction still valid)

and revalidation is |read set| digest comparisons. For a query that is itself
one pass over its read set — a count, a sum, a max — those two costs are the
same thing and the certificate buys **nothing**. It pays exactly where the
computation is expensive relative to its dependency: a solver call, a fixed
point, a model. That ratio, not the size of the read set, is the number to
report, and quoting a small read set as if it were a saving is the error this
module's docstring exists to prevent.

**Digests, not values.** Revalidation compares a hash per key rather than the
value, so a key whose value is a 3,000-element holder set costs one comparison
instead of 3,000. The corpus side of that hash is computed once per snapshot and
amortised across every query, which is a real cost and is charged as one — see
`digest_all`. Comparing values instead would make revalidation O(bytes read) and
put the aggregate case back where it started.

**Misses are reads.** `store.get(k)` returning nothing is a fact the answer
depends on — "this filer holds nothing in that security" is load-bearing — so an
absent key is recorded with a digest of `MISSING`. Recording only hits is how a
certificate silently fails to notice an *addition*, which is 411,122 of the
744,136 changes in the one real corpus delta this repo has.
"""

from __future__ import annotations

import time
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterator, Mapping

__all__ = ["MISSING", "FullScan", "RecordingStore", "Certificate",
           "Revalidation", "certify", "revalidate", "digest_all",
           "changed_keys"]

#: The digest of a key that was read and was not there. A distinct sentinel
#: rather than ``None`` or ``0``, because a stored value that hashes to either
#: would then be indistinguishable from an absence.
MISSING = object()


class FullScan(RuntimeError):
    """The computation iterated the whole store, so its read set is the corpus.

    Raised rather than returning a certificate over every key, because such a
    certificate is *sound* and worthless, and a worthless certificate that looks
    like a real one is how a scoped method quietly becomes an unscoped one. A
    caller that genuinely means to depend on everything can pass
    ``allow_full_scan=True`` and gets the honest large read set.
    """


class RecordingStore(MappingABC):
    """A read-through view over a fact store that remembers what was asked for.

    The store is ``key -> value`` where a key names a *fact* at whatever
    granularity the query works in — ``("holders", cusip)``, ``("parent", lei)``.
    Granularity is the caller's choice and it is the choice that decides whether
    the certificate is tight: a key naming one row gives a huge exact read set,
    a key naming a whole adjacency gives a small read set that invalidates on any
    change beneath it.
    """

    def __init__(self, backing: Mapping[Hashable, Any], *,
                 allow_full_scan: bool = False) -> None:
        self._backing = backing
        self._allow_full_scan = allow_full_scan
        self.read: dict[Hashable, Any] = {}
        self.full_scan = False

    def _record(self, key: Hashable) -> Any:
        value = self._backing.get(key, MISSING)
        # Only the first read is recorded. A deterministic computation reading
        # the same key twice sees the same value, so a later read cannot carry
        # information the first did not.
        if key not in self.read:
            self.read[key] = value
        return value

    def __getitem__(self, key: Hashable) -> Any:
        value = self._record(key)
        if value is MISSING:
            raise KeyError(key)
        return value

    def get(self, key: Hashable, default: Any = None) -> Any:
        value = self._record(key)
        return default if value is MISSING else value

    def __contains__(self, key: object) -> bool:
        return self._record(key) is not MISSING

    def __iter__(self) -> Iterator[Hashable]:
        if not self._allow_full_scan:
            raise FullScan(
                "the computation iterated the store, so it depends on every key "
                "in it. That certificate is sound and worth nothing; index the "
                "query instead, or pass allow_full_scan=True and accept a read "
                "set the size of the corpus.")
        self.full_scan = True
        for key in self._backing:
            self._record(key)
        return iter(self._backing)

    def __len__(self) -> int:
        return len(self._backing)


def _digest(value: Any) -> Any:
    """A hash that is stable within a process and cheap for large values.

    Sets and lists are hashed by content, so a holder set that gained and lost
    the same filer digests equal — which is correct, that answer did not change.
    """
    if value is MISSING:
        return MISSING
    if isinstance(value, (set, frozenset)):
        return hash(frozenset(value))
    if isinstance(value, (list, tuple)):
        return hash(tuple(value))
    return hash(value)


@dataclass(frozen=True)
class Certificate:
    """An answer, everything it rests on, and nothing else.

    ``digests`` is what makes this re-checkable without the old corpus: it is
    the answer's view of the world at the time it was computed, one hash per
    fact read. ``compute_ns`` is carried because the certificate's *worth* is a
    ratio against it, and a certificate quoted without the cost of the thing it
    replaces is not a result.
    """

    answer: Any
    digests: Mapping[Hashable, Any]
    compute_ns: int = 0
    full_scan: bool = False
    meta: Mapping[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.digests)

    @property
    def keys(self) -> tuple[Hashable, ...]:
        return tuple(sorted(self.digests, key=repr))

    def to_dict(self) -> dict[str, Any]:
        return {"answer": self.answer, "size": self.size,
                "compute_ns": self.compute_ns, "full_scan": self.full_scan,
                "keys": [repr(k) for k in self.keys], "meta": dict(self.meta)}


@dataclass(frozen=True)
class Revalidation:
    """Whether a cached answer provably still holds, and what it cost to say so.

    ``valid`` is a *proof*, not a guess, under the two conditions the recording
    trick needs: the computation is deterministic, and it depends on the store
    only through the mapping it was handed. A computation that reaches around
    the store for a fact makes its read set a lie, and there is no way to detect
    that from here — which is why the experiment scripts anchor against full
    recomputation rather than trusting this.
    """

    valid: bool
    checked: int
    changed: tuple[Hashable, ...]
    revalidate_ns: int = 0

    @property
    def speedup_over(self) -> Callable[[int], float]:
        def ratio(compute_ns: int) -> float:
            return compute_ns / self.revalidate_ns if self.revalidate_ns else 0.0
        return ratio


def certify(compute: Callable[[Mapping[Hashable, Any]], Any],
            store: Mapping[Hashable, Any], *,
            allow_full_scan: bool = False,
            meta: Mapping[str, Any] | None = None) -> Certificate:
    """Run ``compute`` against a recording view and keep what it read.

    One pass. The read set is exact for a deterministic computation, unlike
    `possible_answers_scoped`, which iterates to a fixed point because *pinning*
    a conflict can expose reads that the default assignment hid. Nothing is
    pinned here, so one pass sees every read there is.
    """
    rec = RecordingStore(store, allow_full_scan=allow_full_scan)
    t0 = time.perf_counter_ns()
    answer = compute(rec)
    ns = time.perf_counter_ns() - t0
    return Certificate(answer=answer,
                       digests={k: _digest(v) for k, v in rec.read.items()},
                       compute_ns=ns, full_scan=rec.full_scan,
                       meta=dict(meta or {}))


def digest_all(store: Mapping[Hashable, Any]) -> dict[Hashable, Any]:
    """Every key's digest, computed once per snapshot.

    This is the amortised half of revalidation and it is not free — it is one
    pass over the corpus per update. Charged in the ledger against the number of
    answers maintained, because a per-query saving paid for by a per-corpus cost
    is only a saving above some number of queries, and not saying where that
    crossover is would be the same error as quoting throughput as a price.
    """
    return {k: _digest(v) for k, v in store.items()}


def revalidate(cert: Certificate,
               digests: Mapping[Hashable, Any]) -> Revalidation:
    """Does the cached answer still hold? Answered without recomputing it.

    ``digests`` is the *new* snapshot's digest map from :func:`digest_all`. A
    key the certificate read and the new snapshot lacks digests to ``MISSING``,
    which compares unequal to any real digest — so a deletion invalidates, as it
    must.
    """
    t0 = time.perf_counter_ns()
    changed = [k for k, d in cert.digests.items()
               if digests.get(k, MISSING) != d]
    ns = time.perf_counter_ns() - t0
    return Revalidation(valid=not changed, checked=len(cert.digests),
                        changed=tuple(sorted(changed, key=repr)),
                        revalidate_ns=ns)


def changed_keys(old: Mapping[Hashable, Any],
                 new: Mapping[Hashable, Any]) -> frozenset[Hashable]:
    """The keys whose digest moved between two snapshots.

    The delta, in the same currency the certificates are written in. A query
    that supplies a *stability condition* — "this answer survives while fewer
    than m of its facts move" — is checked against this rather than against the
    corpus, and that is the only rung whose cost is proportional to the update
    rather than to the dependency.
    """
    keys = set(old) | set(new)
    return frozenset(k for k in keys
                     if old.get(k, MISSING) != new.get(k, MISSING))
