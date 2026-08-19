"""A multi-paragraph observation surface for machine assignment, exactly aligned.

The third domain. Flood is routing with a subset answer and two expensive
kernels; solvency is a bitemporal boolean with a trivial kernel; scheduling is a
boolean over an **NP-hard search**, with a tunable margin.

Five paragraphs, every claim aligned:

    1  the shop -- machines and their available hours
    2  what each machine can do -- capabilities
    3  the work -- jobs and their durations
    4  requirements -- the capability each job needs
    5  the question

**Distance is deliberate**: a job's duration is in ¶3 and the capability it needs
is in ¶4, so nothing about one job is recoverable from one sentence -- the same
split flood uses for a vehicle's mass and capacity.

**Distractors**: a machine withdrawn for maintenance, a cancelled job, and a
capability nobody on the floor holds. Each is aligned to no claim.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from symbolic_ai_core.world import Quantity

__all__ = ["Span", "Observation", "render_observation", "CAPABILITIES"]

#: The closed capability vocabulary. External knowledge, and the lexical
#: counterpart of flood's numeric value registry.
CAPABILITIES = ("cut", "paint", "weld")

_VARIANTS = {
    "capacity": (
        "{m} has {n:.2f} hours available.",
        "There are {n:.2f} hours free on {m}.",
        "{m} can run for {n:.2f} hours.",
        "Available time on {m}: {n:.2f} hours.",
    ),
    "has_capability": (
        "{m} is set up for {c}.",
        "{m} can do {c} work.",
        "The {c} station is {m}.",
        "{c} is available on {m}.",
    ),
    "duration": (
        "{j} takes {n:.2f} hours.",
        "{j} is a {n:.2f} hour job.",
        "Allow {n:.2f} hours for {j}.",
        "The estimate for {j} is {n:.2f} hours.",
    ),
    "needs_capability": (
        "{j} requires {c}.",
        "{j} cannot be run without {c}.",
        "{c} is needed for {j}.",
        "{j} is a {c} job.",
    ),
}


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    claim: int | None
    kind: str
    entities: tuple[str, ...] = ()


@dataclass
class Observation:
    text: str = ""
    paragraphs: tuple[str, ...] = ()
    spans: tuple[Span, ...] = ()
    seed: int = 0

    def covered(self) -> set[int]:
        return {s.claim for s in self.spans if s.claim is not None}

    def distractors(self) -> tuple[Span, ...]:
        return tuple(s for s in self.spans if s.claim is None)


class _Doc:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.spans: list[Span] = []
        self._n = 0

    def add(self, text, *, claim=None, kind="distractor", entities=()):
        start = self._n
        self.parts.append(text)
        self._n += len(text)
        self.spans.append(Span(start, self._n, claim, kind, entities))

    def glue(self, text):
        self.parts.append(text)
        self._n += len(text)

    def text(self):
        return "".join(self.parts)


def render_observation(case: Any, *, seed: int | None = None,
                       variants: int = 1) -> Observation:
    world = case.world
    rng = random.Random(case.seed if seed is None else seed)

    def pick(kind):
        forms = _VARIANTS[kind]
        return forms[rng.randrange(min(variants, len(forms)))]

    by: dict[str, list[int]] = {}
    for i, c in enumerate(world.claims):
        by.setdefault(c.predicate, []).append(i)

    def role(i, name):
        r = world.claims[i].roles[name]
        return r.id if hasattr(r, "id") else str(r)

    def qty(i):
        v = world.claims[i].roles.get("value")
        return float(v.value) if isinstance(v, Quantity) else float("nan")

    doc = _Doc()
    doc.add("WORKS ORDER. The floor is being scheduled for a single shift.")
    for i in sorted(by.get("capacity", []), key=lambda i: role(i, "of")):
        m = role(i, "of")
        doc.glue(" ")
        doc.add(pick("capacity").format(m=m, n=qty(i)), claim=i,
                kind="capacity", entities=(m,))
    doc.glue(" ")
    doc.add("machine_90 is withdrawn for maintenance and is not available this "
            "shift.")

    doc.glue("\n\nCAPABILITIES.")
    for i in sorted(by.get("has_capability", []),
                    key=lambda i: (role(i, "machine"), role(i, "capability"))):
        m, c = role(i, "machine"), role(i, "capability")
        doc.glue(" ")
        doc.add(pick("has_capability").format(m=m, c=c), claim=i,
                kind="has_capability", entities=(m,))
    doc.glue(" ")
    doc.add("No machine on this floor is set up for anodising.")

    doc.glue("\n\nTHE WORK.")
    for i in sorted(by.get("duration", []), key=lambda i: role(i, "of")):
        j = role(i, "of")
        doc.glue(" ")
        doc.add(pick("duration").format(j=j, n=qty(i)), claim=i,
                kind="duration", entities=(j,))
    doc.glue(" ")
    doc.add("job_90 was cancelled by the customer and has been struck from the "
            "list.")

    doc.glue("\n\nREQUIREMENTS.")
    for i in sorted(by.get("needs_capability", []),
                    key=lambda i: role(i, "job")):
        j, c = role(i, "job"), role(i, "capability")
        doc.glue(" ")
        doc.add(pick("needs_capability").format(j=j, c=c), claim=i,
                kind="needs_capability", entities=(j,))

    doc.glue("\n\nTASKING. ")
    doc.add("Can every job be assigned to a machine that has its capability, "
            "without any machine exceeding its available hours?")

    text = doc.text()
    return Observation(text=text, paragraphs=tuple(text.split("\n\n")),
                       spans=tuple(doc.spans), seed=case.seed)
