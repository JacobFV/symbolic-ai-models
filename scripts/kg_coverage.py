"""Regenerate every number in the KG coverage finding.

    uv run python scripts/kg_coverage.py            # the full 179-lesson grid
    uv run python scripts/kg_coverage.py --seeds 4  # cheaper, same shape

The finding note
(``notes/findings/2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-
reach.md``) is the only place these numbers are argued. This is the only place
they are *produced*, so a reader can disagree with the code rather than with a
paragraph. Written as a script rather than a test because it reports rather than
asserts — the assertions live in ``tests/test_kg.py``.

Three sections, in the order the note uses them:

1. **reach** — how many lessons and how many graph node labels the vendored
   graph actually changes, and whether any tree shape moved;
2. **fallback** — per slot, how often the binder had nothing to say and used the
   curriculum's own word list. A binder that fell back everywhere would look
   like a treatment and behave like the baseline;
3. **control** — the census of both graphs side by side, and the share of edges
   the scramble left in place.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys

import symbolic_ai_data as lc
from symbolic_ai_data.binding import using
from symbolic_ai_core.data import curriculum as C
from symbolic_ai_kg import load
from symbolic_ai_kg.bind import KGBinder, pools_for
from symbolic_ai_kg.registry import KG_NAMES, SHUFFLE_ROUNDS, SHUFFLE_SEED, census
from symbolic_ai_kg.scramble import swap_report

#: Training seeds and eval seeds both. Hashing eval seeds is not tuning against
#: them — the same reasoning ``symbolic_ai_core/data/fingerprint.py`` gives.
DEFAULT_SEEDS = tuple(range(8)) + (1_000_000, 1_000_001, 1_000_002, 1_000_003)


def reach(lessons, seeds, arms=("kg:wordnet", "kg:wordnet-shuffled")):
    base = {}
    for lid in lessons:
        for s in seeds:
            base[(lid, s)] = next(iter(C.generate([lid], n=1, seed0=s,
                                                  curriculum="base")))
    out = {}
    for arm in arms:
        changed = collections.Counter()
        shape_moved: list[tuple[str, int]] = []
        node_changed = node_tot = 0
        nodes_base = nodes_arm = 0
        for (lid, s), b in base.items():
            k = next(iter(C.generate([lid], n=1, seed0=s, curriculum=arm)))
            nodes_base += len(b.graph.labels)
            nodes_arm += len(k.graph.labels)
            if b.graph.types != k.graph.types or b.graph.parent != k.graph.parent:
                shape_moved.append((lid, s))
                continue
            if b.graph.labels != k.graph.labels or b.prompt != k.prompt:
                changed[lid] += 1
            for x, y in zip(b.graph.labels, k.graph.labels):
                node_tot += 1
                node_changed += x != y
        out[arm] = {
            "episodes": len(base),
            "lessons_changed": sorted(changed),
            "node_changed": node_changed, "node_total": node_tot,
            "shape_moved": shape_moved,
            "nodes_base": nodes_base, "nodes_arm": nodes_arm,
        }
    return out


def fallback(lessons, seeds, kg_name="wordnet"):
    kg = load(kg_name)
    asked, fell = collections.Counter(), collections.Counter()
    seen = bound = 0
    for lid in lessons:
        L = lc.get(lid)
        for s in seeds:
            b = KGBinder(kg, lid, s)
            with using(b):
                try:
                    L.example(s)
                    L.structured(s)
                except Exception:                                # pragma: no cover
                    continue
            d = b.describe()
            for slot in d["slots_asked"]:
                asked[slot] += 1
            for slot in d["slots_fallback"]:
                fell[slot] += 1
            seen += d["entities_seen"]
            bound += d["entities_bound"]
    return {"asked": dict(asked), "fell": dict(fell),
            "entities_bound": bound, "entities_seen": seen}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--seeds", type=int, default=0,
                   help="use seeds 0..N-1 only; 0 means the full default grid")
    p.add_argument("--json", help="also write the raw numbers here")
    args = p.parse_args(argv)
    seeds = tuple(range(args.seeds)) if args.seeds else DEFAULT_SEEDS
    lessons = [i for i in lc.lesson_ids() if lc.get(i).status == "implemented"]
    n = len(lessons)
    print(f"{n} lessons x {len(seeds)} seeds {seeds}\n")

    print("=== 3. the graph and its control (printed first: it is the cheapest)")
    cen = census()
    keys = sorted(cen["wordnet"])
    print(f"  {'':22s}" + "".join(f"{k.replace('edge:', ''):>11s}" for k in keys))
    for name in KG_NAMES:
        print(f"  {name:22s}" + "".join(f"{cen[name][k]:>11d}" for k in keys))
    print(f"  censuses identical: {cen['wordnet'] == cen['wordnet-shuffled']}")
    rep = swap_report(load("wordnet"), seed=SHUFFLE_SEED, rounds=SHUFFLE_ROUNDS)
    print(f"\n  scramble at seed {SHUFFLE_SEED}, {SHUFFLE_ROUNDS} attempts per edge:")
    print(f"    {'relation':12s} {'edges':>7s} {'swaps':>9s} {'kept':>6s} {'kept share':>11s}")
    for rel, d in sorted(rep.items(), key=lambda kv: -kv[1]["edges"]):
        print(f"    {rel:12s} {d['edges']:7d} {d['swaps']:9d} {d['kept']:6d} "
              f"{d['kept_share']:11.4f}")
    P = pools_for(load("wordnet"))
    print("\n  anchor pools: " + ", ".join(
        f"{k} {len(v)}" for k, v in sorted(P.items()) if isinstance(v, list)))

    print("\n=== 1. reach")
    r = reach(lessons, seeds)
    for arm, d in r.items():
        print(f"  {arm}")
        print(f"    lessons changed          {len(d['lessons_changed']):4d}/{n} "
              f"({len(d['lessons_changed'])/n:.1%})")
        print(f"    node labels changed      {d['node_changed']:6d}/{d['node_total']} "
              f"({d['node_changed']/max(d['node_total'],1):.4%})")
        print(f"    tree shapes moved        {len(d['shape_moved']):4d}/{d['episodes']} "
              f"({len(d['shape_moved'])/d['episodes']:.4%})  {d['shape_moved'][:6]}")
        print(f"    total nodes base -> arm  {d['nodes_base']} -> {d['nodes_arm']} "
              f"({(d['nodes_arm'] - d['nodes_base'])/max(d['nodes_base'],1):+.5%})")

    print("\n=== 2. fallback, per slot")
    f = fallback(lessons, seeds)
    print(f"    {'slot':16s} {'asked':>8s} {'fell back':>10s} {'share':>8s}")
    for slot in sorted(f["asked"]):
        a, b = f["asked"][slot], f["fell"].get(slot, 0)
        print(f"    {slot:16s} {a:8d} {b:10d} {b/a:8.3f}")
    print(f"    scene objects re-bound from their own kind: "
          f"{f['entities_bound']}/{f['entities_seen']} "
          f"({f['entities_bound']/max(f['entities_seen'],1):.3f})")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"census": cen, "swap": rep, "reach": r, "fallback": f},
                      fh, indent=1)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
