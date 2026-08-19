"""The last box: structured answer -> a grounded answer paragraph.

The pipeline is ``text -> world IR -> multi-kernel flow -> structured output +
text`` and the final box was unbuilt. A renderer is only worth having if its
output is **checkable**, so the design commitment here is:

> **Every factual assertion in the paragraph carries a citation to a claim in the
> world or to a named kernel output, and an unsupported assertion is detectable
> mechanically.**

Two things follow from that and they are the point rather than niceties.

**The structured answer stays canonical.** :attr:`Answer.structured` is what the
flow returned; the paragraph is strictly downstream. Generation quality therefore
cannot contaminate reasoning evaluation -- a renderer that writes badly loses
nothing from the task score, and a renderer that writes *falsely* is caught by
:func:`ungrounded` rather than by a reader's judgement.

**The negative answer is the interesting one.** "No vehicle can make the
delivery" is easy to assert and hard to justify: saying *which* vehicle failed on
*which* crossing at *what* laden mass requires reading `load_report` and the
`load_limit` claims together. That is exactly where an ungrounded renderer would
invent a reason, so it is where the checker earns its place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from symbolic_ai_core.world import Quantity

__all__ = ["Citation", "Answer", "render_answer", "ungrounded"]

_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_ENT = re.compile(r"\b(?:region|truck|bridge)_\d+\b")


@dataclass(frozen=True)
class Citation:
    """One asserted fact and where it came from."""

    start: int
    end: int
    #: ``claim:<index>`` or ``flow:<output>.<path>``
    source: str


@dataclass
class Answer:
    #: exactly what the flow returned. The paragraph never overrides this.
    structured: tuple[str, ...] = ()
    text: str = ""
    citations: tuple[Citation, ...] = ()


class _Para:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.cites: list[Citation] = []
        self._n = 0

    def say(self, text: str, source: str | None = None) -> None:
        start = self._n
        self.parts.append(text)
        self._n += len(text)
        if source:
            self.cites.append(Citation(start, self._n, source))

    def glue(self, text: str) -> None:
        self.parts.append(text)
        self._n += len(text)

    def text(self) -> str:
        return "".join(self.parts)


def _claim_index(world) -> dict[str, int]:
    """``load_limit`` by bridge id, and the demand, for citation."""
    out: dict[str, int] = {}
    for i, c in enumerate(world.claims):
        if c.predicate == "load_limit":
            out[f"limit:{c.roles['of'].id}"] = i
        elif c.predicate == "demand":
            out["demand"] = i
        elif c.predicate in ("mass", "capacity"):
            out[f"{c.predicate}:{c.roles['of'].id}"] = i
    return out


def _walk(edges: list, *, start: str) -> list[str]:
    """Order an unordered edge set into the walk it represents.

    The flow reports a route as a SET of edges. A first version rendered the
    endpoints in list order and produced "region_0 to region_3 to region_4 to
    region_5" for a route that actually runs region_0 -> region_5 -> region_4 ->
    region_3. Every token in that sentence is grounded -- they are all real
    regions -- so the token-level check passed a false ordering, which is why
    :func:`ungrounded` now checks adjacency as well.
    """
    adj: dict[str, list[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if start not in adj:
        ends = [n for n, xs in adj.items() if len(xs) == 1]
        start = ends[0] if ends else next(iter(adj), "")
    out, seen = [start], {start}
    while True:
        nxt = next((x for x in adj.get(out[-1], []) if x not in seen), None)
        if nxt is None:
            return out
        out.append(nxt)
        seen.add(nxt)


def render_answer(case: Any, structured: tuple[str, ...],
                  outputs: dict[str, Any]) -> Answer:
    """A paragraph grounded in the flow's own outputs."""
    world = case.world
    idx = _claim_index(world)
    report = outputs["load_report"].value
    per_vehicle: dict[str, list] = report.get("per_vehicle", {})
    demand = next((float(c.roles["value"].value) for c in world.claims
                   if c.predicate == "demand"
                   and isinstance(c.roles.get("value"), Quantity)), None)
    site = next((c.roles["where"].id for c in world.claims
                 if c.predicate == "needs"), "")
    depot = next((c.roles["where"].id for c in world.claims
                  if c.predicate == "depot"), "")
    p = _Para()

    if structured:
        names = ", ".join(structured)
        p.say(f"{'One vehicle' if len(structured) == 1 else f'{len(structured)} vehicles'} "
              f"can make the delivery: ", "flow:fused")
        p.say(names, "flow:fused")
        p.glue(". ")
    else:
        p.say("No vehicle can make the delivery", "flow:fused")
        p.glue(". ")

    if demand is not None and site:
        p.glue("The requirement is ")
        p.say(f"{demand:.0f}", f"claim:{idx.get('demand')}")
        p.glue(" kg into ")
        p.say(site, "claim:needs")
        p.glue(". ")

    # No vehicle has ANY route: the site is unreachable, and the paragraph has
    # to say so. A first version fell silent here and asserted a verdict with no
    # reason -- caught by the test that a refusal must explain itself.
    if not any(per_vehicle.values()):
        flooded = [c.roles["where"].id for c in world.claims
                   if c.predicate == "flooded"]
        p.glue("No route reaches it at all")
        if flooded:
            p.glue(": the network is cut by flooding in ")
            for n, w in enumerate(flooded):
                if n:
                    p.glue(" and ")
                p.say(w, "claim:flooded")
        p.glue(". ")

    # Per-vehicle justification, successes first, then the refusals with reasons.
    for vehicle in sorted(per_vehicle):
        routes = per_vehicle[vehicle]
        if not routes:
            continue
        r = next((x for x in routes if x.get("feasible")), routes[0])
        edges = r.get("edges") or []
        limits = r.get("limits") or []
        nodes = _walk(edges, start=depot)
        path = " to ".join(nodes)
        src = f"flow:load_report.per_vehicle.{vehicle}"
        if r.get("feasible"):
            p.glue(f"{vehicle} runs ")
            p.say(path or "no route", src)
            if limits:
                p.glue(" and clears the tightest posted limit on it, ")
                p.say(f"{min(limits):.0f}", src)
                p.glue(" kg")
            p.glue(". ")
        else:
            p.glue(f"{vehicle} cannot: on ")
            p.say(path or "no route", src)
            if limits:
                p.glue(" the binding limit is ")
                p.say(f"{min(limits):.0f}", src)
                p.glue(" kg")
            outcome = r.get("outcome", "")
            p.glue(f", and the solver returned {outcome}. "
                   if outcome else ". ")

    unresolved = outputs.get("unresolved")
    n_unres = len(unresolved.value) if unresolved is not None else 0
    if n_unres:
        p.glue("Some facts remain unresolved (")
        p.say(str(n_unres), "flow:unresolved")
        p.glue("), so this answer is conditional on them.")

    return Answer(structured=structured, text=p.text(),
                  citations=tuple(p.cites))


