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


def normalise_nodes(source: str, files: list[Path], out_path: Path,
                    cap: int | None) -> dict[str, Any]:
    """Node tables: id, kind, label. Thrown away entirely by the first pass.

    This was the larger omission. Without nodes the graph is edges between
    opaque identifiers — you can compute its degree distribution and not say
    what a single node *is*. `label` is also the only join key to the
    curriculum's vocabulary, which is words rather than `kg:` ids.

    The `body` field is deliberately **not** carried. Measured over 190,029
    nodes it is median **36 characters**, 70% of it opening `Source: OBO
    Foundry ontology`, with 23,883 distinct openings across the sample — short,
    templated provenance boilerplate rather than prose. Mining it would mostly
    recover facts already present in the structured columns, at the cost of a
    large text column on every row.
    """
    kept = 0
    kinds: Counter[str] = Counter()
    no_label = 0
    rejected: Counter[str] = Counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        out.write("id\tkind\tlabel\tsrc\n")
        for path in files:
            for r in rows_of(path, cap):
                ident, why = parse_id(r.get("id"))
                if ident is None:
                    rejected[f"id:{why}"] += 1
                    continue
                kind = str(r.get("kind") or "")
                label = str(r.get("label") or "").replace("\t", " ").replace("\n", " ")
                if not label:
                    no_label += 1
                kinds[kind] += 1
                out.write(f"{ident}\t{kind}\t{label}\t{source}\n")
                kept += 1

    return {
        "source": source, "nodes_kept": kept, "without_label": no_label,
        "rejected": dict(rejected), "kinds": dict(kinds.most_common(30)),
        "output": str(out_path), "row_cap_per_file": cap,
        "body_field": ("dropped on purpose: median 36 chars, 70% templated OBO "
                       "provenance, 23,883 distinct openings per 190k sample"),
    }


def is_node_file(path: Path) -> bool:
    """Node tables carry ``id`` and no source/target pair."""
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
    return "id" in names and not (names & {"source_id", "sourceId"})


def normalise(source: str, files: list[Path], kmap: dict[str, str],
              out_path: Path, cap: int | None) -> dict[str, Any]:
    kept = 0
    rejected: Counter[str] = Counter()
    unmapped: Counter[str] = Counter()
    canonical: Counter[str] = Counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tsv = out_path.name.endswith(".tsv.gz")
    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        if tsv:
            # `val` carries the one payload column the (s, p, o) shape drops.
            # Two sources have one and both were being discarded silently:
            # `govspend` has `value` (a complaint COUNT -- 3,450 against one
            # company, which makes the row an aggregate rather than an event and
            # is why rejecting govspend as a "dated occurrence" was wrong), and
            # `graph` has `weight`, so every edge weight in the repo's own graph
            # was going in the bin. Empty when the source has neither.
            out.write("s\tp\to\tsrc\torig_kind\tval\n")
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
                v = r.get("value")
                if v is None:
                    v = r.get("weight")
                v = "" if v is None else str(v).replace("\t", " ")
                if tsv:
                    out.write(f"{s}\t{canon}\t{t}\t{source}\t{k_raw}\t{v}\n")
                else:
                    out.write(json.dumps({"s": s, "p": canon, "o": t, "src": source,
                                          "orig_kind": k_raw, "val": v}) + "\n")
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
    ap.add_argument("sources", nargs="*", help="source names; empty = all")
    ap.add_argument("--cap", type=int, default=None,
                    help="per-file row cap; recorded in the manifest")
    ap.add_argument("--tsv", action="store_true",
                    help="compact TSV instead of NDJSON. At 1.2B triples NDJSON "
                         "repeats five keys per row for ~26 GB gzipped against "
                         "TSV's ~15 GB; the header carries the field names once.")
    ap.add_argument("--nodes", action="store_true",
                    help="also normalise node tables (id, kind, label)")
    ap.add_argument("--skip", default="__r2_data_catalog,d1,_dev-bucket,test",
                    help="sources to skip. Defaults are the redundant re-exports "
                         "of `graph` and the 5-row fixture; normalising them would "
                         "double-count the same edges under a second source name.")
    args = ap.parse_args()

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    kmap = build_map(schema)
    root = Path(args.root).expanduser()
    outdir = Path(f"kg/normalized/v{schema['schema_version']}")

    skip = {s for s in args.skip.split(",") if s}
    sources = args.sources or sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name not in skip)
    ext = "tsv.gz" if args.tsv else "ndjson.gz"

    manifests, node_manifests = [], []
    for source in sources:
        if source in skip:
            print(f"{source}: skipped ({args.skip})"); continue
        candidates = sorted(p for p in (root / source).rglob("*")
                            if p.suffix in (".parquet", ".gz") and p.is_file())
        edges = [p for p in candidates if is_edge_file(p)]
        if edges:
            m = normalise(source, edges, kmap, outdir / f"{source}.{ext}", args.cap)
            manifests.append(m)
            print(f"{source:<14} edges seen {m['rows_seen']:>12,}  kept {m['triples_kept']:>12,} "
                  f"({m['kept_fraction']:.1%})  unmapped: {len(m['unmapped_kinds'])}", flush=True)
        if args.nodes:
            nodes = [p for p in candidates if is_node_file(p)]
            if nodes:
                nm = normalise_nodes(source, nodes, outdir / f"{source}.nodes.tsv.gz", args.cap)
                node_manifests.append(nm)
                print(f"{source:<14} nodes kept  {nm['nodes_kept']:>12,}  "
                      f"without label {nm['without_label']:,}", flush=True)
        if not edges and not (args.nodes and nodes):
            print(f"{source}: nothing recognisable", flush=True)

    mpath = outdir / "manifest.json"
    prior = json.loads(mpath.read_text()) if mpath.exists() else {"sources": {}}
    for m in manifests:
        prior["sources"][m["source"]] = m
    if node_manifests:
        prior.setdefault("nodes", {})
        for nm in node_manifests:
            prior["nodes"][nm["source"]] = nm
    prior["schema_version"] = schema["schema_version"]
    prior["mapped_kinds"] = len(kmap)
    mpath.write_text(json.dumps(prior, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {mpath}")


if __name__ == "__main__":
    main()
