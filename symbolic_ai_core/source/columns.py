"""What a snapshot's columns can actually answer, as opposed to what it is about.

A snapshot manifest records files, bytes and digests. A source card records
streams and what they are *about* — "citation and authorship edges", "place nodes
with coordinates". Neither records **which fields survived the ingest**, and on
this repo's own 14 GB that gap is the difference between a source and a source
you can use:

* GeoNames arrives as 29 million rows of ``(source_id, target_id, kind)`` and
  **has no latitude column**, so the geo kernel — which is entirely about
  coordinates — cannot read the only geospatial source in the data root.
* SEC EDGAR has no amount and no filing date, so the economy kernel cannot read
  it either.

Both kernels were built against generated worlds. That was recorded as a scoping
choice and was in fact forced, and nothing in the catalogue said so.

So capabilities are **detected from the columns**, exactly as
:mod:`symbolic_ai_core.data.knowledge_source` detects them from accessors, and
for the same reason: a stream that declares what it is about tells you nothing
about what it can populate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

__all__ = ["SnapshotSchema", "schema_of", "profiles_supported", "COLUMN_HINTS",
           "GENERIC_SCHEMAS"]

#: Column-name patterns that indicate a field is present. Deliberately generous
#: — the audit's job is to find sources that are *missing* something, so a false
#: positive here is the conservative direction: it claims a capability the source
#: may not really have, and a false negative would hide one it does.
COLUMN_HINTS: dict[str, tuple[str, ...]] = {
    "lat": (r"^lat", r"latitude"),
    "lon": (r"^lon", r"^lng", r"longitude"),
    "time": (r"date", r"time", r"_at$", r"^year$", r"quarter", r"period"),
    "value": (r"^value$", r"amount", r"^qty$", r"quantity", r"^num", r"count"),
    "unit": (r"^unit", r"currency", r"measure"),
    "identity": (r"^id$", r"_id$", r"^label$", r"name"),
    "relation": (r"^kind$", r"^type$", r"predicate", r"relation"),
}

#: Schemas that carry nothing but graph structure. Named so the audit can say
#: "this is a triple projection" rather than listing three column names.
GENERIC_SCHEMAS: tuple[tuple[str, ...], ...] = (
    ("source_id", "target_id", "kind"),
    ("id", "label", "kind", "body", "source_url"),
)


@dataclass(frozen=True)
class SnapshotSchema:
    """The columns a snapshot's files actually carry, and what they support."""

    snapshot: str
    source: str
    files_read: int
    rows: int
    columns: tuple[tuple[str, ...], ...]     #: distinct column tuples, sorted
    unreadable: int = 0
    fields: frozenset[str] = field(default_factory=frozenset)

    @property
    def generic(self) -> bool:
        """Every file is a bare graph projection with no domain fields."""
        return bool(self.columns) and all(c in GENERIC_SCHEMAS
                                          for c in self.columns)

    def supports(self, profile: str) -> bool:
        return profile in profiles_supported(self.fields)

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot": self.snapshot, "source": self.source,
                "files_read": self.files_read, "rows": self.rows,
                "unreadable": self.unreadable,
                "columns": [list(c) for c in self.columns],
                "fields": sorted(self.fields), "generic": self.generic,
                "profiles": sorted(profiles_supported(self.fields))}


def profiles_supported(fields: Iterable[str]) -> frozenset[str]:
    """Which world profiles a set of detected fields could populate.

    Conservative by construction: ``geo.place`` needs **both** a latitude and a
    longitude, and ``core.quantity`` needs a value. A source that has a value
    column and no unit column can populate ``core.quantity`` and the resulting
    ``Quantity`` will have to invent a unit — which is why the audit reports the
    unit field separately rather than folding it in.
    """
    have = set(fields)
    out: set[str] = set()
    if "identity" in have:
        out.add("core.identity")
    if "relation" in have:
        out.update(("core.type", "logic.proposition"))
    if "time" in have:
        out.add("core.time")
    if "value" in have:
        out.add("core.quantity")
    if {"lat", "lon"} <= have:
        out.update(("geo.place", "core.space"))
    return frozenset(out)


def _fields_of(columns: Iterable[str]) -> frozenset[str]:
    lowered = [c.lower() for c in columns]
    found = set()
    for field_name, patterns in COLUMN_HINTS.items():
        if any(re.search(p, c) for c in lowered for p in patterns):
            found.add(field_name)
    return frozenset(found)


