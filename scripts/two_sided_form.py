"""Derive the U, do not fit it.

`notes/findings/2026-08-19-the-survival-law-needs-monotone-corruption-...md`
showed scheduling's corruption curve is U-shaped because its claims are
opposite-signed evidence: job claims are demand (dropping them helps) and machine
claims are supply (dropping them hurts). A monotone law cannot represent that.

The temptation is to fit a two-term curve. The better move is to **derive** one,
because every quantity involved is structural and readable off the world:

An instance reads feasible iff every surviving job has a capable surviving
machine.

* A job is a constraint at all only if **both** its claims survive -- its
  ``duration`` and its ``needs_capability`` -- probability ``(1-p)^2``.
* A surviving job is unsatisfiable only if **all** ``m_j`` machines carrying its
  capability lose that capability -- probability ``p^m_j``.

Assuming independence across jobs,

    P(answer = True | p)  =  prod_j [ 1 - (1-p)^2 * p^(m_j) ]

**Nothing here is fitted.** ``m_j`` is the capability multiplicity, counted from
the claims. The form is U-shaped by construction: it tends to 1 at ``p = 0``
because no capability is lost, and to 1 at ``p = 1`` because no job survives as a
constraint, and dips where ``(1-p)^2 p^m`` is largest.

**A stated omission, which is also a prediction.** The model ignores capacity
entirely and represents only capability. At generous slack capability should be
the binding constraint and the model should hold; at tight slack capacity should
start binding and the model should degrade. That is discriminating, so both are
run.

Run: uv run python -u scripts/two_sided_form.py
"""

from __future__ import annotations

import dataclasses
import json
import random
import statistics
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.ops import build_program
from symbolic_ai_kernels import KernelRequest, get_kernel

OUT = Path("runs/two_sided_form.json")
N_CASES = 40
SLACKS = (0.30, 0.05)
RATES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
REPEATS = 4
ASP = get_kernel("asp@1")


def solve(world) -> bool:
    program, _ = build_program(world)
    req = KernelRequest(params={"program": program, "max_models": 1})
    return ASP.run(ASP.project(world, req), req).ok


def multiplicities(case) -> list[int]:
    """``m_j`` for each job: how many machines carry the capability it needs."""
    need = {}
    have: dict[str, set[str]] = {}
    for c in case.world.claims:
        if c.predicate == "needs_capability":
            ids = c.entities()
            need[ids[0]] = str(c.roles.get("capability", ""))
        elif c.predicate == "has_capability":
            ids = c.entities()
            have.setdefault(str(c.roles.get("capability", "")), set()).add(ids[0])
    return [len(have.get(cap, set())) for cap in need.values()]


def predicted(case, p: float, *, machine_needs_both: bool = True) -> float:
    """``P(answer = True | p)`` from structure alone.

    A job is a constraint only if both its claims survive: ``(1-p)^2``. It is
    unsatisfiable only if every machine carrying its capability is unusable.

    ``machine_needs_both`` is the correction the first version missed. A machine
    is usable only if it keeps **both** its ``has_capability`` and its
    ``capacity`` claim, so it survives with ``(1-p)^2`` rather than ``(1-p)``.
    With only the capability channel modelled the U is the right shape with half
    the depth -- measured 0.336 at the trough against a predicted 0.678.
    """
    per_machine_gone = (1.0 - (1.0 - p) ** 2) if machine_needs_both else p
    out = 1.0
    for m in multiplicities(case):
        out *= 1.0 - (1.0 - p) ** 2 * (per_machine_gone ** m if m else 1.0)
    return out


def main() -> None:
    print("P(answer = True) -- derived from structure, nothing fitted\n",
          flush=True)
    rows = []
    for slack in SLACKS:
        cases = [generate(s, slack=slack) for s in range(N_CASES)]
        ms = [m for c in cases for m in multiplicities(c)]
        print(f"slack {slack}: capability multiplicity m_j mean "
              f"{statistics.mean(ms):.2f}, min {min(ms)}, max {max(ms)}")
        print(f"  {'p':>5} {'measured':>9} {'derived':>9} {'err':>7}")
        errs, curve = [], []
        for p in RATES:
            yes = n = 0
            for r in range(REPEATS if 0 < p < 1 else 1):
                rng = random.Random(1300 + 29 * r)
                for c in cases:
                    w = dataclasses.replace(
                        c.world,
                        claims=tuple(x for x in c.world.claims
                                     if rng.random() >= p))
                    yes += solve(w)
                    n += 1
            meas = yes / n
            pred = statistics.mean(predicted(c, p) for c in cases)
            errs.append(abs(pred - meas))
            curve.append({"p": p, "measured": meas, "derived": pred})
            print(f"  {p:>5.1f} {meas:>9.3f} {pred:>9.3f} {pred-meas:>+7.3f}",
                  flush=True)
        lo_m = min(curve, key=lambda r: r["measured"])["p"]
        lo_p = min(curve, key=lambda r: r["derived"])["p"]
        rows.append({"slack": slack, "curve": curve,
                     "mean_abs_error": statistics.mean(errs),
                     "max_abs_error": max(errs),
                     "min_at_measured": lo_m, "min_at_derived": lo_p})
        print(f"  mean |err| {statistics.mean(errs):.3f}, max "
              f"{max(errs):.3f}; minimum at p={lo_m} measured, p={lo_p} "
              f"derived\n", flush=True)

    good, tight = rows[0], rows[1]
    print(f"generous slack {good['slack']}: mean |err| "
          f"{good['mean_abs_error']:.3f}")
    print(f"tight slack    {tight['slack']}: mean |err| "
          f"{tight['mean_abs_error']:.3f}")
    if good["mean_abs_error"] < 0.10 and good["min_at_measured"] == good["min_at_derived"]:
        print(f"\n-> THE DERIVED FORM HOLDS where capability binds, with nothing "
              f"fitted. The U is\n   not a curve family chosen to match; it "
              f"follows from two claims per job and\n   m_j machines per "
              f"capability.")
    else:
        print(f"\n-> the derived form does not hold even at generous slack; "
              f"the demand/supply\n   account is wrong rather than incomplete.")
    if tight["mean_abs_error"] > good["mean_abs_error"] * 1.4:
        print(f"   And it degrades at tight slack as predicted, because it "
              f"models capability\n   and ignores capacity.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
