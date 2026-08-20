"""A second domain: people, so the reading arm's claims can be tested off-corpus.

Every finding in the reading arm is **company intros** — one genre, one relation
family, one corpus. The critical path asked for a second genre; OpenAlex abstracts
turned out to mention their affiliation 3.7% of the time and were abandoned. This
is the replacement, and it is chosen to be a real test rather than a comfortable
one:

- **different register** — a biography, not a corporate description;
- **different relation family** — where a person was born, what they did, who
  they worked for, where they studied;
- **the same gold source**, so the comparison is about the text and not about the
  annotation.

`P19` birthplace, `P106` occupation, `P108` employer, `P69` educated at. The
predictions the arm makes for them, registered here before anything is fetched:
`occupation` should behave like `industry` (lowercase common-noun values, so
`CapitalisedMentions` cannot propose them and the relation reads **0.000** until
a phrase proposer is used); `birthplace` and `educated_at` should behave like
`headquarters` (proper nouns, canonical frames, the strongest relations); and the
**classifier should be the binding factor in all four**, since it has been in all
seven measured so far.

Writes `data/artifacts/people_relations.jsonl`. Touches no existing corpus.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path

import scripts.fetch_wikipedia_parents as W
from scripts.fetch_wikipedia_parents import labels
from scripts.fetch_wikipedia_parents_batched import _get, entities, intros

OUT = Path("data/artifacts/people_relations_more.jsonl")
HAVE = Path("data/artifacts/people_relations.jsonl")
WANT = 5000
PROPS = {"birthplace": "P19", "occupation": "P106",
         "employer": "P108", "educated_at": "P69"}
#: Humans with an occupation and a birthplace, which is the population where the
#: relations are plausibly stated in prose rather than only in the infobox.
TERM = "haswbstatement:P31=Q5 haswbstatement:P106 haswbstatement:P19"
SEARCH = ("https://www.wikidata.org/w/api.php?action=query&format=json"
          "&list=search&srnamespace=0&srlimit=50&sroffset=%d&srsearch=%s")

W._get = _get


def qids(want: int) -> list[str]:
    out: list[str] = []
    off = 0
    while len(out) < want:
        data = json.loads(_get(SEARCH % (off, urllib.parse.quote(TERM))))
        hits = [h["title"] for h in data["query"]["search"]]
        if not hits:
            break
        out += hits
        off += len(hits)
        print(f"   qids {len(out)}", flush=True)
        time.sleep(2.0)
    return out[:want]


def values(ent: dict, pid: str) -> list[str]:
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if HAVE.exists():
        seen = {json.loads(x)["qid"] for x in HAVE.read_text().splitlines()
                if x.strip()}
    print(f"{len(seen)} people already on disk; fetching new ones only")
    ids = [q for q in qids(WANT) if q not in seen]
    print(f"{len(ids)} candidate people", flush=True)
    ents = entities(ids)

    records, need = [], []
    for qid, ent in ents.items():
        title = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
        if not title:
            continue
        rec = {"qid": qid, "title": title}
        for name, pid in PROPS.items():
            rec[f"{name}_ids"] = values(ent, pid)
            need += rec[f"{name}_ids"]
        if not any(rec[f"{n}_ids"] for n in PROPS):
            continue
        records.append(rec)
    print(f"{len(records)} have an English article and a relation", flush=True)

    lab = labels(need)
    text = intros([r["title"] for r in records])
    kept = 0
    with OUT.open("w") as fh:
        for r in records:
            body = text.get(r["title"], "")
            if len(body) < 200:
                continue
            for name in PROPS:
                r[name] = [lab[i] for i in r[f"{name}_ids"] if i in lab]
            r["intro"] = body
            fh.write(json.dumps(r) + "\n")
            kept += 1
    print(f"\n{kept} people -> {OUT}")
    for name in PROPS:
        pass
    rows = [json.loads(x) for x in OUT.read_text().splitlines() if x.strip()]
    for name in PROPS:
        n = sum(1 for r in rows if r.get(name))
        cap = sum(1 for r in rows for v in (r.get(name) or [])
                  if v[:1].isupper())
        tot = sum(1 for r in rows for v in (r.get(name) or []))
        print(f"  {name:<13} {n:5d}/{kept} = {n / max(1, kept):.3f}   "
              f"capitalised {cap / max(1, tot):.3f}")


if __name__ == "__main__":
    main()
