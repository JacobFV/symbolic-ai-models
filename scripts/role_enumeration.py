"""Refusing only when the role ambiguity actually matters.

The role flag refuses whenever the lone-region assignment is unforced -- 29 of
252 -- to remove 3 errors. **Ten times more conservative than the failure**,
which the previous finding named as the thing to fix.

An unforced assignment is usually still inert: which of two regions is called the
depot often does not change which vehicles can deliver. So instead of refusing,
emit the alternatives and refuse only when they **disagree on the answer**.

This is cheap where the earlier unbounded role permutation was vacuous, because
it enumerates what the reader could not settle -- typically two regions -- rather
than what is conceivable.

Run: uv run python -u scripts/role_enumeration.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (
    read_content_roles_checked, read_content_roles_worlds)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

sys.path.insert(0, "scripts")
from insensitivity_certificate import certifies_insensitive  # noqa: E402

OUT = Path("runs/role_enumeration.json")
N = 400
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def main() -> None:
    rows = []
    solves = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, headings=HEADINGS,
                                     shuffle=False)).text
        world, forced = read_content_roles_checked(text)
        try:
            got = solve(world)[0]
        except Exception:
            got = ()
        worlds = read_content_roles_worlds(text)
        answers = set()
        for w in worlds:
            try:
                answers.add(solve(w)[0])
            except Exception:
                answers.add(())
        solves.append(len(worlds))
        rows.append({"ok": got == want, "forced": forced,
                     "roles_agree": len(answers) == 1,
                     "cert": certifies_insensitive(world)})

    n = len(rows)
    policies = {
        "answer everything": lambda r: True,
        "role flag (refuse unforced)": lambda r: r["forced"],
        "role ENUMERATION": lambda r: r["roles_agree"],
        "flag + certificate": lambda r: r["forced"] and r["cert"],
        "ENUMERATION + certificate": lambda r: r["roles_agree"] and r["cert"],
    }
    hdr = f"{'policy':<28} {'answers':>8} {'coverage':>9} {'wrong':>7} {'accuracy':>9}"
    print(f"{n} non-empty cases, 400 seeds, interleaved, "
          f"hard_distractors=True\n")
    print(hdr)
    print("-" * len(hdr))
    out = {}
    for label, accept in policies.items():
        kept = [r for r in rows if accept(r)]
        wrong = sum(not r["ok"] for r in kept)
        out[label] = {"answers": len(kept), "coverage": len(kept) / n,
                      "wrong": wrong,
                      "accuracy": 1 - wrong / len(kept) if kept else 0.0}
        v = out[label]
        print(f"{label:<28} {v['answers']:>8} {v['coverage']:>9.3f} "
              f"{v['wrong']:>7} {v['accuracy']:>9.4f}")

    unforced = sum(1 for r in rows if not r["forced"])
    inert = sum(1 for r in rows if not r["forced"] and r["roles_agree"])
    print(f"\n  unforced assignments        : {unforced}")
    print(f"  of those, INERT (agree)     : {inert}  "
          f"({inert / max(unforced, 1):.0%})")
    print(f"  mean candidate worlds solved: "
          f"{statistics.mean(solves):.2f}")

    flag, enum = out["flag + certificate"], out["ENUMERATION + certificate"]
    print()
    if enum["wrong"] == 0 and enum["coverage"] > flag["coverage"] + 0.02:
        print(f"-> ENUMERATING BEATS REFUSING, AT THE SAME SOUNDNESS. "
              f"{inert} of {unforced} unforced\n   assignments are INERT -- the "
              f"ambiguity is real and does not change the answer -- so\n   "
              f"refusing on all of them threw away coverage for nothing. "
              f"Paired with the\n   certificate: {enum['coverage']:.1%} against "
              f"{flag['coverage']:.1%}, both at 0 wrong.")
        print(f"\n   The cost is {statistics.mean(solves):.2f} solves per case "
              f"on average, against 1 for the flag.\n   That is the same trade "
              f"the link policy makes, at a fraction of the width: the\n   "
              f"candidate set is what the reader could not settle, not what is "
              f"conceivable.")
    elif enum["wrong"]:
        print(f"-> enumeration is NOT sound: {enum['wrong']} wrong at "
              f"{enum['coverage']:.1%} coverage.")
    else:
        print(f"-> enumeration buys little: {enum['coverage']:.1%} against "
              f"{flag['coverage']:.1%}. Most unforced assignments\n   do change "
              f"the answer, so the flag was right to refuse them.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": n, "rows": out, "unforced": unforced,
                               "inert": inert,
                               "mean_solves": statistics.mean(solves)},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
