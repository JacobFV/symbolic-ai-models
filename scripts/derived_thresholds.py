"""Assert at the threshold the kernels imply, rather than at 0.5.

`scripts/asymmetric_sensitivity.py` derives a per-predicate assertion threshold
`θₚ = sₚ⁺ / (sₚ⁺ + sₚ⁻)` from the cost of inventing a claim against the cost of
losing one. It spreads 0.000–0.608 in flood. This spends it.

The reader's belief has to be a probability for a threshold to mean anything, so
each arm fits on three quarters of the training documents and calibrates on the
remaining quarter — the same discipline the real-text arm used, and the reason
this could not be run before the calibrator existed.

Measured in the regime where the reader makes mistakes: fitted on **2** phrasing
variants, tested on **4**.

Predicted before running:

- **The derived rule beats 0.5 end-to-end**, most on flood (θ spread 0.608) and
  least on solvency (0.288). Because almost every θₚ is *below* 0.5, the rule
  asserts more, and the measurement says most invented claims are absorbed.
- The gain is in **recall of the answer**, not precision of the claims: claim F1
  should fall slightly while end-to-end accuracy rises. If both rise, the
  threshold is doing something other than what it was derived for.
- Refuted if the derived rule is at or below 0.5's accuracy in every domain,
  which would mean the asymmetry is real but too small to act on, and the whole
  `L_reader = Σ sᵢ Lᵢ` line ends here as a measurement rather than a mechanism.

Run: uv run python -u scripts/derived_thresholds.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_core.reader.learned import LearnedSpanReader, supervise

from scripts.learned_reader import canonical, induce_schema, key, prf
from scripts.learned_reader import world_from_claims
from scripts.reader_survives import build, domains

THETA = Path("runs/asymmetric_sensitivity.json")
OUT = Path("runs/derived_thresholds.json")
N_TRAIN = 400
N_TEST = 120


def evaluate(reader, dom, test, schema, thresholds) -> dict:
    f1s, oks = [], []
    for c, o, text in test:
        gold = {key(x) for x in canonical(c.world.claims, text)}
        res = reader.run(text)
        claims = res.delta(thresholds=thresholds).claims
        f1s.append(prf(gold, {key(x) for x in canonical(claims, text)})[2])
        try:
            want = dom["answer"](c.world, c)
            mine = dom["answer"](world_from_claims(claims, schema), c)
        except Exception:
            want, mine = object(), None
        oks.append(want == mine)
    return {"f1": statistics.mean(f1s), "acc": statistics.mean(oks),
            "n_correct": sum(oks), "n": len(oks)}


def main() -> None:
    if not THETA.exists():
        raise SystemExit(f"{THETA} missing -- run "
                         "scripts/asymmetric_sensitivity.py first. Inventing "
                         "thresholds would make this arm its own control.")
    measured = json.loads(THETA.read_text())
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        theta = {r["predicate"]: r["theta"] for r in measured[name]["rows"]
                 if r["theta"] == r["theta"]}
        print("    theta " + "  ".join(f"{k}={v:.2f}"
                                       for k, v in sorted(theta.items())))
        train = build(dom, range(N_TRAIN), variants=2)
        test = build(dom, range(1_000_000, 1_000_000 + N_TEST))
        schema = induce_schema([(c, o) for c, o, _ in build(dom, range(N_TRAIN))])

        docs = [supervise(t, o.spans, c.world.claims) for c, o, t in train]
        fit_part = [d for i, d in enumerate(docs) if i % 4]
        cal_part = [d for i, d in enumerate(docs) if not i % 4]
        reader = LearnedSpanReader().fit(fit_part)
        reader.calibrate(cal_part)

        rows = {"uniform 0.5": evaluate(reader, dom, test, schema, None),
                "derived theta": evaluate(reader, dom, test, schema, theta)}
        print(f"    {'rule':<16} {'claim F1':>9} {'end-to-end':>11} {'correct':>9}")
        for k, v in rows.items():
            print(f"    {k:<16} {v['f1']:9.3f} {v['acc']:11.3f} "
                  f"{v['n_correct']:4d}/{v['n']}")
        d_acc = rows["derived theta"]["acc"] - rows["uniform 0.5"]["acc"]
        d_f1 = rows["derived theta"]["f1"] - rows["uniform 0.5"]["f1"]
        print(f"    delta  claim F1 {d_f1:+.3f}   end-to-end {d_acc:+.3f}")
        results[name] = {"theta": theta, **rows, "d_acc": d_acc, "d_f1": d_f1}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
