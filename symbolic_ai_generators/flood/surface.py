"""A multi-paragraph observation surface with exact span → claim alignment.

The flood generator already emits a report, and
`symbolic_ai_generators/flood/read.py` recovers the world from it with regexes
that match that report's exact phrasings. Its own docstring says so: *"a report
written by a person would defeat it entirely"*. That makes it a fine instrument
for turning fidelity down on purpose and a useless one for asking whether
anything can **read**.

This is the surface a reader has to earn. Same latent world, same claims, but:

- **Five paragraphs** in the shape the programme asked for — actors and places,
  infrastructure, current events, quantities and constraints, query context.
- **Distance.** A vehicle's mass is stated in the fleet roster (¶1) and its
  capacity in the quantities paragraph (¶4). Nothing about one entity is
  recoverable from one sentence.
- **References.** After first mention an entity is *"the depot"*, *"that
  crossing"*, *"it"*, *"the same vehicle"*. A reader that keys on canonical ids
  loses every fact stated about a pronoun.
- **Distractors.** Superseded values (*"was rated at X before the resurfacing"*),
  regions outside the affected area, and a vehicle held elsewhere. These are
  aligned to **no claim**, so a reader that takes every number pays for it in
  precision.
- **Indirect statements.** Flooding as negation (*"no longer passable"*) rather
  than as a keyword, limits as *"rated for"* rather than *"posted at"*.

**Every claim in the world is aligned to at least one span, and every span
carries the index of the claim it realises or `None` if it is a distractor.**
That is what makes world-level scoring possible: entity, relation, quantity and
claim precision/recall are all computable against this rather than estimated.

The phrasings deliberately avoid `read.py`'s regexes. That is not a trick — it is
the point. A reader that only works on the surface it was written for has not
been shown to read, and the first number this surface produces is exactly how far
the template reader falls when the words change and the world does not.

Run the alignment self-check with `uv run pytest tests/test_flood_surface.py`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot

__all__ = ["Span", "Observation", "render_observation"]

#: Regions named in the prose that are not in the world at all. A reader that
#: harvests every `region_N` token will invent links and pay in precision.
_OUTSIDE = ("region_88", "region_91", "region_94")


@dataclass(frozen=True)
class Span:
    """A character range of the observation, and what it realises."""

    start: int
    end: int
    #: index into ``world.claims``, or ``None`` for a distractor span
    claim: int | None
    #: the predicate realised, or ``"distractor"``
    kind: str
    #: entity ids the span mentions, canonical form
    entities: tuple[str, ...] = ()
    #: how the entity was referred to: "name", "definite", "pronoun"
    reference: str = "name"

    @property
    def text_of(self):
        return lambda doc: doc[self.start:self.end]


@dataclass
class Observation:
    """The document, its paragraphs, and the alignment."""

    text: str = ""
    paragraphs: tuple[str, ...] = ()
    spans: tuple[Span, ...] = ()
    seed: int = 0
    #: claim index -> the spans realising it
    by_claim: dict[int, tuple[int, ...]] = field(default_factory=dict)

    def covered(self) -> set[int]:
        return {s.claim for s in self.spans if s.claim is not None}

    def distractors(self) -> tuple[Span, ...]:
        return tuple(s for s in self.spans if s.claim is None)


class _Doc:
    """Accumulates text while recording exact offsets."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.spans: list[Span] = []
        self._n = 0

    def add(self, text: str, *, claim: int | None = None,
            kind: str = "distractor", entities: tuple[str, ...] = (),
            reference: str = "name") -> None:
        start = self._n
        self.parts.append(text)
        self._n += len(text)
        self.spans.append(Span(start, self._n, claim, kind, entities,
                               reference))

    def glue(self, text: str) -> None:
        """Connective tissue that realises nothing."""
        self.parts.append(text)
        self._n += len(text)

    def text(self) -> str:
        return "".join(self.parts)


