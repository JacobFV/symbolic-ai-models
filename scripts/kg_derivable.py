"""How many entities can anchor a *derivable* slot? The number that gates the line.

A derivability curriculum needs an entity that satisfies two conditions at once:

1. it can be **anchored** — something says what it is, so a lesson can bind it
   (`is-a` / `instance-of`);
2. at least one attribute of it is **determined** — something says what follows
   from being that, so the attribute slot need not be drawn
   (`has-property`, `capable-of`, `used-for`, `made-of`, `causes`, or the ATOMIC
   if-then block).

Either alone is useless. An entity with a type and no consequences gives a slot
nothing to derive; an entity with properties and no type cannot be anchored by a
lesson. **The intersection is the population, and its size is the ceiling on how
much of the curriculum can carry a derived slot at all.**

This is deliberately measured *before* any model is built, because the previous
KG arm returned a null that was uninterpretable, and the arm before that spent a
sweep on a treatment whose reach nobody had priced. Coverage first is the rule
this line keeps having to relearn.

The output is a `stats.json`, which `.gitignore` tracks, so the number survives a
clone even though the 15 GB it was computed from does not.

Two things this reads that the first version did not
----------------------------------------------------

**TSV as well as NDJSON.** The full 1.2-billion-row normalisation writes
``<source>.tsv.gz`` (five columns, header ``s p o src orig_kind``) because NDJSON
repeats five keys on every row and costs ~26 GB gzipped against TSV's ~15 GB.
The first six sources were normalised to NDJSON before that switch and both
forms are on disk. **A source present in both forms is read once, from the TSV**,
and which form was used is printed and recorded — reading both would double every
count for those six sources, which is the single easiest way to fabricate a
result here.

``<source>.nodes.tsv.gz`` is a *node* table (``id kind label src``), not an edge
table, and is excluded by name — the one place in this pipeline where a filename
is trusted, because it is a name this script's sibling wrote rather than a
convention some upstream source happened to follow.

**Anchors are counted by 64-bit hash, not by string.** ``entities_anchorable``
was 119,125,858 over 216M triples and the full corpus is 5.6x larger; a Python
set of that many strings is tens of gigabytes on a machine doing the user's real
work. Hashes go into a ``uint64`` array (8 bytes each) and are deduplicated with
``numpy.unique``. The expected number of collisions at n = 1.2e9 is
n^2/2^65 = 0.04, so the count is exact with probability ~96% and can be off by at
most a handful; the *intersection* — the number that actually gates the line — is
computed by testing 79k derive-side strings against that hash set, where the
expected collision count is 5e-6. The guard is that this file reproduces the
published 119,125,858 / 15,977 / 9,849 exactly on the six NDJSON sources; if it
ever does not, the hashing is what to suspect first.
"""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

#: Relations that let a lesson *bind* an entity to a class.
ANCHOR = {"is-a", "instance-of"}

#: Relations whose object is *determined* by the subject — the thing that makes
#: a slot derivable rather than drawn. The ATOMIC block is included because an
#: if-then consequence is exactly a determined slot, which is the whole point.
DERIVE = {"has-property", "capable-of", "used-for", "made-of", "causes", "has-a",
          "desires", "not-desires", "manner-of", "defined-as",
          "agent-attribute", "agent-effect", "agent-wants", "agent-needs",
          "agent-reacts", "agent-intends", "other-wants", "other-effect",
          "other-reacts", "precondition-of", "subevent-of"}

#: Anchor ids are hashed to 64 bits rather than kept as strings. blake2b with an
#: 8-byte digest is used instead of `hash()` because `hash()` is salted per
#: process (PYTHONHASHSEED) and would make this script's output depend on which
#: interpreter ran it — the exact failure `test_fitting_is_stable_across_
#: processes` exists to catch one layer up.
def _h(s: str) -> int:
    from hashlib import blake2b
    return int.from_bytes(blake2b(s.encode("utf-8"), digest_size=8).digest(), "big")


def _lines(path: Path):
    """Decompress in a child process; Python's gzip is the bottleneck otherwise."""
    proc = subprocess.Popen(["gzip", "-dc", str(path)], stdout=subprocess.PIPE)
    try:
        for raw in proc.stdout:                      # type: ignore[union-attr]
            yield raw
    finally:
        proc.stdout.close()                          # type: ignore[union-attr]
        proc.wait()


def scan(path_s: str, out_dir_s: str, extra: tuple[str, ...] = ()) -> dict:
    """One file: anchor hashes to a `.npy`, derive counts returned inline.

    Returns counts rather than sets because the derive side is ~79k entities
    across the whole corpus and the anchor side is ~10^8 — the asymmetry is the
    finding this script exists to report, and it is also what makes the memory
    tractable.
    """
    path = Path(path_s)
    derive = DERIVE | set(extra)
    tsv = path.name.endswith(".tsv.gz")
    anchors: list[int] = []
    parts: list[np.ndarray] = []
    derivable: dict[str, Counter[str]] = defaultdict(Counter)
    per_rel: Counter[str] = Counter()
    n = 0

    # A Python list of 10^8 ints is ~4 GB of boxed objects. Drain it into a
    # deduplicated uint64 array every 20M so the peak stays near 1 GB.
    def drain() -> None:
        if anchors:
            parts.append(np.unique(np.asarray(anchors, dtype=np.uint64)))
            anchors.clear()

    it = _lines(path)
    if tsv:
        header = next(it, b"")
        if not header.startswith(b"s\tp\to"):
            raise SystemExit(f"{path}: unexpected TSV header {header!r}")
        for raw in it:
            n += 1
            f = raw.split(b"\t", 3)
            if len(f) < 3:
                continue
            p = f[1].decode()
            if p in ANCHOR:
                anchors.append(_h(f[0].decode()))
                if len(anchors) >= 20_000_000:
                    drain()
            elif p in derive:
                derivable[f[0].decode()][p] += 1
                per_rel[p] += 1
    else:
        for raw in it:
            n += 1
            r = json.loads(raw)
            p = r["p"]
            if p in ANCHOR:
                anchors.append(_h(r["s"]))
                if len(anchors) >= 20_000_000:
                    drain()
            elif p in derive:
                derivable[r["s"]][p] += 1
                per_rel[p] += 1

    drain()
    arr = (np.unique(np.concatenate(parts)) if parts
           else np.zeros(0, dtype=np.uint64))
    npy = Path(out_dir_s) / (path.name.replace(".", "_") + ".npy")
    np.save(npy, arr)
    return {"file": path.name, "rows": n, "anchor_npy": str(npy),
            "anchor_unique_in_file": int(arr.size),
            "derivable": {k: dict(v) for k, v in derivable.items()},
            "per_rel": dict(per_rel)}


