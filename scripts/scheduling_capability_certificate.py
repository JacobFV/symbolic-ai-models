"""The worst channel of the day, answered by the other response.

`has_capability` is multi-valued: nothing corroborates it, `evidence_conflict`
fires 0.000, and one admitted sentence costs **0.210** accuracy with all 42
failures in the **unsound** direction. This morning's conclusion -- that a
multi-valued channel leaves only fixing the reader -- was too strong.
Insensitivity needs no second source and no arity.

Four arms, 200 cases at the default regime:

- **clean** -- default distractors, the published surface;
- **hard machine** -- the spurious ``has_capability``;
and each with the certificate on, reporting coverage, soundness and the solves
it spends, because a check that costs k+1 solves has to be priced and not just
scored.

Run: uv run python -u scripts/scheduling_capability_certificate.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.certificate import (
    certifies_capability_insensitive)
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.scheduling.surface import render_observation

sys.path.insert(0, str(Path(__file__).parent))
from hard_regime_milestone import solve_world  # noqa: E402

OUT = Path("runs/scheduling_capability_certificate.json")
N = 200


def run(hard) -> dict:
    rows = []
    t0 = time.perf_counter()
    for s in range(N):
        case = generate(s)
        text = render_observation(case, variants=4,
                                  hard_distractors=hard).text
        world = read_signature(text)
        got = solve_world(world)[0]
        cert, spent = certifies_capability_insensitive(world, solve_world)
        rows.append({"truth": case.feasible, "got": got, "cert": cert,
                     "spent": spent})
    wall = time.perf_counter() - t0

    n = len(rows)
    wrong = [r for r in rows if r["got"] != r["truth"]]
    certified = [r for r in rows if r["cert"]]
    wrong_cert = [r for r in certified if r["got"] != r["truth"]]
    infeasible = [r for r in rows if r["got"] is False]
    feasible = [r for r in rows if r["got"] is True]
    return {
        "n": n,
        "accuracy": 1 - len(wrong) / n,
        "false_feasible": sum(1 for r in wrong if r["got"] and not r["truth"]),
        "coverage": len(certified) / n,
        "accuracy_certified": (1 - len(wrong_cert) / len(certified)
                               if certified else float("nan")),
        "wrong_certified": len(wrong_cert),
        "coverage_feasible": (statistics.mean(r["cert"] for r in feasible)
                              if feasible else float("nan")),
        "free_share": len(infeasible) / n,
        "mean_solves": statistics.mean(r["spent"] for r in rows),
        "ms_per_case": wall / n * 1000,
    }


def main() -> None:
    out = {}
    print(f"{'surface':<22} {'acc':>6} {'falseF':>7} {'cover':>7} "
          f"{'acc|cert':>9} {'wrong|c':>8} {'cover|feas':>11} {'solves':>7} "
          f"{'ms':>7}")
    print("-" * 92)
    for label, hard in (("clean", False), ("hard machine", "machine")):
        r = run(hard)
        out[label] = r
        print(f"{label:<22} {r['accuracy']:>6.3f} {r['false_feasible']:>7d} "
              f"{r['coverage']:>7.3f} {r['accuracy_certified']:>9.3f} "
              f"{r['wrong_certified']:>8d} {r['coverage_feasible']:>11.3f} "
              f"{r['mean_solves']:>7.2f} {r['ms_per_case']:>7.2f}")

    h = out["hard machine"]
    print(f"\nOf the coverage, {h['free_share']:.3f} is the MONOTONE HALF -- an "
          "infeasible reading,\ncertified with no extra solve, because deleting "
          "a capability cannot rescue it.")
    print("The rest costs one solve per capability claim.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
