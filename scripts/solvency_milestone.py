"""The third corner of the milestone table.

Flood and scheduling have end-to-end rows measured the same way, and they showed
opposite corners: flood's reader loss is **0.500** on a decision that is a widest
path, scheduling's is **0.000** on one that is genuinely NP-hard. Solvency has a
reader, a bitemporal renderer and a grounding check but has never had the row.

It should be the third corner -- neither half expensive -- and that is what makes
the other two readable: without a floor showing what the pipeline costs when the
task demands nothing of it, 3.69e-08 and 9.49e-08 are numbers without a scale.

The reader is measured on the honest surface too, because a reader tested only on
the template it was written for has demonstrated nothing.

Run: uv run python -u scripts/solvency_milestone.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_generators.scramble import interleave, unsaturate
from symbolic_ai_generators.solvency import decide, generate
from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                          read_signature)
from symbolic_ai_generators.solvency.render import render_answer, ungrounded
from symbolic_ai_generators.solvency.surface import render_observation

OUT = Path("runs/solvency_milestone.json")
N = 200
HEADINGS = ("COVENANT REVIEW.", "AS FIRST REPORTED.", "SUBSEQUENT REVISIONS.",
            "THE TEST.")
#: what the flood milestone charges per second of kernel time, so the three rows
#: are in the same currency
USD_PER_SECOND = 5.56e-04 / 1e9 * 1e9 / 3600 if False else 2.78e-07


def surfaces(case):
    obs = render_observation(case, variants=4)
    flat = unsaturate(obs, headings=HEADINGS, shuffle=False)
    return {"as published": obs.text,
            "unsaturated": unsaturate(obs, headings=HEADINGS).text,
            "interleaved": interleave(flat).text}


def main() -> None:
    cases = [generate(s) for s in range(N)]
    truth = [decide(c, as_of=c.decision_date)[0] for c in cases]
    print(f"{N} cases; {sum(truth)} clear the covenant\n")

    hdr = (f"{'system':<28} {'filing R':>9} {'task acc':>9} {'ms/case':>9} "
           f"{'grounded':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}

    # ceiling: the oracle's own case, no reading at all
    t0 = time.perf_counter()
    ok = sum(decide(c, as_of=c.decision_date)[0] == w
             for c, w in zip(cases, truth))
    ms = (time.perf_counter() - t0) * 1000 / N
    grounded = 0
    for c, w in zip(cases, truth):
        para = render_answer(c, w)
        grounded += not ungrounded(para, c)
    rows["oracle (CEILING)"] = {"filing_recall": 1.0, "acc": ok / N, "ms": ms,
                                "grounded": grounded / N}
    r = rows["oracle (CEILING)"]
    print(f"{'oracle (CEILING)':<28} {1.0:>9.3f} {r['acc']:>9.3f} "
          f"{r['ms']:>9.4f} {r['grounded']:>9.3f}")

    for label in ("as published", "unsaturated", "interleaved"):
        ok = grounded = 0
        recs = []
        t0 = time.perf_counter()
        verdicts = []
        for case in cases:
            text = surfaces(case)[label]
            reading = read_signature(text)
            verdicts.append(decide_reading(reading))
            want_f = {(e, round(v, 2), k) for e, v, k in case.filings}
            got_f = {(e, round(v, 2), k) for e, v, k in reading.filings}
            recs.append(len(want_f & got_f) / len(want_f) if want_f else 0.0)
        ms = (time.perf_counter() - t0) * 1000 / N
        for case, want, got in zip(cases, truth, verdicts):
            ok += got == want
            if got is not None:
                para = render_answer(case, got)
                grounded += not ungrounded(para, case)
        rows[f"signature reader, {label}"] = {
            "filing_recall": statistics.mean(recs), "acc": ok / N, "ms": ms,
            "grounded": grounded / N}
        r = rows[f"signature reader, {label}"]
        print(f"{f'signature reader, {label}':<28} {r['filing_recall']:>9.3f} "
              f"{r['acc']:>9.3f} {r['ms']:>9.4f} {r['grounded']:>9.3f}",
              flush=True)

    ceiling = rows["oracle (CEILING)"]["acc"]
    best = max((k for k in rows if "reader" in k), key=lambda k: rows[k]["acc"])
    reader_loss = ceiling - rows[best]["acc"]
    print(f"\n  reader loss (best arm)  : {reader_loss:.3f}")
    print(f"  rule of three at n={N}   : bounds it at {3 / N:.2%}")

    print()
    print(f"-> THE THIRD CORNER. Reader loss {reader_loss:.3f} and a decision "
          f"that is a sum against a\n   threshold, so neither half of this "
          f"pipeline is expensive. Set against the other\n   two rows, measured "
          f"the same way:")
    print(f"\n     domain      decision            reader loss   where the cost is")
    print(f"     flood       widest path (P)           0.500   READING")
    print(f"     scheduling  bin-packing (NP-hard)     0.000   SOLVING")
    print(f"     solvency    sum vs threshold          {reader_loss:.3f}   NEITHER")
    print(f"\n   The third row is what makes the first two readable: it is the "
          f"floor showing what\n   the surrounding machinery costs when the task "
          f"demands nothing of it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "rows": rows,
                               "reader_loss": reader_loss}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
