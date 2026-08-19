"""Real prose with real ground truth: corporate parents from Wikipedia + Wikidata.

Everything measured in this repo runs on text it generated itself. The gap is not
prose -- `data/sources/openalex-prose` has 36k real sentences -- it is **paired**
prose and facts, and every structured source on disk has been normalised into a
node/edge table with the text stripped.

Wikidata supplies the fact (``P749``, *parent organization*) and Wikipedia
supplies the prose. That pairing is the closest real-world analogue of solvency's
``owns``, and it comes with the day's hardest problem built in: company articles
are full of **former** parents -- *"formerly a subsidiary of X"*, *"was acquired
by Y in 2011"*, *"spun off from Z"* -- so a naive extractor picks up ownership
that has ended. That is the uncued-staleness scenario in the wild, with a gold
answer.

Writes ``data/artifacts/wikipedia_parents.jsonl``; ``/data/`` is gitignored, so
this script is the reproduction.

Run: uv run python -u scripts/fetch_wikipedia_parents.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("data/artifacts/wikipedia_parents.jsonl")
UA = "symbolic-ai-models research bot (non-commercial; <1 req/sec)"
WANT = 220

#: WDQS was in an active outage rate-limiting to one request a minute, so this
#: goes through CirrusSearch on wikidata.org and the entity API instead -- more
#: requests, no query service.
SEARCH = ("https://www.wikidata.org/w/api.php?action=query&format=json"
          "&list=search&srnamespace=0&srlimit=50&sroffset=%d&srsearch=%s")
TERM = "haswbstatement:P749 haswbstatement:P31=Q4830453"


def _get(url: str, tries: int = 5) -> bytes:
    for i in range(tries):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            print(f"   {type(e).__name__} {e}; retry {i + 1}")
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"gave up on {url[:90]}")


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
        time.sleep(0.4)
    return out[:want]


def entity(qid: str) -> dict:
    return json.loads(_get(
        f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    )["entities"][qid]


def parents(ent: dict) -> tuple[list[str], list[str]]:
    """(current parent ids, former parent ids).

    A ``P749`` statement carrying an **end time** (``P582``) names a parent the
    company **used to** have. Wikidata keeps both, which is what makes this a
    labelled staleness set rather than only a labelled ownership set.
    """
    cur, old = [], []
    for st in ent.get("claims", {}).get("P749", []):
        snak = st.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        pid = snak["datavalue"]["value"]["id"]
        quals = st.get("qualifiers", {})
        if "P582" in quals or st.get("rank") == "deprecated":
            old.append(pid)
        else:
            cur.append(pid)
    return cur, old


def labels(ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 50):
        chunk = "|".join(ids[i:i + 50])
        data = json.loads(_get(
            "https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
            f"&props=labels&languages=en&ids={chunk}"))
        for qid, ent in data.get("entities", {}).items():
            lab = ent.get("labels", {}).get("en", {}).get("value")
            if lab:
                out[qid] = lab
        time.sleep(0.4)
    return out


def intro(title: str) -> str:
    url = ("https://en.wikipedia.org/w/api.php?action=query&format=json"
           "&prop=extracts&explaintext=1&exintro=1&redirects=1&titles="
           + urllib.parse.quote(title))
    data = json.loads(_get(url))
    for page in data.get("query", {}).get("pages", {}).values():
        if "extract" in page:
            return page["extract"]
    return ""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ids = qids(WANT)
    print(f"{len(ids)} candidate companies\n")

    records = []
    need: list[str] = []
    for n, qid in enumerate(ids, 1):
        try:
            ent = entity(qid)
        except Exception as e:
            print(f"{qid}: {type(e).__name__}")
            continue
        time.sleep(0.4)
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
        if n % 50 == 0:
            print(f"   scanned {n}, kept {len(records)}")

    lab = labels(need)
    kept = 0
    with OUT.open("w") as fh:
        for r in records:
            try:
                text = intro(r["title"])
            except Exception:
                continue
            time.sleep(0.4)
            if len(text) < 200:
                continue
            r["parent"] = lab.get(r["current_ids"][0], "")
            r["current"] = [lab[i] for i in r["current_ids"] if i in lab]
            r["former"] = [lab[i] for i in r["former_ids"] if i in lab]
            if not r["parent"]:
                continue
            r["intro"] = text
            fh.write(json.dumps(r) + "\n")
            kept += 1
            if kept % 25 == 0:
                print(f"   {kept} articles")
    print(f"\n{kept} articles -> {OUT}")


if __name__ == "__main__":
    main()
