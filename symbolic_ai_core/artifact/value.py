"""The artifact itself: an immutable typed value with a content address.

Two things here are load-bearing and neither is obvious.

**The identity is the content, not the producer.** ``artifact_id`` is a hash of
the canonical serialisation, so two kernels that compute the same thing produce
one artifact and a cache hit is a fact rather than a guess. It also means an
artifact cannot be edited: a changed value is a different artifact with a
different id, which is what lets a flow graph memoise by structural hash without
anyone having to remember to invalidate.

**Big things are referenced, not inlined.** A mesh, a raster, a tensor, a corpus
or a solver-native state stays in a blob store and the artifact carries a
``ref``. The flow graph must stay readable as JSON; a graph that contains every
triangle is a file format, not a program.

**Missing is not zero.** ``value is None`` with ``present=False`` says the field
was not observed. A default imputed here would be indistinguishable downstream
from a measurement, which is the mechanism behind more than one wrong number in
this repo's history — see ``notes/lessons`` on silent fallbacks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

__all__ = ["Artifact", "ArtifactRef", "Interval", "Provenance", "artifact_id",
           "canonical_bytes", "to_wire"]

#: Prefix of every artifact id, naming the digest so a later change of algorithm
#: is a *different* id rather than a silent collision across two conventions.
ID_ALGO = "blake2b"


def _instant(text: str | None) -> float | None:
    """An ISO-8601 timestamp as a number, or ``None`` if it is not one."""
    if text is None:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return None


def to_wire(value: Any) -> Any:
    """Recursively replace anything with a ``to_dict`` by its dict form.

    Node parameters are allowed to hold real objects — a ``flow.const@1`` node
    carries an :class:`Artifact`, a ``flow.fold@1`` node carries a ``FoldSpec``
    — because a graph built in Python should not have to be serialised to be
    run. This is the one place that flattens them, and both the wire form and
    the cache key go through it, so a graph and its cached results cannot end up
    keyed on two different renderings of the same parameters.
    """
    if hasattr(value, "to_dict"):
        return to_wire(value.to_dict())
    if isinstance(value, dict):
        return {k: to_wire(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_wire(v) for v in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """The bytes an artifact hashes. Deterministic across processes and runs.

    Sorted keys, no whitespace, UTF-8, and ``NaN``/``Infinity`` rejected rather
    than emitted — ``json`` will happily write bare ``NaN``, which is not JSON
    and does not round-trip through anything else that will ever read this.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def artifact_id(value: Any) -> str:
    """``artifact:blake2b:<hex>`` — the content address of ``value``."""
    h = hashlib.blake2b(canonical_bytes(value), digest_size=32)
    return f"artifact:{ID_ALGO}:{h.hexdigest()}"


@dataclass(frozen=True)
class Interval:
    """A half-open time interval, or an unbounded one. ``None`` is unbounded.

    Used for both of the two times every claim carries: ``valid_time`` is when
    something holds in the represented world, ``transaction_time`` is when this
    system learned it. Economic and political series are revised after
    publication — ALFRED exists beside FRED for exactly this — and a store with
    only one time cannot answer "what did we believe on the day we decided",
    which is the question a backtest is actually asking.
    """

    start: str | None = None
    end: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end}

    @property
    def unbounded(self) -> bool:
        return self.start is None and self.end is None

    def overlaps(self, other: "Interval") -> bool:
        """Whether two intervals can be talking about the same moment.

        An **unbounded** interval overlaps everything, which is the correct
        reading of "this claim does not say when": it cannot be shown to be
        about a different time, so it stays combinable.

        Bounds that are not ISO-parseable are treated as disjoint unless equal.
        That is the conservative direction -- it leaves claims in separate
        groups, producing an unresolved mixture rather than a silent merge, and
        an unresolved mixture is a thing a reader notices.
        """
        if self.unbounded or other.unbounded:
            return True
        a0, a1 = _instant(self.start), _instant(self.end)
        b0, b1 = _instant(other.start), _instant(other.end)
        if None in (a0, a1, b0, b1) and (a0 is None or b0 is None):
            return (self.start, self.end) == (other.start, other.end)
        lo_a = a0 if a0 is not None else float("-inf")
        hi_a = a1 if a1 is not None else float("inf")
        lo_b = b0 if b0 is not None else float("-inf")
        hi_b = b1 if b1 is not None else float("inf")
        return lo_a <= hi_b and lo_b <= hi_a


