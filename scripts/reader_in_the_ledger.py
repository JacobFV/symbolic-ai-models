"""Charging the reader, as the working agreement already requires.

``CLAUDE.md``: *cost is charged to the **system** -- if a reasoner only works
because something upstream produced a graph, that upstream component is in the
ledger.* ``symbolic_ai_core.cost.System`` exists, in its own words, because
"``sum`` is not optional".

And every milestone in this repo prices **kernel artifacts only**. Measured
2026-08-19, reading is 1.9% of flood's time, 0.9% of scheduling's, and **96.1%
of solvency's** -- so the ledger has been pricing 4% of what solvency runs.

This builds each domain's system from both components and reports the north-star
number with the reader in and out.

Run: uv run python -u scripts/reader_in_the_ledger.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_core.cost import Capability, System, cpu_component, ledger

OUT = Path("runs/reader_in_the_ledger.json")


def _tokens(text: str) -> int:
    return max(1, len(text.split()))


def flood_probe():
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood.surface import render_observation

    cases = [generate(s) for s in range(40)]
    texts = [render_observation(c, variants=4).text for c in cases]
    truth = [solve(c.world)[0] for c in cases]

    t0 = time.perf_counter()
    worlds = [read_content_roles(t) for t in texts]
    read_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = [solve(w)[0] for w in worlds]
    solve_s = time.perf_counter() - t0

    ne = [i for i, t in enumerate(truth) if t]
    rate = statistics.mean(got[i] == truth[i] for i in ne)
    floor = 1 - len(ne) / len(cases)          # the empty-answer share
    return texts, read_s, solve_s, rate, floor, len(ne)


def scheduling_probe():
    import sys
    sys.path.insert(0, "scripts")
    from hard_regime_milestone import solve_world

    from symbolic_ai_generators.scheduling import generate_hard
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling.surface import render_observation

    cases = [generate_hard(s) for s in range(20)]
    texts = [render_observation(c, variants=4).text for c in cases]
    truth = [c.feasible for c in cases]

    t0 = time.perf_counter()
    worlds = [read_signature(t) for t in texts]
    read_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = [solve_world(w)[0] for w in worlds]
    solve_s = time.perf_counter() - t0

    rate = statistics.mean(g == w for g, w in zip(got, truth))
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    return texts, read_s, solve_s, rate, floor, len(cases)


def solvency_probe():
    from symbolic_ai_generators.solvency import decide, generate
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    from symbolic_ai_generators.solvency.surface import render_observation

    cases = [generate(s) for s in range(200)]
    texts = [render_observation(c, variants=4).text for c in cases]
    truth = [decide(c, as_of=c.decision_date)[0] for c in cases]

    t0 = time.perf_counter()
    readings = [read_signature(t) for t in texts]
    read_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = [decide_reading(r) for r in readings]
    solve_s = time.perf_counter() - t0

    rate = statistics.mean(g == w for g, w in zip(got, truth))
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    return texts, read_s, solve_s, rate, floor, len(cases)


def main() -> None:
    probes = (("flood", flood_probe), ("scheduling", scheduling_probe),
              ("solvency", solvency_probe))
    print(f"{'domain':<12} {'tok/ans':>8} {'read tok/s':>12} "
          f"{'kernel tok/s':>13} {'$/solved kernel only':>21} "
          f"{'$/solved SYSTEM':>17} {'x':>6}")
    print("-" * 95)
    rows = {}
    for name, probe in probes:
        texts, read_s, solve_s, rate, floor, n = probe()
        toks = sum(_tokens(t) for t in texts)
        per_answer = toks / len(texts)
        reader = cpu_component(f"{name}.reader", toks / read_s,
                               source="measured on this machine")
        kernel = cpu_component(f"{name}.kernel", toks / solve_s,
                               source="measured on this machine")
        cap = Capability(unit="answer", rate=rate, floor=floor, n=n,
                         tokens_per_attempt=per_answer)
        only = ledger(System(name=f"{name} (kernel only)",
                             components=(kernel,)), cap)
        whole = ledger(System(name=f"{name} (system)",
                              components=(reader, kernel)), cap)
        a = only.usd_per_solved_above_floor
        b = whole.usd_per_solved_above_floor
        rows[name] = {"tokens_per_answer": per_answer,
                      "reader_tok_s": toks / read_s,
                      "kernel_tok_s": toks / solve_s,
                      "rate": rate, "floor": floor,
                      "kernel_only": a, "system": b,
                      "ratio": (b / a) if a else float("inf")}
        print(f"{name:<12} {per_answer:>8.0f} {toks / read_s:>12.0f} "
              f"{toks / solve_s:>13.0f} {a:>21.3e} {b:>17.3e} "
              f"{b / a:>5.2f}x", flush=True)

    print()
    order_only = sorted(rows, key=lambda k: rows[k]["kernel_only"])
    order_sys = sorted(rows, key=lambda k: rows[k]["system"])
    print(f"  cheapest first, kernel only : {' < '.join(order_only)}")
    print(f"  cheapest first, whole system: {' < '.join(order_sys)}")

    worst = max(rows, key=lambda k: rows[k]["ratio"])
    print()
    print(f"-> CHARGING THE READER MOVES {worst} BY "
          f"{rows[worst]['ratio']:.1f}x AND THE OTHERS BY "
          f"{max(rows[k]['ratio'] for k in rows if k != worst):.2f}x.")
    if order_only == order_sys:
        print(f"   The ORDERING is unchanged, so cross-domain comparisons "
              f"survive -- but two of three\n   barely moving is exactly why "
              f"the omission lasted. A metric is not validated by the\n   "
              f"cases where its missing term is negligible.")
    else:
        print(f"   AND THE ORDERING CHANGES, so every published cross-domain "
              f"cost comparison in this\n   repo is suspect rather than merely "
              f"incomplete.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
