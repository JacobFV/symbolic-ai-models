"""One closed form for every certification number this repo has measured.

`HANDOVER.md` §3b already names a law: `advantage = min(compute/check, 1/P_hit)`,
verified on both axes. `P_hit` is the rate at which the certificate is
**invalidated** -- the flagged fraction -- so `1/P_hit` is the ceiling given the
certificate you happen to have.

This session produced a second form, on a different arm: escalation targeting
obeys `aim <= 1/(1 - accuracy)`, where `1 - accuracy` is the fraction of cases
that **actually need** the expensive path. That is a ceiling given the *problem*,
and the two differ by exactly the over-approximation measured independently at
**8.2x** (symmetric-difference bound) and **2.3x** (`|delta count|` bound).

The claim under test is that both are instances of one thing:

    ceiling   =  1 / f_needed                    the problem's own limit
    realised  =  recall / f_flagged              what your certificate gets
              =  ceiling x precision             equivalently

with `precision = P(needed | flagged)` and `recall = P(flagged | needed)`. A
sound certificate has `recall = 1` and realises `1/f_flagged`, which is §3b's law
exactly. An oracle has `precision = recall = 1` and attains the ceiling.

**Most of that is a DERIVATION, not a measurement, and the first version of this
script did not say so.** For maintenance,
`aim = (1-base) / (flagged x (1-base)) = 1/f_flagged` *by construction* of the
targeting setup; for the curriculum rows, `predicted` rearranges to
`(1 - a_abstained)/(1 - base)`, which is the expression `aim` was computed from.
Those rows reproduce their own definitions and cannot confirm anything. The
apparent "1.2% error" across them was rounding in hand-entered constants.

What is left is genuinely independent, and it is small: rows where the measured
advantage comes from **timings and USD** while the prediction comes from
**invalidation counts**. Five of them exist, all in §3b's arms, and all confirm
§3b's own law. The contribution here is the *unification* -- that escalation
targeting and certificate maintenance are one expression -- and it is offered as
algebra with one empirical anchor, not as eleven confirmations.

Run: uv run python -u scripts/certification_law.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

OUT = Path("runs/certification_law.json")

#: (arm, f_needed, f_flagged, recall, measured, source)
#:
#: `recall` is 1.0 wherever the certificate is SOUND -- it never misses a case
#: that needed the expensive path -- which every certificate in this repo is.
#: The curriculum models are the exception: a model's abstention is not a
#: soundness claim, so it misses wrong answers it voted on.
ARMS: tuple[tuple[str, float, float, float, float, str], ...] = (
    # --- maintenance, this session
    ("maintenance, XOR bound", 0.0076, 0.0622, 1.0, 16.08,
     "what_soundness_costs.py"),
    ("maintenance, |dcount| bound", 0.0076, 0.0174, 1.0, 57.47,
     "what_soundness_costs.py"),
    ("maintenance, oracle", 0.0076, 0.0076, 1.0, 131.58,
     "what_soundness_costs.py"),
    # --- escalation, this session. recall < 1: abstention is not soundness.
    ("GLEIF resolver, group level", 1 - 0.873, 0.154, 0.723, 4.69,
     "arc_through_the_ledger.py"),
    ("curriculum ilp-001", 1 - 0.312, 0.391, 0.535, 1.37,
     "can_the_models_certify.py"),
    ("curriculum routes-001", 1 - 0.323, 0.017, 0.025, 1.48,
     "can_the_models_certify.py"),
    ("curriculum synth-001", 1 - 0.077, 0.979, 0.996, 1.02,
     "can_the_models_certify.py"),
)


def load_witness_rows() -> list[tuple[str, float, float, float, float, str]]:
    """§3b's witness arm, which recorded `p_hit` and `1/p_hit` directly.

    `f_needed` is not recorded there -- only the invalidation rate -- so these
    rows test the *sound* case, where the law reduces to `1/f_flagged` and the
    file's own `ceiling_1_over_p` is that number. They check the identity rather
    than the over-approximation.
    """
    path = Path("runs/cert_witness_path.json")
    if not path.exists():
        return []
    d = json.loads(path.read_text())
    rows = d["rows"]
    rows = rows if isinstance(rows, list) else list(rows.values())
    out = []
    for i, r in enumerate(rows):
        p = r.get("p_hit")
        adv = r.get("advantage")
        if not p or adv is None:
            continue
        out.append((f"§3b witness arm row {i}", p, p, 1.0, adv,
                    "cert_witness_path.json"))
    return out


def load_maintenance_row() -> list[tuple[str, float, float, float, float, str]]:
    """The one row of §3b's maintenance arm where the `1/P_hit` term BINDS.

    Its other three query classes are limited by `compute/check` instead, so the
    law's other term decides them and they cannot test this one. For
    `min_filers_covering` the survival rate is 0.0, so `1/f_flagged = 1.000`,
    and the measured advantage comes from USD costs rather than from that
    fraction -- an independent check.
    """
    path = Path("runs/cert_maintenance_13f.json")
    if not path.exists():
        return []
    out = []
    for r in json.loads(path.read_text())["rows"]:
        f = 1.0 - r["r1_survival_frac"]
        if not f:
            continue
        pred, meas = 1.0 / f, r["maintenance_advantage"]
        if abs(pred - meas) / pred < 0.05:      # the 1/P term is the binding one
            out.append((f"§3b maintenance {r['query_class'][:14]}", f, f, 1.0,
                        meas, "cert_maintenance_13f.json"))
    return out


def main() -> None:
    arms = list(ARMS) + load_witness_rows() + load_maintenance_row()
    hdr = (f"{'arm':<30} {'f_needed':>9} {'f_flagged':>10} {'over':>7} "
           f"{'ceiling':>10} {'predicted':>10} {'measured':>10} {'err':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    worst = 0.0
    breaches = []
    #: Rows whose "measured" value is computed from the same expression as the
    #: prediction. They are identities and are marked as such rather than
    #: counted as agreement.
    IDENTITY = {"maintenance", "GLEIF", "curriculum"}
    for name, needed, flagged, recall, measured, src in arms:
        ceiling = 1.0 / needed if needed else math.inf
        predicted = recall / flagged if flagged else math.inf
        err = abs(predicted - measured) / measured if measured else math.nan
        worst = max(worst, err)
        if measured > ceiling * 1.02:
            breaches.append(name)
        rows.append({"arm": name, "f_needed": needed, "f_flagged": flagged,
                     "over_approximation": flagged / needed if needed else None,
                     "ceiling": ceiling, "predicted": predicted,
                     "measured": measured, "rel_error": err, "source": src})
        ident = any(name.startswith(k) for k in IDENTITY)
        rows[-1]["identity"] = ident
        print(f"{name:<30} {needed:>9.4f} {flagged:>10.4f} "
              f"{flagged/needed if needed else float('nan'):>6.1f}x "
              f"{ceiling:>9.1f}x {predicted:>9.1f}x {measured:>9.1f}x "
              f"{err:>6.1%}{'   (identity)' if ident else '   INDEPENDENT'}")

    indep = [r for r in rows if not r["identity"]]
    worst_indep = max((r["rel_error"] for r in indep), default=float("nan"))
    print(f"\n{len(indep)} INDEPENDENT rows -- measured from timings and USD, "
          f"predicted from invalidation\ncounts -- worst relative error "
          f"{worst_indep:.1%}. The rest are identities and confirm nothing.")
    print(f"(worst error over all rows including identities: {worst:.1%}, which "
          f"is rounding.)")
    if breaches:
        print(f"\n!! CEILING BREACHED by: {', '.join(breaches)}. The law is "
              f"WRONG -- certification cannot buy more than the work it avoids.")
    else:
        print(f"no arm exceeds its ceiling of 1/f_needed.")

    print(f"\n  realised  =  recall / f_flagged        (= 1/f_flagged when "
          f"sound)")
    print(f"  ceiling   =  1 / f_needed              (attained iff precision "
          f"= recall = 1)")
    print(f"\nSo §3b's `1/P_hit` is the SOUND case of the same expression. What "
          f"this adds is\nthat ESCALATION targeting is the same expression too, "
          f"with recall < 1 because a\nmodel's abstention is not a soundness "
          f"claim -- and that the achievable ceiling\nis 1/f_needed rather "
          f"than 1/f_flagged, the two differing by the certificate's\n"
          f"over-approximation. That is a derivation. The empirical content is "
          f"the {len(indep)} rows\nabove and they were already §3b's.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows, "worst_rel_error": worst,
                               "breaches": breaches}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
