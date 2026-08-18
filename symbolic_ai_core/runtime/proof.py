"""A checkable derivation of an answer, and the asymmetry nobody advertises.

`APPROACH.md` claims two things for this substrate: a different order of magnitude
in cost, and **reasoning that is inspectable rather than inferred**. Six wake-ups
went into the first. This is the second, and measuring it turns up a distinction
that the phrase "inspectable" papers over.

A symbolic answer has two halves and they are not equally justifiable:

* **The existential half** — *there is a route of three legs, none over 2,000 km*
  — has a witness. The route itself. Checking it is three distance comparisons
  and touches nothing else in the graph, so a third party who trusts nothing can
  confirm it in microseconds.
* **The universal half** — *and there is no shorter route* — has no such witness.
  Nothing short of an argument about **every** path establishes it, and a
  certificate for it has to talk about the whole graph.

The standard certificate for the universal half is a **distance labelling**:
give every node a level, then check that no admissible edge skips a level. That
is a single pass over the edges with no search, no queue and no trust in the
solver — genuinely a verification rather than a re-run — but it is the same
order as solving, and this module measures how much that actually costs.

So "inspectable" is true and it is not uniform. The cheap half is the half that
says what *is*; the expensive half is the half that says what *is not*. That
distinction is worth having in the substrate rather than in a footnote, because
a system that reports only the witness is claiming optimality it has not
certified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

__all__ = ["Step", "ProofTrace", "DistanceCertificate", "verify_witness",
           "verify_optimality", "VerificationError"]


class VerificationError(Exception):
    """A trace failed to justify its own claim. Never returned as False.

    A verifier that returns a bare ``False`` invites a caller to treat a
    refutation as a missing value. This carries what broke.
    """


@dataclass(frozen=True)
class Step:
    """One justified move: from, to, and the fact that licensed it."""

    frm: str
    to: str
    measure: float
    bound: float
    relation: str = "<="

    def holds(self) -> bool:
        return self.measure <= self.bound if self.relation == "<=" \
            else self.measure >= self.bound

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.frm, "to": self.to, "measure": self.measure,
                "bound": self.bound, "relation": self.relation}


@dataclass(frozen=True)
class ProofTrace:
    """A witness for an existential claim, with its provenance.

    ``sources`` is not decoration: a route certified from bytes under an
    unresolved licence is a route you may not be able to publish, and the
    trace is where that travels with the answer instead of beside it.
    """

    claim: str
    steps: tuple[Step, ...]
    sources: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    @property
    def length(self) -> int:
        return len(self.steps)

    def endpoints(self) -> tuple[str, str] | None:
        if not self.steps:
            return None
        return self.steps[0].frm, self.steps[-1].to

    def to_dict(self) -> dict[str, Any]:
        return {"claim": self.claim, "steps": [s.to_dict() for s in self.steps],
                "sources": list(self.sources),
                "assumptions": list(self.assumptions)}


@dataclass(frozen=True)
class DistanceCertificate:
    """Levels that certify *no shorter route exists*.

    Valid when: the source is at level 0; every admissible edge ``(u, v)``
    satisfies ``level[v] <= level[u] + 1``; and the target's level matches the
    claimed answer. The middle condition is the one that costs — it quantifies
    over every edge, which is exactly what a universal claim requires.
    """

    source: str
    levels: Mapping[str, int]
    claimed: int


def verify_witness(trace: ProofTrace,
                   admissible: Mapping[str, Any] | None = None,
                   *, source: str | None = None,
                   target: str | None = None) -> int:
    """Check an existential claim from the trace alone. Returns the hop count.

    Touches only the steps in the trace — never the rest of the graph — which
    is the whole reason the existential half is cheap.
    """
    if source is not None and (not trace.steps or trace.steps[0].frm != source):
        raise VerificationError(
            f"trace starts at {trace.steps[0].frm if trace.steps else None!r}, "
            f"not the claimed source {source!r}")
    if target is not None and (not trace.steps or trace.steps[-1].to != target):
        raise VerificationError(
            f"trace ends at {trace.steps[-1].to if trace.steps else None!r}, "
            f"not the claimed target {target!r}")
    prev: str | None = None
    for i, step in enumerate(trace.steps):
        if prev is not None and step.frm != prev:
            raise VerificationError(
                f"step {i} starts at {step.frm!r} but step {i - 1} ended at "
                f"{prev!r}: the trace is not a connected walk")
        if not step.holds():
            raise VerificationError(
                f"step {i} ({step.frm} -> {step.to}) has measure "
                f"{step.measure} which fails {step.relation} {step.bound}")
        if admissible is not None and step.to not in admissible.get(step.frm, ()):
            raise VerificationError(
                f"step {i}: {step.to!r} is not adjacent to {step.frm!r}")
        prev = step.to
    return len(trace.steps)


def verify_optimality(cert: DistanceCertificate,
                      adjacency: Mapping[str, Iterable[str]],
                      target: str) -> int:
    """Check that no shorter route exists. One pass over every edge.

    No search, no queue, and no trust in whatever produced the levels — but it
    reads the whole graph, and that is the price of a universal claim.
    """
    if cert.levels.get(cert.source) != 0:
        raise VerificationError(
            f"source {cert.source!r} is at level "
            f"{cert.levels.get(cert.source)!r}, not 0")
    for u, neighbours in adjacency.items():
        lu = cert.levels.get(u)
        if lu is None:
            continue
        for v in neighbours:
            lv = cert.levels.get(v)
            if lv is not None and lv > lu + 1:
                raise VerificationError(
                    f"edge {u} -> {v} skips a level: {lu} -> {lv}. The "
                    "labelling does not certify a shortest path")
    reached = cert.levels.get(target)
    if reached != cert.claimed:
        raise VerificationError(
            f"target {target!r} is at level {reached!r} but the claim is "
            f"{cert.claimed!r}")
    return cert.claimed
