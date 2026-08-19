"""The scale corpus, fetched in batches instead of one page at a time.

`scripts/fetch_wikipedia_parents_scale.py` asks for one entity and one intro per
request: about 4,900 requests for 2,400 candidates. It reached 49 articles in
several hours behind Wikimedia's 429s, which is the API telling a client to stop
doing that.

Both endpoints take batches, and one of them was already being used that way in
the same file — `labels()` has always sent 50 ids to `wbgetentities`. This sends
**50 entities** and **20 extracts** per request, so the same corpus costs about
**170 requests instead of 4,900**, a 29x reduction. That is not a trick to evade
a rate limit; it is the documented way to ask, and it is gentler on the service
than the version that was being throttled.

Writes `data/artifacts/wikipedia_parents_scale.jsonl`. The published
168-article corpus is a different file and is never touched.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import scripts.fetch_wikipedia_parents as W
from scripts.fetch_wikipedia_parents import labels, parents, qids

OUT = Path("data/artifacts/wikipedia_parents_scale.jsonl")
WANT = 2400
UA = W.UA


def _get(url: str, tries: int = 8) -> bytes:
    for i in range(tries):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            wait = min(300, 10 * 2 ** i)
            print(f"   {type(e).__name__} {e}; waiting {wait}s "
                  f"({i + 1}/{tries})", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"gave up on {url[:90]}")


W._get = _get


def entities(ids: list[str]) -> dict[str, dict]:
    """50 per request, claims and the English sitelink only."""
    out: dict[str, dict] = {}
    for i in range(0, len(ids), 50):
        chunk = "|".join(ids[i:i + 50])
        data = json.loads(_get(
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            "&format=json&props=claims|sitelinks|labels&languages=en"
            f"&sitefilter=enwiki&ids={chunk}"))
        out.update(data.get("entities", {}))
        print(f"   entities {min(i + 50, len(ids))}/{len(ids)}", flush=True)
        time.sleep(0.6)
    return out


def intros(titles: list[str]) -> dict[str, str]:
    """20 per request. `exlimit` is what makes extracts batchable at all."""
    out: dict[str, str] = {}
    for i in range(0, len(titles), 20):
        chunk = titles[i:i + 20]
        data = json.loads(_get(
            "https://en.wikipedia.org/w/api.php?action=query&format=json"
            "&prop=extracts&explaintext=1&exintro=1&exlimit=20&redirects=1"
            "&titles=" + urllib.parse.quote("|".join(chunk), safe="|")))
        q = data.get("query", {})
        # A redirect or a normalisation changes the key the answer comes back
        # under, so both maps are followed rather than assuming identity.
        alias = {m["from"]: m["to"] for m in q.get("normalized", [])}
        alias.update({m["from"]: m["to"] for m in q.get("redirects", [])})
        by_title = {p.get("title", ""): p.get("extract", "")
                    for p in q.get("pages", {}).values()}
        for t in chunk:
            key = t
            for _ in range(3):
                if key in by_title:
                    break
                key = alias.get(key, key)
            if by_title.get(key):
                out[t] = by_title[key]
        print(f"   intros {min(i + 20, len(titles))}/{len(titles)}, "
              f"{len(out)} with text", flush=True)
        time.sleep(0.6)
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ids = qids(WANT)
    print(f"{len(ids)} candidate companies", flush=True)

    ents = entities(ids)
    records, need = [], []
    for qid, ent in ents.items():
        title = ent.get("sitelinks", {}).get("enwiki", {}).get("title")
        if not title:
            continue
        cur, old = parents(ent)
        if not cur:
            continue
        records.append({"qid": qid,
                        "company": ent.get("labels", {}).get(
                            "en", {}).get("value", title),
                        "title": title, "current_ids": cur,
                        "former_ids": old})
        need += cur + old
    print(f"{len(records)} have an English article and a parent", flush=True)

    lab = labels(need)
    text = intros([r["title"] for r in records])
    kept = 0
    with OUT.open("w") as fh:
        for r in records:
            body = text.get(r["title"], "")
            if len(body) < 200:
                continue
            r["parent"] = lab.get(r["current_ids"][0], "")
            if not r["parent"]:
                continue
            r["current"] = [lab[i] for i in r["current_ids"] if i in lab]
            r["former"] = [lab[i] for i in r["former_ids"] if i in lab]
            r["intro"] = body
            fh.write(json.dumps(r) + "\n")
            kept += 1
    print(f"\n{kept} articles -> {OUT}")


if __name__ == "__main__":
    main()
