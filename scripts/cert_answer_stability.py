"""A certificate invalidates when its inputs move. An answer often does not.

The certificate arm (`HANDOVER.md` §3b) measured **soundness** on every row --
`false_survivals = 0`, a certificate never claims valid for an answer that moved
-- and never measured **precision**: how many of its invalidations were
*unnecessary*, because the inputs changed and the answer did not.

That number now matters, because `symbolic_ai_core/cost.py` has a `Targeting`
denominator. Maintenance is a targeting problem in exactly the escalation sense:

    base      recompute nothing; quality is the fraction of answers still right
    targeted  recompute what the certificate flags; quality is 1.0, it is sound
    blind     recompute the same SHARE at random

For a sound certificate the algebra collapses to

    aim_x  =  1 / f_flagged        and a minimal certificate would reach  1 / f_stale

so **over-approximation destroys targeting value in direct proportion**, and the
6,591x over-read measured on shortest path has a price nobody has computed.

**The sharper claim under test.** Expensive computations tend to produce *coarse*
answers -- a small integer, a boolean -- which are insensitive to churn in their
inputs. If that holds, over-approximation costs most exactly where the
computation is dearest, i.e. the recording mechanism is worst precisely where a
certificate is worth having.

ANCHOR: `is_widely_held` has a known **bound**. §3b's stability-margin row
survives 93.62%, and that margin certificate is itself *sound* -- it declares
valid only when the answer provably cannot have moved -- so 6.38% is an **upper
bound** on `f_stale`, not an estimate of it. `f_stale > 6.38%` would mean the
margin certificate declared valid for an answer that moved, which is unsoundness
and must stop the run. A value well *below* it means the margin over-approximates
too, which is a finding rather than a fault.

The first version of this script asserted equality there and read the resulting
disagreement as indicting itself. It is the difference between a bound and an
estimate, and it is the same confusion this repo has recorded before.

Run: uv run python -u scripts/cert_answer_stability.py
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Callable, Hashable, Mapping

from scripts.cert_maintenance_13f import (BASE, NEW_FILE, OLD_FILE, load_store,
                                          q_holder_count, q_min_cover,
                                          q_overlap, q_widely_held)
from symbolic_ai_core.cost import (Capability, System, Targeting,
                                   cpu_component, ledger, ledger_table)
from symbolic_ai_core.runtime.certificate import (Counted, Sensitivity,
                                                  moved_elements)

OUT = Path("runs/cert_answer_stability.json")
SEED = 20260818
N = 5000
N_SOLVER = 300
#: §3b: the margin row survives 93.62%, and the margin certificate is sound, so
#: this is an UPPER BOUND on f_stale and not a target to reproduce.
ANCHOR_WIDELY_HELD_STALE_MAX = 0.0638


def read_set(kind: str, keys: tuple[Hashable, ...]) -> tuple[Hashable, ...]:
    return keys


def measure(name: str, cases: list[tuple[tuple[Hashable, ...], Callable]],
            old: Mapping, new: Mapping, changed: set,
            sensitivity: Callable[[tuple, Mapping], Sensitivity] | None = None,
            ) -> dict[str, Any]:
    """f_flagged, f_stale, and what the gap costs in targeting terms.

    ``sensitivity`` adds the third arm: a margin **derived from the numeric
    intermediate the computation already produced**, rather than from equality
    of the inputs. Its false survivals are checked and must be zero -- a loose
    margin costs money, an unsound one silently serves a wrong answer.
    """
    t0 = time.perf_counter()
    flagged = stale = both = 0
    sens_flagged = sens_false = 0
    for keys, compute in cases:
        f = any(k in changed for k in keys)
        s = compute(old) != compute(new)
        flagged += f
        stale += s
        both += f and s
        if s and not f:
            raise AssertionError(
                f"{name}: an answer moved with no key change -- the read set is "
                "UNSOUND, which is a different and worse failure than being "
                "loose, and it must stop the run")
        if sensitivity is not None:
            survives = sensitivity(keys, old).survives(
                moved_elements(keys, old, new))
            sens_flagged += not survives
            if survives and s:
                sens_false += 1
    n = len(cases)
    ff, fs = flagged / n, stale / n
    row = {"query_class": name, "n": n,
           "f_flagged": ff, "f_stale": fs,
           "precision": (both / flagged) if flagged else float("nan"),
           "over_approximation": (ff / fs) if fs else float("inf"),
           "aim_realised": (1.0 / ff) if ff else float("inf"),
           "aim_ceiling": (1.0 / fs) if fs else float("inf"),
           "seconds": time.perf_counter() - t0}
    if sensitivity is not None:
        if sens_false:
            raise AssertionError(
                f"{name}: the derived margin survived {sens_false} answers that "
                "MOVED. An unsound margin is worse than no margin and this must "
                "stop the run.")
        sf = sens_flagged / n
        row.update(derived_flagged=sf, derived_false_survivals=0,
                   derived_over=(sf / fs) if fs else float("inf"),
                   derived_aim=(1.0 / sf) if sf else float("inf"),
                   recovered=(ff / sf) if sf else float("inf"))
    tail = ""
    if sensitivity is not None:
        tail = (f"  | DERIVED flagged {row['derived_flagged']:>7.2%}  over "
                f"{row['derived_over']:>6.1f}x  recovers "
                f"{row['recovered']:>5.1f}x")
    print(f"{name:<26} flagged {ff:>7.2%}  stale {fs:>7.2%}  "
          f"over {row['over_approximation']:>7.1f}x  "
          f"aim {row['aim_realised']:>5.2f}x of {row['aim_ceiling']:>7.2f}x{tail}",
          flush=True)
    return row


def main() -> None:
    rng = random.Random(SEED)
    print(f"loading two filed snapshots ...", flush=True)
    old = load_store(OLD_FILE)
    new = load_store(NEW_FILE)
    changed = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
    print(f"  {len(old):,} -> {len(new):,} keys, {len(changed):,} moved\n",
          flush=True)

    secs = sorted({k[1] for k in set(old) & set(new) if k[0] == "holders"})
    filers = sorted({k[1] for k in set(old) & set(new) if k[0] == "portfolio"})
    print(f"{len(secs):,} securities and {len(filers):,} filers in both\n",
          flush=True)

    rows = []
    pick = [rng.choice(secs) for _ in range(N)]
    def count_margin(keys: tuple, store: Mapping) -> Sensitivity:
        """A raw count has slack 0 -- every change moves it -- so the derived
        margin degrades to exactly the read-set certificate. That is the
        correct answer for this query, not a failure to find one."""
        return Counted(len(store.get(keys[0], frozenset()))).raw()[1]

    rows.append(measure("holder_count",
                        [((("holders", s),), q_holder_count(s)) for s in pick],
                        old, new, changed, sensitivity=count_margin))
    def widely_held_margin(keys: tuple, store: Mapping) -> Sensitivity:
        """The margin, DERIVED. `q_widely_held` computes `len(holders) >= 100`,
        so the count is an intermediate it already produced; only the discarding
        of it was ever the problem."""
        n = len(store.get(keys[0], frozenset()))
        return Counted(n).at_least(100)[1]

    rows.append(measure("is_widely_held(k=100)",
                        [((("holders", s),), q_widely_held(s, 100))
                         for s in pick],
                        old, new, changed, sensitivity=widely_held_margin))
    pairs = [(rng.choice(filers), rng.choice(filers)) for _ in range(N)]
    rows.append(measure("portfolio_overlap",
                        [((("portfolio", a), ("portfolio", b)),
                          q_overlap(a, b)) for a, b in pairs],
                        old, new, changed))
    covers = [tuple(rng.sample(secs, 12)) for _ in range(N_SOLVER)]
    rows.append(measure("min_filers_covering(12)",
                        [(tuple(("holders", s) for s in c), q_min_cover(c))
                         for c in covers],
                        old, new, changed))

    # --- the anchor. A number already on disk must reproduce.
    wh = next(r for r in rows if r["query_class"].startswith("is_widely_held"))
    ok = wh["f_stale"] <= ANCHOR_WIDELY_HELD_STALE_MAX + 1e-9
    print(f"\nANCHOR is_widely_held: f_stale {wh['f_stale']:.4%} against §3b's "
          f"margin bound of {ANCHOR_WIDELY_HELD_STALE_MAX:.4%} -- "
          f"{'HOLDS' if ok else 'VIOLATED: the margin certificate is UNSOUND'}")
    if not ok:
        raise AssertionError("margin certificate declared valid for a moved "
                             "answer; that is unsoundness, not looseness")
    print(f"  and the margin certificate itself over-approximates by "
          f"{ANCHOR_WIDELY_HELD_STALE_MAX / max(1e-9, wh['f_stale']):.1f}x -- "
          f"the rung §3b called\n  'the one the recording mechanism cannot "
          f"produce' is loose too, just far less so.")

    print(f"\nis over-approximation worst where the computation is dearest?\n")
    print(f"  {'query class':<26} {'compute':>10} {'over-approx':>12}")
    #: §3b, compute ns per answer, for the ordering only
    COMPUTE_NS = {"holder_count": 748, "is_widely_held(k=100)": 739,
                  "portfolio_overlap": 6048,
                  "min_filers_covering(12)": 6_745_104}
    for r in sorted(rows, key=lambda r: COMPUTE_NS[r["query_class"]]):
        print(f"  {r['query_class']:<26} {COMPUTE_NS[r['query_class']]:>9,}ns "
              f"{r['over_approximation']:>11.1f}x")

    # --- and into the ledger, using the denominator built for exactly this.
    sysm = System(name="read-set certificate", components=(
        cpu_component("revalidation", 1e7, source="digest comparison"),))
    ledgers = []
    arms = []
    for r in rows:
        arms.append((r["query_class"][:22], r["f_flagged"], r))
        if "derived_flagged" in r and r["derived_flagged"] < r["f_flagged"]:
            arms.append((("+margin " + r["query_class"])[:22],
                         r["derived_flagged"], r))
    for r in rows:
        base = 1.0 - r["f_stale"]
        blind = base + r["f_flagged"] * (1.0 - base)
        # The certificate is SOUND, so recomputing everything it flags leaves
        # every answer correct: rate 1.0. The floor is recomputing nothing,
        # which leaves `base` of them correct. above_floor is therefore exactly
        # f_stale -- the answers maintenance actually had to save. Passing the
        # same number as rate and floor, as a first version did, makes the
        # column read inf by construction rather than by measurement.
        pass
    for label, flagged, r in arms:
        base = 1.0 - r["f_stale"]
        blind = base + flagged * (1.0 - base)
        ledgers.append(ledger(
            System(name=label, components=sysm.components),
            Capability(unit="maintained answer", rate=1.0, floor=base,
                       n=r["n"], tokens_per_attempt=1.0,
                       source="scripts/cert_answer_stability.py"),
            targeting=Targeting(
                escalated=flagged, rate_base=base, rate_targeted=1.0,
                rate_blind=blind,
                escalated_usd_per_attempt=COMPUTE_NS[r["query_class"]]
                / 1e9 / 3600.0 * 0.02,
                source="scripts/cert_answer_stability.py")))
    print()
    print(ledger_table(ledgers))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "changed_keys": len(changed),
                               "rows": rows,
                               "ledgers": [x.as_dict() for x in ledgers]},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
