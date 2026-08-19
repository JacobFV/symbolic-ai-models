"""Does the structural back-off trade accuracy against certifiability?

`notes/findings/2026-08-18-a-model-can-only-certify-to-the-extent-it-is-usually-right.md`
found that certification value obeys

    aim  =  (1 - a_abstained) / (1 - base)      and therefore  aim <= 1/(1 - base)

and noted a consequence nobody had priced: the ceiling is attained only when
abstained positions score **zero**, so strengthening the back-off -- which this
repo did deliberately, and which raised accuracy -- should *lower* certifiability.

Working the algebra, that reasoning is suspect. Turning the back-off **off**
lowers `a_abstained` (numerator up, aim up) *and* lowers `base` (denominator up,
aim down). Which dominates is a magnitude question, not a sign question, and the
back-off is attached at **every hidden node** rather than only abstained ones --
`symbolic.py` records `ruleinduce` voting on every node at 0.192 and scoring
0.076 before the change, against 0.329 now. So the base effect may simply win and
there may be no trade at all.

If instead aim rises while accuracy falls, the trade is real and
`ledger_table`'s `TARGETING REGIME` warning should fire on the pair -- the guard
built last cycle doing its job on a real comparison rather than a constructed
one.

`synth-001` is omitted: ~20 minutes to fit, and its 1.02x is already understood
as a consequence of its 7.7% base accuracy.

Run: uv run python -u scripts/backoff_vs_certifiability.py
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.can_the_models_certify import measure
from symbolic_ai_core.cost import (Capability, System, Targeting,
                                   cpu_component, ledger, ledger_table)

OUT = Path("runs/backoff_vs_certifiability.json")
MODELS = ("routes-001", "ruleinduce-001", "ilp-001", "syllogism-001")


def main() -> None:
    hdr = (f"{'model':<18} {'back-off':>9} {'label_acc':>10} "
           f"{'acc|voted':>10} {'acc|abst':>9} {'aim':>7} {'ceiling':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for name in MODELS:
        pair = {}
        for on in (True, False):
            try:
                r = measure(name, structural_fallback=on)
            except Exception as exc:                 # noqa: BLE001
                print(f"{name:<18} {'on' if on else 'off':>9} skipped: "
                      f"{type(exc).__name__}: {exc}")
                continue
            pair["on" if on else "off"] = r
            if r["status"] != "measured":
                print(f"{name:<18} {'on' if on else 'off':>9} {r['status']}")
                continue
            print(f"{name:<18} {'on' if on else 'off':>9} "
                  f"{r['label_acc']:>10.3f} {r['acc_voted']:>10.3f} "
                  f"{r['acc_abstained']:>9.3f} {r['aim']:>6.2f}x "
                  f"{r['ceiling']:>8.2f}x", flush=True)
        if "on" in pair and "off" in pair:
            rows.append({"model": name, **{f"{k}_{m}": pair[m].get(k)
                                          for m in ("on", "off")
                                          for k in ("label_acc", "acc_voted",
                                                    "acc_abstained", "aim",
                                                    "ceiling", "status")}})
        print(flush=True)

    usable = [r for r in rows
              if r["status_on"] == "measured" and r["status_off"] == "measured"]
    if not usable:
        print("no model measurable in both arms")
        return

    both = [r for r in usable
            if r["label_acc_on"] > r["label_acc_off"] and r["aim_on"] > r["aim_off"]]
    traded = [r for r in usable
              if r["label_acc_on"] > r["label_acc_off"] and r["aim_on"] < r["aim_off"]]
    print(f"back-off wins BOTH accuracy and aim: {len(both)}/{len(usable)}")
    print(f"back-off trades accuracy for aim:    {len(traded)}/{len(usable)}")
    if len(both) >= len(usable) - len(traded) and not traded:
        print("\n-> NO TRADE. The back-off is better on both axes, so the "
              "consequence recorded\n   in 3t -- that raising accuracy lowers "
              "certifiability -- is FALSE as stated.\n   Lowering a_abstained "
              "does raise aim, and lowering base lowers it more.")
    elif traded:
        print("\n-> THE TRADE IS REAL for "
              f"{', '.join(r['model'] for r in traded)}. aim prefers the arm "
              "that answers\n   worse, which is exactly what the "
              "TARGETING REGIME guard exists to catch.")

    # Put one traded pair through the ledger so the guard is exercised on real
    # rows rather than on a constructed test fixture.
    sysm = (cpu_component("symbolic", 1e7, source="rule-based, CPU"),)
    ledgers = []
    for r in usable:
        for m in ("on", "off"):
            base = r[f"label_acc_{m}"]
            aa = r[f"acc_abstained_{m}"]
            # flagged cancels in aim; any consistent share reproduces it.
            flagged = 0.2
            targeted = base + flagged * (1.0 - aa)
            blind = base + flagged * (1.0 - base)
            if not (0.0 <= targeted <= 1.0 and blind > base):
                continue
            ledgers.append(ledger(
                System(name=f"{r['model'][:12]} bo-{m}", components=sysm),
                Capability(unit="label", rate=base, floor=0.143, n=5233,
                           tokens_per_attempt=1.0,
                           source="scripts/backoff_vs_certifiability.py"),
                targeting=Targeting(escalated=flagged, rate_base=base,
                                    rate_targeted=targeted, rate_blind=blind,
                                    escalated_usd_per_attempt=1e-9)))
    if ledgers:
        print()
        print(ledger_table(ledgers))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