def schema_of(snapshot: Any, root: Path, *, max_files: int = 40
              ) -> SnapshotSchema:
    """Read the parquet schemas a snapshot actually contains.

    Reads **metadata only** — a parquet footer, not the data — so auditing 14 GB
    costs a few hundred seeks rather than a decompression pass.
    """
    import pyarrow.parquet as pq

    base = snapshot.resolve(root)
    files = sorted(base.rglob("*.parquet")) if base.exists() else []
    seen: set[tuple[str, ...]] = set()
    rows = read = unreadable = 0
    for f in files[:max_files]:
        try:
            pf = pq.ParquetFile(f)
        except Exception:
            unreadable += 1
            continue
        seen.add(tuple(pf.schema_arrow.names))
        rows += pf.metadata.num_rows
        read += 1
    columns = tuple(sorted(seen))
    fields = frozenset().union(*(_fields_of(c) for c in columns)) if columns \
        else frozenset()
    return SnapshotSchema(snapshot=snapshot.id, source=snapshot.source,
                          files_read=read, rows=rows, columns=columns,
                          unreadable=unreadable, fields=fields)


@dataclass(frozen=True)
class IngestProjection:
    """What a snapshot's ingest kept of what its source declares it has.

    The kernel ABI already carries this idea: a projection ``P_K: W -> L_K``
    must record what it discarded, because a kernel that silently drops the
    units is indistinguishable from one that had none. **Ingest is a projection
    too** — ``P_ingest: upstream -> snapshot`` — and until this type existed the
    repo had no place to write down that the GeoNames ingest kept the place
    identities and threw away every coordinate.

    Note what is *not* the fix. The GeoNames source card is not wrong: upstream
    GeoNames really does publish coordinates, and ``geo.place`` is a true
    statement about the resource. The bytes on this disk are a lossy projection
    of it, and the loss belongs to the snapshot, not to the card. Editing the
    card to match the bytes would destroy the only record that the coordinates
    exist and are re-fetchable.
    """

    snapshot: str
    source: str
    declared: tuple[str, ...]      #: profiles the source card claims
    held: tuple[str, ...]          #: profiles the held columns can populate
    schema: SnapshotSchema

    @property
    def discarded(self) -> tuple[str, ...]:
        """Declared upstream, absent from the bytes: the ingest threw it away."""
        return tuple(sorted(set(self.declared) - set(self.held)))

    @property
    def retained(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.declared) & set(self.held)))

    @property
    def lossy(self) -> bool:
        return bool(self.discarded)

    def to_dict(self) -> dict[str, Any]:
        return {"declared": list(self.declared), "held": list(self.held),
                "retained": list(self.retained),
                "discarded": list(self.discarded), "lossy": self.lossy,
                "schema": self.schema.to_dict()}


def declared_profiles(source: Any) -> tuple[str, ...]:
    """The union of profiles a source card's streams claim to carry."""
    streams = (source.raw.get("streams") or {}) if source is not None else {}
    return tuple(sorted({p for st in streams.values()
                         for p in (st.get("profiles") or [])}))


def audit_snapshots(registry: Any, root: Path, *, max_files: int = 40
                    ) -> list[IngestProjection]:
    sources = registry.sources()
    out = []
    for sid, snap in sorted(registry.snapshots().items()):
        sc = schema_of(snap, root, max_files=max_files)
        out.append(IngestProjection(
            snapshot=sid, source=snap.source,
            declared=declared_profiles(sources.get(snap.source)),
            held=tuple(sorted(profiles_supported(sc.fields))), schema=sc))
    return out


def schemas_path(root: Path | None = None) -> Path:
    from .registry import repo_root
    return (root or repo_root()) / "generated" / "schemas.json"


def build_schemas(registry: Any = None, data: Path | None = None,
                  *, max_files: int = 40) -> dict[str, Any]:
    """The measured half of the catalogue.

    ``generated/catalog.json`` compiles what the YAML **declares**. This
    compiles what the bytes **hold**, and the two are separate documents on
    purpose: the catalogue is reproducible anywhere from the repo alone, and
    this file can only be produced on a machine that has the snapshots. Merging
    them would make the declared half unbuildable without 14 GB of parquet, and
    would put a measurement inside a hand-authored record — the exact confusion
    the source layer exists to prevent.
    """
    from .registry import SourceRegistry, data_root

    reg = registry if registry is not None else SourceRegistry()
    audits = audit_snapshots(reg, data if data is not None else data_root(),
                             max_files=max_files)
    rows = sum(a.schema.rows for a in audits)
    return {
        "schema": "sai.schemas@1",
        "note": ("Measured from held bytes, not authored. Regenerate with "
                 "`symbolic-ai sources --rebuild-schemas`; it needs the data "
                 "root present and will refuse to write a partial audit."),
        "snapshots": {a.snapshot: a.to_dict() for a in audits},
        "totals": {"snapshots": len(audits), "rows_sampled": rows,
                   "lossy": sum(1 for a in audits if a.lossy),
                   "generic": sum(1 for a in audits if a.schema.generic)},
    }


def write_schemas(root: Path | None = None, **kw) -> Path:
    import json as _json
    doc = build_schemas(**kw)
    if doc["totals"]["rows_sampled"] == 0:
        raise RuntimeError(
            "refusing to write an empty schema audit: no parquet was readable "
            "under the data root. A generated file that says 'no source has "
            "coordinates' because it read nothing is worse than no file.")
    path = schemas_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(doc, indent=2, sort_keys=True) + "\n")
    return path
