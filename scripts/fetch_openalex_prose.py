"""Get raw prose with ground-truth structure onto disk, for the first time.

`notes/findings/2026-08-18-the-framing-factor-we-retracted-is-the-amortisation-constant.md`
established that this repo has **no corpus of raw observations**. All 19
catalogued sources arrive already structured; the longest natural-language field
in 14 GB is a patent title at 59.4 characters. So the first arrow of
`APPROACH.md`'s thesis — `observations -> typed world` — has never been priced,
and there was nothing on disk on which it could be.

Three candidate sources were tried in order of preference:

* **CourtListener** — the best fit, because its 77M-edge citation map is
  *already on disk* as ground truth and citations appear in opinions as prose.
  The v4 API returns **401**: it now requires a token. Both bulk listings are
  closed (404 / 403). Recorded as a blocker rather than worked around.
* **PatentsView** — bucket listing returns 403.
* **OpenAlex** — open, unauthenticated, **200**. Used.

What makes OpenAlex the right substitute rather than merely the available one:
it ships raw prose *and* the structure derived from it, in the same record.
``raw_affiliation_strings`` is unstructured text a human typed; ``institutions``
is that text resolved to ROR identifiers. That pairing is a genuine
text-to-entity task with an anchor, and it needs no credentials.

**The anchor is an anchor, not truth.** OpenAlex's resolution is itself an
automated extractor, so agreement with it is *agreement*, and any accuracy number
downstream must say so — the same circularity the `airport_country` audit found
where a task's ground truth turned out to be one side of the disagreement it was
scored against. The **cost** half of the arm does not depend on the anchor at all.

Polite by construction: the `mailto` parameter puts the request in OpenAlex's
faster pool and identifies the caller, cursor paging avoids deep-offset scans,
and the default volume is 5,000 works in 25 requests.

Run: uv run python -u scripts/fetch_openalex_prose.py [--works N]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

OUT_DIR = Path("data/sources/openalex-prose/openalex-prose-2026-08-18")
MAILTO = "jjunkmail1234567890@gmail.com"
BASE = "https://api.openalex.org/works"
PER_PAGE = 200
#: OpenAlex asks for a descriptive agent; this one names the project and a
#: contact, which is what their polite-pool policy is for.
AGENT = f"symbolic-ai-models research (mailto:{MAILTO})"

#: Only the fields the arm reads. Requesting the whole record would multiply the
#: bytes by roughly six for nothing, and a fetcher that pulls what it does not
#: use is a cost this repo would then have to explain.
SELECT = ",".join((
    "id", "doi", "title", "publication_year", "language", "type",
    "abstract_inverted_index", "authorships", "topics", "primary_topic",
    "referenced_works", "cited_by_count",
))


def reconstruct(inv: dict[str, list[int]] | None) -> str:
    """OpenAlex ships abstracts as an inverted index; put the prose back.

    Positions are absolute word indices, so a gap means a word OpenAlex did not
    index rather than a word that was not there. Joining on present positions
    only is therefore lossy in a way worth naming: the reconstruction is the
    abstract *as OpenAlex holds it*, which is what the downstream cost is
    charged against anyway.
    """
    if not inv:
        return ""
    words: dict[int, str] = {}
    for term, positions in inv.items():
        for p in positions:
            words[p] = term
    return " ".join(words[i] for i in sorted(words))


def pages(n_works: int) -> Iterator[list[dict[str, Any]]]:
    cursor = "*"
    got = 0
    while got < n_works and cursor:
        q = urllib.parse.urlencode({
            "filter": "has_abstract:true,type:article,is_paratext:false",
            "select": SELECT,
            "per-page": min(PER_PAGE, n_works - got),
            "cursor": cursor,
            "mailto": MAILTO,
        })
        req = urllib.request.Request(f"{BASE}?{q}", headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.load(r)
        results = payload.get("results") or []
        if not results:
            return
        got += len(results)
        cursor = (payload.get("meta") or {}).get("next_cursor")
        yield results
        time.sleep(0.2)                     # under their 10/s ceiling by 50x


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", type=int, default=5000)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for batch in pages(args.works):
        for w in batch:
            abstract = reconstruct(w.get("abstract_inverted_index"))
            if not abstract:
                continue
            affils = []
            for a in (w.get("authorships") or []):
                for raw in (a.get("raw_affiliation_strings") or []):
                    affils.append({
                        "raw": raw,
                        "rors": sorted({i["ror"] for i in (a.get("institutions") or [])
                                        if i.get("ror")}),
                    })
            rows.append({
                "id": w.get("id"), "title": w.get("title") or "",
                "year": w.get("publication_year"), "language": w.get("language"),
                "abstract": abstract,
                "affiliations": affils,
                "topics": [t["id"] for t in (w.get("topics") or [])],
                "n_referenced": len(w.get("referenced_works") or []),
                "cited_by_count": w.get("cited_by_count"),
            })
        print(f"  {len(rows):,} works with abstracts "
              f"({time.perf_counter()-t0:.0f}s)", flush=True)

    out = OUT_DIR / "works_p0.jsonl"
    with out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    chars = sum(len(r["abstract"]) for r in rows)
    n_aff = sum(len(r["affiliations"]) for r in rows)
    linked = sum(1 for r in rows for a in r["affiliations"] if a["rors"])
    print(f"\nwrote {out} — {len(rows):,} works, {out.stat().st_size/1e6:.1f} MB")
    print(f"  abstracts: {chars:,} chars, mean {chars/max(1,len(rows)):,.0f}")
    print(f"  affiliation strings: {n_aff:,}, of which {linked:,} "
          f"({linked/max(1,n_aff):.1%}) resolve to at least one ROR id")
    print(f"  distinct ROR ids: "
          f"{len({r for w in rows for a in w['affiliations'] for r in a['rors']}):,}")


if __name__ == "__main__":
    main()
