"""A sweep for the bug class that capacity_gate turned out to have.

`capacity_gate` compared summed **floats** and was unsound at exact fit, refusing
schedules that provably exist. It was found by accident, while measuring
something else, and only because the benchmark had been pushed to its boundary.

That is a bug *class*, not an incident: **a decision made by comparing summed
floating-point quantities**. Every domain here has one. So rather than wait for
another accident, construct the exact-fit case in each and check the decision
against exact integer arithmetic in the domain's own smallest unit.

The hypothesis being tested is sharper than "use floats carefully": the risk is
**summation** against a threshold. Comparing one measured quantity to one posted
quantity has nothing to accumulate; comparing a *sum* does.

Run: uv run python -u scripts/exact_fit_audit.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path("runs/exact_fit_audit.json")
N = 200


def audit_solvency() -> dict:
    """Threshold set to the exact total -- the boundary the generator never hits."""
    from symbolic_ai_generators.solvency import generate

    flips = checked = 0
    example = None
    for s in range(N):
        case = generate(s)
        # the decision's own rule: largest figure known by the date, per member
        best: dict = {}
        for member, value, known in case.filings:
            if known <= case.decision_date:
                best[member] = max(best.get(member, 0.0), value)
        if not best:
            continue
        checked += 1
        float_total = 0.0
        for v in best.values():
            float_total += v
        exact_cents = sum(int(round(v * 100)) for v in best.values())
        threshold = exact_cents / 100.0
        # at exact fit the covenant is MET: total equals the threshold
        float_says = float_total >= threshold
        exact_says = exact_cents >= int(round(threshold * 100))
        if float_says != exact_says:
            flips += 1
            if example is None:
                example = {"seed": s, "float_total": repr(float_total),
                           "threshold": repr(threshold),
                           "delta": repr(float_total - threshold)}
    return {"checked": checked, "flips": flips, "example": example,
            "shape": "sum vs threshold"}


def audit_flood() -> dict:
    """A vehicle whose laden mass is exactly a posted limit."""
    from symbolic_ai_core.world import Quantity
    from symbolic_ai_generators.flood import generate

    flips = checked = 0
    for s in range(N):
        case = generate(s)
        limits, mass = [], []
        demand = None
        for c in case.world.claims:
            q = c.roles.get("value")
            if c.predicate == "load_limit" and isinstance(q, Quantity):
                limits.append(float(q.value))
            elif c.predicate == "mass" and isinstance(q, Quantity):
                mass.append(float(q.value))
            elif c.predicate == "demand" and isinstance(q, Quantity):
                demand = float(q.value)
        if demand is None or not limits or not mass:
            continue
        for m in mass:
            for lim in limits:
                checked += 1
                # construct exact fit: laden mass exactly equals the limit
                laden = m + (lim - m)
                float_says = laden <= lim
                exact_says = int(round(laden * 100)) <= int(round(lim * 100))
                if float_says != exact_says:
                    flips += 1
    return {"checked": checked, "flips": flips, "example": None,
            "shape": "one quantity vs one posted limit"}


def audit_scheduling() -> dict:
    """The fixed gate, re-checked at exact fit."""
    from symbolic_ai_generators.scheduling import generate_hard
    from symbolic_ai_generators.scheduling.ops import capacity_gate

    flips = checked = 0
    for s in range(60):
        case = generate_hard(s)
        checked += 1
        need_search, _ = capacity_gate(case.world)
        if not need_search and case.feasible:
            flips += 1
    return {"checked": checked, "flips": flips, "example": None,
            "shape": "sum vs sum (FIXED 2026-08-19)"}


def main() -> None:
    results = {"solvency": audit_solvency(), "flood": audit_flood(),
               "scheduling": audit_scheduling()}
    print(f"{'domain':<12} {'comparison shape':<34} {'checked':>8} {'flips':>7}")
    print("-" * 66)
    for name, r in results.items():
        print(f"{name:<12} {r['shape']:<34} {r['checked']:>8} {r['flips']:>7}")

    ex = results["solvency"]["example"]
    if ex:
        print(f"\n  solvency example (seed {ex['seed']}):")
        print(f"    float total {ex['float_total']}")
        print(f"    threshold   {ex['threshold']}")
        print(f"    difference  {ex['delta']}")

    print()
    summed = [n for n, r in results.items() if "sum vs" in r["shape"]]
    single = [n for n, r in results.items() if "sum vs" not in r["shape"]]
    if results["solvency"]["flips"] and not results["flood"]["flips"]:
        print(f"-> THE RISK IS SUMMATION, NOT FLOATING POINT. "
              f"{results['solvency']['flips']} of "
              f"{results['solvency']['checked']} solvency decisions flip\n   at "
              f"exact fit, where a sum of two-decimal amounts is compared with a "
              f"threshold;\n   flood flips {results['flood']['flips']} of "
              f"{results['flood']['checked']}, because it compares ONE measured "
              f"quantity with ONE\n   posted limit and has nothing to "
              f"accumulate.")
        print(f"\n   That is a rule applicable by inspection: a decision "
              f"comparing a SUM to a\n   threshold needs exact arithmetic in the "
              f"domain's smallest unit. Domains with\n   that shape here: "
              f"{', '.join(summed)}. Without it: {', '.join(single)}.")
        print(f"\n   Solvency is LATENT rather than broken -- its threshold is "
              f"random, so it lands on\n   the boundary with probability ~0. But "
              f"it is described in this repo as the\n   TUNABLE-MARGIN domain, "
              f"and any sweep to exact fit fires it.")
    elif not results["solvency"]["flips"]:
        print(f"-> no flips anywhere at exact fit, so the class is confined to "
              f"the gate that had it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
