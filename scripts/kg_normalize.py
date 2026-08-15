"""Normalise a source's triples into one relation vocabulary and one id space.

Reads ``kg/normalized/schema.json`` — the mapping is *data*, not code, so a
revision to the vocabulary is a diff a reader can argue with rather than a
rewrite of this file.

Three things it does that a simpler loader would not, each because of a mistake
already paid for in this repo:

* **Rejects rather than admits.** 1.29M ids in the corpus do not parse. Admitted,
  they collapse into one node that every degree statistic then reports as
  structure. Rejections are counted per reason and written to the manifest.
* **Carries provenance on every triple.** ``src`` and ``orig_kind`` ride along,
  because 26 independently-built sources do not produce facts of equal quality
  and a table that pools them without reporting the split is how ``label_acc``
  hid a 72:28 mixture for its entire history.
* **Counts what it dropped, not just what it kept.** A normaliser that reports
  only its output is a floor with no denominator.

Output is NDJSON at ``kg/normalized/v<schema>/<source>.ndjson.gz`` plus a
``manifest.json``. The data is gitignored; the manifest is not.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

SCHEMA = Path("kg/normalized/schema.json")
_ID = re.compile(r"^kg:([a-z0-9_]+):(.+)$")


def build_map(schema: dict[str, Any]) -> dict[str, str]:
    """``orig_kind -> canonical``, flattened from the schema's grouped form."""
    out: dict[str, str] = {}
    for group in schema["canonical_relations"].values():
        for canonical, originals in group.items():
            if canonical == "note":
                continue
            for o in originals:
                out[o] = canonical
    return out


def parse_id(raw: Any) -> tuple[str | None, str]:
    """``(normalised id, reason)``. ``None`` means rejected, with the reason."""
    if not isinstance(raw, str) or not raw:
        return None, "empty"
    s = raw.strip()
    if not s:
        return None, "empty"
    m = _ID.match(s)
    if m:
        return f"kg:{m.group(1)}:{m.group(2)}", "ok"
    # ConceptNet's own form, kept because cskg ships it unprefixed in places.
    if s.startswith("/c/"):
        return f"kg:cskg:{s}", "ok"
    return None, "unparseable"


#: A source directory holds edge tables next to node tables and event logs, and
#: they are not distinguishable by filename — `graph/log/*.ndjson.gz` and
#: `geo/geonames/*_nodes_*.parquet` both sit under the source root. Reading them
#: as edges produced 19.3M `id:empty` rejections that looked like a data-quality
#: problem in the corpus and were entirely an artefact of this script. Detect by
#: **columns**, never by name: a name is a convention and a column list is a fact.
def is_edge_file(path: Path) -> bool:
    try:
        if path.suffix == ".parquet":
            import pyarrow.parquet as pq
            names = set(pq.ParquetFile(path).schema_arrow.names)
        else:
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8") as fh:   # type: ignore[operator]
                first = fh.readline().strip()
            names = set(json.loads(first)) if first else set()
    except Exception:
        return False
    return bool(names & {"source_id", "sourceId"}) and bool(names & {"target_id", "targetId"})


def rows_of(path: Path, cap: int | None) -> Iterator[dict[str, Any]]:
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        n = 0
        for batch in pf.iter_batches(batch_size=65_536):
            for r in batch.to_pylist():
                yield r
                n += 1
                if cap and n >= cap:
                    return
    else:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as fh:   # type: ignore[operator]
            for n, line in enumerate(fh):
                if cap and n >= cap:
                    return
                line = line.strip()
                if line:
                    yield json.loads(line)


def normalise(source: str, files: list[Path], kmap: dict[str, str],
              out_path: Path, cap: int | None) -> dict[str, Any]:
    kept = 0
    rejected: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    canonical: Counter[str] = Counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        for path in files:
            for r in rows_of(path, cap):
                s_raw = r.get("source_id") or r.get("sourceId")
                t_raw = r.get("target_id") or r.get("targetId")
                k_raw = r.get("kind")
                s, s_why = parse_id(s_raw)
                t, t_why = parse_id(t_raw)
                if s is None or t is None:
                    rejected[f"id:{s_why if s is None else t_why}"] += 1
                    continue
                if not isinstance(k_raw, str) or not k_raw:
                    rejected["kind:empty"] += 1
                    continue
                canon = kmap.get(k_raw)
                if canon is None:
                    unmapped[k_raw] += 1
                    rejected["kind:unmapped"] += 1
                    continue
                out.write(json.dumps({"s": s, "p": canon, "o": t,
                                      "src": source, "orig_kind": k_raw}) + "\n")
                kept += 1
                canonical[canon] += 1

    seen = kept + sum(rejected.values())
    return {
        "source": source,
        "files": [str(f) for f in files],
        "rows_seen": seen,
        "triples_kept": kept,
        "kept_fraction": round(kept / seen, 4) if seen else 0.0,
        "rejected": dict(rejected),
        "unmapped_kinds": dict(unmapped.most_common(40)),
        "canonical_counts": dict(canonical.most_common()),
        "output": str(out_path),
        "output_sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "row_cap_per_file": cap,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("sources", nargs="+", help="source directory names")
    ap.add_argument("--cap", type=int, default=None,
                    help="per-file row cap; recorded in the manifest")
    args = ap.parse_args()

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    kmap = build_map(schema)
    root = Path(args.root).expanduser()
    outdir = Path(f"kg/normalized/v{schema['schema_version']}")

    manifests = []
    for source in args.sources:
        candidates = sorted(p for p in (root / source).rglob("*")
                            if p.suffix in (".parquet", ".gz") and p.is_file())
        files = [p for p in candidates if is_edge_file(p)]
        skipped = len(candidates) - len(files)
        if not files:
            print(f"{source}: no edge files ({skipped} non-edge skipped)"); continue
        if skipped:
            print(f"{source}: skipping {skipped} non-edge file(s) (no source/target columns)")
        m = normalise(source, files, kmap, outdir / f"{source}.ndjson.gz", args.cap)
        manifests.append(m)
        print(f"{source:<12} seen {m['rows_seen']:>10,}  kept {m['triples_kept']:>10,} "
              f"({m['kept_fraction']:.1%})  unmapped kinds: {len(m['unmapped_kinds'])}")

    mpath = outdir / "manifest.json"
    prior = json.loads(mpath.read_text()) if mpath.exists() else {"sources": {}}
    for m in manifests:
        prior["sources"][m["source"]] = m
    prior["schema_version"] = schema["schema_version"]
    prior["mapped_kinds"] = len(kmap)
    mpath.write_text(json.dumps(prior, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {mpath}")


if __name__ == "__main__":
    main()
