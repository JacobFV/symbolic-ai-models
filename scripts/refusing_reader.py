"""Guessing buys 1.2% of answers and pays in silent errors of the same size.

`read_content_roles` is 0.988 on the interleaved surface, and in all three
failures it **knew it was guessing**: `needs` resolved by adjacency, `depot`
still open, two unresolved regions left, so which became the depot depended on
document order.

That condition is detectable at read time with no ground truth, so the reader can
refuse instead. This measures what refusing costs -- because abstention is only
the better policy if it removes more error than it removes coverage, and that is
a number rather than a principle.

Run: uv run python -u scripts/refusing_reader.py
"""

from __future__ import annotations

import json
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles_checked
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/refusing_reader.json")
N = 400
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def main() -> None:
    rows = {}
    for label, hard in (("easy distractor", False), ("hard distractor", True)):
        n = guessed = wrong = wrong_when_certain = 0
        wrong_when_guessed = 0
        for s in range(N):
            case = generate(s)
            want = solve(case.world)[0]
            if not want:
                continue
            n += 1
            obs = render_observation(case, variants=4, hard_distractors=hard)
            text = interleave(unsaturate(obs, headings=HEADINGS,
                                         shuffle=False)).text
            try:
                world, forced = read_content_roles_checked(text)
                got = solve(world)[0]
            except Exception:
                got, forced = (), False
            bad = got != want
            wrong += bad
            if forced:
                wrong_when_certain += bad
            else:
                guessed += 1
                wrong_when_guessed += bad
        rows[label] = {"n": n, "guessed": guessed, "wrong": wrong,
                       "wrong_when_certain": wrong_when_certain,
                       "wrong_when_guessed": wrong_when_guessed}

    hdr = (f"{'surface':<18} {'n':>5} {'accuracy':>9} {'refused':>9} "
           f"{'coverage':>9} {'acc | certain':>14}")
    print(hdr)
    print("-" * len(hdr))
    for label, r in rows.items():
        cov = 1 - r["guessed"] / r["n"]
        acc = 1 - r["wrong"] / r["n"]
        certain_n = r["n"] - r["guessed"]
        acc_c = 1 - r["wrong_when_certain"] / certain_n if certain_n else 0.0
        print(f"{label:<18} {r['n']:>5} {acc:>9.4f} {r['guessed']:>9} "
              f"{cov:>9.4f} {acc_c:>14.4f}")

    e = rows["easy distractor"]
    print(f"\n  errors removed by refusing : {e['wrong_when_guessed']} of "
          f"{e['wrong']}")
    print(f"  coverage given up          : {e['guessed']} of {e['n']} "
          f"({e['guessed'] / e['n']:.2%})")
    print(f"  errors left in the answers : {e['wrong_when_certain']}")

    print()
    if e["wrong_when_certain"] == 0 and e["guessed"] <= 3 * max(e["wrong"], 1):
        print(f"-> REFUSING IS WORTH IT. It removes every error "
              f"({e['wrong_when_guessed']}/{e['wrong']}) and costs "
              f"{e['guessed'] / e['n']:.2%}\n   of coverage, leaving soundness "
              f"1.000 on what it does answer. The detector is not much\n   more "
              f"conservative than the failure, which is the condition that "
              f"makes abstention\n   a better policy rather than merely a "
              f"safer-sounding one.")
    elif e["wrong_when_certain"] == 0:
        print(f"-> SOUND BUT EXPENSIVE. It removes every error and gives up "
              f"{e['guessed'] / e['n']:.1%} of coverage\n   to remove "
              f"{e['wrong'] / e['n']:.1%} of error -- "
              f"{e['guessed'] / max(e['wrong'], 1):.0f}x more conservative than "
              f"the failure. Keeping the guess and\n   reporting 0.988 is the "
              f"honest alternative, and which is better depends on what a\n   "
              f"wrong answer costs.")
    else:
        print(f"-> THE DETECTOR MISSES: {e['wrong_when_certain']} errors "
              f"survive in the answers it is confident\n   about, so it is not "
              f"a soundness guarantee.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
