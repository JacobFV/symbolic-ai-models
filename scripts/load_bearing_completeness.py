"""The forgiving completeness the strict one could never be.

`incomplete` demands the answer be **rebuildable** from the paragraph. The
shipped renderer scores 0.000 on that, and so would any explanation a person
would read -- a paragraph reciting 28 facts is worse output, not better. Strict
completeness is a diagnostic and cannot be an objective.

The forgiving version: does the paragraph cite every claim **whose deletion
changes the answer**? That is the load-bearing set, it is what an explanation
owes a reader, and it is achievable at a length someone would read.

Run: uv run python -u scripts/load_bearing_completeness.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.render import render_answer

OUT = Path("runs/load_bearing_completeness.json")
N = 30


def load_bearing(case) -> set[int]:
    """Claim indices whose deletion changes the answer."""
    base = solve(case.world)[0]
    out = set()
    for i in range(len(case.world.claims)):
        trimmed = replace(case.world, claims=tuple(
            c for j, c in enumerate(case.world.claims) if j != i))
        try:
            if solve(trimmed)[0] != base:
                out.add(i)
        except Exception:
            out.add(i)
    return out


def cited(answer) -> set[int]:
    out = set()
    for c in answer.citations:
        if c.source.startswith("claim:"):
            tail = c.source.split(":", 1)[1]
            if tail.isdigit():
                out.add(int(tail))
    return out


def main() -> None:
    sizes, worlds, covered, kinds = [], [], [], {}
    shipped_complete = 0
    n = 0
    for s in range(N):
        case = generate(s)
        if not solve(case.world)[0]:
            continue
        n += 1
        lb = load_bearing(case)
        sizes.append(len(lb))
        worlds.append(len(case.world.claims))
        answer, outs, _ = solve(case.world)
        para = render_answer(case, answer, outs)
        c = cited(para)
        covered.append(len(lb & c) / len(lb) if lb else 1.0)
        shipped_complete += lb <= c
        for i in lb:
            k = case.world.claims[i].predicate
            kinds[k] = kinds.get(k, 0) + 1

    print(f"{n} non-empty cases\n")
    print(f"  claims per world            : {statistics.mean(worlds):.1f}")
    print(f"  LOAD-BEARING claims per case: {statistics.mean(sizes):.1f} "
          f"({statistics.mean(sizes) / statistics.mean(worlds):.0%})")
    print(f"  shipped renderer covers     : "
          f"{statistics.mean(covered):.3f} of them")
    print(f"  shipped renderer complete   : {shipped_complete}/{n}")
    print(f"\n  what is load-bearing, by kind:")
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"    {k:<12} {v / n:>5.2f} per case")

    print()
    frac = statistics.mean(sizes) / statistics.mean(worlds)
    if frac < 0.4 and statistics.mean(covered) < 0.5:
        print(f"-> THE TARGET IS ACHIEVABLE AND THE RENDERER MISSES IT. Only "
              f"{statistics.mean(sizes):.1f} of "
              f"{statistics.mean(worlds):.1f} claims\n   are load-bearing "
              f"({frac:.0%}), so an explanation citing what the decision turned "
              f"on is a\n   paragraph a person would read -- not a recitation. "
              f"The shipped renderer covers\n   {statistics.mean(covered):.0%} "
              f"of them and is complete on {shipped_complete} of {n} cases.")
        print(f"\n   So strict completeness was the wrong bar and the weak one "
              f"is the right target:\n   reachable, short, and currently "
              f"unmet.")
    elif frac >= 0.4:
        print(f"-> NO SHORT EXPLANATION CAN BE COMPLETE. {frac:.0%} of claims "
              f"are load-bearing, so even\n   the forgiving notion demands most "
              f"of the world and the diagnostic is all that is\n   available.")
    else:
        print(f"-> the renderer already covers "
              f"{statistics.mean(covered):.0%} of the load-bearing set.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": n, "claims_per_world": statistics.mean(worlds),
         "load_bearing": statistics.mean(sizes),
         "covered": statistics.mean(covered),
         "complete": shipped_complete,
         "kinds": {k: v / n for k, v in kinds.items()}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
