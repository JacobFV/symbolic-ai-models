"""The third domain, and the same defect for the third time.

Solvency's one distractor is *"A former subsidiary, sub_99, was divested before
the period and does not consolidate"* -- and ``sub_99`` appears **nowhere else**.
It is inert twice over: one entity, so it matches no reader branch, and no
filings, so admitting the ownership would sum to nothing. Flood's disused track
drew its endpoints from outside the network; scheduling's withdrawn machine
carried no capability. Three domains, one defect, and in each case the vocabulary
or the shape rejects the distractor **for free**.

Point them at entities that matter: a divested subsidiary that **files**, and a
withdrawn figure dated inside the window. Each in two phrasings -- one carrying a
declared cancellation word, one carrying none. The **uncued** arm is the honest
floor for `symbolic_ai_generators.staleness`; writing only cued distractors would
decide the experiment.

Run: uv run python -u scripts/solvency_hard_distractors.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency import surface as S
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature, read_signature_consolidated)
from symbolic_ai_generators.staleness import (filter_stale,
                                              stale_by_cancellation)

OUT = Path("runs/solvency_hard_distractors.json")
N = 200


def run(hard, cue: str, gate, reader=read_signature,
        scale: float = 0.5) -> dict:
    rows = []
    for s in range(N):
        case = generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = S.render_observation(case, variants=4, hard_distractors=hard,
                                    cue=cue, hard_scale=scale).text
        if gate:
            text = filter_stale(text, gate)
        got = decide_reading(reader(text))
        rows.append((want, got))
    wrong = [(w, g) for w, g in rows if w != g]
    return {
        "accuracy": 1 - len(wrong) / len(rows),
        "false_true": sum(1 for w, g in wrong if g and not w),
        "false_false": sum(1 for w, g in wrong if not g and w),
    }


def main() -> None:
    readers = {"published": read_signature,
               "consolidated": read_signature_consolidated}
    gates = {"none": None, "cancellation": stale_by_cancellation}
    arms = [("clean (default distractor)", False, "cued"),
            ("hard owns+filing, CUED", True, "cued"),
            ("hard owns+filing, UNCUED", True, "uncued"),
            ("hard owns only, UNCUED", "owns", "uncued"),
            ("hard filing only, UNCUED", "filing", "uncued")]

    out = {}
    cols = [(rn, gn) for rn in readers for gn in gates]
    print(f"{'arm':<30} " + "".join(f"{rn[:4]}/{gn[:6]:>7}" for rn, gn in cols))
    print("-" * (30 + 12 * len(cols)))
    for label, hard, cue in arms:
        cells = {(rn, gn): run(hard, cue, gates[gn], readers[rn])
                 for rn, gn in cols}
        out[label] = {f"{rn}+{gn}": v for (rn, gn), v in cells.items()}
        print(f"{label:<30} " + "".join(
            f"{cells[c]['accuracy']:>7.3f}({cells[c]['false_true']:>3})"
            for c in cols))

    print(f"\n{N} cases. (nT) counts FALSE-TRUE answers -- the unsound "
          "direction,\nwhere an admitted claim inflates the consolidated sum. "
          "Majority floor 0.550.")

    # The injected figure sets the damage, so the headline above is a property
    # of the injection as much as of the reader. Dose-response, published reader,
    # no gate, the uncued owns+filing arm:
    print(f"\n{'spurious figure / threshold':<30} {'accuracy':>10} "
          f"{'false TRUE':>12} {'false FALSE':>13}")
    print("-" * 67)
    out["dose"] = {}
    for scale in (0.05, 0.1, 0.25, 0.5):
        r = run(True, "uncued", None, read_signature, scale)
        out["dose"][scale] = r
        print(f"{scale:<30.2f} {r['accuracy']:>10.3f} {r['false_true']:>12d} "
              f"{r['false_false']:>13d}")
    print("U-SHAPED, and for a reason: the withdrawn-figure distractor is dated\n"
          "the decision date, so it REPLACES the member's real filing. A small\n"
          "spurious figure lowers the sum (false FALSE); a large one raises it\n"
          "(false TRUE). Third instance of opposite-signed evidence in this repo.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
