"""A larger parent corpus, to test whether distant supervision is data-starved.

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

from scripts.fetch_wikipedia_parents import entity, intro, labels, parents, qids

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
