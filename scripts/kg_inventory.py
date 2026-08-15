"""What is actually in the ingest corpus, before anyone designs a schema for it.

The corpus was assumed to be a mix of structured tables and unstructured prose,
with a local model mining facts out of the prose half. It is not. Every source
checked is already ``(source_id, target_id, kind)`` — Gutenberg and
StackExchange included, which are edge lists over catalogue entries rather than
text. So there is nothing to mine and the whole job is **normalisation**:
reconciling the id namespaces and relation vocabularies of ~20 sources that were
built independently.

This script produces the input that decision needs, and writes it as a
``manifest.json`` under ``kg/`` so the answer survives a clone even though the
corpus does not. Per source: row count, the relation vocabulary with counts, and
the id namespaces on each side of the edge.

Sampling is deliberate and declared. `caselaw` alone is 46.7M rows and `wikidata`
12M; a full pass over every file is hours and buys nothing for schema design,
which needs to know *which* relations and namespaces exist rather than exactly
how many of each. ``--rows`` sets the per-file cap and the cap is recorded in
the manifest, because a count read off a sample and a count read off a corpus
are different numbers and this repo has been bitten by exactly that confusion.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

#: An id looks like ``kg:concept:red`` or ``/c/en/penguin/n``. The namespace is
#: what precedes the first payload segment, and it is the thing that has to be
#: reconciled across sources: two sources naming the same entity differently is
#: the normalisation problem in one sentence.
_KG_NS = re.compile(r"^(kg:[a-z0-9_]+:)")
_PATH_NS = re.compile(r"^(/[a-z]+/[a-z]{2}/)")


def namespace_of(ident: str) -> str:
    """The reconcilable prefix of an id, or a shape when there is no prefix."""
    if not isinstance(ident, str) or not ident:
        return "<empty>"
    for pat in (_KG_NS, _PATH_NS):
        m = pat.match(ident)
        if m:
            return m.group(1)
    if ident.isdigit():
        return "<numeric>"
    return "<bare>"


def _iter_parquet(path: Path, cap: int) -> tuple[int, list[dict[str, Any]]]:
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    total = pf.metadata.num_rows
    rows: list[dict[str, Any]] = []
    for batch in pf.iter_batches(batch_size=min(cap, 65_536)):
        rows.extend(batch.to_pylist())
        if len(rows) >= cap:
            break
    return total, rows[:cap]


def _iter_ndjson(path: Path, cap: int) -> tuple[int, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:      # type: ignore[operator]
        for i, line in enumerate(fh):
            if i >= cap:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return -1, rows            # -1: a total would mean decompressing the file


def profile(path: Path, cap: int) -> dict[str, Any]:
    """Row count, relation vocabulary and id namespaces for one file."""
    if path.suffix == ".parquet":
        total, rows = _iter_parquet(path, cap)
    else:
        total, rows = _iter_ndjson(path, cap)

    kinds: Counter[str] = Counter()
    src_ns: Counter[str] = Counter()
    dst_ns: Counter[str] = Counter()
    for r in rows:
        # Both shapes appear: the flat triple tables and the graph's own edges.
        s = r.get("source_id") or r.get("sourceId") or ""
        t = r.get("target_id") or r.get("targetId") or ""
        k = r.get("kind") or ""
        if k:
            kinds[str(k)] += 1
        src_ns[namespace_of(str(s))] += 1
        dst_ns[namespace_of(str(t))] += 1

    return {
        "rows_total": total,
        "rows_sampled": len(rows),
        "kinds": dict(kinds.most_common(40)),
        "n_kinds_in_sample": len(kinds),
        "source_namespaces": dict(src_ns.most_common(10)),
        "target_namespaces": dict(dst_ns.most_common(10)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", help="the ingest corpus root, e.g. ~/Downloads/kg")
    ap.add_argument("--out", default="kg/sources/manifest.json")
    ap.add_argument("--rows", type=int, default=50_000,
                    help="per-file sample cap; recorded in the manifest")
    args = ap.parse_args()

    root = Path(args.root).expanduser()
    files = sorted(p for p in root.rglob("*")
                   if p.suffix in (".parquet",) and "_dev-bucket" not in p.parts)

    by_source: dict[str, Any] = {}
    for p in files:
        source = p.relative_to(root).parts[0]
        try:
            prof = profile(p, args.rows)
        except Exception as exc:                      # a corrupt shard is data
            prof = {"error": f"{type(exc).__name__}: {exc}"}
        entry = by_source.setdefault(source, {"files": 0, "rows_total": 0,
                                              "kinds": Counter(), "src_ns": Counter(),
                                              "dst_ns": Counter(), "errors": []})
        entry["files"] += 1
        if "error" in prof:
            entry["errors"].append({"file": str(p.relative_to(root)), **prof})
            continue
        if prof["rows_total"] > 0:
            entry["rows_total"] += prof["rows_total"]
        entry["kinds"].update(prof["kinds"])
        entry["src_ns"].update(prof["source_namespaces"])
        entry["dst_ns"].update(prof["target_namespaces"])
        print(f"{str(p.relative_to(root)):68s} {prof['rows_total']:>12,} rows  "
              f"{prof['n_kinds_in_sample']:>3} kinds", flush=True)

    out: dict[str, Any] = {
        "corpus_root": str(root),
        "sample_rows_per_file": args.rows,
        "note": ("kinds and namespaces are counted on a per-file SAMPLE of "
                 "sample_rows_per_file rows; rows_total is exact from parquet "
                 "metadata. A sampled count and a corpus count are different "
                 "numbers and must not be quoted interchangeably."),
        "sources": {},
    }
    for name, e in sorted(by_source.items()):
        out["sources"][name] = {
            "files": e["files"],
            "rows_total": e["rows_total"],
            "kinds": dict(e["kinds"].most_common(40)),
            "n_kinds": len(e["kinds"]),
            "source_namespaces": dict(e["src_ns"].most_common(10)),
            "target_namespaces": dict(e["dst_ns"].most_common(10)),
            "errors": e["errors"],
        }

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {dest}")
    print(f"sources: {len(out['sources'])}, "
          f"total rows: {sum(s['rows_total'] for s in out['sources'].values()):,}")


if __name__ == "__main__":
    main()