def _index(world: WorldSnapshot) -> dict[tuple, int]:
    """``(predicate, *entity ids)`` -> claim index, for alignment lookup."""
    out: dict[tuple, int] = {}
    for i, c in enumerate(world.claims):
        out[(c.predicate, *c.entities())] = i
    return out


def _q(claim: Claim) -> float:
    v = claim.roles.get("value")
    return float(v.value) if isinstance(v, Quantity) else float("nan")


def render_observation(case: Any, *, seed: int | None = None) -> Observation:
    """Render ``case`` as five aligned paragraphs.

    ``case`` is a :class:`~symbolic_ai_generators.flood.FloodCase`. The world is
    read off ``case.world`` so the alignment indexes the same claim tuple the
    kernels consume -- an alignment against a re-derived world would be a
    different object and would silently drift.
    """
    world = case.world
    rng = random.Random(case.seed if seed is None else seed)
    idx = _index(world)
    doc = _Doc()

    by_pred: dict[str, list[int]] = {}
    for i, c in enumerate(world.claims):
        by_pred.setdefault(c.predicate, []).append(i)

    def ent(c: int, role: str) -> str:
        r = world.claims[c].roles[role]
        return r.id if isinstance(r, EntityRef) else str(r)

    # ---- 1. actors, places, background ---------------------------------
    depot_i = by_pred["depot"][0]
    depot = ent(depot_i, "where")
    regions = sorted({e for i in by_pred.get("link", [])
                      for e in world.claims[i].entities()})
    doc.add(f"SITUATION REPORT. The relief operation covers {len(regions)} "
            f"districts in the valley.")
    doc.glue(" ")
    doc.add(f"Depot operations are run out of {depot}, which is where every "
            f"vehicle starts the day.", claim=depot_i, kind="depot",
            entities=(depot,))
    doc.glue(" ")
    doc.add(f"Districts {_OUTSIDE[0]} and {_OUTSIDE[1]} lie outside the "
            f"affected area and are not served by this operation.")
    doc.glue(" ")
    doc.add("The fleet on site is as follows.")
    for n, mi in enumerate(sorted(by_pred.get("mass", []),
                                  key=lambda i: ent(i, "of"))):
        v = ent(mi, "of")
        doc.glue(" ")
        doc.add(f"{v} weighs {_q(world.claims[mi]):.0f} kg empty.",
                claim=mi, kind="mass", entities=(v,))
        if n == 0:
            doc.glue(" ")
            doc.add(f"A further vehicle, truck_90, is committed elsewhere in "
                    f"the region and is unavailable.")

    # ---- 2. infrastructure and relationships ---------------------------
    doc.glue("\n\n")
    doc.add("ROAD NETWORK.")
    for li in by_pred.get("link", []):
        a, b = ent(li, "a"), ent(li, "b")
        doc.glue(" ")
        doc.add(f"{a} and {b} are joined by a surfaced road.",
                claim=li, kind="link", entities=(a, b))
    doc.glue(" ")
    doc.add(f"A disused track once ran from {_OUTSIDE[0]} to {_OUTSIDE[2]}; it "
            f"has not carried traffic for years.")
    for bi in by_pred.get("bridge_on", []):
        a, b = ent(bi, "a"), ent(bi, "b")
        doc.glue(" ")
        doc.add(f"The {a}-{b} road runs over a river crossing.",
                claim=bi, kind="bridge_on", entities=(a, b))

    # ---- 3. current events, failures, changes --------------------------
    doc.glue("\n\n")
    doc.add("OVERNIGHT.")
    for fi in by_pred.get("flooded", []):
        w = ent(fi, "where")
        doc.glue(" ")
        doc.add(f"Water rose through {w} during the night and it is no longer "
                f"passable; nothing may be routed through it.",
                claim=fi, kind="flooded", entities=(w,))
    doc.glue(" ")
    doc.add("Two footbridges were also lost, neither of them on a road used by "
            "heavy vehicles.")

    # ---- 4. quantities, constraints, exceptions ------------------------
    doc.glue("\n\n")
    doc.add("LOADING AND LIMITS.")
    limits = sorted(by_pred.get("load_limit", []),
                    key=lambda i: ent(i, "of"))
    bridge_pair = {ent(bi, "via"): (ent(bi, "a"), ent(bi, "b"))
                   for bi in by_pred.get("bridge_on", [])}
    for n, li in enumerate(limits):
        br = ent(li, "of")
        a, b = bridge_pair.get(br, (br, br))
        kg = _q(world.claims[li])
        doc.glue(" ")
        if n == 1:
            # A superseded value: the distractor is the OLD number. It must not
            # coincide with any real quantity in the world, or "take every
            # number" would be accidentally right here and the distractor would
            # not be testing anything.
            real = {_q(c) for c in world.claims
                    if isinstance(c.roles.get("value"), Quantity)}
            offsets = [d for d in (500, 1000, 1500, 2000, 2500, 700, 1300)
                       if kg + d not in real]
            old_kg = kg + (rng.choice(offsets) if offsets else 10_000)
            doc.add(f"The {a}-{b} crossing was rated at {old_kg:.0f} kg before "
                    f"last year's resurfacing;")
            doc.glue(" ")
            doc.add(f"it is now rated for {kg:.0f} kg.", claim=li,
                    kind="load_limit", entities=(br,), reference="pronoun")
        else:
            doc.add(f"The {a}-{b} crossing is rated for {kg:.0f} kg.",
                    claim=li, kind="load_limit", entities=(br,),
                    reference="definite")
    doc.glue(" ")
    doc.add("Ratings are for the laden vehicle, not the payload alone.")
    caps = sorted(by_pred.get("capacity", []), key=lambda i: ent(i, "of"))
    masses = {ent(i, "of"): _q(world.claims[i]) for i in by_pred.get("mass", [])}
    for n, ci in enumerate(caps):
        v = ent(ci, "of")
        doc.glue(" ")
        if n == 0:
            # A pronoun needs a RECOVERABLE antecedent, or the ground truth is
            # wrong rather than the reader. The naming sentence is glue -- it
            # realises no claim -- and the pronoun in the next sentence resolves
            # to it, which is the coreference step the reader has to do.
            lightest = min(masses, key=lambda k: masses[k]) if masses else v
            doc.glue(f"Turning to payloads, {lightest} is the lightest of "
                     f"them. ")
            doc.add(f"It can take a further {_q(world.claims[ci]):.0f} kg on "
                    f"top of its own weight.", claim=ci, kind="capacity",
                    entities=(v,), reference="pronoun")
        else:
            doc.add(f"The vehicle listed as {v} can take a further "
                    f"{_q(world.claims[ci]):.0f} kg.", claim=ci,
                    kind="capacity", entities=(v,), reference="definite")

    # ---- 5. query context ----------------------------------------------
    doc.glue("\n\n")
    needs_i = by_pred["needs"][0]
    dem_i = by_pred["demand"][0]
    site = ent(needs_i, "where")
    doc.add("TASKING.")
    doc.glue(" ")
    doc.add(f"A request has come in from {site}.", claim=needs_i,
            kind="needs", entities=(site,))
    doc.glue(" ")
    doc.add(f"It is for {_q(world.claims[dem_i]):.0f} kg of supplies.",
            claim=dem_i, kind="demand", entities=(site,),
            reference="pronoun")
    doc.glue(" ")
    doc.add("Which vehicles in the fleet can complete that delivery in one "
            "run, starting from the depot?")

    text = doc.text()
    paragraphs = tuple(text.split("\n\n"))
    by_claim: dict[int, list[int]] = {}
    for si, s in enumerate(doc.spans):
        if s.claim is not None:
            by_claim.setdefault(s.claim, []).append(si)
    return Observation(text=text, paragraphs=paragraphs,
                       spans=tuple(doc.spans), seed=case.seed,
                       by_claim={k: tuple(v) for k, v in by_claim.items()})
