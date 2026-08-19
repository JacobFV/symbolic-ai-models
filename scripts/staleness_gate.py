"""A second reading of the SAME sentence, since no second source exists.

The channel that matters in both domains is **multi-valued** -- flood's
``flooded`` and scheduling's ``has_capability`` -- so no arity constraint checks
it, and in both domains that is where the damage is (0.655 and 0.790 accuracy
against detectors that fire 0.000 of the time). Nothing else in either document
knows those facts, so there is no second **source**. What is left is a second
reading of the same sentence: does it take back what it says?

Two gates, because the generators have confounded two signals -- every real
phrasing is present tense and every distractor is past tense **with** a
cancelling clause. `stale_by_tense` keys on the past; `stale_by_cancellation`
keys on the taking back. The arm that separates them is the third one:

- **hard** -- the honest distractor surface in each domain;
- **hard + gate** -- the same, with stale sentences dropped;
- **past** -- real claims rephrased in the past but **still true**, which is
  where a tense gate should destroy the reading and a cancellation gate should
  not.

Run: uv run python -u scripts/staleness_gate.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from symbolic_ai_generators.staleness import (filter_stale,
                                              stale_by_cancellation,
                                              stale_by_tense)

OUT = Path("runs/staleness_gate.json")

#: Real claims phrased in the past and still true. The arm that decides whether
#: the cancellation cues are a tense detector wearing a different name.
PAST_TRUE = {
    "scheduling": {
        "has_capability": (
            "{m} was fitted for {c} work.",
            "{m} was commissioned to do {c}.",
            "The {c} head was installed on {m}.",
            "{m} was equipped for {c}.",
        ),
    },
    "flood": {
        "link": (
            "{a} was joined to {b} by a surfaced road.",
            "A made road was laid between {a} and {b}.",
            "A carriageway was built connecting {a} with {b}.",
            "{a} was linked to {b} by road.",
        ),
    },
}

GATES = {"none": None, "tense": stale_by_tense,
         "cancellation": stale_by_cancellation}


def scheduling(hard, variants_override, gate) -> float:
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling import surface as S
    sys.path.insert(0, str(Path(__file__).parent))
    from hard_regime_milestone import solve_world

    original = dict(S._VARIANTS)
    if variants_override:
        for k, v in variants_override.items():
            S._VARIANTS[k] = v
    try:
        ok = []
        for s in range(200):
            case = generate(s)
            text = S.render_observation(case, variants=4,
                                        hard_distractors=hard).text
            if gate:
                text = filter_stale(text, gate)
            ok.append(solve_world(read_signature(text))[0] == case.feasible)
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    return statistics.mean(ok)


def flood(hard, variants_override, gate) -> float:
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood import surface as S
    from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

    original = dict(S._VARIANTS)
    if variants_override:
        for k, v in variants_override.items():
            S._VARIANTS[k] = v
    try:
        ok = []
        for s in range(400):
            case = generate(s)
            want = solve(case.world)[0]
            if not want:
                continue
            obs = S.render_observation(case, variants=4,
                                       hard_distractors=hard)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            text = interleave(flat).text
            if gate:
                text = filter_stale(text, gate)
            try:
                got = solve(read_content_roles(text))[0]
            except Exception:
                got = ()
            ok.append(got == want)
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    return statistics.mean(ok)


def main() -> None:
    out = {}
    for name, fn, hard in (("scheduling", scheduling, "machine"),
                           ("flood", flood, True)):
        print(f"=== {name} ===")
        print(f"{'surface':<34} " + "".join(f"{g:>15}" for g in GATES))
        print("-" * (34 + 15 * len(GATES)))
        rows = {
            "clean (default distractors)": (False, None),
            "hard distractors": (hard, None),
            "clean, real claims in the PAST": (False, PAST_TRUE[name]),
            "hard, real claims in the PAST": (hard, PAST_TRUE[name]),
        }
        out[name] = {}
        for label, (h, ov) in rows.items():
            cells = {g: fn(h, ov, gate) for g, gate in GATES.items()}
            out[name][label] = cells
            print(f"{label:<34} " + "".join(f"{cells[g]:>15.3f}" for g in GATES))
        print()

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
