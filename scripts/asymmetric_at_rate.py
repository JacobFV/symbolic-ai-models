"""False-positive sensitivity at the rate a reader actually invents, not one at a time.

`scripts/asymmetric_sensitivity.py` inserts **one** false claim into an otherwise
perfect world and finds inventing is cheaper than losing almost everywhere —
`s⁺ < s⁻` in 13 of 15 cases, giving thresholds `θₚ = s⁺/(s⁺+s⁻)` well below 0.5
and the rule "assert freely".

Spending those thresholds on a reader with a graded posterior **hurt**: flood
0.350 → 0.317 end-to-end, scheduling 0.642 → 0.633. So the derivation is right
and its input is wrong, in exactly the way the deletion side was already known to
be wrong: single-perturbation sensitivity understates the cost of the
perturbation **rate** a real reader produces. `link` measured 0.150 per deletion
and 0.625 at the reader's own rate of four — a 4.17x gap — and nothing about that
argument was specific to deletions.

So `s⁺` is re-measured the same way: insert as many false claims of `p` as the
reader actually emits per document, drawn plausibly, and re-derive

    θₚ = sₚ⁺(rate) / (sₚ⁺(rate) + sₚ⁻(rate))

with **both** sides rate-matched, which the first derivation was not.

Predicted before running:

- **`s⁺` rises steeply for the redundant predicates**, the same ones whose `s⁻`
  rose: `link`, `has_capability`, anything the reader emits several of. One
  spurious road is off the best route; four spurious roads include a shortcut
  that is not there.
- **θ moves up toward and past 0.5** for those predicates, inverting the rule
  from "assert freely" to "assert carefully where you assert often".
- The derived rule then stops hurting. If it still hurts with both sides
  rate-matched, the threshold form itself is wrong rather than its inputs, and
  this line closes.

Run: uv run python -u scripts/asymmetric_at_rate.py
"""

from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from symbolic_ai_core.reader.learned import LearnedSpanReader, supervise

from scripts.asymmetric_sensitivity import corrupt_one
from scripts.learned_reader import canonical, induce_schema, key
from scripts.reader_survives import build, domains
from scripts.sensitivity_weights import N_DOCS, N_TRAIN, answer_of

OUT = Path("runs/asymmetric_at_rate.json")
DRAWS = 3


def reader_rates(dom, schema, docs, reader) -> tuple[dict, dict]:
    """How many claims of each predicate the reader invents and loses per doc."""
    fp: dict[str, list[int]] = defaultdict(list)
    fn: dict[str, list[int]] = defaultdict(list)
    for c, o, text in docs:
        gold = {key(x) for x in canonical(c.world.claims, text)}
        got = {key(x) for x in canonical(reader.run(text).delta().claims, text)}
        for pred in {k[0] for k in gold | got}:
            fp[pred].append(len({k for k in got - gold if k[0] == pred}))
            fn[pred].append(len({k for k in gold - got if k[0] == pred}))
    return ({p: statistics.mean(v) for p, v in fp.items()},
            {p: statistics.mean(v) for p, v in fn.items()})


def main() -> None:
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        docs = build(dom, range(1_000_000, 1_000_000 + N_DOCS[name]))
        schema = induce_schema([(c, o) for c, o, _ in
                                build(dom, range(N_TRAIN))])
        train = build(dom, range(N_TRAIN), variants=2)
        reader = LearnedSpanReader(model="logistic").fit(
            [supervise(t, o.spans, c.world.claims) for c, o, t in train])
        fp_rate, fn_rate = reader_rates(dom, schema, docs, reader)

        rng = random.Random(17)
        minus: dict[str, list[int]] = defaultdict(list)
        plus: dict[str, list[int]] = defaultdict(list)
        for c, o, text in docs:
            claims = list(c.world.claims)
            want = answer_of(dom, claims, c, schema)
            pool: dict[str, list[str]] = defaultdict(list)
            for cl in claims:
                for r, v in cl.roles.items():
                    if hasattr(v, "id"):
                        pool[cl.predicate + ":" + r].append(v.id)
            types = {e.id: e.types for e in c.world.entities.values()}
            by_type: dict[tuple, list[str]] = defaultdict(list)
            for eid, ts in types.items():
                by_type[ts].append(eid)
            idx: dict[str, list[int]] = defaultdict(list)
            for i, cl in enumerate(claims):
                idx[cl.predicate].append(i)

            for p, ii in idx.items():
                k_del = max(1, round(fn_rate.get(p, 0.0)))
                k_ins = max(1, round(fp_rate.get(p, 0.0)))
                for _ in range(DRAWS):
                    drop = set(rng.sample(ii, min(k_del, len(ii))))
                    rest = [x for j, x in enumerate(claims) if j not in drop]
                    minus[p].append(answer_of(dom, rest, c, schema) != want)

                    bad = []
                    for src in rng.sample(ii, min(k_ins, len(ii))):
                        b = corrupt_one(claims[src], pool, rng, by_type, types)
                        if b is not None and b.to_dict() != claims[src].to_dict():
                            bad.append(b)
                    if bad:
                        plus[p].append(
                            answer_of(dom, claims + bad, c, schema) != want)

        rows = []
        for p in sorted(minus):
            sm = statistics.mean(minus[p])
            sp = statistics.mean(plus[p]) if plus[p] else float("nan")
            th = sp / (sp + sm) if (sp == sp and sp + sm) else float("nan")
            rows.append({"predicate": p, "s_minus": sm, "s_plus": sp,
                         "theta": th, "k_del": max(1, round(fn_rate.get(p, 0))),
                         "k_ins": max(1, round(fp_rate.get(p, 0))),
                         "fp_rate": fp_rate.get(p, 0.0),
                         "fn_rate": fn_rate.get(p, 0.0)})
        print(f"    {'predicate':<18} {'k-':>3} {'k+':>3} {'s-':>7} {'s+':>7} "
              f"{'theta':>7}")
        for r in rows:
            print(f"    {r['predicate']:<18} {r['k_del']:3d} {r['k_ins']:3d} "
                  f"{r['s_minus']:7.3f} {r['s_plus']:7.3f} {r['theta']:7.3f}")
        results[name] = {"rows": rows}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
