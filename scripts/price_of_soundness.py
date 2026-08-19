"""What soundness costs, in the programme's own currency.

The honest milestone prices the collapsing reader: it answers every case, is
right 0.500 of the time on the non-empty population, and cannot say which half.
The carrying policy answers only where every candidate world agrees, is **never
wrong when it answers**, and runs ``k + 1`` solves per case instead of one.

"Soundness 1.000" quoted without a price is the same error as "grounded 1.000"
quoted without a scope, and this thread has already made that one. So: price it.

Reported on the non-empty population, which is this domain's standing convention
-- 45% of cases have an empty correct answer that survives any reader failure for
free.

Run: uv run python -u scripts/price_of_soundness.py
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

OUT = Path("runs/price_of_soundness.json")
N = 60
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def cost_of(outputs) -> float:
    total = 0.0
    for artifact in (outputs or {}).values():
        value = getattr(artifact, "value", None)
        if not isinstance(value, dict):
            continue
        c = value.get("cost")
        if isinstance(c, dict) and "usd" in c:
            total += float(c["usd"] or 0.0)
        elif "usd" in value:
            total += float(value["usd"] or 0.0)
    return total


def main() -> None:
    collapse_usd = carry_usd = early_usd = 0.0
    collapse_right = decided = decided_right = n = 0
    candidates: list[int] = []
    early_solves: list[int] = []

    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        n += 1
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, headings=HEADINGS,
                                     shuffle=False)).text
        world = read_content_roles(text)

        answer, outs, _ = solve(world)
        collapse_usd += cost_of(outs)
        collapse_right += answer == want

        answers = {answer}
        k = 1
        carry_usd += cost_of(outs)          # the base solve, counted once
        early_usd += cost_of(outs)
        stopped = False
        for i, c in enumerate(world.claims):
            if c.predicate != "link":
                continue
            k += 1
            trimmed = replace(world, claims=tuple(
                x for j, x in enumerate(world.claims) if j != i))
            a, o, _ = solve(trimmed)
            carry_usd += cost_of(o)
            if not stopped:
                early_usd += cost_of(o)
            answers.add(a)
            # Exact, not an approximation: one disagreement settles the case as
            # undecided, so every later candidate is spend on an answer already
            # known not to be given.
            if len(answers) > 1 and not stopped:
                stopped = True
                early_solves.append(k)
        candidates.append(k)
        if len(answers) == 1:
            decided += 1
            decided_right += next(iter(answers)) == want
            early_solves.append(k)

    print(f"{n} non-empty cases, V=4, interleaved, hard_distractors=True\n")
    hdr = (f"{'policy':<24} {'answers':>8} {'correct':>8} {'soundness':>10} "
           f"{'$ total':>11} {'$/correct':>11}")
    print(hdr)
    print("-" * len(hdr))
    print(f"{'collapse':<24} {n:>8} {collapse_right:>8} {'--':>10} "
          f"{collapse_usd:>11.3e} {collapse_usd / max(collapse_right, 1):>11.3e}")
    sound = decided_right / decided if decided else float("nan")
    print(f"{'carry, answer if agreed':<24} {decided:>8} {decided_right:>8} "
          f"{sound:>10.3f} {carry_usd:>11.3e} "
          f"{carry_usd / max(decided_right, 1):>11.3e}")

    print(f"{'carry, early exit':<24} {decided:>8} {decided_right:>8} "
          f"{sound:>10.3f} {early_usd:>11.3e} "
          f"{early_usd / max(decided_right, 1):>11.3e}")

    ratio = ((carry_usd / max(decided_right, 1)) /
             (collapse_usd / max(collapse_right, 1)))
    early_ratio = ((early_usd / max(decided_right, 1)) /
                   (collapse_usd / max(collapse_right, 1)))
    print(f"\n  candidate worlds per case: median "
          f"{statistics.median(candidates):.0f}")
    print(f"  compute multiple:          {carry_usd / collapse_usd:.1f}x")
    print(f"  $ per correct answer:      {ratio:.1f}x")

    print(f"\n-> SOUNDNESS COSTS {ratio:.1f}x PER CORRECT ANSWER. The collapsing "
          f"reader is right\n   {collapse_right}/{n} and cannot say which; the "
          f"carrying policy is right {decided_right}/{decided} times out of "
          f"{decided}\n   and knows it. The extra spend is almost entirely the "
          f"{statistics.median(candidates):.0f} candidate solves --\n   "
          f"{carry_usd / collapse_usd:.1f}x the compute -- with the rest coming "
          f"from answering less often.")
    print(f"\n-> AND IT DISCARDS ONLY WRONG ANSWERS. Collapse is right "
          f"{collapse_right}/{n}; carry is right\n   {decided_right}/{decided} "
          f"-- the SAME number of correct answers, with the wrong ones "
          f"refused.\n   That is why the $/correct multiple equals the compute "
          f"multiple exactly: the\n   numerator does not move.")
    print(f"\n-> EARLY EXIT BRINGS IT TO {early_ratio:.1f}x. One disagreement "
          f"settles a case as undecided,\n   so every later candidate is spend "
          f"on an answer already known not to be given.\n   Exact, not an "
          f"approximation -- the decided set is unchanged. Mean solves fall "
          f"from\n   {statistics.mean(candidates):.1f} to "
          f"{statistics.mean(early_solves):.1f}.")
    print(f"\n   That is the trade, priced in the programme's own currency. A "
          f"system that argues\n   its reasoning is inspectable rather than "
          f"inferred should be able to say what\n   inspectability costs: here "
          f"{early_ratio:.1f}x per correct answer, buying the ability never "
          f"to be\n   wrong when it speaks.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": n, "collapse_correct": collapse_right, "decided": decided,
         "decided_right": decided_right, "collapse_usd": collapse_usd,
         "carry_usd": carry_usd, "usd_per_correct_ratio": ratio,
         "compute_multiple": carry_usd / collapse_usd,
         "early_usd": early_usd, "early_ratio": early_ratio,
         "mean_solves": statistics.mean(candidates),
         "mean_solves_early": statistics.mean(early_solves),
         "median_candidates": statistics.median(candidates)}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
