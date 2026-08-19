"""Turning "it depends what a wrong answer costs" into a number.

Three certificates were measured on 2026-08-19 and the north star cannot see any
of them: `usd_per_solved_above_floor` counts answers, so refusing half of them
makes the row worse however sound it is. `cost.break_even_wrong_cost` prices the
trade instead of assuming it -- what a wrong answer must cost, relative to a
right one, for the certificate to pay.

All three rows are on the honest surface, and the compute multiple is measured,
not assumed.

Run: uv run python -u scripts/break_even_wrong_cost.py
"""

from __future__ import annotations

import json
from pathlib import Path

from symbolic_ai_core.cost import break_even_wrong_cost

OUT = Path("runs/break_even_wrong_cost.json")

#: (name, accuracy answering everything, certificate coverage, compute multiple,
#:  accuracy among the certified, where the numbers come from)
ROWS = [
    ("flood, role-independent certificate", 0.679, 0.488, 1.0, 1.0,
     "runs/ambiguity_at_the_lexical_floor.json + the price-of-soundness arm; "
     "one solve plus a DFS is what the collapsing reader already spends"),
    ("scheduling, capability certificate", 0.790, 0.525, 3.07, 1.0,
     "runs/scheduling_capability_certificate.json, solves 1.00 -> 3.07"),
    ("solvency, membership certificate", 0.485, 0.485, 1.0, 1.0,
     "runs/solvency_membership_certificate.json, uncued owns arm; the check "
     "costs one sum per member against a decision that is already a sum"),
]


def main() -> None:
    out = {}
    print(f"{'certificate':<40} {'acc':>6} {'cover':>7} {'compute':>8} "
          f"{'break-even W':>13}")
    print("-" * 78)
    for name, rate, cover, mult, cert, src in ROWS:
        w = break_even_wrong_cost(rate, cover, mult, cert)
        out[name] = {"rate": rate, "coverage": cover, "compute_multiple": mult,
                     "break_even_wrong_cost": w, "source": src}
        verdict = "FREE" if w <= 0 else f"{w:.2f}x"
        print(f"{name:<40} {rate:>6.3f} {cover:>7.3f} {mult:>8.2f} "
              f"{verdict:>13}")

    print("\nW is what ONE wrong answer must cost in units of one right answer.")
    print("W <= 0 means the certificate earns at least as much utility per unit")
    print("of compute even when a wrong answer costs no more than a right one --")
    print("no trade to weigh, take it. A positive W is a real decision, and it")
    print("is the caller's, not the system's.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
