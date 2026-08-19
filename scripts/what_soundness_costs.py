"""What soundness costs, priced in the instrument built to price certification.

Every certificate in this repo is **sound**: it never declares valid for an
answer that moved. That has never been priced, and there is now something to
price it with. The derived margin flags **5.47%** of answers where only **0.78%**
actually moved, so an oracle would reach `aim× = 1/0.0078 = 128×` against the
margin's 18×. The gap is the cost of never being wrong.

Relaxing the margin by a factor `alpha` -- flag iff `delta >= alpha × slack` --
buys fewer recomputes and serves some wrong answers. Under `Targeting`,

    aim_x = (rate_targeted - base) / (flagged x (1 - base))

and the numerator loses only the answers that moved *inside the relaxed band*,
which is a small fraction of a small fraction, while the denominator falls
linearly in `flagged`. So **aim× should rise with unsoundness**.

**This is not a proposal to ship an unsound certificate.** It is a test of the
instrument: if `aim×` alone ranks an unsound arm above a sound one, then `aim×`
must never be read without the `rate` column beside it, and `Targeting` should
say so itself rather than leaving a reader to notice.

Run: uv run python -u scripts/what_soundness_costs.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from scripts.cert_maintenance_13f import NEW_FILE, OLD_FILE, load_store
from symbolic_ai_core.cost import (Capability, System, Targeting,
                                   cpu_component, ledger, ledger_table)
from symbolic_ai_core.runtime.certificate import Counted

OUT = Path("runs/what_soundness_costs.json")
SEED = 20260818
M_KEYS = 5000
K = 100
ALPHAS = (1.0, 1.5, 2.0, 4.0, 8.0, 16.0, 64.0)


def main() -> None:
    rng = random.Random(SEED)
    old = load_store(OLD_FILE)
    new = load_store(NEW_FILE)
    secs = sorted({k[1] for k in set(old) & set(new) if k[0] == "holders"})
    keys = [("holders", s) for s in rng.sample(secs, M_KEYS)]

    moved, slack, delta = {}, {}, {}
    for k in keys:
        c_old = len(old[k])
        c_new = len(new.get(k, frozenset()))
        moved[k] = (c_old >= K) != (c_new >= K)
        slack[k] = Counted(c_old).at_least(K)[1].slack
        delta[k] = len(old[k] ^ new.get(k, frozenset()))

    n = len(keys)
    f_stale = sum(moved.values()) / n
    base = 1.0 - f_stale
    read_set_flagged = sum(1 for k in keys if delta[k] > 0) / n
    print(f"{n:,} queries. {f_stale:.2%} of answers actually moved; a read set "
          f"flags {read_set_flagged:.2%};\nan oracle flagging exactly the movers "
          f"would reach aim {1/f_stale:,.1f}x.\n")

    def arm(flagged_keys: set) -> tuple[float, float, float]:
        """flagged share, quality after maintenance, aim x."""
        flagged = len(flagged_keys) / n
        wrong = sum(1 for k in keys if moved[k] and k not in flagged_keys) / n
        rate = 1.0 - wrong
        blind = base + flagged * (1.0 - base)
        aim = (rate - base) / (blind - base) if blind > base else float("nan")
        return flagged, rate, aim

    hdr = (f"{'policy':<28} {'flagged':>9} {'wrong served':>13} {'rate':>8} "
           f"{'aim x':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for a in ALPHAS:
        fk = {k for k in keys if delta[k] >= a * slack[k]}
        flagged, rate, aim = arm(fk)
        sound = all(k in fk for k in keys if moved[k])
        rows[f"alpha={a:g}"] = {"alpha": a, "flagged": flagged, "rate": rate,
                                "wrong": 1 - rate, "aim": aim, "sound": sound}
        print(f"{'margin, alpha=' + f'{a:g}':<28} {flagged:>8.2%} "
              f"{1-rate:>12.3%} {rate:>8.4f} {aim:>8.1f}x"
              f"{'   SOUND' if sound else ''}")
    # --- a SECOND sound bound, much tighter. |delta count| rather than
    # |old XOR new|: an add and a remove cancel in a count and do not cancel in
    # a symmetric difference. Still sound, because |count(B)-count(A)| is exactly
    # what the threshold cares about; still loose, because a rise of +1000 while
    # already above the threshold cannot flip the answer and its magnitude
    # exceeds the slack anyway.
    #
    # This is a COUNTERFACTUAL flagged rate, not a deployable certificate: on two
    # snapshots |delta count| costs the same as recomputing. It is deployable
    # only when the update stream supplies signed adds and removes per key --
    # the Delta type parked in notes/decisions/2026-08-18-not-building-a-delta-...
    dcount = {k: abs(len(new.get(k, frozenset())) - len(old[k])) for k in keys}
    fk_mag = {k for k in keys if dcount[k] >= slack[k]}
    flagged, rate, aim = arm(fk_mag)
    sound_mag = all(k in fk_mag for k in keys if moved[k])
    rows["magnitude bound"] = {"alpha": None, "flagged": flagged, "rate": rate,
                               "wrong": 1 - rate, "aim": aim,
                               "sound": sound_mag}
    print(f"{'|delta count| (sound, tighter)':<28} {flagged:>8.2%} "
          f"{1-rate:>12.3%} {rate:>8.4f} {aim:>8.1f}x"
          f"{'   SOUND' if sound_mag else '   UNSOUND -- BUG'}")

    fk_oracle = {k for k in keys if moved[k]}
    flagged, rate, aim = arm(fk_oracle)
    rows["oracle"] = {"alpha": None, "flagged": flagged, "rate": rate,
                      "wrong": 1 - rate, "aim": aim, "sound": True}
    print(f"{'ORACLE (flags exactly movers)':<28} {flagged:>8.2%} "
          f"{1-rate:>12.3%} {rate:>8.4f} {aim:>8.1f}x   SOUND")

    mag = rows["magnitude bound"]
    xor = rows["alpha=1"]
    orc_flagged = f_stale
    print(f"\nthe 8.2x decomposes:")
    print(f"  XOR bound        flags {xor['flagged']:>6.2%}  "
          f"({xor['flagged']/orc_flagged:>5.1f}x the oracle)")
    print(f"  |delta count|    flags {mag['flagged']:>6.2%}  "
          f"({mag['flagged']/orc_flagged:>5.1f}x the oracle)")
    print(f"  oracle           flags {orc_flagged:>6.2%}")
    print(f"\n  of the {xor['flagged']/orc_flagged:.1f}x total looseness, "
          f"{xor['flagged']/mag['flagged']:.1f}x is the XOR over-counting a "
          f"count\n  and {mag['flagged']/orc_flagged:.1f}x is what no sound "
          f"bound can remove without computing the answer.")

    sound_rows = [r for r in rows.values() if r["sound"] and r["alpha"]]
    best_sound = max(sound_rows, key=lambda r: r["aim"])
    best_any = max((r for r in rows.values() if r["alpha"]),
                   key=lambda r: r["aim"])
    print(f"\nbest SOUND arm: alpha={best_sound['alpha']:g} at "
          f"{best_sound['aim']:.1f}x")
    print(f"best arm on aim alone: alpha={best_any['alpha']:g} at "
          f"{best_any['aim']:.1f}x, serving "
          f"{best_any['wrong']:.3%} of answers wrong")
    if best_any["aim"] > best_sound["aim"]:
        print(f"\n  -> aim x RANKS AN UNSOUND ARM FIRST, by "
              f"{best_any['aim']/best_sound['aim']:.2f}x. The metric can be "
              f"gamed by\n     unsoundness and must never be read without the "
              f"rate column beside it.")
    else:
        print(f"\n  -> aim x prefers the sound arm; the metric is "
              f"self-protecting here.")

    # The ledger reads both columns, which is the point.
    sysm = (cpu_component("revalidation", 1e7, source="digest compare"),)
    ledgers = []
    # The oracle is deliberately NOT a ledger row. It is a bound, not a system:
    # flagging exactly the movers requires knowing which answers moved, which is
    # the thing being certified. A ledger of systems that contains an oracle
    # ranks a thing nobody can build above the things they can.
    for name in ("alpha=1", "alpha=1.5", "alpha=8", "alpha=16", "alpha=64"):
        r = rows[name]
        blind = base + r["flagged"] * (1.0 - base)
        ledgers.append(ledger(
            System(name=name, components=sysm),
            Capability(unit="maintained answer", rate=r["rate"], floor=base,
                       n=n, tokens_per_attempt=1.0,
                       source="scripts/what_soundness_costs.py"),
            targeting=Targeting(escalated=r["flagged"], rate_base=base,
                                rate_targeted=r["rate"], rate_blind=blind,
                                escalated_usd_per_attempt=277.5 / 1e9 / 3600
                                * 0.02)))
    print()
    print(ledger_table(ledgers))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "n": n, "f_stale": f_stale,
                               "read_set_flagged": read_set_flagged,
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
