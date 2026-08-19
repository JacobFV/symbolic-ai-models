"""Sensitivity measured at the rate the reader actually errs, not one claim at a time.

`scripts/sensitivity_weights.py` deletes **one** gold claim and asks whether the
answer changes. Training on those weights raises claim F1 in all three domains
and *lowers* flood's end-to-end accuracy by 0.075 — the largest-spread domain,
which is the one it was supposed to help most.

The diagnosis is in the previous finding, written before this arm ran: flood's
`link` has the **lowest** single-deletion sensitivity in the domain (0.144)
because the road network is cyclic and redundant, and the **highest** total
contribution, because there are eight of them and the reader loses half. Single
deletion is the wrong estimator for a redundant predicate: one missing edge is
routed around, four missing edges are not.

So measure sensitivity at the rate the reader actually errs. For each document
and predicate, delete `round(nₚ qₚ)` of its claims — `qₚ` from the reader being
trained — over several random draws:

    sₚ^eff = P(the answer changes | the reader's own share of p is missing)

Predicted before running:

- `sₚ^eff / sₚ` is **large for redundant predicates and ≈1 for singletons**.
  flood's `link` should rise steeply (8 claims, half lost); `depot`, `needs` and
  `demand` are single claims so deleting `nq` of them is deleting one, and the
  ratio must be exactly 1 by construction — that is the control built into the
  measurement.
- Ranking by `sₚ^eff` should put `link` at or near the top of flood, inverting
  the single-deletion order.
- Refuted if `link` stays low, which would mean the redundancy is real at every
  loss rate and flood's end-to-end drop has some other cause.

Run: uv run python -u scripts/sensitivity_at_rate.py
"""

from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from scripts.learned_reader import induce_schema
from scripts.reader_survives import build, domains, fit_on
from scripts.sensitivity_weights import N_DOCS, N_TRAIN, answer_of, measure_q

OUT = Path("runs/sensitivity_at_rate.json")
DRAWS = 4


def main() -> None:
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        docs = build(dom, range(1_000_000, 1_000_000 + N_DOCS[name]))
        schema = induce_schema([(c, o) for c, o, _ in
                                build(dom, range(N_TRAIN))])
        reader, _ = fit_on(build(dom, range(N_TRAIN), variants=2))
        q, cnt, failure = measure_q(dom, reader, docs, schema)

        rng = random.Random(11)
        flips: dict[str, list[int]] = defaultdict(list)
        single: dict[str, list[int]] = defaultdict(list)
        for c, o, text in docs:
            claims = list(c.world.claims)
            want = answer_of(dom, claims, c, schema)
            idx: dict[str, list[int]] = defaultdict(list)
            for i, cl in enumerate(claims):
                idx[cl.predicate].append(i)
            for p, ii in idx.items():
                k = max(1, round(len(ii) * q.get(p, 0.0)))
                for _ in range(DRAWS):
                    drop = set(rng.sample(ii, min(k, len(ii))))
                    rest = [x for j, x in enumerate(claims) if j not in drop]
                    flips[p].append(answer_of(dom, rest, c, schema) != want)
                one = {rng.choice(ii)}
                rest = [x for j, x in enumerate(claims) if j not in one]
                single[p].append(answer_of(dom, rest, c, schema) != want)

        rows = []
        for p in sorted(flips, key=lambda x: -statistics.mean(flips[x])):
            s1 = statistics.mean(single[p])
            se = statistics.mean(flips[p])
            rows.append({"predicate": p, "s_single": s1, "s_eff": se,
                         "k": max(1, round(cnt.get(p, 0) * q.get(p, 0.0))),
                         "n": cnt.get(p, 0), "q": q.get(p, 0.0),
                         "ratio": se / s1 if s1 else float("inf")})
        print(f"    reader failure {failure:.3f}")
        print(f"    {'predicate':<18} {'n':>5} {'q':>6} {'k':>3} "
              f"{'s_single':>9} {'s_eff':>7} {'ratio':>7}")
        for r in rows:
            print(f"    {r['predicate']:<18} {r['n']:5.1f} {r['q']:6.3f} "
                  f"{r['k']:3d} {r['s_single']:9.3f} {r['s_eff']:7.3f} "
                  f"{r['ratio']:7.2f}")
        results[name] = {"rows": rows, "measured_failure": failure,
                         "s": {r["predicate"]: {"s": r["s_eff"]} for r in rows}}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
