"""Refusing to collapse, when the suspect claim is a distractor rather than a role.

Nothing downstream of a reader can see the true world, so no grounding check
catches an invented claim -- that is the scope result of
``2026-08-19-grounded-means-consistent-with-what-was-read-not-true``. The one
response left is for the reader to **decline to collapse**.

The audit says, offline and without a reader, that flood's ``(2 regions, 0
number)`` signature is shared with prose. A reader cannot tell *which* link
sentence is the distractor, but it knows the kind is suspect. So: emit the
ambiguity, and answer only where every candidate world agrees.

Enumerating all subsets of suspect links is exponential and would be vacuous, so
the hypothesis is bounded and matches the generator's actual situation: **at most
one link is spurious**. That is ``k + 1`` worlds -- the full set, and each single
deletion.

Reported as soundness and decidedness rather than accuracy, because a system that
refuses is not wrong.

Run: uv run python -u scripts/carry_distractor_ambiguity.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/carry_distractor_ambiguity.json")
N = 60
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def candidate_worlds(world):
    """The read world, and each world with one link claim removed."""
    yield world
    links = [i for i, c in enumerate(world.claims) if c.predicate == "link"]
    for i in links:
        yield replace(world, claims=tuple(c for j, c in enumerate(world.claims)
                                          if j != i))


def main() -> None:
    collapse_ok, sound, decided, sizes = [], [], [], []
    decided_and_right = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, headings=HEADINGS,
                                     shuffle=False)).text
        world = read_content_roles(text)

        collapse_ok.append(solve(world)[0] == want)

        answers = set()
        n = 0
        for cand in candidate_worlds(world):
            n += 1
            try:
                answers.add(solve(cand)[0])
            except Exception:
                pass
        sizes.append(n)
        sound.append(want in answers)
        is_decided = len(answers) == 1
        decided.append(is_decided)
        if is_decided:
            decided_and_right.append(next(iter(answers)) == want)

    print(f"{N} cases, V=4, interleaved, hard_distractors=True\n")
    print(f"{'policy':<34} {'accuracy':>9} {'soundness':>10} {'decided':>9}")
    print("-" * 65)
    print(f"{'collapse (answer regardless)':<34} "
          f"{statistics.mean(collapse_ok):>9.3f} {'--':>10} {'1.000':>9}")
    print(f"{'carry at-most-one-spurious':<34} "
          f"{'--':>9} {statistics.mean(sound):>10.3f} "
          f"{statistics.mean(decided):>9.3f}")
    print(f"\n  candidate worlds per case: median "
          f"{statistics.median(sizes):.0f}, max {max(sizes)}")
    if decided_and_right:
        print(f"  when it decides, it is right: "
              f"{statistics.mean(decided_and_right):.3f} "
              f"({len(decided_and_right)} cases)")

    d = statistics.mean(decided)
    a = statistics.mean(collapse_ok)
    print()
    if statistics.mean(sound) < 0.999:
        print(f"-> SOUNDNESS IS NOT 1.000 ({statistics.mean(sound):.3f}). The "
              f"at-most-one-spurious hypothesis\n   is wrong for this "
              f"generator, which is stated as exact and therefore worth "
              f"knowing.")
    elif d >= 0.2:
        print(f"-> USABLE. Soundness 1.000 with {d:.3f} decided, against a "
              f"collapsing reader that\n   answers everything at {a:.3f} and "
              f"cannot say which half is wrong. Refusing on the\n   rest "
              f"converts a silent error rate into a bounded one.")
    else:
        print(f"-> SOUND BUT VACUOUS: {d:.3f} decided. Carrying distractor "
              f"ambiguity behaves like\n   carrying role ambiguity -- free "
              f"soundness that runs out of usefulness quickly --\n   because "
              f"most links are load-bearing and deleting one changes the "
              f"answer. Content\n   remains the only thing that resolves it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": N, "collapse_accuracy": a, "soundness": statistics.mean(sound),
         "decided": d, "median_worlds": statistics.median(sizes),
         "right_when_decided": (statistics.mean(decided_and_right)
                                if decided_and_right else None)}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
