"""Reader arms for the five-paragraph observation surface.

`scripts/reader_arms.py` measured arm zero: the repo's template reader, written
for the *old* report, recovers **0.000** of the world from
`surface.render_observation` and is indistinguishable from having no reader at
all. This is the first arm that actually reads it, plus the ablations that price
the two mechanisms the surface was built to require.

The two keyword arguments are **ablations, not options** -- the same convention
`flood/flow.py` uses for its kernels, and for the same reason: each removes one
capability while leaving everything else identical, so the drop is attributable.

``coref=False``
    Drop the three claims stated through a pronoun -- the superseded crossing's
    *"it is now rated for N kg"*, the lightest vehicle's *"It can take a further
    N kg"*, and the request's *"It is for N kg of supplies"*. Global recall falls
    by about 3 claims in 28; the question is what that costs downstream, since
    one of the three is the demand, which the dependency ablation found critical
    in 55% of cases.

``reject_distractors=False``
    Fall back to loose patterns that take any region pair as a link, any
    ``rated at|for`` as a limit and any ``truck_N`` as a vehicle -- so the
    superseded load limit, the disused track between two regions outside the
    area, and the vehicle committed elsewhere all enter the world.

**Entity linking is a real step here and not a regex.** The world keys load
limits to ``bridge_i`` ids that the text never states; they are assigned by
``enumerate(sorted(bridges.items()))`` over ``(a, b)`` pairs. A reader recovers
them only by finding every crossing and reproducing that ordering.
"""

from __future__ import annotations

import re

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)

__all__ = ["read_surface", "read_lexical"]

_DEPOT = re.compile(r"Depot operations are run out of (region_\d+)")
_MASS = re.compile(r"(truck_\d+) weighs (\d+) kg empty")
_LINK = re.compile(r"(region_\d+) and (region_\d+) are joined by a surfaced "
                   r"road")
_BRIDGE = re.compile(r"The (region_\d+)-(region_\d+) road runs over a river "
                     r"crossing")
_FLOOD = re.compile(r"Water rose through (region_\d+) during the night")
_LIMIT = re.compile(r"The (region_\d+)-(region_\d+) crossing is rated for "
                    r"(\d+) kg")
_LIMIT_PRONOUN = re.compile(r"The (region_\d+)-(region_\d+) crossing was rated "
                            r"at \d+ kg before last year's resurfacing; +it is "
                            r"now rated for (\d+) kg")
_LIGHTEST = re.compile(r"Turning to payloads, (truck_\d+) is the lightest")
_CAP_PRONOUN = re.compile(r"It can take a further (\d+) kg on top of its own "
                          r"weight")
_CAP_NAMED = re.compile(r"The vehicle listed as (truck_\d+) can take a further "
                        r"(\d+) kg")
_NEEDS = re.compile(r"A request has come in from (region_\d+)")
_DEMAND = re.compile(r"It is for (\d+) kg of supplies")

#: loose forms, used only when distractor rejection is ablated away
_LOOSE_LINK = re.compile(r"(region_\d+)\D{1,40}?(region_\d+)")
_LOOSE_LIMIT = re.compile(r"rated (?:at|for) (\d+) kg")
_LOOSE_TRUCK = re.compile(r"(truck_\d+)")


def _assemble(links, flooded, crossings, vehicles, depot, needs,
              demand) -> WorldSnapshot:
    """Build the world, reproducing the generator's own id conventions."""
    entities: dict[str, Entity] = {}
    claims: list[Claim] = []
    regions = {r for pair in links for r in pair} | set(flooded)
    regions |= {r for pair in crossings for r in pair}
    if depot:
        regions.add(depot)
    if needs:
        regions.add(needs)
    for rid in sorted(regions):
        entities[rid] = Entity(rid, types=("region",),
                               facets={"geo.place": Facet("geo.place",
                                                          {"name": rid})})
    for a, b in links:
        claims.append(Claim("link", {"a": EntityRef(a), "b": EntityRef(b)}))
    for f in flooded:
        claims.append(Claim("flooded", {"where": EntityRef(f)}))
    # bridge ids follow `enumerate(sorted(bridges.items()))` on the (a, b) pair
    for i, (a, b) in enumerate(sorted(crossings)):
        bid = f"bridge_{i}"
        entities[bid] = Entity(bid, types=("bridge",), facets={
            "geo.network": Facet("geo.network", {"span": f"{a}-{b}"})})
        claims.append(Claim("bridge_on", {"a": EntityRef(a), "b": EntityRef(b),
                                          "via": EntityRef(bid)}))
        limit = crossings[(a, b)]
        if limit is not None:
            claims.append(Claim("load_limit", {"of": EntityRef(bid),
                                               "value": Quantity(limit, "kg")}))
    for vid, (mass, cap) in sorted(vehicles.items()):
        entities[vid] = Entity(vid, types=("vehicle",), facets={
            "scene.body": Facet("scene.body", {"kind": "truck"}),
            "logic.constraint": Facet("logic.constraint", {
                "variables": {"payload": {"unit": "kg"}}})})
        if mass is not None:
            claims.append(Claim("mass", {"of": EntityRef(vid),
                                         "value": Quantity(mass, "kg")}))
        if cap is not None:
            claims.append(Claim("capacity", {"of": EntityRef(vid),
                                             "value": Quantity(cap, "kg")}))
    if depot:
        claims.append(Claim("depot", {"where": EntityRef(depot)}))
    if needs:
        claims.append(Claim("needs", {"where": EntityRef(needs)}))
        if demand is not None:
            claims.append(Claim("demand", {"of": EntityRef(needs),
                                           "value": Quantity(demand, "kg")}))
    return WorldSnapshot(entities=entities, claims=tuple(claims))


