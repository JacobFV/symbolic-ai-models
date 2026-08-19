"""Which reconstruction errors matter: influence-weighted, not counted.

The strategic frame asks **what information must be recovered, with what
fidelity**. Ordinary claim precision/recall answers neither: it treats every fact
as equally valuable, and this repo already measured a reader at **0.998 claim
recall and 0.500 accuracy**, because its failure was a claim it *added* and recall
cannot see a false positive.

The formalism is ``X --R--> W_hat --K--> Y`` with ``W1 ~_K W2 iff K(W1)=K(W2)``.
The reader does not need ``W_hat = W``; it needs ``W_hat ~_K W``. So define, by
**intervention on the true world**:

- a missing claim is **influential** if deleting it from ``W`` changes ``K(W)``;
- a spurious claim is **influential** if adding it to ``W`` changes ``K(W)``.

**Critical error mass** is the count of influential claims in the symmetric
difference. The claim under test is that ``W_hat ~_K W`` iff that mass is zero --
in which case it is not a predictor but a *characterisation* of the equivalence
class.

Compared against the obvious baselines: claim recall, claim precision, and the
raw size of the symmetric difference.

Run: uv run python -u scripts/influence_weighted.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/influence_weighted.json")
N = 200


def key(claim) -> tuple:
    roles = []
    for name in sorted(claim.roles):
        r = claim.roles[name]
        roles.append((name, r.id if hasattr(r, "id")
                      else (float(r.value) if hasattr(r, "value") else str(r))))
    return (claim.predicate, tuple(roles))


def answer(world):
    try:
        return solve(world)[0]
    except Exception:
        return None


def auc(scores_pos, scores_neg) -> float:
    """P(a positive scores below a negative), ties at 0.5 -- lower is better here."""
    if not scores_pos or not scores_neg:
        return float("nan")
    wins = sum((p < n) + 0.5 * (p == n)
               for p in scores_pos for n in scores_neg)
    return wins / (len(scores_pos) * len(scores_neg))


def main() -> None:
    rows = []
    by_kind: dict[str, list] = {}
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        try:
            read = read_content_roles(text)
            got = solve(read)[0]
        except Exception:
            continue

        true_by_key = {key(c): c for c in case.world.claims}
        read_by_key = {key(c): c for c in read.claims}
        missing = [true_by_key[k] for k in true_by_key.keys() - read_by_key]
        spurious = [read_by_key[k] for k in read_by_key.keys() - true_by_key]

        # influence by intervention ON THE TRUE WORLD
        critical = 0
        for c in missing:
            kept = tuple(x for x in case.world.claims if key(x) != key(c))
            hit = answer(replace(case.world, claims=kept)) != want
            critical += hit
            by_kind.setdefault(c.predicate, []).append(hit)
        for c in spurious:
            added = case.world.claims + (c,)
            hit = answer(replace(case.world, claims=added)) != want
            critical += hit
            by_kind.setdefault(c.predicate, []).append(hit)

        rows.append({
            "seed": s,
            "correct": got == want,
            "critical": critical,
            "delta": len(missing) + len(spurious),
            "recall": 1 - len(missing) / max(len(true_by_key), 1),
            "precision": 1 - len(spurious) / max(len(read_by_key), 1),
        })

    n = len(rows)
    right = [r for r in rows if r["correct"]]
    wrong = [r for r in rows if not r["correct"]]
    print(f"{n} non-empty cases on the honest surface; "
          f"{len(right)} correct, {len(wrong)} wrong\n")

    print(f"{'quantity':<26} {'mean|correct':>13} {'mean|wrong':>12} "
          f"{'AUC':>7}")
    print("-" * 62)
    out = {"n": n, "accuracy": len(right) / n}
    for name, field, flip in (("claim recall", "recall", True),
                              ("claim precision", "precision", True),
                              ("symmetric difference", "delta", False),
                              ("CRITICAL ERROR MASS", "critical", False)):
        a = statistics.mean(r[field] for r in right)
        b = statistics.mean(r[field] for r in wrong)
        # score so that LOW = looks correct
        pos = [(-r[field] if flip else r[field]) for r in right]
        neg = [(-r[field] if flip else r[field]) for r in wrong]
        area = auc(pos, neg)
        out[name] = {"mean_correct": a, "mean_wrong": b, "auc": area}
        print(f"{name:<26} {a:>13.3f} {b:>12.3f} {area:>7.3f}")

    zero = [r for r in rows if r["critical"] == 0]
    nonzero = [r for r in rows if r["critical"] > 0]
    exact_fwd = statistics.mean(r["correct"] for r in zero) if zero else 0.0
    exact_rev = (1 - statistics.mean(r["correct"] for r in nonzero)
                 if nonzero else 0.0)
    out["zero_mass_and_correct"] = exact_fwd
    out["nonzero_mass_and_wrong"] = exact_rev
    out["zero_mass_share"] = len(zero) / n
    print(f"\ncritical mass 0 on {len(zero)}/{n}: correct on "
          f"{exact_fwd:.3f} of them")
    print(f"critical mass > 0 on {len(nonzero)}/{n}: wrong on "
          f"{exact_rev:.3f} of them")
    print("\nIf both were 1.000 the mass would CHARACTERISE the equivalence")
    print("class W_hat ~_K W rather than predict it. Single-claim intervention")
    print("cannot see JOINT influence, and flood is known to have jointly")
    print("critical pairs, so a residual of exactly that kind is expected.")

    print("\nPER-KIND INFLUENCE -- the effective deletion dependency of the")
    print("error mix, which `audit.deletion_dependency` measures OFFLINE before")
    print("any reader exists:")
    print(f"  {'kind':<14} {'errors':>7} {'influential':>12}")
    print("  " + "-" * 35)
    for k, v in sorted(by_kind.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:<14} {len(v):>7} {statistics.mean(v):>12.3f}")
    total = [x for v in by_kind.values() for x in v]
    out["per_kind_influence"] = {k: statistics.mean(v)
                                 for k, v in by_kind.items()}
    out["effective_d"] = statistics.mean(total) if total else 0.0
    print(f"  {'ALL':<14} {len(total):>7} {statistics.mean(total):>12.3f}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
