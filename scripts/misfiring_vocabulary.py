"""Can a declared vocabulary be WORSE than none? The control, run properly.

`scripts/adversarial_variants.py` names this as its more important question and
cannot answer it. Its `_verify_adversarial` asserts that no adversarial phrasing
contains a declared anchor, using ``t.startswith(w)`` over
``re.findall(r"[a-z]+", s.lower())`` -- which is **exactly the predicate
`_anchor_role` computes**. So `_anchor_role` returns ``""`` on every adversarial
sentence by construction, the arm reduces to the emptied-anchor arm, and the two
agree **case by case** (252/252 at 400 seeds, 34/34 at 60) rather than
"landing on the floor to three decimals". A control that asserts the mechanism
cannot fire cannot measure what happens when it fires.

So: phrasings that **do** carry an anchor, for the **wrong** role, and for
exactly one role, so `_anchor_role` returns a confident wrong answer rather than
silence. `_verify_misfires` asserts the misfire **exists**, which is the honest
inversion of the verification above.

Three arms on the same cases, at 400 seeds:

- **none** -- original phrasings, anchors emptied. The floor.
- **evading** -- adversarial phrasings. Provably identical to the floor.
- **misfiring** -- phrasings that trip the wrong anchor.

Run: uv run python -u scripts/misfiring_vocabulary.py
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.read_surface import (ROLE_ANCHORS,
                                                       read_content_roles)
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/misfiring_vocabulary.json")
N = 400
EMPTY = {"depot": (), "flooded": (), "needs": ()}

#: Natural phrasings for one role that carry the vocabulary of another. Each
#: must trip exactly ONE anchor set and it must be the wrong one -- asserted
#: below, not eyed.
MISFIRING = {
    # says "the fleet lives here", trips `require` -> needs
    "depot": (
        "Crews are required to sign on at {w} before any run.",
        "Every lorry is required back at {w} by dusk.",
        "{w} is where the yard is, and all runs are required to end there.",
        "Drivers are required to garage at {w}.",
    ),
    # says "nothing can pass", trips `origin` -> depot
    "flooded": (
        "The original road through {w} is gone and nothing may pass.",
        "{w} is off the map; its original crossing has given way.",
        "Nothing gets through {w} -- the original route is shut.",
        "Traffic through {w} has ceased; the original way in is closed.",
    ),
    # says "they have run out", trips `water` -> flooded
    "needs": (
        "Stocks of drinking water at {w} have run out.",
        "{w} has no water left in store and has said so.",
        "The water reserve at {w} is empty.",
        "{w} has run its water store dry and called it in.",
    ),
}

#: Which role each set is *meant* to trip instead of its own.
WRONG = {"depot": "needs", "flooded": "depot", "needs": "flooded"}


def _hits(form: str) -> set[str]:
    tokens = re.findall(r"[a-z]+", form.lower())
    return {role for role, words in ROLE_ANCHORS.items()
            if any(t.startswith(w) for t in tokens for w in words)}


def _verify_misfires() -> None:
    """Every phrasing must trip exactly one anchor set, and the wrong one.

    The inversion of `adversarial_variants._verify_adversarial`, which asserts
    no anchor is tripped and thereby decides its own experiment.
    """
    for role, forms in MISFIRING.items():
        for form in forms:
            hit = _hits(form)
            assert hit == {WRONG[role]}, (role, form, sorted(hit),
                                          f"wanted exactly {{{WRONG[role]}}}")


def score(interleaved: bool, *, anchors, variants) -> tuple[int, float]:
    original = dict(S._VARIANTS)
    if variants is not None:
        for role, forms in variants.items():
            S._VARIANTS[role] = forms
    try:
        ok = []
        for s in range(N):
            case = generate(s)
            want = solve(case.world)[0]
            if not want:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            text = interleave(flat).text if interleaved else unsaturate(obs).text
            try:
                got = solve(read_content_roles(text, anchors=anchors))[0]
            except Exception:
                got = ()
            ok.append(got == want)
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    return len(ok), statistics.mean(ok)


def main() -> None:
    _verify_misfires()
    print("every misfiring phrasing verified to trip exactly one WRONG "
          "anchor set\n")

    arms = {
        "no vocabulary (anchors emptied)": (EMPTY, None),
        "declared, phrasings evade it": (None, None),   # filled below
        "declared, phrasings MISFIRE": (None, MISFIRING),
    }
    # the evading arm needs the adversarial phrasings, imported lazily so this
    # script stands alone if that one is ever retired
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from adversarial_variants import ADVERSARIAL
    arms["declared, phrasings evade it"] = (None, ADVERSARIAL)

    out = {}
    print(f"{'vocabulary':<34} {'grouped':>9} {'interleaved':>12}")
    print("-" * 58)
    for name, (anchors, variants) in arms.items():
        n_g, g = score(False, anchors=anchors, variants=variants)
        n_i, i = score(True, anchors=anchors, variants=variants)
        out[name] = {"n": n_g, "grouped": g, "interleaved": i}
        print(f"{name:<34} {g:>9.3f} {i:>12.3f}")

    floor = out["no vocabulary (anchors emptied)"]
    mis = out["declared, phrasings MISFIRE"]
    print(f"\nn = {floor['n']} non-empty cases at {N} seeds.")
    for cell in ("grouped", "interleaved"):
        d = mis[cell] - floor[cell]
        verdict = "WORSE than no vocabulary" if d < -0.02 else "not worse"
        print(f"  {cell:<12} misfiring {mis[cell]:.3f} vs floor "
              f"{floor[cell]:.3f}  ({d:+.3f})  -> {verdict}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
