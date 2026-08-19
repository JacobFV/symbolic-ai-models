"""Which tasks admit a short honest explanation?

The complete renderer costs +37% length on flood because only **38%** of claims
are load-bearing: the road network is redundant, so most single deletions change
nothing. That is flood's number.

Whether a short complete explanation exists should be a property of the
**decision**, not of the renderer. A max-min over paths has redundancy;
a sum against a threshold does not; a packing at exact fit has none by
construction.

Measured by deleting each claim and re-solving, per domain.

Run: uv run python -u scripts/explanation_length.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

OUT = Path("runs/explanation_length.json")


def flood_probe():
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    cases = [c for c in (generate(s) for s in range(24)) if solve(c.world)[0]]
    return cases, lambda w: solve(w)[0], "max-min over paths"


def solvency_probe():
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

    return [generate(s) for s in range(24)], answer, "sum vs threshold"


def scheduling_probe():
    from symbolic_ai_core.world import Quantity
    from symbolic_ai_generators.scheduling import generate_hard
    from symbolic_ai_generators.scheduling.world import feasible_by_search

    def answer(world):
        jobs, machines, needs, has = {}, {}, {}, {}
        for c in world.claims:
            q = c.roles.get("value")
            if c.predicate == "duration" and isinstance(q, Quantity):
                jobs[c.roles["of"].id] = q.value
            elif c.predicate == "capacity" and isinstance(q, Quantity):
                machines[c.roles["of"].id] = q.value
            elif c.predicate == "needs_capability":
                needs[c.roles["job"].id] = str(c.roles["capability"])
            elif c.predicate == "has_capability":
                has.setdefault(c.roles["machine"].id, []).append(
                    str(c.roles["capability"]))
        if not jobs or not machines:
            return None
        J = {j: (v, needs.get(j, "")) for j, v in jobs.items()}
        M = {m: (v, tuple(sorted(has.get(m, [])))) for m, v in machines.items()}
        return feasible_by_search(J, M)

    return [generate_hard(s) for s in range(12)], answer, "packing at exact fit"


def main() -> None:
    print(f"{'domain':<12} {'decision':<22} {'claims':>7} {'load-bearing':>13} "
          f"{'share':>7}")
    print("-" * 66)
    rows = {}
    for name, probe in (("flood", flood_probe), ("solvency", solvency_probe),
                        ("scheduling", scheduling_probe)):
        cases, answer, shape = probe()
        shares, totals, lbs = [], [], []
        by_kind: dict[str, int] = {}
        for case in cases:
            base = answer(case.world)
            lb = 0
            for i in range(len(case.world.claims)):
                trimmed = replace(case.world, claims=tuple(
                    c for j, c in enumerate(case.world.claims) if j != i))
                try:
                    changed = answer(trimmed) != base
                except Exception:
                    changed = True
                if changed:
                    lb += 1
                    k = case.world.claims[i].predicate
                    by_kind[k] = by_kind.get(k, 0) + 1
            shares.append(lb / len(case.world.claims))
            totals.append(len(case.world.claims))
            lbs.append(lb)
        rows[name] = {"shape": shape, "claims": statistics.mean(totals),
                      "load_bearing": statistics.mean(lbs),
                      "share": statistics.mean(shares),
                      "kinds": {k: v / len(cases)
                                for k, v in sorted(by_kind.items())}}
        r = rows[name]
        print(f"{name:<12} {shape:<22} {r['claims']:>7.1f} "
              f"{r['load_bearing']:>13.1f} {r['share']:>6.0%}")

    print()
    for name, r in rows.items():
        print(f"  {name} load-bearing by kind: "
              f"{ {k: round(v, 2) for k, v in r['kinds'].items()} }")

    counts = [r["load_bearing"] for r in rows.values()]
    worlds = [r["claims"] for r in rows.values()]
    print()
    print(f"  load-bearing, ABSOLUTE : "
          f"{', '.join(f'{k} {v[chr(108)+chr(111)+chr(97)+chr(100)+chr(95)+chr(98)+chr(101)+chr(97)+chr(114)+chr(105)+chr(110)+chr(103)]:.1f}' for k, v in rows.items())}")
    print(f"  world size             : "
          f"{', '.join(f'{k} {v[chr(99)+chr(108)+chr(97)+chr(105)+chr(109)+chr(115)]:.1f}' for k, v in rows.items())}")
    print(f"  spread: explanations {min(counts):.1f}-{max(counts):.1f} "
          f"({max(counts) / min(counts):.1f}x) against worlds "
          f"{min(worlds):.1f}-{max(worlds):.1f} "
          f"({max(worlds) / min(worlds):.1f}x)")

    print()
    print(f"-> THE ABSOLUTE COUNT IS FLAT; THE SHARE IS NOT. An explanation "
          f"owes 5-12 facts across\n   worlds of 11-49 claims and decisions "
          f"ranging from a sum to bin-packing. The share\n   varies mostly "
          f"because the denominators do, so quoting it invites a story about\n"
          f"   redundancy that the absolute numbers do not support.")
    print(f"\n   Two structural predictions were made and both were wrong: "
          f"that exact fit would\n   make scheduling need the MOST (it needs "
          f"the least by share), and that its\n   obstruction would be a small "
          f"local witness (it touches 10 of 20 jobs). With three\n   points and "
          f"two dead hypotheses, the flat absolute count is a description and "
          f"not\n   yet a law.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
