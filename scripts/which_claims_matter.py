"""Which claims the answer actually depends on -- the weights `s_i`, measured.

The reader's objective should not be claim F1. F1 counts every claim equally and
the kernels do not: some claims are load-bearing and some are furniture. The
programme's formal statement of this is

    P(failure) ~= sum_i p_i s_i

where `p_i` is the reader's probability of getting claim `i` wrong and `s_i` is
downstream sensitivity to that error, giving a training objective
`L_reader = sum_i s_i L_i` -- backpropagating importance from the symbolic
computation into the reader without differentiating through the kernels.

`s_i` has been an assumption. This measures it, per predicate, on a reader that
makes real mistakes: fitted on **2 phrasing variants** and tested on **4**, so
half the held-out sentences are worded in a way the fit never saw. For each
document the per-predicate recall is recorded alongside whether the kernels then
got the right answer, and the statistic is

    AUC(recall of predicate p  ->  answer correct)

a predicate whose recall ranks correct documents above incorrect ones at 0.9 is
carrying the answer; one at 0.5 is not being used.

Predicted before running: in flood the quantity predicates that feed the SMT step
(`mass`, `capacity`, `load_limit`, `demand`) rank highest and `link` is close
behind, since reachability gates everything; `bridge_on` should matter only
through `load_limit`. In solvency `revenue` should dominate `owns`, because a
missing member with no filings changes no sum. In scheduling `duration` and
`capacity` should lead. The prediction that would be most interesting to lose is
the flood one: if `link` outranks the quantities, the answer is gated by
structure rather than by arithmetic and the reader's effort belongs elsewhere.

Run: uv run python -u scripts/which_claims_matter.py
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from scripts.learned_reader import auc, canonical, induce_schema, world_from_claims
from scripts.reader_survives import build, domains, fit_on

OUT = Path("runs/which_claims_matter.json")
N_TRAIN = 400
N_TEST = 120


def by_predicate(claims):
    out = defaultdict(set)
    for c in claims:
        out[c.predicate].add(_k(c))
    return out


def _k(c):
    from symbolic_ai_core.world import EntityRef, Quantity
    parts = []
    for r in sorted(c.roles):
        v = c.roles[r]
        parts.append((r, v.id if isinstance(v, EntityRef)
                      else round(float(v.value), 2) if isinstance(v, Quantity)
                      else str(v).lower()))
    return (c.predicate, tuple(parts), c.transaction_time.start)


def main() -> None:
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        train = build(dom, range(N_TRAIN), variants=2)
        test = build(dom, range(1_000_000, 1_000_000 + N_TEST))
        schema = induce_schema([(c, o) for c, o, _ in
                                build(dom, range(N_TRAIN))])
        reader, _ = fit_on(train)

        recs: dict[str, list[float]] = defaultdict(list)
        oks: list[bool] = []
        for c, o, text in test:
            gold = by_predicate(canonical(c.world.claims, text))
            res = reader.run(text)
            got = by_predicate(canonical(res.delta().claims, text))
            for p, g in gold.items():
                recs[p].append(len(g & got[p]) / len(g))
            try:
                want = dom["answer"](c.world, c)
                mine = dom["answer"](
                    world_from_claims(res.delta().claims, schema), c)
            except Exception:
                want, mine = object(), None
            oks.append(want == mine)

        rows = []
        for p, r in sorted(recs.items()):
            pos = [x for x, k in zip(r, oks) if k]
            neg = [x for x, k in zip(r, oks) if not k]
            rows.append({"predicate": p, "mean_recall": statistics.mean(r),
                         "auc": auc(pos, neg),
                         "perfect_share": sum(1 for x in r if x == 1.0) / len(r)})
        rows.sort(key=lambda x: (-(x["auc"] if x["auc"] == x["auc"] else -1)))
        print(f"    answered correctly {sum(oks)}/{len(oks)} = "
              f"{statistics.mean(oks):.3f}")
        print(f"    {'predicate':<18} {'recall':>8} {'perfect':>8} "
              f"{'AUC(rec->ok)':>13}")
        for x in rows:
            a = f"{x['auc']:.3f}" if x["auc"] == x["auc"] else "  --"
            print(f"    {x['predicate']:<18} {x['mean_recall']:8.3f} "
                  f"{x['perfect_share']:8.3f} {a:>13}")
        results[name] = {"acc": statistics.mean(oks), "rows": rows}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
