"""A typer with recall, since recall is what a candidate filter needs.

51% of the residual on the real-text task is **non-organisations**, and a typer
for exactly that already existed — doing one search hit and one subclass hop,
which rejects *BBC*, *Bertelsmann*, *CBS Studios* and *Amazon MGM Studios*.
Applying it therefore cost coverage 0.589 → 0.411 to lift precision 0.626 → 0.681.

**For a candidate filter, a false negative discards a correct answer while a false
positive merely fails to remove noise the rest of the stack can still handle.** So
the trade should be made the other way: top **three** search hits rather than one,
and `P279` walked to depth **three** with a memoised class map.

Compares v1 against v2, on the reader that currently wins — state patterns first,
transfer verbs as fallback.

Run: uv run python -u scripts/typer_v2.py
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
from wikipedia_parents import SRC, _END, _STOP, _names, hit  # noqa: E402

CACHE = Path("data/artifacts/wikidata_types_v2.json")
CLASSES = Path("data/artifacts/wikidata_classes.json")
V1 = Path("data/artifacts/wikidata_types.json")
OUT = Path("runs/typer_v2.json")
UA = "symbolic-ai-models research bot (non-commercial; <1 req/sec)"

ORG_ROOTS = {"Q43229", "Q4830453", "Q783794", "Q6881511", "Q3778211"}
DEPTH = 3
HITS = 3

NAME = r"([A-Z][\w.&'-]*(?:\s+(?:[A-Z][\w.&'-]*|of|and|de|for))*)"
STATE = re.compile(
    r"\b(?:a |an |the )?(?:wholly[- ]owned |majority[- ]owned |direct )?"
    r"(?:subsidiary|division|unit|arm|affiliate)\s+of\s+(?:the\s+)?" + NAME +
    r"|\bowned\s+by\s+(?:the\s+)?" + NAME +
    r"|\bheld\s+by\s+(?:the\s+)?" + NAME +
    r"|\bcontrolled\s+by\s+(?:the\s+)?" + NAME)
EVENT = re.compile(
    r"\b(?:acquired|bought|purchased|taken\s+over)\s+by\s+(?:the\s+)?" + NAME +
    r"|\bpart\s+of\s+(?:the\s+)?" + NAME)


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


def parents_of(qid: str, classes: dict) -> list[str]:
    if qid in classes:
        return classes[qid]
    ent = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    time.sleep(0.3)
    e = (ent or {}).get("entities", {}).get(qid, {})
    ups = [st["mainsnak"]["datavalue"]["value"]["id"]
           for st in e.get("claims", {}).get("P279", [])
           if st.get("mainsnak", {}).get("snaktype") == "value"]
    classes[qid] = ups
    return ups


def is_org(name: str, cache: dict, classes: dict) -> bool:
    if name in cache:
        return cache[name]
    data = _get("https://www.wikidata.org/w/api.php?action=wbsearchentities"
                f"&format=json&language=en&limit={HITS}&type=item&search="
                + urllib.parse.quote(name))
    time.sleep(0.3)
    for h in ((data or {}).get("search") or [])[:HITS]:
        ent = _get("https://www.wikidata.org/wiki/Special:EntityData/"
                   f"{h['id']}.json")
        time.sleep(0.3)
        e = (ent or {}).get("entities", {}).get(h["id"], {})
        frontier = [st["mainsnak"]["datavalue"]["value"]["id"]
                    for st in e.get("claims", {}).get("P31", [])
                    if st.get("mainsnak", {}).get("snaktype") == "value"]
        seen: set[str] = set()
        for _ in range(DEPTH):
            if set(frontier) & ORG_ROOTS:
                cache[name] = True
                return True
            nxt: list[str] = []
            for c in frontier[:4]:
                if c in seen:
                    continue
                seen.add(c)
                nxt += parents_of(c, classes)
            frontier = nxt
            if not frontier:
                break
    cache[name] = False
    return False


def pull(rx, text: str) -> list[str]:
    out = []
    for m in rx.finditer(text):
        n = next((g for g in m.groups() if g), "")
        n = _END.split(n)[0]
        n = _STOP.sub("", n).strip(" .,'")
        if len(n) > 2:
            out.append(n)
    return out


def main() -> None:
    rows = [json.loads(x) for x in SRC.read_text().splitlines() if x.strip()]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    classes = json.loads(CLASSES.read_text()) if CLASSES.exists() else {}
    v1 = json.loads(V1.read_text()) if V1.exists() else {}

    names = sorted({c for r in rows
                    for c in pull(STATE, r["intro"]) + pull(EVENT, r["intro"])})
    print(f"{len(names)} candidate strings; {len(cache)} cached")
    for n, name in enumerate(names, 1):
        is_org(name, cache, classes)
        if n % 20 == 0:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache))
            CLASSES.write_text(json.dumps(classes))
            print(f"   typed {n}")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache))
    CLASSES.write_text(json.dumps(classes))

    shared = [n for n in names if n in v1]
    print(f"\ntyped as organisation: v2 {statistics.mean(cache[n] for n in names):.3f}"
          f"   v1 {statistics.mean(v1[n] for n in shared):.3f} (on {len(shared)} shared)")
    gained = [n for n in shared if cache[n] and not v1[n]]
    lost = [n for n in shared if v1[n] and not cache[n]]
    print(f"v2 accepts {len(gained)} that v1 rejected, e.g. {gained[:6]}")
    print(f"v2 rejects {len(lost)} that v1 accepted, e.g. {lost[:4]}")

    def ok(g, r):
        return _names(g, r.get("current") or [r["parent"]]) or hit(g, r["parent"])

    tot = len(rows)
    print(f"\n{'policy':<34} {'coverage':>9} {'correct':>9} {'precision':>11}")
    print("-" * 66)
    out = {}
    for lab, typer in (("state-first, no typing", None),
                       ("  + typing v1", v1), ("  + TYPING v2", cache)):
        ans, cor = [], []
        for r in rows:
            c = pull(STATE, r["intro"]) or pull(EVENT, r["intro"])
            if typer is not None:
                c = [x for x in c if typer.get(x)]
            if not c:
                continue
            ans.append(1)
            cor.append(ok(c[0], r))
        out[lab] = {"coverage": len(ans) / tot, "correct": sum(cor) / tot,
                    "precision": statistics.mean(cor) if cor else 0.0}
        print(f"{lab:<34} {out[lab]['coverage']:>9.3f} "
              f"{out[lab]['correct']:>9.3f} {out[lab]['precision']:>11.3f}")
    print("\nthe number to beat is 0.393 correct, from the untyped state-first reader")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
