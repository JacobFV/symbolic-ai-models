"""Can insensitivity rescue the arm detection cannot see?

Today's floor is the **uncued** divested-filer distractor: *"sub_98 left the
group in April"* is semantically stale, carries no declared cue, and has the
ownership signature exactly. The staleness gate cannot see it and neither can any
arity check, because `owns` is multi-valued. Accuracy 0.485, unmoved by every
combination built.

The other response to a corrupt channel is answer-insensitivity: refuse to decide
whether the membership is real, and prove the verdict does not depend on it. That
is available here and vacuous on the revenue channel, because dropping a *member*
moves the sum by one filing where dropping a *filing* always moves it.

Reports coverage and soundness on four surfaces, and what actually sets the
coverage -- which is not the margin but the **one-sidedness**: dropping a member
can only lower the sum.

Run: uv run python -u scripts/solvency_membership_certificate.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as S
from symbolic_ai_generators.solvency.certificate import (
    certifies_membership_insensitive)
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature, read_signature_consolidated)

OUT = Path("runs/solvency_membership_certificate.json")
N = 200


def run(hard, cue, reader) -> dict:
    rows = []
    for s in range(N):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = S.render_observation(case, variants=4, hard_distractors=hard,
                                    cue=cue).text
        r = reader(text)
        rows.append({"want": want, "got": decide_reading(r),
                     "cert": certifies_membership_insensitive(r)})
    n = len(rows)
    certified = [x for x in rows if x["cert"]]
    wrong_all = [x for x in rows if x["got"] != x["want"]]
    wrong_cert = [x for x in certified if x["got"] != x["want"]]
    return {
        "n": n,
        "accuracy": 1 - len(wrong_all) / n,
        "coverage": len(certified) / n,
        "accuracy_certified": (1 - len(wrong_cert) / len(certified)
                               if certified else float("nan")),
        "wrong_certified": len(wrong_cert),
    }


def main() -> None:
    arms = [
        ("clean surface", False, "cued", read_signature),
        ("hard owns, UNCUED (published reader)", "owns", "uncued",
         read_signature),
        ("hard owns, UNCUED (consolidated)", "owns", "uncued",
         read_signature_consolidated),
        ("hard owns+filing, UNCUED (consolidated)", True, "uncued",
         read_signature_consolidated),
    ]
    out = {}
    print(f"{'arm':<42} {'acc':>7} {'coverage':>9} {'acc|cert':>9} "
          f"{'wrong|cert':>11}")
    print("-" * 82)
    for label, hard, cue, reader in arms:
        r = run(hard, cue, reader)
        out[label] = r
        print(f"{label:<42} {r['accuracy']:>7.3f} {r['coverage']:>9.3f} "
              f"{r['accuracy_certified']:>9.3f} {r['wrong_certified']:>11d}")

    # What sets the coverage, and it is not the margin: the check is ONE-SIDED.
    # Removing a member can only LOWER the sum, so a verdict of False survives
    # every deletion for free, and a verdict of True survives only when no
    # single member's filing covers the margin.
    truth = [decide(generate(s), as_of=generate(s).decision_date)[0]
             for s in range(N)]
    false_share = 1 - statistics.mean(truth)
    rows = []
    for s in range(N):
        case = generate(s)
        r = read_signature(S.render_observation(case, variants=4).text)
        rows.append((decide_reading(r), certifies_membership_insensitive(r)))
    fires_false = statistics.mean(c for v, c in rows if v is False)
    fires_true = statistics.mean(c for v, c in rows if v is True)
    print(f"\nfalse-verdict share {false_share:.3f}; the certificate fires on "
          f"{fires_false:.3f} of them\nand on {fires_true:.3f} of the true "
          f"ones. IT IS THE MONOTONE HALF: dropping a member\ncan only lower "
          "the sum, so 'below threshold' is free and 'above' almost never.")
    out["false_share"] = false_share
    out["fires_on_false"] = fires_false
    out["fires_on_true"] = fires_true

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
