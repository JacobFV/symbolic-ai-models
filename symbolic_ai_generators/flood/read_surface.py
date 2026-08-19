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

__all__ = ["read_surface", "read_lexical", "read_signature"]

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


# ---------------------------------------------------------------------------
# arm 5: type signatures, not words
# ---------------------------------------------------------------------------
#
# `scripts/reader_generalisation.py` showed both earlier arms collapse when the
# lexicon changes: a pattern set and a cue-word router are each written against
# a phrasing, and four phrasings per kind take both to 0.000.
#
# The world IR offers something paraphrase does not touch: the **type signature**
# of what a sentence mentions -- how many regions, how many vehicles, how many
# quantities. Signatures alone are ambiguous,
#
#     (2 regions, 0 qty)  ->  link  OR  bridge_on
#     (1 vehicle, 1 qty)  ->  mass  OR  capacity
#     (1 region,  0 qty)  ->  flooded OR depot OR needs
#     (0 entities, 1 qty) ->  capacity-by-pronoun OR demand
#
# and **paragraph position** resolves every one of them except link/bridge_on.
# That last resolves structurally rather than lexically: every bridge in the
# generator carries a load limit, so the bridge pairs are exactly the pairs that
# appear in the quantities paragraph, and links are the pairs in the
# infrastructure paragraph.
#
# Nothing here reads a content word. The only lexical commitment is the
# paragraph headings, which are section labels rather than phrasings.

_SECTIONS = ("SITUATION REPORT", "ROAD NETWORK", "OVERNIGHT",
             "LOADING AND LIMITS", "TASKING")


def _sentences(paragraph: str):
    for raw in re.split(r"(?<=\.)\s+", paragraph):
        if raw.strip():
            yield raw


def signature_readings(text: str) -> tuple[dict, dict]:
    """Split a document into what the signature FIXES and what it leaves open.

    Returns ``(fixed, open_)``. ``fixed`` holds the claims whose role the type
    signature determines on its own; ``open_`` holds the groups where it does
    not, each as ``{group: [candidate readings]}``.

    Position resolves these groups in `read_signature`, but position is a
    property of *this generator's five-paragraph template*. With it ablated the
    ambiguity is real, and the critical invariant says the reader should hand it
    on rather than guess.
    """
    links: list[tuple[str, str]] = []
    crossings: dict[tuple[str, str], float | None] = {}
    lone_region: list[str] = []
    veh_numbers: dict[str, list[float]] = {}
    bare_numbers: list[float] = []
    for sent in _sentences(text.replace("\n\n", " ")):
        regions = list(dict.fromkeys(_REGION.findall(sent)))
        trucks = list(dict.fromkeys(_TRUCK_ID.findall(sent)))
        nums = [float(n) for n in _NUM.findall(sent)]
        if len(regions) == 2 and nums:
            crossings[(regions[0], regions[1])] = nums[-1]
        elif len(regions) == 2 and not nums and not trucks:
            links.append((regions[0], regions[1]))
        elif len(regions) == 1 and not nums and not trucks:
            lone_region.append(regions[0])
        elif len(trucks) == 1 and nums:
            veh_numbers.setdefault(trucks[0], []).append(nums[0])
        elif not regions and not trucks and nums:
            bare_numbers.append(nums[0])
    # link vs bridge_on resolves STRUCTURALLY: a bridge is a pair carrying a
    # limit, and every bridge in this generator carries one.
    for pair in crossings:
        if pair not in links and (pair[1], pair[0]) not in links:
            links.append(pair)
    fixed = {"links": links, "crossings": crossings}
    open_ = {"vehicle_roles": veh_numbers,      # which number is mass, which cap
             "region_roles": lone_region,       # flooded / depot / needs
             "bare_numbers": bare_numbers}      # pronoun capacity / demand
    return fixed, open_


def read_signature(text: str) -> WorldSnapshot:
    """``text -> WorldSnapshot`` by entity-type signature and section position."""
    paragraphs = text.split("\n\n")
    links: list[tuple[str, str]] = []
    flooded: list[str] = []
    crossings: dict[tuple[str, str], float | None] = {}
    vehicles: dict[str, list] = {}
    depot = needs = ""
    demand = None
    last_vehicle = ""

    for pi, para in enumerate(paragraphs):
        for sent in _sentences(para):
            regions = _REGION.findall(sent)
            trucks = _TRUCK_ID.findall(sent)
            nums = [float(n) for n in _NUM.findall(sent)]
            sig = (len(set(regions)), len(set(trucks)), len(nums))

            if pi == 0:                                   # actors and places
                if sig[:2] == (1, 0) and not nums:
                    depot = depot or regions[0]
                elif sig[1] == 1 and nums:
                    # a vehicle and a number in the roster is its mass
                    vehicles.setdefault(trucks[0], [None, None])[0] = nums[0]
                    last_vehicle = trucks[0]
            elif pi == 1:                                 # infrastructure
                if len(set(regions)) == 2 and not nums:
                    a, b = regions[0], regions[1]
                    if (a, b) not in links and (b, a) not in links:
                        links.append((a, b))
            elif pi == 2:                                 # current events
                if regions:
                    flooded.append(regions[0])
            elif pi == 3:                                 # quantities
                if len(set(regions)) == 2 and nums:
                    # the LAST quantity is the current one; an earlier number in
                    # the same sentence is a superseded value
                    crossings[(regions[0], regions[1])] = nums[-1]
                elif trucks and nums:
                    vehicles.setdefault(trucks[0], [None, None])[1] = nums[0]
                    last_vehicle = trucks[0]
                elif trucks and not nums and not regions:
                    # A NAMING sentence: one vehicle, no quantity. It introduces
                    # the referent the next bare quantity attaches to.
                    #
                    # This branch was missing, and its absence is what made the
                    # capacity claims fail -- last_vehicle kept whatever the ¶1
                    # roster left, so the pronoun bound to the wrong vehicle. It
                    # was read as evidence that superlative-mediated reference
                    # needs a lexical resource. It does not: the antecedent is
                    # the nearest preceding lone vehicle mention, recoverable
                    # from POSITION and SIGNATURE with no content word read.
                    last_vehicle = trucks[0]
                elif nums and not regions and not trucks:
                    # a bare quantity here attaches to the vehicle most recently
                    # named -- coreference by recency, not by pronoun spelling
                    if last_vehicle:
                        vehicles.setdefault(
                            last_vehicle, [None, None])[1] = nums[0]
            elif pi == 4:                                 # query context
                if regions and not nums:
                    needs = needs or regions[0]
                elif nums and not regions:
                    demand = nums[0]

    # A pair carrying a limit is a bridge; the rest of the network is plain link.
    for pair in crossings:
        if pair not in links and (pair[1], pair[0]) not in links:
            links.append(pair)
    return _assemble(links, flooded, crossings,
                     {k: tuple(v) for k, v in vehicles.items()},
                     depot, needs, demand)


