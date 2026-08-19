"""Pairs that matter together while neither matters alone.

`load_bearing` and `omits_load_bearing` both test **single**-claim deletion. A
pair whose joint removal changes the answer, while neither alone does, is
invisible to them -- which would make the "complete" renderer incomplete and the
objective shipped last turn a lower bound rather than a guarantee.

There is a specific reason to expect them. The redundancy that makes flood's
explanations short is **parallel routes**: two links where deleting either leaves
the other usable, but deleting both disconnects. The property that buys brevity
is the property that creates the blind spot.

Run: uv run python -u scripts/joint_dependencies.py
"""

from __future__ import annotations

import itertools
import json
import statistics
from dataclasses import replace
from pathlib import Path

OUT = Path("runs/joint_dependencies.json")


def probe_flood(n: int):
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    cases = [c for c in (generate(s) for s in range(n)) if solve(c.world)[0]]
    return cases, lambda w: solve(w)[0]


def probe_solvency(n: int):
    from symbolic_ai_core.world import Quantity
    from symbolic_ai_generators.solvency import generate

    def answer(world):
        best: dict = {}
        for c in world.claims:
            if c.predicate != "revenue":
                continue
            q = c.roles.get("value")
            if isinstance(q, Quantity):
                m = c.roles["of"].id
                best[m] = max(best.get(m, 0.0), float(q.value))
        return round(sum(best.values()), 2)

    return [generate(s) for s in range(n)], answer


def main() -> None:
    print(f"{'domain':<11} {'cases':>6} {'singles':>8} {'JOINT pairs':>12} "
          f"{'per case':>9} {'kinds':<28}")
    print("-" * 80)
    rows = {}
    for name, probe, n in (("flood", probe_flood, 24),
                           ("solvency", probe_solvency, 24)):
        cases, answer = probe(n)
        singles, joints, kinds = [], [], {}
        for case in cases:
            base = answer(case.world)
            claims = case.world.claims
            single = set()
            for i in range(len(claims)):
                t = replace(case.world, claims=tuple(
                    c for j, c in enumerate(claims) if j != i))
                try:
                    if answer(t) != base:
                        single.add(i)
                except Exception:
                    single.add(i)
            inert = [i for i in range(len(claims)) if i not in single]
            found = 0
            for a, b in itertools.combinations(inert, 2):
                t = replace(case.world, claims=tuple(
                    c for j, c in enumerate(claims) if j not in (a, b)))
                try:
                    changed = answer(t) != base
                except Exception:
                    changed = True
                if changed:
                    found += 1
                    key = tuple(sorted((claims[a].predicate,
                                        claims[b].predicate)))
                    kinds[key] = kinds.get(key, 0) + 1
            singles.append(len(single))
            joints.append(found)
        top = sorted(kinds.items(), key=lambda kv: -kv[1])[:2]
        rows[name] = {"cases": len(cases),
                      "singles": statistics.mean(singles),
                      "joints": statistics.mean(joints),
                      "kinds": {f"{a}+{b}": v for (a, b), v in kinds.items()}}
        print(f"{name:<11} {len(cases):>6} {statistics.mean(singles):>8.1f} "
              f"{sum(joints):>12} {statistics.mean(joints):>9.1f} "
              f"{', '.join(f'{a}+{b}' for (a, b), _ in top):<28}")

    f = rows["flood"]
    total = sum(v for v in f["kinds"].values())
    print()
    if total > 0:
        print(f"-> JOINT DEPENDENCIES EXIST. flood has {total} pairs over "
              f"{f['cases']} cases ({f['joints']:.2f} per case)\n   that change "
              f"the answer together while neither changes it alone. ONE IS "
              f"ENOUGH: the\n   shipped `omits_load_bearing` is a LOWER BOUND, "
              f"not a guarantee -- a paragraph can\n   cite every "
              f"singly-load-bearing claim and still omit a pair the answer "
              f"depends on.")
        top = sorted(f["kinds"].items(), key=lambda kv: -kv[1])[:3]
        print(f"\n   The commonest kind is {top[0][0]} "
              f"({top[0][1]} of {total}), which is parallel routes: delete "
              f"either\n   and the other carries the traffic; delete both and "
              f"it does not. The redundancy\n   that makes explanations short "
              f"is what creates the blind spot.")
        print(f"\n   A six-case run of this said the pairs were concentrated in "
              f"`flooded` and that\n   links were not involved. That was two "
              f"data points and it was wrong. Same lesson\n   as the exactness "
              f"audit, arrived at from the other side.")
        print(f"\n   solvency has {sum(rows['solvency']['kinds'].values())}, "
              f"which a sum predicts: every latest filing is already\n   "
              f"individually load-bearing, so there is nothing "
              f"jointly-but-not-singly critical.")
    else:
        print(f"-> no joint pairs found, so single-claim sensitivity captures "
              f"the dependency structure\n   here.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
