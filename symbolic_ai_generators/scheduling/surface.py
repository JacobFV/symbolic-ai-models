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


def _hard_pairs(world):
    """(machine, capability it lacks), (job, capability it does not need).

    Both drawn from the world so the sentence names a real entity and an
    in-vocabulary word -- the two properties that make the default distractors
    inert. Either may be ``None`` if nothing qualifies.
    """
    has: dict[str, set] = {}
    needs: dict[str, set] = {}
    for c in world.claims:
        if c.predicate == "has_capability":
            has.setdefault(c.roles["machine"].id, set()).add(
                c.roles["capability"])
        elif c.predicate == "needs_capability":
            needs.setdefault(c.roles["job"].id, set()).add(
                c.roles["capability"])
    mp = next(((m, c) for m in sorted(has) for c in CAPABILITIES
               if c not in has[m]), None)
    jp = next(((j, c) for j in sorted(needs) for c in CAPABILITIES
               if c not in needs[j]), None)
    return mp, jp


def render_observation(case: Any, *, seed: int | None = None,
                       variants: int = 1,
                       hard_distractors: bool | str = False,
                       packed: bool = False) -> Observation:
    """Render the works order.

    ``hard_distractors`` points the distractors at **real** entities with
    **in-vocabulary** capabilities, which the reader must then admit. The
    default distractors are defanged the same way flood's disused track was: the
    withdrawn machine and cancelled job carry no capability and no quantity, and
    "no machine is set up for anodising" names a capability outside the
    vocabulary, so the capability list rejects all three for free.

    The two hard forms are **not symmetric**, and the asymmetry is the point:
    each job needs exactly one capability, so a spurious ``needs_capability`` is
    an arity violation and can be caught; a machine holds any number, so a
    spurious ``has_capability`` cannot. And the uncatchable one is the
    **unsound** one -- an extra machine capability makes an infeasible instance
    read as feasible.

    ``packed`` renders **two claims in one sentence** -- a machine's capacity and
    one of its capabilities -- with a span for each over the same text. Real prose
    does this constantly and none of the generated surfaces did; see
    ``notes/findings/2026-08-19-on-real-prose-the-sentence-is-the-wrong-unit.md``.
    Default ``False`` so published numbers keep their meaning.

    Pass ``True`` for both, or ``"machine"`` / ``"job"`` for one side, so the
    two can be priced apart. Default ``False``, so every published number keeps
    its meaning; ``True`` is the honest setting.
    """
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
    cap_of: dict[str, int] = {}
    for i in by.get("has_capability", []):
        cap_of.setdefault(role(i, "machine"), i)
    packed_machines = set()
    for i in sorted(by.get("capacity", []), key=lambda i: role(i, "of")):
        m = role(i, "of")
        doc.glue(" ")
        if packed and m in cap_of:
            j = cap_of[m]
            c = role(j, "capability")
            start = doc._n
            doc.add(f"{m} is set up for {c} and has {qty(i):.2f} hours "
                    "available.", claim=i, kind="capacity", entities=(m,))
            doc.spans.append(Span(start, doc._n, j, "has_capability", (m,)))
            packed_machines.add(m)
            continue
        doc.add(pick("capacity").format(m=m, n=qty(i)), claim=i,
                kind="capacity", entities=(m,))
    doc.glue(" ")
    doc.add("machine_90 is withdrawn for maintenance and is not available this "
            "shift.")
    _sides = ({"machine", "job"} if hard_distractors is True
              else {hard_distractors} if hard_distractors else set())
    _mp, _jp = _hard_pairs(world) if _sides else (None, None)

    doc.glue("\n\nCAPABILITIES.")
    for i in sorted(by.get("has_capability", []),
                    key=lambda i: (role(i, "machine"), role(i, "capability"))):
        m, c = role(i, "machine"), role(i, "capability")
        if m in packed_machines and cap_of.get(m) == i:
            continue                      # already stated inside its capacity line
        doc.glue(" ")
        doc.add(pick("has_capability").format(m=m, c=c), claim=i,
                kind="has_capability", entities=(m,))
    doc.glue(" ")
    doc.add("No machine on this floor is set up for anodising.")
    if _mp and "machine" in _sides:
        m, c = _mp
        doc.glue(" ")
        doc.add(f"{m} was set up to {c} last shift, before the head came off.")

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
    if _jp and "job" in _sides:
        j, c = _jp
        doc.glue(" ")
        doc.add(f"{j} used to {c} as well, until the drawing was revised.")

    doc.glue("\n\nTASKING. ")
    doc.add("Can every job be assigned to a machine that has its capability, "
            "without any machine exceeding its available hours?")

    text = doc.text()
    return Observation(text=text, paragraphs=tuple(text.split("\n\n")),
                       spans=tuple(doc.spans), seed=case.seed)
