"""Two detectors, neither of which covers the other's failure.

`role_assignment_forced` catches lone-region guessing and is blind to the phantom
link -- accuracy among forced readings is **0.664** on the hard-distractor
surface. The insensitivity certificate catches link sensitivity and has no view
of role assignment: a misread depot is not a link deletion.

So: measure each alone and both together, on the surface where both failure modes
are live.

Applying this turn's own lesson, at **400 seeds**. The certificate's soundness on
this surface was established at N=60 -- which by the rule of three bounds only
~5% -- and "fires iff the enumeration decides" is a different claim from "fires
implies correct". The second has not been checked at scale.

Run: uv run python -u scripts/combined_detector.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles_checked
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

sys.path.insert(0, "scripts")
from insensitivity_certificate import certifies_insensitive  # noqa: E402

OUT = Path("runs/combined_detector.json")
N = 400
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def main() -> None:
    cases = []
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
        cases.append({"ok": got == want, "forced": forced,
                      "cert": certifies_insensitive(world)})

    n = len(cases)
    policies = {
        "answer everything": lambda c: True,
        "role flag only": lambda c: c["forced"],
        "certificate only": lambda c: c["cert"],
        "both": lambda c: c["forced"] and c["cert"],
    }
    print(f"{n} non-empty cases at 400 seeds, interleaved, "
          f"hard_distractors=True\n")
    hdr = f"{'policy':<22} {'answers':>8} {'coverage':>9} {'wrong':>7} {'accuracy':>9}"
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for label, accept in policies.items():
        kept = [c for c in cases if accept(c)]
        wrong = sum(not c["ok"] for c in kept)
        acc = 1 - wrong / len(kept) if kept else 0.0
        rows[label] = {"answers": len(kept), "coverage": len(kept) / n,
                       "wrong": wrong, "accuracy": acc}
        print(f"{label:<22} {len(kept):>8} {len(kept) / n:>9.3f} "
              f"{wrong:>7} {acc:>9.4f}")

    cert, both = rows["certificate only"], rows["both"]
    print(f"\n  rule of three at n={cert['answers']}: a clean run would bound "
          f"the error at "
          f"{3 / max(cert['answers'], 1):.2%}")

    print()
    if cert["wrong"] == 0 and both["answers"] == cert["answers"]:
        print(f"-> THE CERTIFICATE ALONE IS SOUND, AND THE ROLE FLAG ADDS "
              f"NOTHING HERE. Every case it\n   fires on is already "
              f"role-forced, so link-insensitivity implicitly certifies the\n"
              f"   roles: a misread depot changes which routes exist, which "
              f"shows up as sensitivity\n   to deletion. That is a structural "
              f"fact rather than a coincidence.")
    elif cert["wrong"] == 0:
        print(f"-> THE CERTIFICATE ALONE IS SOUND at "
              f"{cert['coverage']:.1%} coverage over "
              f"{cert['answers']} answers, bounding\n   its error at "
              f"{3 / max(cert['answers'], 1):.2%}. Adding the role flag costs "
              f"{cert['coverage'] - both['coverage']:.1%} coverage and\n   "
              f"removes nothing, so it is not worth pairing on this surface.")
    elif both["wrong"] == 0:
        print(f"-> THE PAIR IS SOUND WHERE NEITHER IS ALONE. The certificate "
              f"lets {cert['wrong']} wrong answers\n   through at 400 seeds -- "
              f"role errors, which link-insensitivity cannot see -- and the "
              f"role\n   flag lets {rows['role flag only']['wrong']} through. "
              f"Together: 0 wrong at {both['coverage']:.1%} coverage.")
        print(f"\n   Neither number was visible at the sample each was "
              f"originally measured on.")
    else:
        print(f"-> NEITHER IS SOUND, even paired: {both['wrong']} wrong at "
              f"{both['coverage']:.1%} coverage.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": n, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
