"""Arm D: independently authored prose to a multi-relation world, and a query
whose answer is stated in no single sentence.

The milestone the strategic frame names. Three relation families read from 168
Wikipedia intros -- `parent`, `country`, `headquarters` -- reconciled into one
world, then a **composed** query:

    which parent groups control companies whose country is X?

joins `parent(c, p)` with `country(c, X)`. No sentence in any article states the
answer; it exists only in the world.

Two things are measured, and the second is the point:

1. per-relation extraction, because the relations are not equally readable;
2. whether **critical error mass** -- the influence-weighted quantity that
   characterised the equivalence class on generated worlds -- predicts
   composed-query correctness on real text.

**Declared external knowledge**, in the repo's usual sense: a nationality
adjective to country map, closed-class and listed here rather than mined from the
ground truth.

Run: uv run python -u scripts/multi_relation_world.py
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wikipedia_parents import candidates  # noqa: E402

PARENTS = Path("data/artifacts/wikipedia_parents.jsonl")
RELS = Path("data/artifacts/company_relations.jsonl")
OUT = Path("runs/multi_relation_world.json")

#: Closed class, declared. The same discipline as the flood value registry: it is
#: external knowledge, it is ablatable, and it was not read off the answers.
NATIONALITY = {
    "french": "France", "italian": "Italy", "german": "Germany",
    "japanese": "Japan", "american": "United States", "british": "United Kingdom",
    "chinese": "China", "spanish": "Spain", "dutch": "Netherlands",
    "swiss": "Switzerland", "swedish": "Sweden", "danish": "Denmark",
    "norwegian": "Norway", "finnish": "Finland", "russian": "Russia",
    "korean": "South Korea", "indian": "India", "canadian": "Canada",
    "australian": "Australia", "brazilian": "Brazil", "mexican": "Mexico",
    "polish": "Poland", "austrian": "Austria", "belgian": "Belgium",
    "irish": "Ireland", "portuguese": "Portugal", "turkish": "Turkey",
    "israeli": "Israel", "taiwanese": "Taiwan", "singaporean": "Singapore",
    "scottish": "United Kingdom", "welsh": "United Kingdom",
    "english": "United Kingdom", "czech": "Czech Republic",
    "hungarian": "Hungary", "greek": "Greece", "argentine": "Argentina",
    "chilean": "Chile", "thai": "Thailand", "vietnamese": "Vietnam",
    "indonesian": "Indonesia", "malaysian": "Malaysia",
    "new zealand": "New Zealand", "south african": "South Africa",
}

_HQ = re.compile(
    r"\b(?:headquartered|based|head office|headquarters)\s+(?:in|at)\s+"
    r"(?:the\s+)?([A-Z][\w.'-]*(?:[ -][A-Z][\w.'-]*)*)")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def read_country(text: str) -> str | None:
    low = text.lower()
    best = None
    for adj, country in NATIONALITY.items():
        m = re.search(rf"\b{re.escape(adj)}\b", low)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), country)
    return best[1] if best else None


def read_hq(text: str) -> str | None:
    m = _HQ.search(re.sub(r"\s+", " ", text))
    return m.group(1) if m else None


def read_parent(text: str) -> str | None:
    c = candidates(text)
    return c[0] if c else None


def matches(guess: str | None, gold: list[str]) -> bool:
    if not guess or not gold:
        return False
    g = norm(guess)
    return any(g and (g == norm(x) or g in norm(x) or norm(x) in g)
               for x in gold)


def main() -> None:
    if not RELS.exists():
        print(f"{RELS} missing -- run scripts/fetch_company_relations.py")
        return
    parents = {json.loads(x)["qid"]: json.loads(x)
               for x in PARENTS.read_text().splitlines() if x.strip()}
    rows = []
    for line in RELS.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        p = parents.get(rec["qid"])
        if not p:
            continue
        rec["intro"] = p["intro"]
        rec["parent_gold"] = p.get("current") or [p["parent"]]
        rows.append(rec)

    print(f"{len(rows)} companies with prose and ground truth\n")

    # ---- 1. per-relation extraction --------------------------------------
    read = []
    for r in rows:
        read.append({
            "qid": r["qid"], "title": r["title"],
            "parent": read_parent(r["intro"]),
            "country": read_country(r["intro"]),
            "hq": read_hq(r["intro"]),
            "parent_gold": r["parent_gold"],
            "country_gold": r.get("country", []),
            "hq_gold": r.get("headquarters", []),
        })

    print(f"{'relation':<14} {'gold known':>11} {'answered':>10} "
          f"{'correct':>9} {'precision':>11}")
    print("-" * 60)
    stats = {}
    for rel, gold_key in (("parent", "parent_gold"), ("country", "country_gold"),
                          ("hq", "hq_gold")):
        known = [x for x in read if x[gold_key]]
        ans = [x for x in known if x[rel]]
        cor = [1 for x in ans if matches(x[rel], x[gold_key])]
        stats[rel] = {"gold_known": len(known) / len(read),
                      "answered": len(ans) / max(len(known), 1),
                      "correct": len(cor) / max(len(known), 1),
                      "precision": len(cor) / max(len(ans), 1)}
        print(f"{rel:<14} {stats[rel]['gold_known']:>11.3f} "
              f"{stats[rel]['answered']:>10.3f} {stats[rel]['correct']:>9.3f} "
              f"{stats[rel]['precision']:>11.3f}")

    # ---- 2. the composed query -------------------------------------------
    def groups_in(country: str, source: str) -> set[str]:
        """parent(c, p) JOIN country(c, X) -> {p}. Stated in no sentence."""
        out = set()
        for x in read:
            if source == "gold":
                c_ok = any(norm(country) == norm(g) for g in x["country_gold"])
                ps = x["parent_gold"]
            else:
                c_ok = x["country"] and norm(x["country"]) == norm(country)
                ps = [x["parent"]] if x["parent"] else []
            if c_ok:
                out |= {norm(p) for p in ps if p}
        return out

    countries = sorted({norm(c) for x in read for c in x["country_gold"]})
    scored = []
    for c in countries:
        gold = groups_in(c, "gold")
        if not gold:
            continue
        got = groups_in(c, "read")
        tp = len(gold & got)
        prec = tp / len(got) if got else 0.0
        rec = tp / len(gold)
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        scored.append({"country": c, "gold": len(gold), "got": len(got),
                       "precision": prec, "recall": rec, "f1": f1})
    scored.sort(key=lambda s: -s["gold"])

    print(f"\nCOMPOSED QUERY -- parent(c,p) JOIN country(c,X), "
          f"{len(scored)} countries with a non-empty answer")
    print(f"{'country':<20} {'|gold|':>7} {'|read|':>7} {'prec':>7} "
          f"{'recall':>7} {'F1':>7}")
    print("-" * 60)
    for s in scored[:8]:
        print(f"{s['country']:<20} {s['gold']:>7} {s['got']:>7} "
              f"{s['precision']:>7.3f} {s['recall']:>7.3f} {s['f1']:>7.3f}")
    macro = {k: statistics.mean(s[k] for s in scored)
             for k in ("precision", "recall", "f1")}
    print(f"{'MACRO':<20} {'':>7} {'':>7} {macro['precision']:>7.3f} "
          f"{macro['recall']:>7.3f} {macro['f1']:>7.3f}")

    # ---- 3. influence, on a UNION query rather than a threshold ----------
    # critical mass ~ d * |errors|, and the law says weighting separates only
    # when d < 1. A threshold decision hides most single-claim errors inside the
    # margin; a UNION enumerates, so every contributing claim shows. Measure d
    # rather than assume it.
    infl = {"parent": [], "country": []}
    for c in [s["country"] for s in scored[:6]]:
        gold = groups_in(c, "gold")
        for x in read:
            if not (x["country"] and norm(x["country"]) == norm(c)):
                continue
            for rel in ("parent", "country"):
                if not x[rel]:
                    continue
                saved = x[rel]
                x[rel] = None
                changed = groups_in(c, "read") != groups_in(c, "read")
                x[rel] = saved
                # recompute properly: drop the claim, compare the answer set
                x[rel] = None
                after = groups_in(c, "read")
                x[rel] = saved
                before = groups_in(c, "read")
                infl[rel].append(after != before)
    print("\nINFLUENCE ON THE UNION QUERY -- share of read claims whose removal")
    print("changes the answer set (this is d, and the law says weighting buys")
    print("separation only when d < 1):")
    for rel, v in infl.items():
        if v:
            print(f"   {rel:<10} {len(v):>5} claims   d = {statistics.mean(v):.3f}")
    out_infl = {k: (statistics.mean(v) if v else None) for k, v in infl.items()}

    out = {"n": len(rows), "per_relation": stats, "queries": scored,
           "macro": macro, "union_influence": out_infl}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
