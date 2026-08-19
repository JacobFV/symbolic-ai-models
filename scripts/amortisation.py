"""When does writing the reader pay for itself?

The break-even accuracy finding showed no accuracy closes the price gap, and
ended on what it could not compute: **development cost is measured nowhere in
this repo**, so "337x cheaper per answer" cannot be turned into "worth building".

The missing quantity is the break-even **episode count**:

    N* = development_cost / (llm_usd_per_answer - our_usd_per_answer)

Development cost stays a **parameter**. Inventing one number would be a guess
wearing a measurement's clothes; reporting the curve lets a reader put their own
figure in. Lines of code are shown only as a scale anchor, explicitly not a cost.

Run: uv run python -u scripts/amortisation.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

OUT = Path("runs/amortisation.json")

#: from scripts/break_even_accuracy.py, measured
OUR_USD_PER_ANSWER = {"flood": 4.901e-08, "scheduling": 1.447e-07,
                      "solvency": 3.362e-10}
TOKENS = {"flood": 362, "scheduling": 325, "solvency": 150}
PRICES = {"small hosted model": 0.15, "frontier model": 3.00}
BUDGETS = (100.0, 1_000.0, 10_000.0, 100_000.0)

READERS = {
    "flood": "symbolic_ai_generators/flood/read_surface.py",
    "scheduling": "symbolic_ai_generators/scheduling/read_surface.py",
    "solvency": "symbolic_ai_generators/solvency/read_surface.py",
}


def loc(path: str) -> int:
    try:
        text = Path(path).read_text().splitlines()
    except OSError:
        return 0
    return sum(1 for line in text
               if line.strip() and not line.strip().startswith("#"))


def main() -> None:
    print("reader size, as a SCALE ANCHOR and not a cost:\n")
    for name, path in READERS.items():
        print(f"  {name:<12} {loc(path):>5} non-comment lines")

    print(f"\nbreak-even episodes: how many answers before writing the reader "
          f"pays back\n")
    hdr = (f"{'domain':<12} {'vs model':<20} {'saving/answer':>14} "
           + " ".join(f"{'$' + format(b, ',.0f'):>13}" for b in BUDGETS))
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for name, ours in OUR_USD_PER_ANSWER.items():
        for label, price in PRICES.items():
            llm = price / 1e6 * TOKENS[name]
            saving = llm - ours
            cells = []
            for b in BUDGETS:
                n = b / saving
                cells.append(f"{n:>13,.0f}")
                rows[f"{name}|{label}|{b:.0f}"] = n
            print(f"{name:<12} {label:<20} {saving:>14.3e} "
                  + " ".join(cells))

    frontier = {k: v for k, v in rows.items()
                if "frontier" in k and k.endswith("|1000")}
    cheap = {k: v for k, v in rows.items()
             if "small hosted" in k and k.endswith("|1000")}
    print(f"\n  at $1,000 of engineering: "
          f"{min(frontier.values()):,.0f}-{max(frontier.values()):,.0f} episodes "
          f"against a frontier model,")
    print(f"  {min(cheap.values()):,.0f}-{max(cheap.values()):,.0f} against a "
          f"cheap hosted one.")

    print()
    print(f"-> THE SAME MEASUREMENT, IN THE FORM THAT DECIDES ANYTHING. "
          f"'337x cheaper per answer'\n   sounds decisive; 'pays back after a "
          f"million episodes' is a volume threshold, and\n   it is the one that "
          f"tells you whether to write the reader.")
    # Equal budgets assume equal effort, and the readers are not equal sizes.
    # Scaling by lines is still not a cost, but it is the ratio the flat table
    # hides.
    lines = {k: loc(v) for k, v in READERS.items()}
    base = min(lines.values())
    print(f"\n  scaled by reader size (lines relative to the smallest), "
          f"vs a frontier model.")
    print(f"  CONFOUNDED: flood's file holds five reader ARMS built for "
          f"research -- rules, lexical,\n  signature/index, signature/roles, "
          f"signature+content -- where the others hold one.\n  Read the "
          f"ordering, not the multiple.")
    for name in OUR_USD_PER_ANSWER:
        llm = PRICES["frontier model"] / 1e6 * TOKENS[name]
        saving = llm - OUR_USD_PER_ANSWER[name]
        scaled = 1_000.0 * (lines[name] / base) / saving
        print(f"    {name:<12} {lines[name]:>4} lines  ->  {scaled:>13,.0f} "
              f"episodes")

    print(f"\n   The rankings INVERT. Solvency's saving is the smallest in "
          f"absolute terms -- 150\n   tokens and a decision that costs nothing "
          f"-- so at a flat budget it needs the most\n   episodes despite "
          f"having the largest per-answer multiple, 1.3M x. A big ratio on a\n"
          f"   tiny number is still a tiny number, and the multiple is the "
          f"figure that flatters.")
    print(f"\n   And scheduling pays back soonest because its reader is "
          f"{lines['scheduling']} lines, which is\n   the "
          f"structure-dependence law showing up in a budget: job_ and machine_ "
          f"prefixes fix\n   the predicate, the audit measures that offline at "
          f"0.000 ambiguity mass, and the\n   reader that follows is short. "
          f"THE AUDIT PREDICTS HOW EXPENSIVE THE READER WILL BE TO\n   WRITE, "
          f"before one exists -- and therefore how soon the symbolic route pays "
          f"back.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"loc": {k: loc(v) for k, v in READERS.items()},
                               "break_even_episodes": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
