"""Move a staged corpus into the data root and write its snapshot manifest.

This is the tool that turns "14 GB sitting in ~/Downloads" into something the
rest of the substrate can reason about: bytes under a predictable root in their
**native layout**, and a tracked manifest that says which source they came from,
when, what is in them and what each file hashes to.

Three rules it enforces, all of which are cheaper to enforce here than to repair
later:

* **Native layout is preserved verbatim.** Parquet collections, Iceberg tables,
  BIDS trees, zarr stores and NDJSON exports each have a layout their own tools
  expect. Rewriting them into one house style breaks every reader upstream ships
  and buys nothing that a manifest does not already give.
* **The move is a rename, never a copy.** Same filesystem, so it costs no disk
  and no time, and the bytes are never duplicated into a second half-migrated
  tree that somebody later has to reconcile.
* **A snapshot asserts what is on a named disk**, not what a source is. The
  source card is written separately and says nothing about holdings.

Usage::

    uv run python scripts/ingest_snapshot.py --plan          # what would move
    uv run python scripts/ingest_snapshot.py --run           # move and manifest
    uv run python scripts/ingest_snapshot.py --run --no-hash # skip the digests
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from symbolic_ai_core.source.manifest import (canonical_json, dump_yaml,  # noqa: E402
                                              manifest_hash)
from symbolic_ai_core.source.registry import data_root, repo_root  # noqa: E402

#: A snapshot with more files than this gets a sidecar TSV instead of an inline
#: file list. A manifest nobody opens because it is 9,000 lines long is a
#: manifest that stops being checked.
INLINE_FILE_LIMIT = 40


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def build_manifest(*, source: str, snapshot_id: str, root: Path, rel_root: str,
                   acquired: dict[str, Any], stream_of, storage_format: str,
                   layout: str, notes: str, do_hash: bool,
                   workers: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    files = walk(root)
    rows: list[dict[str, Any]] = []
    if do_hash and files:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            digests = list(ex.map(_sha256, files))
    else:
        digests = ["" for _ in files]
    inventory: dict[str, dict[str, Any]] = {}
    for p, digest in zip(files, digests):
        rel = str(p.relative_to(root))
        stream = stream_of(rel)
        row = {"path": rel, "bytes": p.stat().st_size, "stream": stream}
        if digest:
            row["sha256"] = digest
        rows.append(row)
        inv = inventory.setdefault(stream, {"files": 0, "bytes": 0})
        inv["files"] += 1
        inv["bytes"] += row["bytes"]
    man: dict[str, Any] = {
        "id": snapshot_id,
        "source": f"source/{source}",
        "acquired": acquired,
        "upstream_release": "unresolved",
        "storage": {"layout": layout, "format": storage_format,
                    "root": rel_root,
                    "locations": [f"file://{root}"]},
        "inventory": dict(sorted(inventory.items())),
    }
    if notes:
        man["notes"] = notes
    if len(rows) <= INLINE_FILE_LIMIT:
        man["files"] = rows
    else:
        man["files_sidecar"] = f"{snapshot_id.replace('@', '__')}.files.tsv"
        man["files_digest"] = ("sha256:" + hashlib.sha256(
            canonical_json(rows)).hexdigest())
    man["manifest_hash"] = manifest_hash(man)
    return man, rows


def write_sidecar(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("sha256\tbytes\tstream\tpath\n")
        for r in rows:
            f.write(f"{r.get('sha256','')}\t{r['bytes']}\t{r['stream']}\t{r['path']}\n")


def move_tree(src: Path, dst: Path) -> None:
    """Rename when possible; fall back to a copy across filesystems.

    ``shutil.move`` already does this, but it is worth naming: a cross-device
    ingest of 14 GB is a real copy and takes real minutes, and a caller who
    thinks they issued a rename will conclude the tool has hung.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"{dst} already exists; refusing to merge two "
                              f"snapshots into one directory")
    same = os.stat(src).st_dev == os.stat(dst.parent).st_dev
    if not same:
        print(f"  note: {src} and {dst} are on different filesystems -- this is "
              f"a copy, not a rename", flush=True)
    shutil.move(str(src), str(dst))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo_root(), capture_output=True,
                          text=True).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-hash", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default="", help="comma-separated source ids")
    args = ap.parse_args()
    if not (args.plan or args.run):
        ap.error("pass --plan or --run")

    from kg_ingest_plan import PLAN, STAGING          # noqa: E402
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    root = data_root()
    acquired_at = str(date.today())

    for entry in PLAN:
        if only and entry["source"] not in only:
            continue
        # "src" or "src::dest-relative-to-the-snapshot-root"
        pairs = [(STAGING / d.split("::")[0],
                  d.split("::")[1] if "::" in d else Path(d).name)
                 for d in entry["dirs"]]
        present = [(src, rel) for src, rel in pairs if src.exists()]
        dest_root = root / "sources" / entry["source"] / entry["snapshot_slug"]
        rel_root = str(dest_root.relative_to(root))
        if args.plan:
            n = sum(len(walk(src)) if src.is_dir() else 1 for src, _ in present)
            b = sum(sum(p.stat().st_size for p in walk(src)) if src.is_dir()
                    else src.stat().st_size for src, _ in present)
            print(f"{entry['source']:<20} {len(present)}/{len(pairs)} dirs "
                  f"{n:>5} files {b/2**30:>7.2f} GiB -> {rel_root}")
            continue
        if not present:
            print(f"skip {entry['source']}: none of {entry['dirs']} present")
            continue
        for src, rel in present:
            move_tree(src, dest_root / rel)
        man, rows = build_manifest(
            source=entry["source"], snapshot_id=entry["snapshot_id"],
            root=dest_root, rel_root=rel_root,
            acquired=dict(entry["acquired"], relocated_at=acquired_at),
            stream_of=entry["stream_of"], storage_format=entry["format"],
            layout=entry["layout"], notes=entry.get("notes", ""),
            do_hash=not args.no_hash, workers=args.workers)
        out = (repo_root() / "manifests" / "snapshots" / entry["source"]
               / f"{entry['snapshot_slug']}.yaml")
        if "files_sidecar" in man:
            write_sidecar(out.parent / man["files_sidecar"], rows)
        dump_yaml(out, man, header=(
            "# GENERATED by scripts/ingest_snapshot.py, then editable by hand.\n"
            "# A snapshot says what bytes were obtained and where they are now;\n"
            "# what the source IS lives in catalog/sources/."))
        print(f"wrote {out.relative_to(repo_root())}  "
              f"{sum(v['files'] for v in man['inventory'].values())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
