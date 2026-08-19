"""Ground truth for a second and third relation, so the world can be composed.

Arm D needs a world with more than one relation family and a query whose answer
is stated in no single sentence. The 168 companies already carry Wikidata `P749`
(parent). This adds `P17` (country) and `P159` (headquarters location), which are
**ground truth for scoring**, never features for reading.

Writes ``data/artifacts/company_relations.jsonl``.

Run: uv run python -u scripts/fetch_company_relations.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SRC = Path("data/artifacts/wikipedia_parents.jsonl")
OUT = Path("data/artifacts/company_relations.jsonl")
UA = "symbolic-ai-models research bot (non-commercial; <1 req/sec)"
WANT = {"P17": "country", "P159": "headquarters"}


def _get(url: str, tries: int = 4):
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def main() -> None:
    rows = [json.loads(x) for x in SRC.read_text().splitlines() if x.strip()]
    need_labels: set[str] = set()
    out = []
    for n, r in enumerate(rows, 1):
        ent = _get("https://www.wikidata.org/wiki/Special:EntityData/"
                   f"{r['qid']}.json")
        time.sleep(0.35)
        claims = ((ent or {}).get("entities", {}).get(r["qid"], {})
                  .get("claims", {}))
        rec = {"qid": r["qid"], "title": r["title"],
               "current_ids": r["current_ids"]}
        for pid, name in WANT.items():
            ids = []
            for st in claims.get(pid, []):
                snak = st.get("mainsnak", {})
                if snak.get("snaktype") == "value":
                    ids.append(snak["datavalue"]["value"]["id"])
            rec[f"{name}_ids"] = ids
            need_labels |= set(ids)
        out.append(rec)
        if n % 40 == 0:
            print(f"   {n}/{len(rows)}")

    labels: dict[str, str] = {}
    ids = sorted(need_labels)
    for i in range(0, len(ids), 50):
        chunk = "|".join(ids[i:i + 50])
        data = _get("https://www.wikidata.org/w/api.php?action=wbgetentities"
                    f"&format=json&props=labels&languages=en&ids={chunk}")
        for qid, e in (data or {}).get("entities", {}).items():
            lab = e.get("labels", {}).get("en", {}).get("value")
            if lab:
                labels[qid] = lab
        time.sleep(0.35)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as fh:
        for rec in out:
            for name in WANT.values():
                rec[name] = [labels[i] for i in rec[f"{name}_ids"]
                             if i in labels]
            fh.write(json.dumps(rec) + "\n")
    have_c = sum(1 for r in out if r.get("country"))
    have_h = sum(1 for r in out if r.get("headquarters"))
    print(f"\n{len(out)} companies -> {OUT}")
    print(f"   country known for {have_c}, headquarters for {have_h}")


if __name__ == "__main__":
    main()
