"""What are the candidates, before deciding what to do with them.

Section 9 of the strategic correction: the agreement result refutes treating
**arbitrary extracted strings** as mutually exclusive possible worlds, not
preserving ambiguity. Before branching, establish what the candidates mean.

Resolves each candidate to a Wikidata QID and its aliases -- **identity only**.
``P749``, the parent relation, is the answer and is never consulted.

Three measurements:

1. **the pair taxonomy** over multi-candidate articles -- same entity, distinct,
   unresolved;
2. **entity-level corroboration** (counting alias mentions) against string-level;
3. **same-QID agreement** against string agreement.

Run: uv run python -u scripts/candidate_semantics.py
"""

from __future__ import annotations

import collections
import itertools
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

CACHE = Path("data/artifacts/wikidata_identity.json")
OUT = Path("runs/candidate_semantics.json")
UA = "symbolic-ai-models research bot (non-commercial; <1 req/sec)"


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


def resolve(name: str, cache: dict) -> dict:
    """{qid, label, aliases} -- identity only, no relations."""
    if name in cache:
        return cache[name]
    data = _get("https://www.wikidata.org/w/api.php?action=wbsearchentities"
                "&format=json&language=en&limit=1&type=item&search="
                + urllib.parse.quote(name))
    time.sleep(0.35)
    hits = (data or {}).get("search") or []
    if not hits:
        cache[name] = {"qid": None, "label": None, "aliases": []}
        return cache[name]
    qid = hits[0]["id"]
    ent = _get("https://www.wikidata.org/w/api.php?action=wbgetentities"
               f"&format=json&props=labels|aliases&languages=en&ids={qid}")
    time.sleep(0.35)
    e = (ent or {}).get("entities", {}).get(qid, {})
    label = e.get("labels", {}).get("en", {}).get("value")
    aliases = [a["value"] for a in e.get("aliases", {}).get("en", [])]
    cache[name] = {"qid": qid, "label": label, "aliases": aliases}
    return cache[name]


def main() -> None:
    rows = [json.loads(x) for x in SRC.read_text().splitlines() if x.strip()]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    names = sorted({c for r in rows for c in candidates(r["intro"])})
    print(f"{len(names)} distinct candidate strings; {len(cache)} cached")
    for n, name in enumerate(names, 1):
        resolve(name, cache)
        if n % 25 == 0:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache))
            print(f"   resolved {n}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache))
    got = sum(1 for v in cache.values() if v.get("qid"))
    print(f"{got}/{len(cache)} resolved to a QID\n")

    def ok(g, r):
        return _names(g, r.get("current") or [r["parent"]]) or hit(g, r["parent"])

    # ---- 1. pair taxonomy over multi-candidate articles ------------------
    tax = collections.Counter()
    multi = 0
    for r in rows:
        cs = candidates(r["intro"])
        if len(cs) < 2:
            continue
        multi += 1
        seen = set()
        for a, b in itertools.combinations(cs, 2):
            qa, qb = cache.get(a, {}).get("qid"), cache.get(b, {}).get("qid")
            if a == b:
                continue
            k = (min(a, b), max(a, b))
            if k in seen:
                continue
            seen.add(k)
            if qa is None or qb is None:
                tax["unresolved"] += 1
            elif qa == qb:
                tax["same entity"] += 1
            else:
                tax["distinct"] += 1
    total = sum(tax.values())
    print(f"{multi} multi-candidate articles, {total} candidate pairs")
    for k, v in tax.most_common():
        print(f"   {k:<14} {v:>5} {v / max(total, 1):>7.3f}")

    # ---- 2 & 3. corroboration and agreement, string vs entity ------------
    def string_mentions(name, text):
        core = next((w for w in re.findall(r"[A-Za-z0-9]+", name)
                     if len(w) > 2), "")
        return len(re.findall(rf"\b{re.escape(core)}", text, flags=re.I)) if core else 0

    def entity_mentions(name, text):
        ent = cache.get(name, {})
        forms = [name] + ([ent["label"]] if ent.get("label") else []) \
            + list(ent.get("aliases", []))[:8]
        cores = set()
        for f in forms:
            w = next((x for x in re.findall(r"[A-Za-z0-9]+", f) if len(x) > 2), "")
            if w:
                cores.add(w.lower())
        return sum(len(re.findall(rf"\b{re.escape(c)}", text, flags=re.I))
                   for c in cores)

    out = {"pair_taxonomy": dict(tax), "multi_articles": multi,
           "resolved": got, "distinct_names": len(cache)}
    n = len(rows)
    print(f"\n{'policy':<38} {'coverage':>9} {'correct':>9} {'precision':>11}")
    print("-" * 70)
    for lab, mode in (("first match", "all"),
                      ("+ STRING corroboration", "string"),
                      ("+ ENTITY corroboration", "entity"),
                      ("string agreement", "agree_str"),
                      ("SAME-QID agreement", "agree_qid")):
        ans, cor = [], []
        for r in rows:
            cs = candidates(r["intro"])
            if not cs:
                continue
            if mode == "string" and string_mentions(cs[0], r["intro"]) < 2:
                continue
            if mode == "entity" and entity_mentions(cs[0], r["intro"]) < 2:
                continue
            if mode == "agree_str" and len({c.lower() for c in cs}) != 1:
                continue
            if mode == "agree_qid":
                qids = {cache.get(c, {}).get("qid") for c in cs}
                if None in qids or len(qids) != 1:
                    continue
            ans.append(1)
            cor.append(ok(cs[0], r))
        out[lab] = {"coverage": len(ans) / n, "correct": sum(cor) / n,
                    "precision": statistics.mean(cor) if cor else 0.0}
        print(f"{lab:<38} {out[lab]['coverage']:>9.3f} "
              f"{out[lab]['correct']:>9.3f} {out[lab]['precision']:>11.3f}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