def read_surface(text: str, *, coref: bool = True,
                 reject_distractors: bool = True) -> WorldSnapshot:
    """``text -> WorldSnapshot`` for the five-paragraph surface."""
    links = [(a, b) for a, b in _LINK.findall(text)]
    flooded = list(_FLOOD.findall(text))
    depot = (m.group(1) if (m := _DEPOT.search(text)) else "")
    needs = (m.group(1) if (m := _NEEDS.search(text)) else "")

    crossings: dict[tuple[str, str], float | None] = {
        (a, b): None for a, b in _BRIDGE.findall(text)}
    for a, b, kg in _LIMIT.findall(text):
        crossings[(a, b)] = float(kg)
    if coref:
        for a, b, kg in _LIMIT_PRONOUN.findall(text):
            crossings[(a, b)] = float(kg)

    vehicles: dict[str, list] = {}
    for vid, kg in _MASS.findall(text):
        vehicles.setdefault(vid, [None, None])[0] = float(kg)
    for vid, kg in _CAP_NAMED.findall(text):
        vehicles.setdefault(vid, [None, None])[1] = float(kg)
    demand = None
    if coref:
        # the pronoun's antecedent is a naming sentence that realises no claim
        if (lm := _LIGHTEST.search(text)) and (cm := _CAP_PRONOUN.search(text)):
            vehicles.setdefault(lm.group(1), [None, None])[1] = float(
                cm.group(1))
        if dm := _DEMAND.search(text):
            demand = float(dm.group(1))

    if not reject_distractors:
        # take every region pair as a link and every truck as a vehicle
        for a, b in _LOOSE_LINK.findall(text):
            if a != b and (a, b) not in links and (b, a) not in links:
                links.append((a, b))
        for vid in set(_LOOSE_TRUCK.findall(text)):
            vehicles.setdefault(vid, [None, None])
        loose = [float(x) for x in _LOOSE_LIMIT.findall(text)]
        for i, key in enumerate(sorted(crossings)):
            if i < len(loose):
                crossings[key] = loose[i]

    return _assemble(links, flooded,
                     {k: v for k, v in crossings.items()},
                     {k: tuple(v) for k, v in vehicles.items()},
                     depot, needs, demand)


#: sentence -> predicate, by the words that distinguish it. The lexical arm has
#: no per-claim pattern: it decides WHICH template a sentence realises by word
#: overlap, then pulls entities and numbers out positionally.
_CUES = {
    "link": ("joined", "surfaced", "road"),
    "bridge_on": ("runs", "over", "river", "crossing"),
    "load_limit": ("crossing", "rated"),
    "mass": ("weighs", "empty"),
    "capacity": ("take", "further"),
    "flooded": ("water", "rose", "passable"),
    "depot": ("depot", "operations"),
    "needs": ("request", "come"),
    "demand": ("supplies",),
}
_REGION = re.compile(r"region_\d+")
_TRUCK_ID = re.compile(r"truck_\d+")
_NUM = re.compile(r"\b(\d+) kg\b")


def read_lexical(text: str) -> WorldSnapshot:
    """A different mechanism: cue-word routing, then positional extraction.

    No pattern knows the whole sentence. Each sentence is routed to the claim
    template whose cue words it best matches, and the entities and quantities
    are then taken by position. It cannot tell *"is rated for"* from *"was rated
    at"*, which is exactly the kind of distinction a lexical method loses.
    """
    links, flooded = [], []
    crossings: dict[tuple[str, str], float | None] = {}
    vehicles: dict[str, list] = {}
    depot = needs = ""
    demand = None
    for raw in re.split(r"(?<=[.;])\s+", text):
        s = raw.lower()
        best, score = None, 0
        for pred, cues in _CUES.items():
            hit = sum(c in s for c in cues)
            if hit > score:
                best, score = pred, hit
        if best is None or score < len(_CUES[best]) - 1:
            continue
        regions = _REGION.findall(raw)
        trucks = _TRUCK_ID.findall(raw)
        nums = [float(n) for n in _NUM.findall(raw)]
        if best == "link" and len(regions) >= 2:
            links.append((regions[0], regions[1]))
        elif best == "bridge_on" and len(regions) >= 2:
            crossings.setdefault((regions[0], regions[1]), None)
        elif best == "load_limit" and len(regions) >= 2 and nums:
            crossings[(regions[0], regions[1])] = nums[-1]
        elif best == "mass" and trucks and nums:
            vehicles.setdefault(trucks[0], [None, None])[0] = nums[0]
        elif best == "capacity" and nums:
            vid = trucks[0] if trucks else None
            if vid:
                vehicles.setdefault(vid, [None, None])[1] = nums[0]
        elif best == "flooded" and regions:
            flooded.append(regions[0])
        elif best == "depot" and regions:
            depot = regions[0]
        elif best == "needs" and regions:
            needs = regions[0]
        elif best == "demand" and nums:
            demand = nums[0]
    return _assemble(links, flooded, crossings,
                     {k: tuple(v) for k, v in vehicles.items()},
                     depot, needs, demand)
