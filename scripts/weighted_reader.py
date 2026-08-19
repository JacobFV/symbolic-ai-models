"""`L_reader = Σ sᵢ Lᵢ`, run against uniform weighting on the same fit.

The measured sensitivities say uniform weighting is wrong: flood's predicates
span 6.6x in how often deleting one of them changes the answer. This is the arm
that asks whether knowing that is worth anything.

The classifier's mistake-driven update is scaled by the downstream sensitivity of
the labels it confused — priced at the max of the two, because missing a
load-bearing claim and inventing one are both errors against it. Nothing on the
other side of the boundary has to be differentiable; the weights come from
deleting gold claims and re-running the kernels.

Measured in the regime where the reader makes mistakes: fitted on **2** phrasing
variants, tested on **4**.

Predicted before running:

- **End-to-end accuracy rises and claim F1 does not.** That is the whole claim.
  If both rise, weighting is just a better-tuned classifier and says nothing
  about sensitivity; if F1 rises and accuracy does not, the weights are pointing
  at the wrong claims.
- The gain tracks the spread of `sₚ`: largest on flood (6.6x), small on solvency
  (1.7x) and scheduling (2.0x).
- Refuted by no movement anywhere, which would mean the classifier's errors are
  not on a margin any reweighting can reach — plausible, since a phrasing it has
  never seen is not a close call.

Run: uv run python -u scripts/weighted_reader.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from symbolic_ai_core.reader.learned import LearnedSpanReader, supervise

from scripts.learned_reader import auc, canonical, induce_schema, key, prf
from scripts.learned_reader import world_from_claims
from scripts.reader_survives import build, domains

#: Which sensitivity estimate to weight by. `sensitivity_weights.json` deletes
#: one claim; `sensitivity_at_rate.json` deletes the reader's own share, which
#: is 4.17x larger for flood's `link` and is the estimate that respects
#: redundancy. Pass a path to compare them.
WEIGHTS = Path(sys.argv[1] if len(sys.argv) > 1
               else "runs/sensitivity_weights.json")
OUT = Path("runs/weighted_reader.json"
           if len(sys.argv) < 2 else
           f"runs/weighted_reader_{Path(sys.argv[1]).stem}.json")
N_TRAIN = 400
N_TEST = 120


def normalised(s: dict) -> dict[str, float]:
    """Mean 1, so the weighted fit differs in SHAPE and not in learning rate.

    Without this the weighted arm would also be training with a smaller step and
    any difference would be confounded with it.
    """
    raw = {p: row["s"] for p, row in s.items()}
    m = statistics.mean(raw.values())
    return {p: v / m for p, v in raw.items()}


def evaluate(reader, dom, test, schema) -> dict:
    f1s, oks = [], []
    for c, o, text in test:
        gold = {key(x) for x in canonical(c.world.claims, text)}
        res = reader.run(text)
        got = {key(x) for x in canonical(res.delta().claims, text)}
        f1s.append(prf(gold, got)[2])
        try:
            want = dom["answer"](c.world, c)
            mine = dom["answer"](world_from_claims(res.delta().claims, schema), c)
        except Exception:
            want, mine = object(), None
        oks.append(want == mine)
    pos = [f for f, k in zip(f1s, oks) if k]
    neg = [f for f, k in zip(f1s, oks) if not k]
    return {"f1": statistics.mean(f1s), "acc": statistics.mean(oks),
            "auc": auc(pos, neg), "n_correct": sum(oks), "n": len(oks)}


def main() -> None:
    if not WEIGHTS.exists():
        raise SystemExit(
            f"{WEIGHTS} is missing. Run scripts/sensitivity_weights.py first -- "
            "this arm has no meaning with invented weights, and defaulting to "
            "uniform would make it silently the control.")
    measured = json.loads(WEIGHTS.read_text())
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        w = normalised(measured[name]["s"])
        print("    weights " + "  ".join(f"{p}={v:.2f}"
                                         for p, v in sorted(w.items())))
        test = build(dom, range(1_000_000, 1_000_000 + N_TEST))
        schema = induce_schema([(c, o) for c, o, _ in build(dom, range(N_TRAIN))])
        results[name] = {"weights": w}

        # Two failure regimes, because the hypothesis is about WHICH ONE
        # reweighting can reach. Out of distribution the classifier has no
        # feature that fires and the decision is not close; thin evidence is
        # made of close decisions, which is where a cost can move a boundary.
        for regime, train in (
                ("unseen phrasings", build(dom, range(N_TRAIN), variants=2)),
                ("thin evidence", build(dom, range(6)))):
            docs = [supervise(t, o.spans, c.world.claims) for c, o, t in train]
            rows = {}
            for arm, weights in (("uniform", None),
                                 ("sensitivity-weighted", w)):
                reader = LearnedSpanReader(weights=weights).fit(docs)
                rows[arm] = evaluate(reader, dom, test, schema)
            d_f1 = rows["sensitivity-weighted"]["f1"] - rows["uniform"]["f1"]
            d_acc = rows["sensitivity-weighted"]["acc"] - rows["uniform"]["acc"]
            print(f"    -- {regime}")
            for arm, r in rows.items():
                print(f"       {arm:<22} F1 {r['f1']:6.3f}  "
                      f"end-to-end {r['acc']:6.3f}  {r['n_correct']:3d}/{r['n']}")
            print(f"       delta  F1 {d_f1:+.3f}   end-to-end {d_acc:+.3f}")
            results[name][regime] = {**rows, "d_f1": d_f1, "d_acc": d_acc}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
