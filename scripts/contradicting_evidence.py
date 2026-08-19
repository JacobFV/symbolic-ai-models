"""The one signal that sees a misfire, and it was being thrown away.

A **misfire** -- an anchor firing on a sentence it was not written for -- costs
0.290 against having no vocabulary at all, and is invisible to every check this
repo has built. It reads as ``forced``, so enumeration gives one world and
agreement is vacuous; its sentence is consumed, so `audit.unconsumed` sees
nothing; and `certifies_insensitive` builds its graph from the roles, so it
inherits the error.

But the reader has **two independent signals** for the needs site: the lexical
anchor, and positional adjacency to the bare demand quantity. It consults the
second only when the first stayed silent::

    if not needs and adjacent and adjacent in unresolved:

so when they disagree, the disagreement is discarded. `evidence_conflict`
recovers it.

Six arms, 400 seeds, graded by WHICH role misfires -- because `needs` is the
only role with a second independent signal, so only a misfire that **steals
needs** can be seen at all.

Run: uv run python -u scripts/contradicting_evidence.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.read_surface import (evidence_conflict,
                                                       read_content_roles)
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

sys.path.insert(0, str(Path(__file__).parent))
from adversarial_variants import ADVERSARIAL          # noqa: E402
from misfiring_vocabulary import MISFIRING            # noqa: E402

OUT = Path("runs/contradicting_evidence.json")
N = 400


def run(variants) -> dict:
    original = dict(S._VARIANTS)
    if variants is not None:
        for role, forms in variants.items():
            S._VARIANTS[role] = forms
    try:
        rows = []
        for s in range(N):
            case = generate(s)
            want = solve(case.world)[0]
            if not want:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            text = interleave(flat).text
            try:
                got = solve(read_content_roles(text))[0]
            except Exception:
                got = ()
            rows.append({"seed": s, "wrong": got != want,
                         "conflict": bool(evidence_conflict(text))})
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)

    n = len(rows)
    wrong = [r for r in rows if r["wrong"]]
    right = [r for r in rows if not r["wrong"]]
    fired = [r for r in rows if r["conflict"]]
    caught = [r for r in wrong if r["conflict"]]
    return {"n": n, "wrong": len(wrong), "fires": len(fired),
            "accuracy": len(right) / n,
            "recall": len(caught) / len(wrong) if wrong else float("nan"),
            "false_alarm": (len(fired) - len(caught)) / len(right)
            if right else float("nan"),
            "precision": len(caught) / len(fired) if fired else float("nan")}


def main() -> None:
    # Graded arms: which ROLE misfires decides whether the check can see it.
    # `needs` is the only role with a second, independent signal (adjacency to
    # the demand quantity), so only a misfire that STEALS `needs` is visible.
    only = lambda role: {**{r: S._VARIANTS[r] for r in MISFIRING
                           if r != role}, role: MISFIRING[role]}
    base = dict(S._VARIANTS)
    arms = {"published (original phrasings)": None,
            "evading (adversarial)": ADVERSARIAL,
            "misfiring: depot only (steals needs)": {"depot": MISFIRING["depot"]},
            "misfiring: flooded only (steals depot)":
                {"flooded": MISFIRING["flooded"]},
            "misfiring: needs only (steals flooded)":
                {"needs": MISFIRING["needs"]},
            "misfiring: all three": MISFIRING}
    del only, base
    out = {}
    print(f"{'surface':<38} {'acc':>7} {'fires':>7} {'fire rate':>10}")
    print("-" * 66)
    for name, variants in arms.items():
        r = run(variants)
        out[name] = r
        print(f"{name:<38} {r['accuracy']:>7.3f} {r['fires']:>7} "
              f"{r['fires'] / r['n']:>10.3f}")

    print("\nThe check detects the CONDITION (an anchor fired on a sentence it")
    print("was not written for), not the consequence. A misfire does not always")
    print("change the answer, so fire rate is compared against the arm, not")
    print("against wrongness. The evading arm is vacuous by construction -- no")
    print("anchor fires, so no two signals can disagree.")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
