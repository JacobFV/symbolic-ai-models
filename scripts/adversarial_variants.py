"""Phrasings written against the declared anchors, which is the honest floor.

`read_content_roles` scores 1.000 in all four cells of the phrasing x
arrangement grid, using five declared words for flooding and a handful each for
depot and needs. Those words were fixed before the generator's variants were
read -- but the variants were not written to *evade* them.

So: four more phrasings per residual role, each avoiding **every** declared
anchor. At V=8 half the draws are adversarial.

Two things are being measured, and the second matters more:

- how far accuracy falls when the vocabulary does not reach the wording;
- whether a declared vocabulary can be **worse than none**, by *misfiring* -- an
  anchor hitting a sentence it was not written for assigns a confident wrong
  role where an empty vocabulary would have left it to elimination. Below the
  0.618 emptied-anchor floor means that happened.

Run: uv run python -u scripts/adversarial_variants.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (ROLE_ANCHORS,
                                                       read_content_roles)
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/adversarial_variants.json")
N = 60

#: Four more phrasings per residual role, each avoiding every declared anchor.
#: Checked against ROLE_ANCHORS by ``_verify_adversarial`` below rather than by
#: eye, because an adversarial variant that accidentally contains an anchor
#: would quietly make this experiment easy.
ADVERSARIAL = {
    "depot": (
        "Every lorry is garaged at {w} overnight.",
        "The fleet sleeps at {w}.",
        "{w} is where the yard is.",
        "Crews sign on and off at {w}.",
    ),
    "flooded": (
        "{w} is cut off and nothing may pass through it.",
        "Nothing gets through {w} any more.",
        "{w} has been written off for the duration.",
        "Traffic through {w} has ceased entirely.",
    ),
    "needs": (
        "{w} has called in an order.",
        "An appeal has gone up from {w}.",
        "{w} is short and has said so.",
        "Word has come from {w} that they are out.",
    ),
}


def _verify_adversarial() -> None:
    """No adversarial variant may contain a declared anchor. Checked, not eyed."""
    import re
    for role, forms in ADVERSARIAL.items():
        for form in forms:
            tokens = re.findall(r"[a-z]+", form.lower())
            for r, words in ROLE_ANCHORS.items():
                hit = [w for t in tokens for w in words if t.startswith(w)]
                assert not hit, (role, form, r, hit)


def score(V: int, interleaved: bool) -> float:
    ok = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = S.render_observation(case, variants=V)
        flat = unsaturate(obs, drop_headings=True, shuffle=False)
        text = interleave(flat).text if interleaved else unsaturate(obs).text
        try:
            got = solve(read_content_roles(text))[0]
        except Exception:
            got = ()
        ok.append(got == want)
    return statistics.mean(ok)


def main() -> None:
    _verify_adversarial()
    print("every adversarial variant verified free of declared anchors\n")

    original = dict(S._VARIANTS)
    baseline = {"V4_grouped": score(4, False), "V4_interleaved": score(4, True)}

    # Extend the residual roles with the adversarial forms. _pick draws from
    # forms[:variants], so V=8 makes half the draws adversarial.
    S._VARIANTS = dict(original)
    for role, extra in ADVERSARIAL.items():
        S._VARIANTS[role] = tuple(original[role]) + extra
    try:
        mixed = {"V8_grouped": score(8, False),
                 "V8_interleaved": score(8, True)}
        # all-adversarial: only the evading forms
        S._VARIANTS = dict(original)
        for role, extra in ADVERSARIAL.items():
            S._VARIANTS[role] = extra
        allbad = {"V4_grouped": score(4, False),
                  "V4_interleaved": score(4, True)}
    finally:
        S._VARIANTS = original

    print(f"{'phrasing set':<34} {'grouped':>9} {'interleaved':>12}")
    print("-" * 58)
    print(f"{'original 4 (published)':<34} {baseline['V4_grouped']:>9.3f} "
          f"{baseline['V4_interleaved']:>12.3f}")
    print(f"{'8, half adversarial':<34} {mixed['V8_grouped']:>9.3f} "
          f"{mixed['V8_interleaved']:>12.3f}")
    print(f"{'4, ALL adversarial':<34} {allbad['V4_grouped']:>9.3f} "
          f"{allbad['V4_interleaved']:>12.3f}")
    print(f"{'(anchors emptied, for reference)':<34} {0.765:>9.3f} "
          f"{0.618:>12.3f}")

    hard = allbad["V4_interleaved"]
    print()
    if hard < 0.618 - 0.02:
        print(f"-> THE VOCABULARY MISFIRES. All-adversarial scores {hard:.3f}, "
              f"BELOW the 0.618 floor of\n   having no vocabulary at all. A "
              f"declared anchor hitting a sentence it was not\n   written for "
              f"assigns a confident wrong role where an empty vocabulary would "
              f"have\n   left it to elimination. That is a defect in the arm, "
              f"not a missing word.")
    elif hard < 0.9:
        print(f"-> THE PUBLISHED 1.000 IS A CEILING, NOT A CAPABILITY. Against "
              f"phrasings written to\n   evade the declared words it falls to "
              f"{hard:.3f}, and it degrades to -- not below --\n   the "
              f"no-vocabulary floor, so the anchors never actively mislead. "
              f"The honest\n   summary is that the arm is invariant to the "
              f"paraphrases it has words for.")
    else:
        print(f"-> Survives adversarial phrasing at {hard:.3f}, which "
              f"CONTRADICTS the ablation's\n   +0.382 and means elimination is "
              f"carrying more than the ablation suggested.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "baseline": baseline, "mixed": mixed,
                               "all_adversarial": allbad}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
