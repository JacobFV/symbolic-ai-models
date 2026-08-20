"""Country and headquarters for the closed corpus, so a second relation is testable.

The promotion queue's open gap on the clumping result is **a second relation**:
the effect is measured only for `parent`, and `country`'s frames are adjacency
rather than lexis, so there is real reason to expect it to behave differently.

`data/artifacts/company_relations.jsonl` has country and headquarters gold for
**168** qids, and only **15** of the 415 chain pairs have it on both ends — which
is the exact sample size this session wrote a lesson note about. The fix is a
fetch, not an estimator.

P17 (country) and P159 (headquarters) for all 2,502 articles in the closed
corpus: 51 batched requests through the same `wbgetentities` path the parent
fetch uses. Writes `data/artifacts/company_relations_scale.jsonl`; the
168-qid file is untouched so every number measured on it keeps its corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.fetch_wikipedia_parents import labels
from scripts.fetch_wikipedia_parents_batched import entities

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("data/artifacts/company_relations_scale_v2.jsonl")
#: Relations whose value is an ENTITY and which an intro plausibly states.
#: `founder` and `industry` were added to give the frame-concentration/readability
#: fit more than three points -- two of which were the relations it was derived
#: from, which is not a fit.
PROPS = {"country": "P17", "headquarters": "P159",
         "founder": "P112", "industry": "P452"}


def values(ent: dict, pid: str) -> list[str]:
    """Current values only — a statement with an end time names a former one."""
    out = []
    for st in ent.get("claims", {}).get(pid, []):
        snak = st.get("mainsnak", {})
        if snak.get("snaktype") != "value" or st.get("rank") == "deprecated":
            continue
        if "P582" in st.get("qualifiers", {}):
            continue
        val = snak["datavalue"]["value"]
        if isinstance(val, dict) and "id" in val:
            out.append(val["id"])
    return out


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    qids = [r["qid"] for r in rows]
    print(f"{len(qids)} articles to enrich", flush=True)

    ents = entities(qids)
    need: list[str] = []
    got: dict[str, dict[str, list[str]]] = {}
    for qid, ent in ents.items():
        rec = {name: values(ent, pid) for name, pid in PROPS.items()}
        got[qid] = rec
        for ids in rec.values():
            need += ids
    lab = labels(need)

    kept = 0
    with OUT.open("w") as fh:
        for r in rows:
            rec = got.get(r["qid"])
            if not rec:
                continue
            out = {"qid": r["qid"], "title": r["title"]}
            for name, ids in rec.items():
                out[f"{name}_ids"] = ids
                out[name] = [lab[i] for i in ids if i in lab]
            fh.write(json.dumps(out) + "\n")
            kept += 1
    have_c = sum(1 for q in got if got[q]["country"])
    have_h = sum(1 for q in got if got[q]["headquarters"])
    print(f"\n{kept} records -> {OUT}")
    print(f"  with a country: {have_c} ({have_c / max(1, kept):.3f})")
    print(f"  with a headquarters: {have_h} ({have_h / max(1, kept):.3f})")


if __name__ == "__main__":
    main()