@dataclass(frozen=True)
class Provenance:
    """Where an artifact came from, in enough detail to re-derive or blame it."""

    producer: str = ""                       #: node id, kernel id or source id
    inputs: tuple[str, ...] = ()             #: artifact ids this was computed from
    source: str = ""                         #: source manifest id, if ingested
    source_version: str = ""                 #: pinned snapshot of that source
    license: str = ""                        #: SPDX id, or the source's own name
    method: str = ""                         #: how, when "producer" is not enough

    def to_dict(self) -> dict[str, Any]:
        return {"producer": self.producer, "inputs": list(self.inputs),
                "source": self.source, "source_version": self.source_version,
                "license": self.license, "method": self.method}


@dataclass(frozen=True)
class ArtifactRef:
    """A pointer to bytes that are too large to travel inline.

    ``media_type`` is what the bytes *are* (arrow, parquet, npy, glb, png);
    ``uri`` is where they sit. Nothing in the flow layer reads them; a kernel
    that declares it can handle the media type does.
    """

    uri: str
    media_type: str = "application/octet-stream"
    n_bytes: int | None = None
    digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"uri": self.uri, "media_type": self.media_type,
                "n_bytes": self.n_bytes, "digest": self.digest}


@dataclass(frozen=True)
class Artifact:
    """One immutable typed value on one edge of a flow graph.

    ``type`` is the port type the flow layer checks (``term_graph``,
    ``world_snapshot``, ``claim_set``, ``text``). ``schema`` names the versioned
    wire schema the payload conforms to. ``profiles`` says which world profiles
    the payload actually carries, which is what a kernel matches its
    ``requires`` against — a kernel asks for capabilities, never for the whole
    ontology.
    """

    type: str
    value: Any = None
    ref: ArtifactRef | None = None
    schema: str = ""
    profiles: tuple[str, ...] = ()
    unit: str = ""
    frame: str = ""
    valid_time: Interval = field(default_factory=Interval)
    transaction_time: Interval = field(default_factory=Interval)
    provenance: Provenance = field(default_factory=Provenance)
    present: bool = True
    meta: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.value is not None and self.ref is not None:
            raise ValueError(
                "an artifact carries an inline value or a ref, never both: two "
                "copies of one value is how they come to disagree")
        if not self.present and self.value is not None:
            raise ValueError("an absent artifact cannot carry a value; a "
                             "default here is indistinguishable downstream "
                             "from a measurement")

    # ---- identity ----------------------------------------------------
    def descriptor(self) -> dict[str, Any]:
        """Everything that defines this artifact, as plain JSON. Hashed."""
        return {
            "type": self.type,
            "value": self.value,
            "ref": self.ref.to_dict() if self.ref is not None else None,
            "schema": self.schema,
            "profiles": list(self.profiles),
            "unit": self.unit,
            "frame": self.frame,
            "valid_time": self.valid_time.to_dict(),
            "transaction_time": self.transaction_time.to_dict(),
            "present": self.present,
            "meta": dict(self.meta),
        }

    @property
    def id(self) -> str:
        """Content address. **Provenance is excluded on purpose.**

        Two kernels that computed the same value produce the same artifact, and
        should hit the same cache entry. If provenance were hashed they would
        not, and the cache would be keyed on who asked rather than on what was
        asked — which is the same value stored twice under different names.
        """
        return artifact_id(self.descriptor())

    def with_provenance(self, prov: Provenance) -> "Artifact":
        return replace(self, provenance=prov)

    def to_dict(self) -> dict[str, Any]:
        d = self.descriptor()
        d["id"] = self.id
        d["provenance"] = self.provenance.to_dict()
        return d

    @classmethod
    def absent(cls, type_: str, *, why: str = "") -> "Artifact":
        """An artifact that says a value was not observed, and why."""
        return cls(type=type_, present=False, meta={"absent_because": why} if why else {})
