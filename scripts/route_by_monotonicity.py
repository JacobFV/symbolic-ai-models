"""Routing on the form of a query, not on how it turned out.

Monotonicity is now measured on the same axis four times — twice before this
session (`inspectability-is-asymmetric`: a witness verifies **247x** cheaper than
solving, an optimality certificate **2.0x dearer** than re-solving; and its
datalog companion) and twice inside it (the **93x** maintenance split between a
cover's witness and its optimality claim, and monotone queries repairing a noisy
world where the antitone one cannot).

Every one of those ends in the same stated design consequence, and none of them
built it:

> world construction and answer construction want **opposite defaults**, and
> nothing in the architecture says so.

So: a router. Two worlds already exist — `v4` abstains and is precise, `v4r`
emits every candidate and is complete — and the claim under test is that a query's
**form** decides which one it should be answered from.

**The honest version, which is the whole experiment.** Routing on *measured*
per-class performance is tautological: pick the winner per class and it wins. The
non-trivial claim is that monotonicity is a **static, syntactic** property —
readable from the query's shape before it runs, without seeing any answer — and
that routing on it alone recovers most of what an oracle would get. So the router
is handed the query's declared form and nothing else, and it is scored against:

    each single world alone      — the baseline it must beat to exist
    an ORACLE                    — picks the better world per class *after*
                                   seeing both scores, which is the ceiling

Run: SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \\
     uv run python -u scripts/route_by_monotonicity.py
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path
from typing import Any, Callable

from scripts.completeness_limit import boolean_scores
from scripts.first_arrow_gazetteer import ROR, v4
from scripts.first_arrow_geo import GeoGazetteer
from scripts.first_arrow_prose import load, score
from scripts.two_arrows_end_to_end import build_worlds, collaborators, v4_recall

OUT = Path("runs/route_by_monotonicity.json")
SEED = 20260818
N = 2000

#: The router's entire input: the query's set expression, declared. `monotone`
#: means every input set appears under union or intersection only, so adding a
#: member can only add to the answer. `A - B` is antitone in `B`; `|A| == 1` is
#: neither. Nothing here consults a result.
FORM = {
    "institutions_of(work)":        {"expr": "A",       "monotone": True},
    "collaborators(institution)":   {"expr": "U A_i",   "monotone": True},
    "works_at(institution)":        {"expr": "U A_i",   "monotone": True},
    "works_at_both(A,B)":           {"expr": "A & B",   "monotone": True},
    "institutions_unique_to(w1,w2)": {"expr": "A - B",  "monotone": False},
    "is_single_institution(work)":  {"expr": "|A| == 1", "monotone": False},
}


def main() -> None:
    rng = random.Random(SEED)
    gz = GeoGazetteer(ROR)
    works = load()
    ids = [w["id"] for w in works]

    worlds: dict[str, tuple] = {}
    for label, fn in (("precise", v4), ("complete", v4_recall)):
        worlds[label] = build_worlds(works, gz, fn)[:4]
    ref, _, inv_ref, _ = worlds["precise"]
    real = sorted({i for v in ref.values() for i in v})
    print(f"{len(works):,} works, {len(real):,} reference institutions", flush=True)

    # One draw of query instances, shared by both worlds and by the router.
    work_pairs = [(a, b) for a, b in
                  ((rng.choice(ids), rng.choice(ids)) for _ in range(N * 4))
                  if a != b][:N]
    inst_pairs = []
    while len(inst_pairs) < N:
        a = rng.choice(real)
        cos = sorted(collaborators(ref, inv_ref, a))
        if cos:
            inst_pairs.append((a, rng.choice(cos)))
    insts = rng.sample(real, min(N, len(real)))
    single = rng.sample(ids, min(N, len(ids)))

    def evaluate(world_label: str) -> dict[str, float]:
        _, ext, _, inv_ext = worlds[world_label]
        out: dict[str, float] = {}
        out["institutions_of(work)"] = score(
            [(ext[w["id"]], ref[w["id"]]) for w in works])["f1"]
        out["collaborators(institution)"] = score(
            [p for p in ((collaborators(ext, inv_ext, i),
                          collaborators(ref, inv_ref, i)) for i in insts)
             if p[1]])["f1"]
        out["works_at(institution)"] = score(
            [p for p in ((inv_ext.get(i, set()), inv_ref.get(i, set()))
                         for i in insts) if p[1]])["f1"]
        out["works_at_both(A,B)"] = score(
            [(inv_ext.get(a, set()) & inv_ext.get(b, set()),
              inv_ref.get(a, set()) & inv_ref.get(b, set()))
             for a, b in inst_pairs])["f1"]
        out["institutions_unique_to(w1,w2)"] = score(
            [p for p in ((ext[a] - ext[b], ref[a] - ref[b])
                         for a, b in work_pairs) if p[1]])["f1"]
        out["is_single_institution(work)"] = boolean_scores(
            [(len(ext[w]) == 1, len(ref[w]) == 1) for w in single])["accuracy"]
        return out

    precise = evaluate("precise")
    complete = evaluate("complete")

    hdr = (f"{'query class':<32} {'form':<11} {'mono':>5} {'precise':>9} "
           f"{'complete':>9} {'routed':>9} {'oracle':>9}")
    print()
    print(hdr)
    print("-" * len(hdr))
    routed: dict[str, float] = {}
    oracle: dict[str, float] = {}
    for q, form in FORM.items():
        # The router's decision, made from `form` alone.
        pick = "complete" if form["monotone"] else "precise"
        routed[q] = (complete if pick == "complete" else precise)[q]
        oracle[q] = max(precise[q], complete[q])
        star = " " if routed[q] == oracle[q] else "*"
        print(f"{q:<32} {form['expr']:<11} "
              f"{'yes' if form['monotone'] else 'no':>5} {precise[q]:>9.3f} "
              f"{complete[q]:>9.3f} {routed[q]:>8.3f}{star} {oracle[q]:>9.3f}")

    def mean(d):
        return statistics.mean(d[q] for q in FORM)

    print()
    print(f"{'mean over the mixed workload':<32} {'':<11} {'':>5} "
          f"{mean(precise):>9.3f} {mean(complete):>9.3f} {mean(routed):>9.3f} "
          f"{mean(oracle):>9.3f}")
    best_single = max(mean(precise), mean(complete))
    print(f"\nrouted vs the better single world: {mean(routed)-best_single:+.3f}")
    print(f"routed vs the oracle ceiling:      {mean(routed)-mean(oracle):+.3f} "
          f"({'recovers all of it' if abs(mean(routed)-mean(oracle)) < 1e-9 else 'leaves some on the table'})")
    wrong = [q for q in FORM if routed[q] < oracle[q]]
    print(f"classes the static form rule gets wrong: "
          f"{wrong if wrong else 'none'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "n": N, "form": FORM,
                               "precise": precise, "complete": complete,
                               "routed": routed, "oracle": oracle,
                               "mean": {"precise": mean(precise),
                                        "complete": mean(complete),
                                        "routed": mean(routed),
                                        "oracle": mean(oracle)}}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
