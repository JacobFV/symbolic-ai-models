"""`s_i` measured by intervention, and the failure model it licenses.

`scripts/which_claims_matter.py` tried to read downstream sensitivity off the
correlation between a predicate's recall and whether the answer came out right.
It cannot work, and the reason is worth keeping: the load-bearing predicates in
flood are recovered at recall 1.000 on **every** document, so they have no
variance and rank nothing, AUC 0.500 by construction. An observational estimate
of importance is confounded by how hard each claim is to read.

So intervene. For each document and each claim in the **gold** world, delete that
claim and re-run the kernels:

    s_p = P(the answer changes | one claim of predicate p is deleted)

That is sensitivity with the reader taken out of it entirely -- a property of the
task, not of any reader. It is what `L_reader = sum_i s_i L_i` needs, and it is
reusable: any reader's expected failure can be predicted from its own per-claim
error rates and this one vector.

Then the model gets tested rather than assumed. With `q_p` the reader's
per-predicate error rate and `n_p` the number of claims of that predicate per
document,

    P(failure) ~= 1 - prod_p (1 - s_p)^(n_p q_p)

is compared against the failure rate that reader actually suffers.

Predicted before running:

- `s_p` is far from uniform. In flood, deleting a `link` should flip the answer
  much more often than deleting a `mass`, because reachability gates the whole
  computation while a mass only matters for the vehicle that turns out to be
  marginal. In solvency, deleting a `revenue` should flip far more than an
  `owns`, since a member with no filing contributes nothing to the sum either
  way. If `s_p` comes out flat, the weighted objective has nothing to buy and
  step 6 of the critical path should be dropped.
- The independence model **overestimates** failure, because reader errors are
  correlated within a document (a phrasing it cannot parse costs the whole
  paragraph) and because some deletions are recoverable from the rest of the
  world. Predicted overestimate by a factor of 1.2-2.5.

Run: uv run python -u scripts/sensitivity_weights.py
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from symbolic_ai_core.world import WorldSnapshot

from scripts.learned_reader import canonical, induce_schema, world_from_claims
from scripts.reader_survives import build, domains, fit_on
from scripts.which_claims_matter import by_predicate

OUT = Path("runs/sensitivity_weights.json")
N_TRAIN = 400
#: flood re-solves an ASP+SMT flow once per deleted claim, so it gets fewer
#: documents rather than a cheaper oracle.
N_DOCS = {"solvency": 40, "scheduling": 40, "flood": 20}


def answer_of(dom, claims, case, schema):
    try:
        return dom["answer"](world_from_claims(claims, schema), case)
    except Exception:
        return _UNANSWERABLE


class _Unanswerable:
    def __repr__(self):
        return "<unanswerable>"


_UNANSWERABLE = _Unanswerable()


def measure_s(dom, docs, schema) -> dict[str, dict]:
    """Leave-one-claim-out on the gold world. No reader involved."""
    flips: dict[str, list[int]] = defaultdict(list)
    for c, o, text in docs:
        claims = list(c.world.claims)
        want = answer_of(dom, claims, c, schema)
        for i, claim in enumerate(claims):
            rest = claims[:i] + claims[i + 1:]
            flips[claim.predicate].append(answer_of(dom, rest, c, schema) != want)
    return {p: {"s": statistics.mean(v), "n_interventions": len(v)}
            for p, v in flips.items()}


def measure_q(dom, reader, docs, schema):
    """The reader's per-predicate error rate, and what it actually costs."""
    err: dict[str, list[float]] = defaultdict(list)
    count: dict[str, list[int]] = defaultdict(list)
    oks = []
    for c, o, text in docs:
        gold = by_predicate(canonical(c.world.claims, text))
        got = by_predicate(canonical(reader.run(text).delta().claims, text))
        for p, g in gold.items():
            err[p].append(1.0 - len(g & got[p]) / len(g))
            count[p].append(len(g))
        want = answer_of(dom, c.world.claims, c, schema)
        oks.append(answer_of(dom, reader.run(text).delta().claims, c, schema)
                   == want)
    return ({p: statistics.mean(v) for p, v in err.items()},
            {p: statistics.mean(v) for p, v in count.items()},
            1.0 - statistics.mean(oks))


def main() -> None:
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        n = N_DOCS[name]
        train_full = build(dom, range(N_TRAIN))
        schema = induce_schema([(c, o) for c, o, _ in train_full])
        docs = build(dom, range(1_000_000, 1_000_000 + n))

        s = measure_s(dom, docs, schema)
        reader, _ = fit_on(build(dom, range(N_TRAIN), variants=2))
        q, cnt, failure = measure_q(dom, reader, docs, schema)

        pred = 1.0
        for p, row in s.items():
            pred *= (1.0 - row["s"]) ** (cnt.get(p, 0.0) * q.get(p, 0.0))
        pred = 1.0 - pred

        print(f"    {'predicate':<18} {'s_p':>7} {'n_p':>6} {'q_p':>7} "
              f"{'n q s':>8}")
        for p in sorted(s, key=lambda x: -s[x]["s"]):
            contrib = cnt.get(p, 0) * q.get(p, 0) * s[p]["s"]
            print(f"    {p:<18} {s[p]['s']:7.3f} {cnt.get(p, 0):6.1f} "
                  f"{q.get(p, 0):7.3f} {contrib:8.3f}")
        spread = max(v["s"] for v in s.values()) - min(v["s"] for v in s.values())
        print(f"    s_p spread {spread:.3f}   "
              f"predicted failure {pred:.3f} vs measured {failure:.3f}"
              f"   ratio {pred / failure if failure else float('nan'):.2f}")
        results[name] = {"s": s, "q": q, "n": cnt, "predicted_failure": pred,
                         "measured_failure": failure, "n_docs": n}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