def inputs(root: Path) -> tuple[list[Path], dict[str, str]]:
    """Edge files, one per source, TSV winning over NDJSON. Says which it took."""
    by_source: dict[str, Path] = {}
    chosen: dict[str, str] = {}
    for f in sorted(root.glob("*.gz")):
        if f.name.endswith(".nodes.tsv.gz"):
            continue
        if f.name.endswith(".tsv.gz"):
            source, form = f.name[: -len(".tsv.gz")], "tsv"
        elif f.name.endswith(".ndjson.gz"):
            source, form = f.name[: -len(".ndjson.gz")], "ndjson"
        else:
            continue
        # TSV wins: it is what the full run wrote. NDJSON survives only for the
        # six sources normalised before the switch, and reading both would count
        # those six twice.
        if source in by_source and form == "ndjson":
            continue
        by_source[source] = f
        chosen[source] = form
    return [by_source[s] for s in sorted(by_source)], chosen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("normalized", help="kg/normalized/vN")
    ap.add_argument("--out", default=None)
    ap.add_argument("--jobs", type=int, default=4,
                    help="parallel readers. The machine carries the user's real "
                         "work; 4 is the standing cap for this pipeline.")
    ap.add_argument("--derive-extra", default="",
                    help="comma-separated canonicals to ADD to DERIVE for this "
                         "run, recorded in the stats. This exists for one "
                         "question: `has-part` is ConceptNet's `/r/HasA` in "
                         "Wikidata's dialect and `has-a` is already a "
                         "determiner, so admitting it may move the usable "
                         "population by orders of magnitude. That would be a "
                         "fact about the DEFINITION of a determined attribute, "
                         "not about the corpus, and it must be run as its own "
                         "arm rather than folded into the mapping.")
    args = ap.parse_args()

    extra = tuple(x for x in args.derive_extra.split(",") if x)
    root = Path(args.normalized)
    files, chosen = inputs(root)
    print(f"{len(files)} edge files, {args.jobs} readers")
    for s in sorted(chosen):
        print(f"  {s:<14} {chosen[s]}")

    anchored = np.zeros(0, dtype=np.uint64)
    derivable: dict[str, Counter[str]] = defaultdict(Counter)
    per_rel: Counter[str] = Counter()
    per_source_rows: dict[str, int] = {}
    n = 0

    with tempfile.TemporaryDirectory(prefix="kg-derivable-") as tmp:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            for res in ex.map(scan, [str(f) for f in files], [tmp] * len(files),
                              [extra] * len(files)):
                n += res["rows"]
                per_source_rows[res["file"]] = res["rows"]
                part = np.load(res["anchor_npy"])
                anchored = np.unique(np.concatenate([anchored, part]))
                for e, d in res["derivable"].items():
                    derivable[e].update(d)
                per_rel.update(res["per_rel"])
                print(f"  {res['file']:<24} rows {res['rows']:>13,}  "
                      f"anchors so far {anchored.size:>12,}  "
                      f"derive entities {len(derivable):>9,}", flush=True)

    hashes = np.fromiter((_h(e) for e in derivable), dtype=np.uint64,
                         count=len(derivable))
    hit = np.isin(hashes, anchored)
    both = [e for e, h in zip(derivable, hit) if h]
    unique = sum(1 for e in both if all(c == 1 for c in derivable[e].values()))

    stats = {
        "triples_read": n,
        "entities_anchorable": int(anchored.size),
        "entities_with_a_determined_attribute": len(derivable),
        "entities_BOTH": len(both),
        "of_those_single_valued": unique,
        "note": ("`entities_BOTH` is the population a derivability curriculum can "
                 "draw from: anchorable AND carrying at least one determined "
                 "attribute. `of_those_single_valued` is the subset where every "
                 "determining relation has exactly one object, which is the clean "
                 "case -- several objects means the lesson must choose, which is a "
                 "different and harder task than deriving."),
        "anchors_counted_by": ("64-bit blake2b hash, deduplicated with numpy. "
                               "Expected collisions at n=1.2e9 is 0.04; the "
                               "intersection is computed by testing 79k strings "
                               "against that set, expected collisions 5e-6."),
        "determiners": sorted(DERIVE | set(extra)),
        "derive_extra": list(extra),
        "input_form_per_source": chosen,
        "rows_per_file": per_source_rows,
        "determining_relations": dict(per_rel.most_common()),
    }
    out = Path(args.out or (root / "stats.json"))
    out.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")

    print(f"\ntriples read                     {n:>12,}")
    print(f"anchorable (is-a/instance-of)    {anchored.size:>12,}")
    print(f"with a determined attribute      {len(derivable):>12,}")
    print(f"BOTH -- the usable population    {len(both):>12,}")
    print(f"  of those, single-valued        {unique:>12,}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
