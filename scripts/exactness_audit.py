"""What our exact numbers actually bound.

The solvency reader was reported at 1.000 over 60 seeds and was wrong on 2.25% of
cases. That was not an isolated slip: by the **rule of three**, zero failures in
``N`` cases bounds the true rate at roughly ``3/N`` with 95% confidence, so a
sample of 34 excludes only rates above 8.8%. Several load-bearing findings here
are asserted as exact on samples that small.

This re-runs the claimed-exact ones at 400 seeds and reports, for each, the bound
its original sample supported against the bound it supports now.

A bound is worth having whether or not the number moves. "Exact over 400"
excludes 0.75%; "exact over 34" excludes 8.8%; both read as 1.000 on the page.

Run: uv run python -u scripts/exactness_audit.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("runs/exactness_audit.json")
BIG = 400


def rule_of_three(n: int) -> float:
    return 3.0 / n if n else 1.0


def flood_reader() -> tuple[int, int, int]:
    """(failures, checked, original N) for signature+content, interleaved."""
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood.surface import render_observation
    from symbolic_ai_generators.scramble import interleave, unsaturate

    H = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
         "LOADING AND LIMITS.", "TASKING.")
    bad = n = 0
    for s in range(BIG):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        n += 1
        obs = render_observation(case, variants=4)
        text = interleave(unsaturate(obs, headings=H, shuffle=False)).text
        try:
            got = solve(read_content_roles(text))[0]
        except Exception:
            got = ()
        bad += got != want
    return bad, n, 34


def flood_certificate() -> tuple[int, int, int]:
    """(failures, checked, original N) for 'fires iff decided'."""
    import sys
    from dataclasses import replace
    sys.path.insert(0, "scripts")
    from insensitivity_certificate import certifies_insensitive

    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood.surface import render_observation
    from symbolic_ai_generators.scramble import interleave, unsaturate

    H = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
         "LOADING AND LIMITS.", "TASKING.")
    bad = n = 0
    for s in range(BIG):
        case = generate(s)
        if not solve(case.world)[0]:
            continue
        n += 1
        obs = render_observation(case, variants=4, hard_distractors=True)
        world = read_content_roles(
            interleave(unsaturate(obs, headings=H, shuffle=False)).text)
        answers = {solve(world)[0]}
        for i, c in enumerate(world.claims):
            if c.predicate == "link":
                answers.add(solve(replace(world, claims=tuple(
                    x for j, x in enumerate(world.claims) if j != i)))[0])
        bad += certifies_insensitive(world) != (len(answers) == 1)
    return bad, n, 95


def scheduling_reader() -> tuple[int, int, int]:
    """(failures, checked, original N) for claim recall 1.000, interleaved."""
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling.surface import render_observation
    from symbolic_ai_generators.scramble import interleave, unsaturate

    bad = n = 0
    for s in range(BIG):
        case = generate(s, n_jobs=6, n_machines=3, slack=0.15)
        obs = render_observation(case, variants=4)
        text = interleave(unsaturate(obs, headings=("WORKS ORDER.",),
                                     shuffle=False)).text
        world = read_signature(text)
        t = {(c.predicate, tuple(sorted(c.entities())))
             for c in case.world.claims}
        g = {(c.predicate, tuple(sorted(c.entities()))) for c in world.claims}
        n += 1
        bad += t != g
    return bad, n, 40


def main() -> None:
    checks = (("flood signature+content, interleaved", flood_reader),
              ("flood insensitivity certificate", flood_certificate),
              ("scheduling reader, interleaved", scheduling_reader))
    print(f"{'claim':<38} {'orig N':>7} {'bounded':>9} {'now N':>7} "
          f"{'failures':>9} {'bounded':>9}")
    print("-" * 84)
    rows = {}
    for label, fn in checks:
        bad, n, orig = fn()
        rows[label] = {"failures": bad, "checked": n, "original_n": orig,
                       "old_bound": rule_of_three(orig),
                       "new_bound": rule_of_three(n) if bad == 0 else bad / n}
        r = rows[label]
        now = (f"{rule_of_three(n):.3%}" if bad == 0 else f"{bad / n:.2%} MEAS")
        print(f"{label:<38} {orig:>7} {rule_of_three(orig):>8.1%} {n:>7} "
              f"{bad:>9} {now:>9}", flush=True)

    broke = [k for k, v in rows.items() if v["failures"]]
    print()
    if broke:
        print(f"-> {len(broke)} of {len(rows)} BROKE at 400 seeds: "
              f"{', '.join(broke)}.")
        print(f"   The solvency reader was not an isolated slip.")
    else:
        print(f"-> none broke. The samples were adequate BY LUCK rather than by "
              f"design, which\n   leaves the method wrong even though the "
              f"numbers stand: nothing about the original\n   samples bounded "
              f"what they were asserting.")
    print(f"\n   What changes either way is the BOUND. Zero failures in 34 "
          f"cases excludes error\n   rates above 8.8%; in 400 it excludes above "
          f"0.75%. Both read as '1.000' on the page,\n   and the findings should "
          f"say which they mean.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"big_n": BIG, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
