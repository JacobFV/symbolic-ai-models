"""Deleting a claim and inventing one are not the same error, and the gap is the threshold.

The sensitivity-weighted objective failed as a training weight because a
margin-scaled update over-predicts the upweighted class: it protects a critical
claim by inventing it. The finding named the fix as "a calibrated loss and a
separate, higher price on false positives". This derives that price rather than
assuming it, and turns it into the one thing a reader actually controls — **when
to assert**.

`sₚ` as measured is a *deletion* sensitivity: `P(answer changes | one claim of p
is removed)`. Its mirror was never measured:

    sₚ⁻ = P(answer changes | one true claim of p is DELETED)      [known]
    sₚ⁺ = P(answer changes | one FALSE claim of p is INSERTED)    [this]

If they are equal, sensitivity **cancels** in the decision rule — a false
negative and a false positive cost the same, so the optimal threshold is 0.5 for
every predicate and no amount of weighting can help. If they differ, expected
cost is minimised by asserting when

    b > θₚ = sₚ⁺ / (sₚ⁺ + sₚ⁻)

with `b` a calibrated probability. That is a per-predicate threshold **derived**
from the kernels rather than tuned, and it is the form in which downstream
importance can reach a reader without deforming its training.

Predicted before running:

- **The asymmetry is large and signed the way redundancy predicts.** flood's
  `link` absorbs a deletion (sₚ⁻ = 0.144: the road network is cyclic) but a
  *false* road creates a route that does not exist and cannot be absorbed, so
  sₗᵢₙₖ⁺ should be far higher — 0.4 or more — giving θ well above 0.5 and the
  rule "be conservative about asserting roads".
- **Singleton predicates are symmetric.** `depot`, `needs`, `demand` are one
  claim each; deleting the only one and inserting a wrong one both destroy the
  query, so θ ≈ 0.5 and the rule changes nothing for them.
- If every θₚ lands near 0.5, sensitivity genuinely cancels, the decision rule is
  uniform, and the whole `L_reader = Σ sᵢ Lᵢ` line should be closed rather than
  reformulated.

Run: uv run python -u scripts/asymmetric_sensitivity.py
"""

from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from symbolic_ai_core.world import Claim, EntityRef, Quantity

from scripts.learned_reader import induce_schema
from scripts.reader_survives import build, domains
from scripts.sensitivity_weights import N_DOCS, N_TRAIN, answer_of

OUT = Path("runs/asymmetric_sensitivity.json")
DRAWS = 3


def corrupt_one(claim: Claim, pool: dict[str, list[str]], rng,
                by_type: dict[str, list[str]] | None = None,
                types: dict[str, tuple] | None = None) -> Claim | None:
    """One plausible falsehood: a role re-pointed at another entity of its kind,
    or a quantity perturbed. Plausible matters -- a claim about an entity that
    appears nowhere is a false positive no reader would produce and no kernel
    would be fooled by.
    """
    ents = [r for r, v in claim.roles.items() if isinstance(v, EntityRef)]
    quants = [r for r, v in claim.roles.items() if isinstance(v, Quantity)]
    if ents and rng.random() < 0.6:
        role = rng.choice(ents)
        cur = claim.roles[role].id
        same = [e for e in pool.get(claim.predicate + ":" + role, [])
                if e != cur]
        if not same and by_type is not None and types is not None:
            # A singleton role -- flood's `depot` and `needs` name one region
            # each -- has no same-role alternative, so the substitute is drawn
            # from entities of the SAME TYPE in the same world. Without this the
            # two predicates whose false positives did the damage in the
            # weighted-objective arm are exactly the two that cannot be measured.
            same = [e for e in by_type.get(types.get(cur, ()), [])
                    if e != cur]
        if same:
            return Claim(predicate=claim.predicate,
                         roles={**claim.roles, role: EntityRef(rng.choice(same))},
                         valid_time=claim.valid_time,
                         transaction_time=claim.transaction_time)
    if quants:
        role = rng.choice(quants)
        q = claim.roles[role]
        factor = rng.choice((0.5, 0.7, 1.4, 2.0))
        return Claim(predicate=claim.predicate,
                     roles={**claim.roles,
                            role: Quantity(value=q.value * factor, unit=q.unit)},
                     valid_time=claim.valid_time,
                     transaction_time=claim.transaction_time)
    return None


def main() -> None:
    results = {}
    for name, dom in domains().items():
        print(f"\n=== {name}")
        docs = build(dom, range(1_000_000, 1_000_000 + N_DOCS[name]))
        schema = induce_schema([(c, o) for c, o, _ in
                                build(dom, range(N_TRAIN))])
        rng = random.Random(5)
        minus: dict[str, list[int]] = defaultdict(list)
        plus: dict[str, list[int]] = defaultdict(list)
        for c, o, text in docs:
            claims = list(c.world.claims)
            want = answer_of(dom, claims, c, schema)
            pool: dict[str, list[str]] = defaultdict(list)
            for cl in claims:
                for r, v in cl.roles.items():
                    if isinstance(v, EntityRef):
                        pool[cl.predicate + ":" + r].append(v.id)
            types = {e.id: e.types for e in c.world.entities.values()}
            by_type: dict[tuple, list[str]] = defaultdict(list)
            for eid, ts in types.items():
                by_type[ts].append(eid)
            for i, cl in enumerate(claims):
                rest = claims[:i] + claims[i + 1:]
                minus[cl.predicate].append(
                    answer_of(dom, rest, c, schema) != want)
                for _ in range(DRAWS):
                    bad = corrupt_one(cl, pool, rng, by_type, types)
                    if bad is None or bad.to_dict() == cl.to_dict():
                        continue
                    plus[cl.predicate].append(
                        answer_of(dom, claims + [bad], c, schema) != want)

        rows = []
        for p in sorted(minus):
            sm = statistics.mean(minus[p])
            sp = statistics.mean(plus[p]) if plus[p] else float("nan")
            theta = sp / (sp + sm) if (sp == sp and sp + sm) else float("nan")
            rows.append({"predicate": p, "s_minus": sm, "s_plus": sp,
                         "theta": theta,
                         "ratio": (sp / sm) if sm else float("inf")})
        print(f"    {'predicate':<18} {'s- (delete)':>12} {'s+ (invent)':>12} "
              f"{'ratio':>7} {'theta':>7}")
        for r in rows:
            print(f"    {r['predicate']:<18} {r['s_minus']:12.3f} "
                  f"{r['s_plus']:12.3f} {r['ratio']:7.2f} {r['theta']:7.3f}")
        spread = max(r["theta"] for r in rows) - min(r["theta"] for r in rows)
        print(f"    theta spread {spread:.3f} "
              f"({'a uniform 0.5 rule is wrong' if spread > 0.15 else
                  'sensitivity cancels; a uniform rule is right'})")
        results[name] = {"rows": rows, "theta_spread": spread}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
