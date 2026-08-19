"""Does solvency survive interleaving, as the audit predicted before the reader?

`scripts/audit_domains.py` computes an ambiguity mass of 0.000 for solvency: no
sentence signature carries more than one claim kind. The instrument's claim is
that this predicts structure-independence -- a reader should type every sentence
from its shape alone, and destroying arrangement should cost nothing.

That prediction was made when solvency had **no reader at all**. This builds the
check.

Run: uv run python -u scripts/solvency_arrangement.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.scramble import interleave, unsaturate
from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                          read_signature)
from symbolic_ai_generators.solvency.surface import render_observation

OUT = Path("runs/solvency_arrangement.json")
N = 60
HEADINGS = ("COVENANT REVIEW.", "AS FIRST REPORTED.", "SUBSEQUENT REVISIONS.",
            "THE TEST.")


def score(V: int, surface: str) -> tuple[float, float]:
    """(answer accuracy, filing recall)."""
    acc, rec = [], []
    for s in range(N):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        obs = render_observation(case, variants=V)
        if surface == "as published":
            text = obs.text
        elif surface == "unsaturated":
            text = unsaturate(obs, headings=HEADINGS).text
        else:
            flat = unsaturate(obs, headings=HEADINGS, shuffle=False)
            text = interleave(flat).text
        r = read_signature(text)
        acc.append(decide_reading(r) == want)
        want_f = {(e, round(v, 2), k) for e, v, k in case.filings}
        got_f = {(e, round(v, 2), k) for e, v, k in r.filings}
        rec.append(len(want_f & got_f) / len(want_f) if want_f else 0.0)
    return statistics.mean(acc), statistics.mean(rec)


def main() -> None:
    print(f"{'V':>2} {'surface':<14} {'answer acc':>11} {'filing recall':>14}")
    print("-" * 45)
    rows = {}
    for V in (1, 4):
        for surface in ("as published", "unsaturated", "interleaved"):
            a, r = score(V, surface)
            rows[f"V{V}|{surface}"] = {"accuracy": a, "filing_recall": r}
            print(f"{V:>2} {surface:<14} {a:>11.3f} {r:>14.3f}", flush=True)
        print()

    base = rows["V4|as published"]["accuracy"]
    hard = rows["V4|interleaved"]["accuracy"]
    print(f"-> the audit predicted structure-independence from an ambiguity "
          f"mass of 0.000,\n   before this reader existed. Measured: "
          f"{base:.3f} published, {hard:.3f} interleaved "
          f"({hard - base:+.3f}).")
    if abs(hard - base) < 0.05 and base > 0.9:
        print(f"   THE PREDICTION HOLDS. Destroying arrangement costs nothing "
              f"here, and the audit\n   said so from the surface alone -- which "
              f"is what an instrument is for.")
    elif hard < base - 0.05:
        print(f"   THE PREDICTION FAILS. Something outside sentence signature "
              f"carries the reading,\n   and the audit is incomplete. That is "
              f"the more interesting result and it names\n   the next thing to "
              f"measure.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
