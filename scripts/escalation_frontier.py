"""The frontier the whole programme lives on, and nobody had drawn it.

Every cost number in this repo compares a **cheap-and-wrong** system against an
**expensive-and-assumed-perfect** one. That is not a choice anyone would make.
The choice anyone would actually make is a **hybrid**: let cheap structure answer
what it can, and escalate the rest.

And the arithmetic of that is brutal and simple. A model answer costs $4.54e-03,
ours costs ~2e-09, so if a fraction `f` of decisions escalate the hybrid costs
about `f x 4.54e-03` and **the advantage is 1/f**. Escalating half the work
gives 2x. Escalating a twentieth gives 20x. The million-fold numbers in
`session_ledger.py` exist only at `f = 0`, which is the same as saying they exist
only at 60% quality.

So the programme's real number is not the cost ratio. It is the **knee**: how much
of the work cheap structure can do *confidently*, because that is what sets `f`.
This is the mandate's standing challenge stated as a measurement —

> force expensive cognition toward the irreducibly ambiguous boundary cases while
> cheap structured computation handles everything else

— and it only means anything if the cheap layer can **tell which cases those
are**. If its confidence does not predict its accuracy, escalation cannot be
targeted and the only options are cheap-and-wrong or expensive-and-right with
nothing between them.

The model's contribution is entered at **perfect accuracy**, the same generous
assumption the ledger uses and for the same reason: the comparison is blocked on
credentials (`ROADMAP.md` 0b) and a bound that assumes the opponent is perfect
needs none.

Run: SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \\
     uv run python -u scripts/escalation_frontier.py
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

from scripts.first_arrow_gazetteer import ROR
from scripts.first_arrow_geo import GeoGazetteer
from scripts.first_arrow_prose import TRAIN_FRAC, components, load, norm, score
from scripts.first_arrow_ladder import Index

OUT = Path("runs/escalation_frontier.json")
SEED = 20260818
#: from scripts/session_ledger.py — a model answer over the 302.3-token dependency
MODEL_USD = 4.535e-03
#: from the same ledger — our marginal cost, dwarfed and carried for honesty
OURS_USD = 2.2e-09


def confidence(gz: GeoGazetteer, raw: str) -> tuple[str, set[str]]:
    """What the extractor knows, and how sure it is — from the registry alone.

    Three tiers, and they are the extractor's *own* structure rather than a
    fitted score:

    ``certain``    every component that matched named exactly one institution.
    ``ambiguous``  at least one component matched several, so the registry
                   offers a choice the extractor cannot make.
    ``silent``     nothing matched at all.
    """
    hits = gz.propose(raw)
    if not hits:
        return "silent", set()
    out: set[str] = set()
    ambiguous = False
    for cands in hits:
        if len(cands) == 1:
            out |= cands
        else:
            ambiguous = True
    return ("ambiguous" if ambiguous else "certain"), out


def main() -> None:
    rng = random.Random(SEED)
    gz = GeoGazetteer(ROR)
    works = load()
    idx = list(range(len(works)))
    rng.shuffle(idx)
    cut = int(len(idx) * TRAIN_FRAC)
    ix = Index([works[i] for i in idx[:cut]])
    test = [works[i] for i in idx[cut:]]

    pairs = [(a["raw"], set(a["rors"])) for w in test
             for a in w["affiliations"] if a["rors"]]
    unseen = [p for p in pairs if norm(p[0]) not in ix.full]
    print(f"{len(unseen):,} held-out affiliation strings never seen verbatim\n",
          flush=True)

    tiers: dict[str, list] = {"certain": [], "ambiguous": [], "silent": []}
    for raw, truth in unseen:
        tier, pred = confidence(gz, raw)
        tiers[tier].append((pred, truth))

    n = len(unseen)
    hdr = f"{'tier':<12} {'share':>8} {'n':>7} {'F1':>7} {'prec':>7} {'rec':>7}"
    print(hdr)
    print("-" * len(hdr))
    stats = {}
    for tier in ("certain", "ambiguous", "silent"):
        rows = tiers[tier]
        s = score(rows) if rows else {"f1": 0.0, "precision": 0.0, "recall": 0.0}
        stats[tier] = {"share": len(rows) / n, "n": len(rows), **s}
        print(f"{tier:<12} {len(rows)/n:>7.1%} {len(rows):>7,} {s['f1']:>7.3f} "
              f"{s['precision']:>6.1%} {s['recall']:>6.1%}")

    informative = stats["certain"]["f1"] - stats["ambiguous"]["f1"]
    print(f"\nconfidence is {'INFORMATIVE' if informative > 0.15 else 'NOT informative'}: "
          f"certain beats ambiguous by {informative:+.3f} F1")

    # --- the frontier. Escalating a tier means a model answers it, perfectly.
    print()
    hdr2 = (f"{'policy':<38} {'f escalated':>12} {'quality':>9} "
            f"{'$/answer':>12} {'advantage':>11}")
    print(hdr2)
    print("-" * len(hdr2))

    policies = [
        ("symbolic only, escalate nothing", ()),
        ("escalate SILENT only", ("silent",)),
        ("escalate AMBIGUOUS only", ("ambiguous",)),
        ("escalate silent + ambiguous", ("silent", "ambiguous")),
        ("model only, escalate everything", ("certain", "ambiguous", "silent")),
    ]
    rows_out = {}
    for name, esc in policies:
        f = sum(stats[t]["share"] for t in esc)
        # Quality: escalated tiers score 1.0; the rest keep their measured F1.
        quality = sum(stats[t]["share"] * (1.0 if t in esc else stats[t]["f1"])
                      for t in ("certain", "ambiguous", "silent"))
        usd = f * MODEL_USD + (1 - f) * OURS_USD
        adv = MODEL_USD / usd if usd else float("inf")
        rows_out[name] = {"f": f, "quality": quality, "usd": usd,
                          "advantage": adv}
        print(f"{name:<38} {f:>11.1%} {quality:>9.3f} {usd:>12.3e} "
              f"{adv:>10.1f}x")

    print("\nThe knee is the row that buys the most quality per unit of "
          "escalation.")
    base = rows_out["symbolic only, escalate nothing"]
    for name, r in rows_out.items():
        if r["f"] == 0 or r["f"] >= 0.999:
            continue
        gain = r["quality"] - base["quality"]
        print(f"  {name:<38} +{gain:.3f} quality for {r['f']:.1%} escalated "
              f"=> {gain/r['f']:.2f} quality per unit escalated, "
              f"advantage {r['advantage']:.1f}x")

    # --- the only fair comparison: advantage AT FIXED QUALITY.
    #
    # Reading "17.7x" against an earlier "8.1x" is this repo's oldest trap in a
    # new place: those are different operating points. A better extractor moves
    # the whole frontier, and the way to say by how much is to fix the quality
    # and read off the price. Escalation order is silent first (1.00 quality per
    # unit), then ambiguous (0.49), then certain -- best-value first, which is
    # what any real policy would do.
    order = [("silent", stats["silent"]), ("ambiguous", stats["ambiguous"]),
             ("certain", stats["certain"])]
    curve = []
    f = 0.0
    q = sum(t["share"] * t["f1"] for t in stats.values())
    curve.append((0.0, q))
    for _, t in order:
        f += t["share"]
        q += t["share"] * (1.0 - t["f1"])
        curve.append((f, q))

    def advantage_at(target: float) -> tuple[float, float]:
        """Interpolate the frontier to a quality target; return (f, advantage)."""
        for (f0, q0), (f1, q1) in zip(curve, curve[1:]):
            if q0 <= target <= q1:
                w = 0.0 if q1 == q0 else (target - q0) / (q1 - q0)
                ff = f0 + w * (f1 - f0)
                usd = ff * MODEL_USD + (1 - ff) * OURS_USD
                return ff, (MODEL_USD / usd if usd else float("inf"))
        return 1.0, 1.0

    print("\nadvantage AT FIXED QUALITY — the only comparison that is fair "
          "across extractors")
    print(f"  {'quality target':<16} {'f needed':>10} {'advantage':>12}")
    fixed = {}
    for target in (0.65, 0.75, 0.85, 0.95):
        ff, adv = advantage_at(target)
        fixed[target] = {"f": ff, "advantage": adv}
        print(f"  {target:<16.2f} {ff:>9.1%} {adv:>11.1f}x")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "n_unseen": n, "tiers": stats,
                               "policies": rows_out,
                               "frontier_curve": curve,
                               "advantage_at_fixed_quality": fixed,
                               "model_usd": MODEL_USD, "ours_usd": OURS_USD},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
