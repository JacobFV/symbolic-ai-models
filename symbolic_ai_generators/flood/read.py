"""``text -> WorldSnapshot`` for the flood report, and a controlled-noise channel.

**This is a template reader and it proves nothing about parsing.** It matches the
phrasings this repo's own generator emits; a report written by a person would
defeat it entirely. It exists for one purpose: to put a *real* text→world step
in front of the kernels so that the question below can be asked at all.

The question is the one nobody has a number for:

> **How much parse fidelity does a multi-kernel pipeline actually need?**

That matters directly for the cost argument. If the pipeline degrades gracefully,
a cheap approximate reader can serve it and the reader's price is small. If it
falls off a cliff, the reader must be near-perfect and its price dominates
everything the symbolic side saves. Measuring it needs a reader whose fidelity
can be *turned down on purpose*, which is what :func:`corrupt` is for.

Corruption is applied to the **recovered world**, not to the text, and is
per-claim-type, because the interesting result is not an average — it is which
kind of fact the pipeline cannot afford to lose.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import replace
from typing import Iterable, Mapping

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)

__all__ = ["read_report", "corrupt", "misread", "CLAIM_KINDS",
           "MISREADS"]

#: The fact types the report carries, and therefore the ones corruption can
#: remove one at a time.
CLAIM_KINDS = ("link", "flooded", "load_limit", "mass", "capacity", "demand")

_LINK = re.compile(r"(region_\d+) to (region_\d+)")
_FLOOD = re.compile(r"has closed ([^.]+) to all traffic")
_LIMIT = re.compile(r"the (region_\d+)-(region_\d+) crossing is posted at "
                    r"(\d+) kg")
_TRUCK = re.compile(r"(truck_\d+) has an unladen mass of (\d+) kg and a "
                    r"capacity of (\d+) kg")
_DEPOT = re.compile(r"The depot at (region_\d+)")
_DEMAND = re.compile(r"(region_\d+) requires a delivery of (\d+) kg")


def read_report(text: str) -> WorldSnapshot:
    """Recover the world from the report. Raises if a required section is absent.

    Raising rather than returning a partial world is deliberate: a world missing
    its demand site still runs through the whole pipeline and produces an
    answer, and that answer would be about a different question.
    """
    entities: dict[str, Entity] = {}
    claims: list[Claim] = []

    def region(rid: str) -> None:
        entities.setdefault(rid, Entity(rid, types=("region",), facets={
            "geo.place": Facet("geo.place", {"name": rid})}))

    survey = text.split("Flooding.")[0]
    for a, b in _LINK.findall(survey):
        region(a)
        region(b)
        a, b = sorted((a, b))
        claims.append(Claim("link", {"a": EntityRef(a), "b": EntityRef(b)}))
    if not claims:
        raise ValueError("no carriageways recovered; this is not a flood report")

    m = _FLOOD.search(text)
    if m:
        for rid in re.findall(r"region_\d+", m.group(1)):
            region(rid)
            claims.append(Claim("flooded", {"where": EntityRef(rid)}))

    for i, (a, b, limit) in enumerate(_LIMIT.findall(text)):
        region(a)
        region(b)
        bid = f"bridge_{i}"
        entities[bid] = Entity(bid, types=("bridge",), facets={
            "geo.network": Facet("geo.network", {"span": f"{a}-{b}"})})
        a, b = sorted((a, b))
        claims.append(Claim("bridge_on", {"a": EntityRef(a), "b": EntityRef(b),
                                          "via": EntityRef(bid)}))
        claims.append(Claim("load_limit", {"of": EntityRef(bid),
                                           "value": Quantity(float(limit), "kg")}))

    trucks = _TRUCK.findall(text)
    if not trucks:
        raise ValueError("no fleet recovered")
    for vid, mass, cap in trucks:
        entities[vid] = Entity(vid, types=("vehicle",), facets={
            "scene.body": Facet("scene.body", {"kind": "truck"}),
            "logic.constraint": Facet("logic.constraint", {
                "variables": {"payload": {"unit": "kg"}}})})
        claims.append(Claim("mass", {"of": EntityRef(vid),
                                     "value": Quantity(float(mass), "kg")}))
        claims.append(Claim("capacity", {"of": EntityRef(vid),
                                         "value": Quantity(float(cap), "kg")}))

    d = _DEPOT.search(text)
    n = _DEMAND.search(text)
    if not d or not n:
        raise ValueError("no depot or no requirement recovered")
    region(d.group(1))
    region(n.group(1))
    claims.append(Claim("depot", {"where": EntityRef(d.group(1))}))
    claims.append(Claim("needs", {"where": EntityRef(n.group(1))}))
    claims.append(Claim("demand", {"of": EntityRef(n.group(1)),
                                   "value": Quantity(float(n.group(2)), "kg")}))
    return WorldSnapshot(entities=entities, claims=tuple(claims))


def corrupt(world: WorldSnapshot, *, seed: int, rate: float,
            kinds: Iterable[str] = CLAIM_KINDS) -> WorldSnapshot:
    """Drop each claim of the named kinds with probability ``rate``.

    A dropped claim is a **recall** failure, which is the failure mode a real
    reader has most of: a sentence it did not match. Precision failures — a claim
    invented or a number misread — are a different channel and are not simulated
    here, so a result from this is a *lower bound* on how badly a real reader
    would hurt.

    ``bridge_on`` is dropped together with its ``load_limit``, because a reader
    that missed the sentence missed both halves of it; dropping only one would
    simulate a failure no reader has.
    """
    r = random.Random(int.from_bytes(
        hashlib.blake2b(f"corrupt|{seed}|{rate}|{sorted(kinds)}".encode(),
                        digest_size=8).digest(), "big"))
    kinds = set(kinds)
    dropped_bridges: set[str] = set()
    kept: list[Claim] = []
    for c in world.claims:
        if c.predicate == "load_limit" and "load_limit" in kinds:
            if r.random() < rate:
                dropped_bridges.add(c.roles["of"].id)
                continue
        elif c.predicate in kinds and r.random() < rate:
            continue
        kept.append(c)
    if dropped_bridges:
        kept = [c for c in kept
                if not (c.predicate == "bridge_on"
                        and c.roles["via"].id in dropped_bridges)]
    return WorldSnapshot(entities=world.entities, claims=tuple(kept),
                         alignments=world.alignments)


#: How a reader gets a number *wrong* rather than missing it. Each is a real
#: failure of OCR, tokenisation or unit handling, not an abstract perturbation:
#: a dropped or duplicated digit, a transposition, a thousands separator eaten,
#: a tonne read as a kilogram.
MISREADS = ("digit_dropped", "digit_added", "transposed", "unit_confused",
            "off_by_percent")


def misread(world: WorldSnapshot, *, seed: int, rate: float,
            direction: str = "either") -> WorldSnapshot:
    """Corrupt each Quantity with probability ``rate``, keeping the claim.

    This is the **precision** channel, and it is a different thing from
    :func:`corrupt`'s recall channel. A missing constraint is protected by
    slack — most bridge limits are not the binding one, so losing one often
    costs nothing. A *wrong* constraint has no such protection: it binds at the
    wrong value, and the pipeline has no way to notice.

    ``direction`` isolates the asymmetry that matters operationally.
    ``"permissive"`` only makes limits larger and masses smaller — errors that
    let a vehicle through that should not go. ``"conservative"`` only does the
    reverse. ``"either"`` is the realistic mixture. A reader whose errors are
    conservative is usable in a way one whose errors are permissive is not, even
    at the same error rate, and an average over both hides that entirely.
    """
    r = random.Random(int.from_bytes(
        hashlib.blake2b(f"misread|{seed}|{rate}|{direction}".encode(),
                        digest_size=8).digest(), "big"))
    #: which way a bigger number pushes the answer, per predicate
    permissive_up = {"load_limit": True, "capacity": True,
                     "mass": False, "demand": False}
    out = []
    for c in world.claims:
        q = c.roles.get("value")
        if not isinstance(q, Quantity) or r.random() >= rate:
            out.append(c)
            continue
        want_up = permissive_up.get(c.predicate)
        value = _perturb(q.value, r)
        if direction != "either" and want_up is not None:
            up = (want_up if direction == "permissive" else not want_up)
            if (value > q.value) != up:
                value = q.value + (q.value - value)      # flip the direction
        value = max(1.0, round(value, 3))
        out.append(replace(c, roles={**c.roles,
                                     "value": Quantity(value, q.unit, q.stderr)}))
    return WorldSnapshot(entities=world.entities, claims=tuple(out),
                         alignments=world.alignments)


def _perturb(value: float, r: random.Random) -> float:
    kind = r.choice(MISREADS)
    digits = str(int(value))
    if kind == "digit_dropped" and len(digits) > 1:
        i = r.randrange(len(digits))
        return float(digits[:i] + digits[i + 1:] or "1")
    if kind == "digit_added":
        i = r.randrange(len(digits) + 1)
        return float(digits[:i] + str(r.randrange(10)) + digits[i:])
    if kind == "transposed" and len(digits) > 1:
        i = r.randrange(len(digits) - 1)
        swapped = list(digits)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        return float("".join(swapped))
    if kind == "unit_confused":
        return value * r.choice([1000.0, 0.001])          # t read as kg
    return value * (1.0 + r.choice([-0.3, -0.2, 0.2, 0.3]))