def ungrounded(answer: Answer, case: Any, outputs: dict[str, Any]) -> list[str]:
    """Tokens asserted in the paragraph that nothing supports.

    Every number and entity id in the text must appear in the world's claims or
    in the flow's outputs. This is the check that lets a renderer be *wrong*
    rather than merely *ungraceful*, and it is why the paragraph is safe to
    generate at all: an invented crossing limit shows up here, not in a reader's
    impression of the prose.

    **Scope, and it is narrower than "grounded" sounds.** The admissible edges
    below are built from ``report``, i.e. from the routes the flow computed *from
    the world it was given*. When that world came from a reader, a route over a
    claim the reader **invented** is self-consistent and passes. Measured
    2026-08-19 on the hard-distractor surface: a case whose true answer is EMPTY
    renders as *"truck_0 runs region_0 to region_3"* -- a road that exists in no
    claim of the true world -- and this function returns ``[]``.

    So it certifies **internal consistency with the world as read**, not truth.
    It catches renderer errors -- invented numbers, false orderings, a paragraph
    contradicting the structured answer -- and it cannot, by construction, catch
    reader errors. A pipeline quoting "grounded 1.000" as a safety property is
    quoting the wrong thing unless its world is the oracle's.
    """
    known_nums: set[str] = set()
    known_ents: set[str] = set()
    for c in case.world.claims:
        known_ents.update(c.entities())
        v = c.roles.get("value")
        if isinstance(v, Quantity):
            known_nums.add(f"{float(v.value):.0f}")
            known_nums.add(f"{float(v.value):g}")
    report = outputs["load_report"].value
    for vehicle, routes in report.get("per_vehicle", {}).items():
        known_ents.add(vehicle)
        for r in routes:
            for a, b in r.get("edges") or []:
                known_ents.update((a, b))
            for lim in r.get("limits") or []:
                known_nums.add(f"{float(lim):.0f}")
    known_nums.update(str(len(answer.structured)))
    unresolved = outputs.get("unresolved")
    if unresolved is not None:
        known_nums.add(str(len(unresolved.value)))

    # Relation-level check. Token grounding cannot see a false ORDERING -- every
    # region in "region_0 to region_3 to region_4" may be real while the walk is
    # not one -- so every consecutive pair stated as a route must be an edge of
    # some reported route.
    real_edges: set[frozenset] = set()
    for routes in report.get("per_vehicle", {}).values():
        for r in routes:
            for a, b in r.get("edges") or []:
                real_edges.add(frozenset((a, b)))
    # Contradiction check. Token grounding and adjacency both pass a sentence
    # that asserts the OPPOSITE of the structured answer using only real tokens
    # on a real route -- "truck_1 runs <real path> and clears 4500 kg" when
    # truck_1 is not in the decision. The whole separation between reasoning and
    # generation is that the structured answer is canonical and the paragraph is
    # downstream; that is worth nothing if the paragraph can disagree with it and
    # nothing notices.
    bad: list[str] = []
    can = set(answer.structured)
    for m in re.finditer(r"(truck_\d+) (runs|cannot)", answer.text):
        vehicle, verb = m.group(1), m.group(2)
        asserted_able = verb == "runs"
        if asserted_able != (vehicle in can):
            bad.append(
                f"paragraph says {vehicle} {verb!r} but the structured answer "
                f"{'includes' if vehicle in can else 'excludes'} it")
    for m in re.finditer(r"((?:region_\d+)(?: to region_\d+)+)", answer.text):
        hops = m.group(1).split(" to ")
        for a, b in zip(hops, hops[1:]):
            if frozenset((a, b)) not in real_edges:
                bad.append(f"route hop {a}->{b} is not an edge of any "
                           f"reported route")

    for tok in _NUM.findall(answer.text):
        if tok not in known_nums:
            bad.append(f"number {tok} appears in no claim or flow output")
    for tok in _ENT.findall(answer.text):
        if tok not in known_ents:
            bad.append(f"entity {tok} appears in no claim or flow output")
    return bad
