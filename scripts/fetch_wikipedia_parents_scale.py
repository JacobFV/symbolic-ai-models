"""A larger parent corpus, to test whether distant supervision is data-starved.

**Superseded by `scripts/fetch_wikipedia_parents_batched.py`.** This asks for one
entity and one intro per request -- about 4,900 requests for 2,400 candidates --
and reached 49 articles in several hours behind Wikimedia's 429s. The batched
version does the same job in about 170 requests by sending 50 entities and 20
extracts at a time, which is the documented way to ask and gentler on the service
than the version that was being throttled. Kept because the long-backoff `_get`
below is the right shape for any endpoint that has no batch form, and because a
superseded script is a record of what was tried.

`scripts/fetch_wikipedia_parents.py` built the 168-article corpus every published
real-text number is measured on, and **that file is not touched here** -- this
writes a separate one, because overwriting it would silently redefine
`0.601 / 0.393 / 0.653` and every finding that quotes them.

The question this corpus exists to answer: the learned reader fitted by distant
supervision reaches 0.101 correct on `parent` against a hand-written pattern
set's 0.393, and multi-instance pruning made it *worse* (0.042), which says the
binding constraint is the 126 training articles rather than the label noise. If
that is right, an order of magnitude more articles should move it a long way; if
it is wrong, it will not move at all.

Same source and same rate limit as the original: Wikidata CirrusSearch for
companies with P749, the entity API for labels and sitelinks, and the REST
summary endpoint for intros, at under one request a second with an identifying
non-personal user agent.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import urllib.request

import scripts.fetch_wikipedia_parents as W
from scripts.fetch_wikipedia_parents import entity, intro, labels, parents, qids

#: The original `_get` retries five times over 45 seconds, which is not enough
#: for a 429 -- the first search request exhausted it. Wikimedia asks clients to
#: back off rather than to keep asking, so this waits minutes, not seconds, and
#: gives up honestly rather than hammering.
def _get(url: str, tries: int = 8) -> bytes:
    import time as _t
    for i in range(tries):
        req = urllib.request.Request(
            url, headers={"User-Agent": W.UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            wait = min(600, 15 * 2 ** i)
            print(f"   {type(e).__name__} {e}; waiting {wait}s "
                  f"(attempt {i + 1}/{tries})", flush=True)
            _t.sleep(wait)
    raise RuntimeError(f"gave up on {url[:90]} after {tries} attempts")


W._get = _get

OUT = Path("data/artifacts/wikipedia_parents_scale.jsonl")
WANT = 2400


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ids = qids(WANT)
    print(f"{len(ids)} candidate companies", flush=True)

    records, need = [], []
    for n, qid in enumerate(ids, 1):
        try:
            ent = entity(qid)
        except Exception:
            continue
        time.sleep(0.35)
        title = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
        if not title:
            continue
        cur, old = parents(ent)
        if not cur:
            continue
        records.append({"qid": qid,
                        "company": ent.get("labels", {}).get(
                            "en", {}).get("value", title),
                        "title": title, "current_ids": cur, "former_ids": old})
        need += cur + old
        if n % 100 == 0:
            print(f"   scanned {n}, kept {len(records)}", flush=True)

    lab = labels(need)
    kept = 0
    with OUT.open("w") as fh:
        for r in records:
            try:
                text = intro(r["title"])
            except Exception:
                continue
            time.sleep(0.35)
            if len(text) < 200:
                continue
            r["parent"] = lab.get(r["current_ids"][0], "")
            r["current"] = [lab[i] for i in r["current_ids"] if i in lab]
            r["former"] = [lab[i] for i in r["former_ids"] if i in lab]
            if not r["parent"]:
                continue
            r["intro"] = text
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            kept += 1
            if kept % 100 == 0:
                print(f"   {kept} articles", flush=True)
    print(f"\n{kept} articles -> {OUT}")


if __name__ == "__main__":
    main()
