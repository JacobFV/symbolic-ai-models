"""Close the corpus under the parent relation, so composed queries are measurable.

The scale corpus has 1,661 articles and only **191 two-hop chains**, because a
chain needs the parent to have an article too. At a two-hop rate of a few per
cent that is four to six successes, and the lesson note
`notes/lessons/2026-08-19-a-rate-without-its-numerator-is-not-a-result.md` says
plainly that no composed-query claim can rest on it.

The fix is not a better estimator, it is more chains. **1,037 distinct parent
QIDs are named by the corpus and absent from it**, and they are the parents of
1,470 articles. Fetching them turns every one of those into a potential two-hop
chain and adds three-hop chains where the new article has its own parent.

About 60 batched requests — 21 for the entities, the rest for intros — against
the 4,900 the one-at-a-time fetcher would have used.

Writes `data/artifacts/wikipedia_parents_closure.jsonl` (the new articles only)
and `data/artifacts/wikipedia_parents_closed.jsonl` (the union). **Neither the
168-article file nor the 1,661-article file is modified**: every published number
keeps the corpus it was measured on.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.fetch_wikipedia_parents import labels, parents
from scripts.fetch_wikipedia_parents_batched import entities, intros

SCALE = Path("data/artifacts/wikipedia_parents_scale.jsonl")
NEW = Path("data/artifacts/wikipedia_parents_closure.jsonl")
CLOSED = Path("data/artifacts/wikipedia_parents_closed.jsonl")


def main() -> None:
    rows = [json.loads(x) for x in SCALE.read_text().splitlines() if x.strip()]
    have = {r["qid"] for r in rows}
    missing = sorted({pid for r in rows
                      for pid in (r.get("current_ids") or [])[:1]
                      if pid not in have})
    print(f"{len(rows)} articles; {len(missing)} parent qids to fetch",
          flush=True)

    ents = entities(missing)
    records, need = [], []
    for qid, ent in ents.items():
        title = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
        if not title:
            continue
        cur, old = parents(ent)
        records.append({"qid": qid,
                        "company": ent.get("labels", {}).get(
                            "en", {}).get("value", title),
                        "title": title, "current_ids": cur,
                        "former_ids": old})
        need += cur + old
    print(f"{len(records)} have an English article; "
          f"{sum(1 for r in records if r['current_ids'])} also have a parent",
          flush=True)

    lab = labels(need) if need else {}
    text = intros([r["title"] for r in records])
    kept = 0
    with NEW.open("w") as fh:
        for r in records:
            body = text.get(r["title"], "")
            if len(body) < 200:
                continue
            # A node with no parent of its own is still worth keeping: it is a
            # chain MIDDLE for its children even when it is a root itself, and
            # excluding roots would bias the graph toward deep branches.
            r["parent"] = lab.get(r["current_ids"][0], "") if r["current_ids"] else ""
            r["current"] = [lab[i] for i in r["current_ids"] if i in lab]
            r["former"] = [lab[i] for i in r["former_ids"] if i in lab]
            r["intro"] = body
            fh.write(json.dumps(r) + "\n")
            kept += 1
    print(f"\n{kept} new articles -> {NEW}")

    new_rows = [json.loads(x) for x in NEW.read_text().splitlines() if x.strip()]
    with CLOSED.open("w") as fh:
        for r in rows + new_rows:
            fh.write(json.dumps(r) + "\n")
    allr = {r["qid"]: r for r in rows + new_rows}
    edge = {q: (r.get("current_ids") or [None])[0] for q, r in allr.items()}
    hop2 = [q for q in edge if edge[q] in allr and edge.get(edge[q])]
    hop3 = [q for q in hop2 if edge.get(edge[q]) in allr
            and edge.get(edge.get(edge[q]))]
    print(f"{len(allr)} articles -> {CLOSED}")
    print(f"two-hop chains 191 -> {len(hop2)}; three-hop chains {len(hop3)}")


if __name__ == "__main__":
    main()