def signature_worlds(text: str, *, cap: int = 512,
                     open_groups: frozenset[str] = frozenset(
                         {"vehicle", "region", "bare"}),
                     truth=None) -> list[WorldSnapshot]:
    """Every world consistent with what the signature could determine.

    Position is not used. Each open group is enumerated: a vehicle's two numbers
    may be (mass, capacity) or (capacity, mass); the three lone regions may take
    the flooded/depot/needs roles in any order; a bare quantity may be the
    pronoun capacity or the demand.

    Returns ``[]`` if the product exceeds ``cap`` -- a refusal, not a guess,
    which is what the ambiguity machinery elsewhere in this repo does when the
    world's product is too large to name.
    """
    import itertools

    fixed, open_ = signature_readings(text)
    roles = open_["vehicle_roles"]
    regions = open_["region_roles"]
    bare = list(open_["bare_numbers"])
    if len(regions) < 3 or not roles:
        return []
    # The generator can flood MORE THAN ONE region, so the lone-region
    # sentences are not always exactly three. A first version enumerated
    # permutations of the first three and could not reach the true assignment
    # whenever a case had two floods -- unsound on seed 25, caught by the
    # soundness check. Choose the depot and the needs site; everything else
    # lone is flooded.
    # Trucks named with TWO numbers have an ordering ambiguity. Trucks named
    # with ONE have the other attribute stated as a bare quantity elsewhere --
    # the pronoun capacity -- so a bare number is either the demand or the
    # missing capacity of such a truck. A first version enumerated only which
    # bare number was the demand and dropped the rest on the floor, which left
    # one vehicle with no capacity in EVERY world and put the truth outside the
    # enumeration on 19 of 22 cases. The soundness check caught it.
    # A group not in `open_groups` is resolved from `truth` -- an ORACLE for
    # that group only. That is how the ambiguity level is swept: it isolates
    # "how wide is the bound when k groups are open" from "can the reader close
    # them", which are different questions and only the first is asked here.
    paired = sorted(v for v, n in roles.items() if len(n) == 2)
    single = sorted(v for v, n in roles.items() if len(n) == 1)
    if len(bare) < len(single):
        return []
    veh_choices = list(itertools.product([0, 1], repeat=len(paired)))
    region_choices = [(d, n) for d in range(len(regions))
                      for n in range(len(regions)) if d != n]
    demand_choices = list(range(len(bare))) if bare else [None]
    if truth is not None:
        by = {c.predicate: c for c in truth.claims}
        if "vehicle" not in open_groups:
            want = {c.roles["of"].id: float(c.roles["value"].value)
                    for c in truth.claims if c.predicate == "mass"}
            veh_choices = [vc for vc in veh_choices
                           if all(roles[n][1 if f else 0] == want.get(n)
                                  for n, f in zip(paired, vc))]
        if "region" not in open_groups:
            dp = by["depot"].roles["where"].id
            nd = by["needs"].roles["where"].id
            region_choices = [rc for rc in region_choices
                              if (regions[rc[0]], regions[rc[1]]) == (dp, nd)]
        if "bare" not in open_groups:
            dv = float(by["demand"].roles["value"].value)
            demand_choices = [i for i in demand_choices
                              if i is not None and bare[i] == dv]
    if not (veh_choices and region_choices and demand_choices):
        return []
    total = (len(veh_choices) * len(region_choices) * max(1, len(demand_choices)))
    if total > cap:
        return []

    out: list[WorldSnapshot] = []
    for vc in veh_choices:
        base = {}
        for name, flip in zip(paired, vc):
            a, b = roles[name]
            base[name] = (b, a) if flip else (a, b)
        for di in demand_choices:
            demand = bare[di] if di is not None else None
            leftover = [x for j, x in enumerate(bare) if j != di]
            if len(leftover) < len(single):
                continue
            vehicles = dict(base)
            for name, cap_kg in zip(single, leftover):
                vehicles[name] = (roles[name][0], cap_kg)
            for di_, ni_ in region_choices:
                depot_r, needs_r = regions[di_], regions[ni_]
                flooded_r = [r for j, r in enumerate(regions)
                             if j not in (di_, ni_)]
                out.append(_assemble(
                    fixed["links"], flooded_r, dict(fixed["crossings"]),
                    dict(vehicles), depot_r, needs_r, demand))
    return out
