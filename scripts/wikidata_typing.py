"""Entity typing as a given: is this candidate string an organisation?

Three independent routes named **entity typing** as the missing capability for
real text, and the crude version failed -- rejecting real single-word company
names along with *CPR*, moving the ranker by 0.008 and costing first-match 0.017.
That was a test of a bad typer, not of typing.

Wikidata is the standard and answers exactly one question here: does this string
resolve to something that is an **organisation** (``P31``/``P279*`` reaching
``Q43229``)? **The parent relation ``P749`` is the answer and is never consulted
as a feature** -- the whole arm would be circular otherwise.

Caches to ``data/artifacts/wikidata_types.json``; ``/data/`` is gitignored, so
this script is the reproduction.

Run: uv run python -u scripts/wikidata_typing.py
"""

from __future__ import annotations

import json
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wikipedia_parents import SRC, _names, candidates, hit  # noqa: E402

CACHE = Path("data/artifacts/wikidata_types.json")
OUT = Path("runs/wikidata_typing.json")
UA = "symbolic-ai-models research bot (non-commercial; <1 req/sec)"

#: organisation, and business as a fallback root
ORG_ROOTS = {"Q43229", "Q4830453", "Q783794", "Q6881511"}


def _get(url: str, tries: int = 4):
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"   {type(e).__name__}; retry {i + 1}")
            time.sleep(2 * (i + 1))
    return None


def is_organisation(name: str, cache: dict) -> bool | None:
    if name in cache:
        return cache[name]
    data = _get("https://www.wikidata.org/w/api.php?action=wbsearchentities"
                "&format=json&language=en&limit=1&type=item&search="
                + urllib.parse.quote(name))
    time.sleep(0.4)
    hits = (data or {}).get("search") or []
    if not hits:
        cache[name] = False
        return False
    qid = hits[0]["id"]
    ent = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    time.sleep(0.4)
    ent = (ent or {}).get("entities", {}).get(qid, {})
    claims = ent.get("claims", {})
    # P31 instance-of, then one hop of P279 subclass-of on each class
    classes = []
    for st in claims.get("P31", []):
        snak = st.get("mainsnak", {})
        if snak.get("snaktype") == "value":
            classes.append(snak["datavalue"]["value"]["id"])
    if set(classes) & ORG_ROOTS:
        cache[name] = True
        return True
    for cid in classes[:3]:
        cls = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{cid}.json")
        time.sleep(0.4)
        cls = (cls or {}).get("entities", {}).get(cid, {})
        ups = [s["mainsnak"]["datavalue"]["value"]["id"]
               for s in cls.get("claims", {}).get("P279", [])
               if s.get("mainsnak", {}).get("snaktype") == "value"]
        if set(ups) & ORG_ROOTS:
            cache[name] = True
            return True
    cache[name] = False
    return False


STOP = {"the", "of", "and", "group", "holdings", "holding", "company",
        "corporation", "corp", "inc", "ltd", "limited", "plc", "llc", "sa",
        "nv", "ag", "co", "media", "entertainment", "international", "music",
        "records", "studios", "streaming", "a", "an"}


def core(s: str) -> str:
    t = [w for w in re.findall(r"[A-Za-z0-9]+", s)
         if w.lower() not in STOP and len(w) > 2]
    return t[0].lower() if t else ""


def main() -> None:
    rows = [json.loads(x) for x in SRC.read_text().splitlines() if x.strip()]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    names = sorted({c for r in rows for c in candidates(r["intro"])})
    print(f"{len(names)} distinct candidate strings; {len(cache)} cached")
    for n, name in enumerate(names, 1):
        is_organisation(name, cache)
        if n % 25 == 0:
            print(f"   typed {n}")
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, indent=0))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=0))
    org = sum(1 for v in cache.values() if v)
    print(f"\n{org} of {len(cache)} candidate strings resolve to an "
          f"organisation ({org / max(len(cache), 1):.3f})\n")

    def mentions(k, t):
        return len(re.findall(rf"\b{re.escape(k)}", t, flags=re.I))

    def ranked(cands, text):
        import collections
        cl = collections.defaultdict(list)
        for c in cands:
            k = core(c)
            if k:
                cl[k].append(c)
        if not cl:
            return cands[0]
        b = max(cl, key=lambda k: (mentions(k, text), len(cl[k])))
        return max(cl[b], key=len)

    def ok(g, r):
        return _names(g, r.get("current") or [r["parent"]]) or hit(g, r["parent"])

    out = {}
    print(f"{'policy':<34} {'coverage':>9} {'correct':>9} {'precision':>11}")
    print("-" * 66)
    for lab, pick, typing in (("first match", lambda c, t: c[0], False),
                              ("first match + wikidata typing",
                               lambda c, t: c[0], True),
                              ("ranked", ranked, False),
                              ("RANKED + wikidata typing", ranked, True)):
        ans, cor = [], []
        for r in rows:
            c = candidates(r["intro"])
            if typing:
                c = [x for x in c if cache.get(x)]
            if not c:
                continue
            g = pick(c, r["intro"])
            ans.append(1)
            cor.append(ok(g, r))
        out[lab] = {"coverage": len(ans) / len(rows),
                    "correct": sum(cor) / len(rows),
                    "precision": statistics.mean(cor)}
        print(f"{lab:<34} {out[lab]['coverage']:>9.3f} "
              f"{out[lab]['correct']:>9.3f} {out[lab]['precision']:>11.3f}")

    print("\nOnly P31/P279* against organisation is consulted. P749 -- the parent")
    print("relation, which is the answer -- is never used as a feature.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
