"""Is the empty cell unsolved, or closed?

The enumerating arm stops at 2.5 worlds and 32.4% decided on the V=4 interleaved
surface. The residual is **depot vs flooded**: both are realised as one-region,
no-number, no-vehicle sentences, and the type signature cannot tell them apart.

Before building a reader for that cell, ask whether one can exist. A reader that
consults no content word observes only:

- the entity types in each sentence (region / vehicle / bare quantity),
- the numbers, and whether they fall in a declared value vocabulary,
- which sentences mention which entity.

So compute each lone region's **content-free fingerprint** -- the multiset of
sentence signatures over every sentence mentioning it -- and ask whether the
depot's differs from a flooded region's. If they are identical, no content-free
reader can separate them whatever its architecture, and 32.4% is a **ceiling**
rather than a limitation of one arm.

Run: uv run python -u scripts/is_the_empty_cell_reachable.py
"""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/empty_cell_reachable.json")
N = 60

_REGION = re.compile(r"region_\d+")
_TRUCK = re.compile(r"truck_\d+")
_NUM = re.compile(r"\b(\d+) kg\b")


def fingerprint(text: str, entity: str) -> Counter:
    """Everything a content-free reader can observe about one entity."""
    out: Counter = Counter()
    for sent in re.split(r"(?<=\.)\s+", text):
        if entity not in sent:
            continue
        regions = set(_REGION.findall(sent))
        trucks = set(_TRUCK.findall(sent))
        nums = [float(n) for n in _NUM.findall(sent)]
        kinds = tuple(sorted({k for k, reg in VALUE_REGISTRY.items()
                              for n in nums if n in reg}))
        # position of the entity among the regions is itself content-free, but
        # only meaningful relative to the others, so record the count not the id
        out[(len(regions), len(trucks), len(nums), kinds)] += 1
    return out


def main() -> None:
    same = diff = 0
    rows = []
    per_case_ambiguous = []
    for seed in range(N):
        case = generate(seed)
        obs = render_observation(case, variants=4)
        flat = unsaturate(obs, drop_headings=True, shuffle=False)
        text = interleave(flat).text

        depot = next((c.roles["where"].id for c in case.world.claims
                      if c.predicate == "depot"), None)
        flooded = [c.roles["where"].id for c in case.world.claims
                   if c.predicate == "flooded"]
        needs = next((c.roles["where"].id for c in case.world.claims
                      if c.predicate == "needs"), None)
        if depot is None or not flooded:
            continue

        fd = fingerprint(text, depot)
        collisions = [f for f in flooded if fingerprint(text, f) == fd]
        rows.append({"seed": seed, "depot": depot, "flooded": flooded,
                     "needs": needs, "n_flooded": len(flooded),
                     "collides_with": collisions})
        if collisions:
            same += 1
        else:
            diff += 1
        # how many lone regions are mutually indistinguishable at all
        lone = [depot, *flooded] + ([needs] if needs else [])
        prints = [fingerprint(text, e) for e in lone]
        groups: list[list[int]] = []
        for i, f in enumerate(prints):
            for g in groups:
                if prints[g[0]] == f:
                    g.append(i)
                    break
            else:
                groups.append([i])
        per_case_ambiguous.append(max(len(g) for g in groups))

    n = same + diff
    print(f"{n} cases with both a depot and at least one flooded region\n")
    print(f"  depot fingerprint IDENTICAL to some flooded region: "
          f"{same:>3}/{n}  ({same/n:.1%})")
    print(f"  depot fingerprint distinguishable:                  "
          f"{diff:>3}/{n}  ({diff/n:.1%})")
    print(f"\n  largest mutually indistinguishable group of lone regions: "
          f"median {statistics.median(per_case_ambiguous):.1f}, "
          f"max {max(per_case_ambiguous)}")

    # --- DISTINGUISHABLE IS NOT IDENTIFIABLE ------------------------------
    # The count above is asymmetry, not information. A reader still needs a rule
    # mapping observation -> role, and the feature the fingerprints actually
    # differ on is node degree in the road network, which has no reason to
    # encode depot-ness. Two further tests, the second architecture-independent.
    print("\n\nidentifiability, which is the question that was actually asked:\n")
    hits = ties = m = 0
    for r in rows:
        seed = r["seed"]
        case = generate(seed)
        obs = render_observation(case, variants=4)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        lone = [r["depot"], *r["flooded"]] + ([r["needs"]] if r["needs"] else [])
        if len(lone) < 3:
            continue
        m += 1
        deg = {e: sum(v for k, v in fingerprint(text, e).items()
                      if k[0] == 2 and k[1] == 0) for e in lone}
        order = sorted(lone, key=lambda e: -deg[e])
        hits += order[0] == r["depot"]
        ties += any(deg[e] == deg[r["depot"]] for e in lone if e != r["depot"])
    chance = statistics.mean(
        1 / max(len([x["depot"], *x["flooded"]] + ([x["needs"]] if x["needs"]
                else [])), 1) for x in rows)
    print(f"  'the depot is the highest-degree lone region': "
          f"{hits}/{m} = {hits/m:.1%}  (chance {chance:.1%})")
    print(f"  it ties with another lone region: {ties}/{m} = {ties/m:.1%}")

    # Is observation -> role even a FUNCTION? If the same content-free
    # observation carries "depot" in one case and "flooded" in another, then NO
    # deterministic content-free reader can be right about both, whatever its
    # architecture. This bounds every possible such reader at once.
    from collections import defaultdict
    norm: dict = defaultdict(set)
    for r in rows:
        case = generate(r["seed"])
        obs = render_observation(case, variants=4)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        roles = {r["depot"]: "depot"} | {f: "flooded" for f in r["flooded"]}
        if r["needs"]:
            roles[r["needs"]] = "needs"
        lone = list(roles)
        if len(lone) < 3:
            continue
        fps = {e: fingerprint(text, e) for e in lone}
        deg = {e: sum(v for k, v in fps[e].items() if k[0] == 2 and k[1] == 0)
               for e in lone}
        order = sorted(lone, key=lambda e: -deg[e])
        for e in lone:
            rest = tuple(sorted((k, v) for k, v in fps[e].items()
                                if k[0] != 2 or k[1] != 0))
            norm[(order.index(e), len(lone), rest)].add(roles[e])
    ambiguous = {k: v for k, v in norm.items() if len(v) > 1}
    slots = sum(len(v) for v in norm.values())
    amb_slots = sum(len(v) for v in ambiguous.values())
    print(f"\n  rank-normalised observations: {len(norm)} distinct, "
          f"{len(ambiguous)} carry more than one role")
    print(f"  role-slots that are ambiguous: {amb_slots}/{slots}")

    if amb_slots / slots > 0.8:
        print(f"\n-> CLOSED to content-free reading. Fingerprints DIFFER in "
              f"{same and diff/n or diff/n:.1%} of cases,\n   but the "
              f"difference is incidental graph degree, not information: the "
              f"degree rule sits at\n   {hits/m:.1%} against {chance:.1%} "
              f"chance, and observation -> role is not even a FUNCTION\n   "
              f"({amb_slots}/{slots} role-slots ambiguous). No deterministic "
              f"reader consuming only entity\n   types, numbers and registry "
              f"membership can settle depot vs flooded. CONTENT IS\n   "
              f"REQUIRED here, which makes a lexical resource a necessity "
              f"rather than a shortcut.")
    else:
        print(f"\n-> REACHABLE: a consistent content-free rule survives the "
              f"collision test.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": n, "identical": same, "distinct": diff,
                               "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
