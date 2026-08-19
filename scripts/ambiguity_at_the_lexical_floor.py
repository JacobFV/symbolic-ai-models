"""What emitting the ambiguity buys where the vocabulary genuinely fails.

`read_content_roles` scores 1.000 on the published surface and **0.618** when
every phrasing is written to evade its declared anchors
(`scripts/adversarial_variants.py`). That 0.382 is the measured case for
lexical generalisation.

But the reader is not *guessing at random* in that regime -- it is guessing by
document order, and it **knows** it is guessing. Directive 19's response is to
emit the alternatives rather than collapse to one. Every measurement of that
machinery so far was taken on the published surface, where the anchors mostly
fire and the open set is small. This runs it where the anchors are silent.

Four arms on the same cases:

- **collapse** -- `read_content_roles`, one guessed world. Answers everything.
- **flag** -- refuse when `role_assignment_forced` is False.
- **emit** -- `read_content_roles_worlds`, answer only when every candidate
  assignment agrees.
- **emit+certify** -- and every candidate must also certify insensitivity.

The question is whether the 0.382 is *decision-relevant* ambiguity or merely
*lexical* ambiguity: if the candidates mostly agree, the words the reader
lacked were settling something inert.

Run: uv run python -u scripts/ambiguity_at_the_lexical_floor.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.certificate import certifies_role_independent
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.read_surface import (
    read_content_roles, read_content_roles_checked, read_content_roles_worlds)
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

sys.path.insert(0, str(Path(__file__).parent))
from adversarial_variants import ADVERSARIAL, _verify_adversarial  # noqa: E402

OUT = Path("runs/ambiguity_at_the_lexical_floor.json")
N = 400


def surface(case, interleaved: bool, hard: bool = False) -> str:
    obs = S.render_observation(case, variants=4, hard_distractors=hard)
    if not interleaved:
        return unsaturate(obs).text
    return interleave(unsaturate(obs, drop_headings=True, shuffle=False)).text


def answer(world):
    try:
        return solve(world)[0]
    except Exception:
        return ()


def run(interleaved: bool, hard: bool = False) -> dict:
    rows = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue                      # non-empty population, as published
        text = surface(case, interleaved, hard)

        collapse = answer(read_content_roles(text))
        _, forced = read_content_roles_checked(text)
        worlds = read_content_roles_worlds(text)
        answers = [answer(w) for w in worlds]
        agree = len(set(answers)) == 1
        certified = agree and certifies_role_independent(text, solve)

        rows.append({
            "seed": s, "want": list(want), "collapse": list(collapse),
            "forced": forced, "n_worlds": len(worlds), "agree": agree,
            "emitted": list(answers[0]) if agree else None,
            "certified": certified,
        })
    return {"interleaved": interleaved, "hard": hard, "rows": rows}


def report(res: dict) -> dict:
    rows = res["rows"]
    n = len(rows)

    def arm(name, decided, given):
        d = [r for r in rows if decided(r)]
        wrong = [r for r in d if given(r) != tuple(r["want"])]
        return {"name": name, "coverage": len(d) / n, "n_decided": len(d),
                "wrong": len(wrong),
                "soundness": 1 - len(wrong) / len(d) if d else float("nan"),
                "accuracy_overall": (len(d) - len(wrong)) / n,
                "wrong_seeds": [r["seed"] for r in wrong][:8]}

    arms = [
        arm("collapse", lambda r: True, lambda r: tuple(r["collapse"])),
        arm("flag", lambda r: r["forced"], lambda r: tuple(r["collapse"])),
        arm("emit", lambda r: r["agree"], lambda r: tuple(r["emitted"])),
        arm("emit+certify", lambda r: r["certified"],
            lambda r: tuple(r["emitted"])),
    ]

    amb = [r for r in rows if not r["forced"]]
    amb_agree = [r for r in amb if r["agree"]]
    # Of the cases the collapsing reader gets WRONG, how many does emission
    # even have a chance on -- i.e. is the ambiguity decision-relevant?
    bad = [r for r in rows if tuple(r["collapse"]) != tuple(r["want"])]
    bad_agree = [r for r in bad if r["agree"]]

    return {"n": n, "arms": arms,
            "ambiguous": len(amb),
            "ambiguous_inert": len(amb_agree) / len(amb) if amb else 0.0,
            "mean_worlds": sum(r["n_worlds"] for r in rows) / n,
            "collapse_wrong": len(bad),
            "collapse_wrong_but_candidates_agree": len(bad_agree)}


def main() -> None:
    _verify_adversarial()
    print("every adversarial variant verified free of declared anchors\n")

    original = dict(S._VARIANTS)
    S._VARIANTS = dict(original)
    for role, extra in ADVERSARIAL.items():
        S._VARIANTS[role] = extra           # all-adversarial: evading forms only
    try:
        out = {}
        for interleaved, hard in ((False, False), (True, False), (True, True)):
            res = run(interleaved, hard)
            rep = report(res)
            label = ("interleaved" if interleaved else "grouped") + (
                " + hard_distractors" if hard else "")
            out[label] = rep
            print(f"=== all-adversarial, {label}   "
                  f"{rep['n']} non-empty cases ===")
            print(f"{'arm':<14} {'coverage':>9} {'wrong':>6} {'soundness':>10} "
                  f"{'acc overall':>12}")
            print("-" * 56)
            for a in rep["arms"]:
                print(f"{a['name']:<14} {a['coverage']:>9.3f} {a['wrong']:>6d} "
                      f"{a['soundness']:>10.4f} {a['accuracy_overall']:>12.3f}")
            print(f"\nrole assignment unforced on {rep['ambiguous']}/{rep['n']}; "
                  f"of those {rep['ambiguous_inert']:.3f} are INERT "
                  f"(all candidates agree). mean {rep['mean_worlds']:.2f} worlds.")
            print(f"collapse is wrong on {rep['collapse_wrong']}, and on "
                  f"{rep['collapse_wrong_but_candidates_agree']} of those the "
                  f"candidates AGREE -- emission cannot help there.\n")
    finally:
        S._VARIANTS = original

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
