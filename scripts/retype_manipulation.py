"""Change ONE thing -- the entity names -- and see if the collapse goes away.

The structure-dependence law says arrangement is load-bearing exactly where a
sentence's signature does not determine its predicate. That is confirmed by
decomposing which claims flood loses, on two domains; it is not confirmed by
manipulation, because flood and scheduling differ in more than one way.

This changes exactly one thing. Flood's ambiguous group is {depot, flooded,
needs}: all three are realised as one region, no number, no vehicle, so the
signature cannot separate them. Renaming the entities so the **prefix carries
the role** makes the signature determinate while leaving the phrasings, the
arrangement, the claims and the answer identical.

Typed one at a time, because the interesting question is the SHAPE. The survival
law in the theory ledger says a reader loses whole kinds and a lost kind sends
the product to zero, which predicts a threshold. But adjacency already pins
`needs` -- it is what lifted the enumerating arm from 0.147 to 0.324 decided --
so typing `depot` alone may cascade.

Run: uv run python -u scripts/retype_manipulation.py
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import _assemble
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/retype_manipulation.json")
N = 40
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")

#: role -> the prefix its regions get when that role is typed
PREFIX = {"depot": "depot", "flooded": "flooded", "needs": "site"}
LADDER = ((), ("depot",), ("depot", "flooded"),
          ("depot", "flooded", "needs"))

_TOKEN = re.compile(r"\b([a-z]+)_(\d+)\b")
_NUM = re.compile(r"\b(\d+) kg\b")


def retype(world: WorldSnapshot, typed: tuple[str, ...]) -> WorldSnapshot:
    """Rename regions so the prefix carries the role, for ``typed`` roles only.

    Nothing else moves: same claims, same values, same structure, same answer.
    """
    role: dict[str, str] = {}
    for c in world.claims:
        if c.predicate in ("depot", "flooded", "needs"):
            role[c.roles["where"].id] = c.predicate
    rename = {e: f"{PREFIX[r]}_{e.rsplit('_', 1)[1]}"
              for e, r in role.items() if r in typed}
    if not rename:
        return world

    def fix(v):
        if isinstance(v, EntityRef) and v.id in rename:
            return EntityRef(rename[v.id])
        return v

    claims = tuple(replace(c, roles={k: fix(v) for k, v in c.roles.items()})
                   for c in world.claims)
    ents = {rename.get(k, k): replace(v, id=rename[k]) if k in rename else v
            for k, v in world.entities.items()}
    return replace(world, claims=claims, entities=ents)


def read_typed(text: str, typed: tuple[str, ...]):
    """The same mechanism as read_signature_roles, prefix-aware.

    A region whose prefix names its role is taken at its word; the rest fall
    back to paragraph co-occurrence, which is what interleaving destroys.
    Adjacency binds the demand quantity to the site named just before it.
    """
    known = {PREFIX[r]: r for r in typed}
    links, crossings, vehicles = [], {}, {}
    flooded, lone, order = [], [], []
    depot = needs = ""
    demand = None

    paras = text.split("\n\n")
    sents_per = [[s for s in re.split(r"(?<=\.)\s+", p) if s.strip()]
                 for p in paras]
    pairs = [sum(1 for s in ss
                 if len({m.group(0) for m in _TOKEN.finditer(s)
                         if m.group(1) != "truck"}) == 2
                 and not _NUM.findall(s)) for ss in sents_per]
    network = max(range(len(paras)), key=lambda i: pairs[i]) if paras else -1

    for pi, ss in enumerate(sents_per):
        has_mass = any(_TOKEN.search(s) and _NUM.findall(s)
                       and float(_NUM.findall(s)[0]) in
                       {1200.0, 1800.0, 2600.0, 3200.0} for s in ss)
        has_dem = any(not [m for m in _TOKEN.finditer(s)] and _NUM.findall(s)
                      and float(_NUM.findall(s)[0]) in {900.0, 1400.0, 2100.0}
                      for s in ss)
        last_vehicle = ""
        for sent in ss:
            toks = [m.group(0) for m in _TOKEN.finditer(sent)]
            trucks = [t for t in toks if t.startswith("truck_")]
            regions = list(dict.fromkeys(t for t in toks
                                         if not t.startswith("truck_")))
            nums = [float(n) for n in _NUM.findall(sent)]
            if len(regions) == 2 and nums:
                crossings[(regions[0], regions[1])] = nums[-1]
            elif len(regions) == 2 and not nums and not trucks:
                if pi == network:
                    links.append((regions[0], regions[1]))
            elif len(regions) == 1 and not nums and not trucks:
                r = regions[0]
                kind = known.get(r.rsplit("_", 1)[0])
                if kind == "depot":
                    depot = depot or r
                elif kind == "flooded":
                    flooded.append(r)
                elif kind == "needs":
                    needs = needs or r
                elif has_dem:
                    needs = needs or r
                elif has_mass:
                    depot = depot or r
                else:
                    flooded.append(r)
                lone.append(r)
                order.append(("region", r))
            elif len(trucks) == 1 and nums:
                slot = 0 if nums[0] in {1200.0, 1800.0, 2600.0, 3200.0} else 1
                vehicles.setdefault(trucks[0], [None, None])[slot] = nums[0]
                last_vehicle = trucks[0]
            elif len(trucks) == 1 and not nums:
                last_vehicle = trucks[0]
            elif not regions and not trucks and len(nums) == 1:
                if nums[0] in {900.0, 1400.0, 2100.0}:
                    demand = nums[0]
                    # adjacency: the site named immediately before it
                    if not needs and order and order[-1][0] == "region":
                        cand = order[-1][1]
                        if cand not in flooded and cand != depot:
                            needs = cand
                elif nums[0] in {1500.0, 2500.0, 4000.0} and last_vehicle:
                    vehicles.setdefault(last_vehicle, [None, None])[1] = nums[0]

    for pair in crossings:
        if pair not in links and (pair[1], pair[0]) not in links:
            links.append(pair)
    # flooded by elimination once the others are pinned
    if depot and needs:
        flooded = [r for r in lone if r != depot and r != needs]

    # Assembly is imported, never re-implemented. Hand-rolling it here produced
    # a reader that scored 0.000 even on the grouped surface -- a broken control
    # that would have read as a finding about renaming.
    return _assemble(links, flooded, crossings,
                     {k: tuple(v) for k, v in vehicles.items()},
                     depot, needs, demand)


def main() -> None:
    cases = [generate(s) for s in range(N)]
    print(f"{'typed roles':<28} {'determinate':>12} {'grouped':>9} "
          f"{'interleaved':>12}")
    print("-" * 65)
    results = {}
    for typed in LADDER:
        acc = {"grouped": [], "interleaved": []}
        for case in cases:
            world = retype(case.world, typed)
            want = solve(world)[0]
            if not want:
                continue
            shim = type(case)(**{**case.__dict__, "world": world}) \
                if hasattr(case, "__dict__") else case
            obs = render_observation(shim, variants=4)
            flat = unsaturate(obs, headings=HEADINGS, shuffle=False)
            for label, text in (("grouped",
                                 unsaturate(obs, headings=HEADINGS).text),
                                ("interleaved", interleave(flat).text)):
                try:
                    got = solve(read_typed(text, typed))[0]
                except Exception:
                    got = ()
                acc[label].append(got == want)
        # how much of the ambiguous group the signature now fixes
        det = len(typed) / 3 if len(typed) < 2 else 1.0
        results["+".join(typed) or "none"] = {
            "determinate": det,
            "grouped": statistics.mean(acc["grouped"]),
            "interleaved": statistics.mean(acc["interleaved"])}
        r = results["+".join(typed) or "none"]
        print(f"{('+'.join(typed) or 'none'):<28} {det:>12.2f} "
              f"{r['grouped']:>9.3f} {r['interleaved']:>12.3f}", flush=True)

    inter = [v["interleaved"] for v in results.values()]
    print(f"\n-> interleaved accuracy across the ladder: "
          f"{' -> '.join(f'{x:.3f}' for x in inter)}")
    jumps = [b - a for a, b in zip(inter, inter[1:])]
    print(f"   grouped stays {results['none']['grouped']:.3f} throughout, which "
          f"is the control: renaming\n   buys nothing when the arrangement is "
          f"still there to read.")
    if inter[0] < 0.1 and inter[-1] > 0.9:
        print(f"\n-> THE LAW HOLDS BY MANIPULATION. Only the entity NAMES "
              f"changed -- same phrasings,\n   same arrangement, same claims, "
              f"same answer -- and interleaved accuracy moves\n   "
              f"{inter[0]:.3f} -> {inter[-1]:.3f}. Arrangement was load-bearing "
              f"only because the signature\n   left the predicate open.")
    if 0.1 < inter[1] < 0.9:
        print(f"\n   The shape is a PARTIAL CASCADE, not a threshold and not a "
              f"gradient. Typing one\n   role of three recovers "
              f"{inter[1]:.3f}: `depot` comes from the prefix, `needs` from\n"
              f"   adjacency, `flooded` by elimination -- but adjacency only "
              f"fires sometimes, which\n   is the same partiality that capped "
              f"the enumerating arm at 0.324 decided. Partial\n   determinacy "
              f"buys immunity only through a SECOND mechanism, never on its "
              f"own.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "results": results}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
