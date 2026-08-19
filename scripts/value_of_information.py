"""The rational rule for where to spend reading effort, and whether it predicts.

Section 14 of the strategic frame: once query-relative equivalence is explicit,
ask what observation would most reduce uncertainty over the answer -- and derive
the decision rule before training a router.

With `d` measured per relation per query and extraction accuracy measured per
relation, the rule is immediate. Improving relation `r` can only help on the
claims that are currently **wrong** and only matters on the ones that are
**influential**, so to first order:

    VOI(r)  ~  d_r * (1 - acc_r) / cost_r

A single query cannot discriminate this from the naive *improve the weakest
relation*, because on the union query `parent` has both the higher `d` and the
lower accuracy. So two queries that **swap the roles**:

    A.  groups in country X     -- parent ENUMERATED, country FILTERS
    B.  countries of group G    -- country ENUMERATED, parent FILTERS

then oracle-fix a fixed share of one relation's errors and measure the F1 gain.
The test is whether the gain ratio follows VOI or follows headroom.

Run: uv run python -u scripts/value_of_information.py
"""

from __future__ import annotations

import json
import random
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from multi_relation_world import (PARENTS, RELS, matches, norm, read_country,
                                  read_hq, read_parent)  # noqa: E402

OUT = Path("runs/value_of_information.json")
FIX_SHARE = 0.5


def load():
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
        rows.append({
            "qid": rec["qid"],
            "parent": read_parent(p["intro"]),
            "country": read_country(p["intro"]),
            "parent_gold": p.get("current") or [p["parent"]],
            "country_gold": rec.get("country", []),
        })
    return rows


def answer_a(read, country):
    """groups in country X -- parent enumerated, country filters."""
    return frozenset(norm(x["parent"]) for x in read
                     if x["parent"] and x["country"]
                     and norm(x["country"]) == norm(country))


def gold_a(read, country):
    return frozenset(norm(p) for x in read
                     if any(norm(g) == norm(country) for g in x["country_gold"])
                     for p in x["parent_gold"])


def answer_b(read, group):
    """countries of group G -- country enumerated, parent filters."""
    return frozenset(norm(x["country"]) for x in read
                     if x["country"] and x["parent"]
                     and norm(x["parent"]) == norm(group))


def gold_b(read, group):
    return frozenset(norm(c) for x in read
                     if any(norm(p) == norm(group) for p in x["parent_gold"])
                     for c in x["country_gold"])


def f1(got, gold):
    if not gold:
        return None
    tp = len(got & gold)
    p = tp / len(got) if got else 0.0
    r = tp / len(gold)
    return 2 * p * r / (p + r) if p + r else 0.0


def macro(read, probes, ans, gld):
    vals = [f1(ans(read, k), gld(read, k)) for k in probes]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else 0.0


def influence(read, probes, ans, rel):
    hits = []
    for k in probes:
        for x in read:
            if not x[rel]:
                continue
            saved = x[rel]
            before = ans(read, k)
            x[rel] = None
            after = ans(read, k)
            x[rel] = saved
            hits.append(after != before)
    return statistics.mean(hits) if hits else 0.0


def repair(read, rel, share, seed=0):
    """Oracle-fix a share of the relation's wrong or missing values."""
    rng = random.Random(seed)
    out = [dict(x) for x in read]
    gold_key = f"{rel}_gold"
    bad = [x for x in out if not matches(x[rel], x[gold_key]) and x[gold_key]]
    for x in rng.sample(bad, int(len(bad) * share)):
        x[rel] = x[gold_key][0]
    return out


def main() -> None:
    read = load()
    countries = [c for c, _ in sorted(
        ((c, sum(1 for x in read if any(norm(g) == norm(c)
                                        for g in x["country_gold"])))
         for c in {norm(g) for x in read for g in x["country_gold"]}),
        key=lambda kv: -kv[1])[:6]]
    groups = [g for g, _ in sorted(
        ((g, sum(1 for x in read if any(norm(p) == norm(g)
                                        for p in x["parent_gold"])))
         for g in {norm(p) for x in read for p in x["parent_gold"]}),
        key=lambda kv: -kv[1])[:6]]

    acc = {}
    for rel in ("parent", "country"):
        known = [x for x in read if x[f"{rel}_gold"]]
        acc[rel] = statistics.mean(matches(x[rel], x[f"{rel}_gold"])
                                   for x in known)

    print(f"extraction accuracy   parent {acc['parent']:.3f}   "
          f"country {acc['country']:.3f}")
    print(f"headroom (1 - acc)    parent {1 - acc['parent']:.3f}   "
          f"country {1 - acc['country']:.3f}\n")

    out = {"accuracy": acc}
    print(f"{'query':<34} {'rel':<9} {'d':>7} {'VOI':>8} {'F1':>7} "
          f"{'F1 after fix':>13} {'gain':>7}")
    print("-" * 88)
    for name, probes, ans, gld in (
            ("A. groups in country X", countries, answer_a, gold_a),
            ("B. countries of group G", groups, answer_b, gold_b)):
        base = macro(read, probes, ans, gld)
        row = {}
        for rel in ("parent", "country"):
            d = influence(read, probes, ans, rel)
            voi = d * (1 - acc[rel])
            fixed = repair(read, rel, FIX_SHARE)
            after = macro(fixed, probes, ans, gld)
            row[rel] = {"d": d, "voi": voi, "base": base, "after": after,
                        "gain": after - base}
            print(f"{name:<34} {rel:<9} {d:>7.3f} {voi:>8.3f} {base:>7.3f} "
                  f"{after:>13.3f} {after - base:>7.3f}")
        out[name] = row
        gp, gc = row["parent"]["gain"], row["country"]["gain"]
        vp, vc = row["parent"]["voi"], row["country"]["voi"]
        print(f"{'':<34} {'ratio':<9} {'':>7} "
              f"{(vp / vc if vc else float('inf')):>8.2f} {'':>7} {'':>13} "
              f"{(gp / gc if gc else float('inf')):>7.2f}")
        print()

    print(f"Half of each relation's errors are oracle-fixed. VOI ~ d*(1-acc);")
    print("the test is whether the GAIN ratio follows VOI or follows headroom,")
    print(f"which ranks parent above country in both queries "
          f"({1 - acc['parent']:.2f} against {1 - acc['country']:.2f}).")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
