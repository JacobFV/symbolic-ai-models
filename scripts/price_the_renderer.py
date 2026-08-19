"""The third stage, which no milestone has ever priced.

The lesson written this turn says to check a metric where its **missing term
dominates**, not where it is comfortable. Applying it immediately: the ledger now
knows three stages -- read, solve, render -- and only two have ever been
measured. The pipeline's deliverable is a *grounded paragraph*, and nothing has
charged for producing it.

Where it would dominate is solvency, whose solve is 0.002 ms and read 0.061 ms.
For flood and scheduling, whose kernels run 8.6 ms and 26 ms, rendering has to be
enormous to matter.

Run: uv run python -u scripts/price_the_renderer.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

OUT = Path("runs/price_the_renderer.json")


def flood():
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood.render import render_answer
    from symbolic_ai_generators.flood.surface import render_observation

    cases = [generate(s) for s in range(40)]
    texts = [render_observation(c, variants=4).text for c in cases]
    t0 = time.perf_counter()
    worlds = [read_content_roles(t) for t in texts]
    read = time.perf_counter() - t0
    t0 = time.perf_counter()
    solved = [solve(w) for w in worlds]
    slv = time.perf_counter() - t0
    t0 = time.perf_counter()
    for case, (ans, outs, _) in zip(cases, solved):
        render_answer(case, ans, outs)
    ren = time.perf_counter() - t0
    return read, slv, ren, len(cases)


def scheduling():
    import sys
    sys.path.insert(0, "scripts")
    from hard_regime_milestone import solve_world

    from symbolic_ai_generators.scheduling import generate_hard
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling.render import render_answer
    from symbolic_ai_generators.scheduling.surface import render_observation

    cases = [generate_hard(s) for s in range(20)]
    texts = [render_observation(c, variants=4).text for c in cases]
    t0 = time.perf_counter()
    worlds = [read_signature(t) for t in texts]
    read = time.perf_counter() - t0
    t0 = time.perf_counter()
    answers = [solve_world(w)[0] for w in worlds]
    slv = time.perf_counter() - t0
    t0 = time.perf_counter()
    for case, a in zip(cases, answers):
        render_answer(case, bool(a))
    ren = time.perf_counter() - t0
    return read, slv, ren, len(cases)


def solvency():
    from symbolic_ai_generators.solvency import decide, generate
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    from symbolic_ai_generators.solvency.render import render_answer
    from symbolic_ai_generators.solvency.surface import render_observation

    cases = [generate(s) for s in range(200)]
    texts = [render_observation(c, variants=4).text for c in cases]
    t0 = time.perf_counter()
    readings = [read_signature(t) for t in texts]
    read = time.perf_counter() - t0
    t0 = time.perf_counter()
    answers = [decide_reading(r) for r in readings]
    slv = time.perf_counter() - t0
    t0 = time.perf_counter()
    for case, a in zip(cases, answers):
        render_answer(case, bool(a))
    ren = time.perf_counter() - t0
    return read, slv, ren, len(cases)


def main() -> None:
    print(f"{'domain':<12} {'read ms':>9} {'solve ms':>10} {'render ms':>11} "
          f"{'read %':>8} {'solve %':>9} {'render %':>10}")
    print("-" * 74)
    rows = {}
    for name, fn in (("flood", flood), ("scheduling", scheduling),
                     ("solvency", solvency)):
        read, slv, ren, n = fn()
        total = read + slv + ren
        rows[name] = {"read_ms": read / n * 1000, "solve_ms": slv / n * 1000,
                      "render_ms": ren / n * 1000, "read_share": read / total,
                      "solve_share": slv / total, "render_share": ren / total}
        r = rows[name]
        print(f"{name:<12} {r['read_ms']:>9.3f} {r['solve_ms']:>10.3f} "
              f"{r['render_ms']:>11.3f} {r['read_share']:>7.1%} "
              f"{r['solve_share']:>8.1%} {r['render_share']:>9.1%}",
              flush=True)

    worst = max(rows, key=lambda k: rows[k]["render_share"])
    share = rows[worst]["render_share"]
    print()
    if share > 0.25:
        print(f"-> RENDERING IS THE LARGEST TERM SOMEWHERE. In {worst} it is "
              f"{share:.0%} of the pipeline,\n   against "
              f"{rows[worst]['solve_share']:.1%} for the decision it explains. "
              f"That domain's cost is text handling\n   almost entirely, and "
              f"the reasoning it exists to price is a rounding error.")
        print(f"\n   Both omissions found this way have the same shape: the "
              f"term is negligible in\n   the domains with expensive kernels "
              f"and dominant in the one without. Checking\n   only the "
              f"comfortable cases would have missed both.")
    elif share > 0.05:
        print(f"-> RENDERING IS A REAL BUT MINOR TERM: at most {share:.1%}, in "
              f"{worst}. Worth pricing\n   for completeness; it does not change "
              f"a conclusion.")
    else:
        print(f"-> RENDERING IS NEGLIGIBLE EVERYWHERE (at most {share:.1%}). "
              f"The read/solve split is the\n   whole story and the third stage "
              f"is bookkeeping -- which closes the stage\n   accounting rather "
              f"than opening it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
