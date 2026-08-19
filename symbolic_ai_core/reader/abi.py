"""The reader contract, and `reader.run@1`."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from symbolic_ai_core.artifact.value import Artifact
from symbolic_ai_core.flow.port import Port
from symbolic_ai_core.flow.registry import OpDef, register_op
from symbolic_ai_core.world import Claim, WorldDelta, WorldSnapshot

__all__ = ["ReadResult", "Reader", "Factor", "Mention", "Alignment",
           "register_reader", "get_reader", "list_readers", "READER_RUN"]


@dataclass(frozen=True)
class Alignment:
    """One claim and the span of text it was read from.

    The generated surfaces supply this exactly; a learned reader is trained on it
    and a deployed one emits it so a renderer can cite the source rather than the
    reading.
    """

    start: int
    end: int
    claim: int                      #: index into ``ReadResult.claims``
    detail: str = ""


@dataclass(frozen=True)
class Mention:
    """A surface span and the entities it *might* denote. Identity stays open.

    Candidate identity belongs early and **collapse belongs late**, because
    relation semantics disambiguate identity -- *Mercury* plus *orbits the Sun*
    is resolved by the predicate, not before it. A reader that resolves
    irrevocably at the mention stage throws away the evidence that would have
    settled it.
    """

    start: int
    end: int
    text: str
    entities: tuple[str, ...] = ()      #: candidate ids, best first
    belief: tuple[float, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class Factor:
    """A constraint over candidate claims, compact rather than enumerated.

    The point of not returning a settled world is to be able to say

        claim A: 0.62,  claim B: 0.38,  A XOR B

    without materialising two worlds. Enumeration is one *reading* of a factor
    set and is exponential in the number of open choices; the factor is what the
    reader actually knows.

    ``kind`` is ``"xor"`` (exactly one holds), ``"at_most_one"``, ``"implies"``
    (the first entails the rest) or ``"requires"`` (the first is only assertable
    with the rest). ``exclusive`` kinds are the ones for which agreement across
    readings is a sound *and complete* error detector -- measured, and measured
    not to hold when the alternatives are merely different facts.
    """

    kind: str
    claims: tuple[int, ...]             #: indices into ``ReadResult.claims``
    detail: str = ""

    @property
    def exclusive(self) -> bool:
        return self.kind in ("xor", "at_most_one")


@dataclass(frozen=True)
class ReadResult:
    """What a reader produces. Deliberately not a `WorldSnapshot`, and
    deliberately not a single `WorldDelta`.

    A snapshot is a settled world: handing one back means every distinction the
    reader could not make has already been guessed, invisibly. A single delta is
    barely better -- it still forces one reading. What a reader actually knows is
    **a pool of candidate claims, a belief over them, and constraints among
    them**, which is what these fields are.

    Collapsing to a delta is a *decision*, taken by :meth:`delta` and by nobody
    implicitly.
    """

    claims: tuple[Claim, ...] = ()
    belief: Mapping[int, float] = field(default_factory=dict)
    factors: tuple[Factor, ...] = ()
    mentions: tuple[Mention, ...] = ()
    unresolved: tuple[str, ...] = ()
    alignments: tuple[Alignment, ...] = ()
    provenance: str = ""
    cost_s: float = 0.0
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def confidence_of(self, i: int) -> float:
        return float(self.belief.get(i, 1.0))

    def delta(self, *, threshold: float = 0.5,
              thresholds: Mapping[str, float] | None = None) -> WorldDelta:
        """One reading, chosen here rather than assumed upstream.

        Takes every claim believed at or above its threshold, then honours the
        exclusive factors by keeping only each factor's best-believed member.
        That is a *policy*; a caller with a better one should write it, and the
        fact that it has to is the point.

        ``thresholds`` gives a **per-predicate** cut, which is what the kernels
        actually imply. Deleting a true claim and inventing a false one are not
        equally costly, and the ratio differs by predicate: expected cost is
        minimised at ``s⁺ / (s⁺ + s⁻)``, measured at 0.000 for a claim that only
        supplies capacity and 0.608 for one that imposes a constraint. A single
        0.5 for everything asserts the truth of a uniformity that was measured
        and found false.
        """
        def cut(i: int) -> float:
            if thresholds is None:
                return threshold
            return float(thresholds.get(self.claims[i].predicate, threshold))

        keep = {i for i in range(len(self.claims))
                if self.confidence_of(i) >= cut(i)}
        for f in self.factors:
            if not f.exclusive:
                continue
            members = [i for i in f.claims if i < len(self.claims)]
            if len(members & keep if isinstance(members, set)
                   else set(members) & keep) <= 1:
                continue
            best = max(members, key=self.confidence_of)
            keep -= set(members) - {best}
        return WorldDelta(claims=tuple(self.claims[i] for i in sorted(keep)))

    def settled(self) -> bool:
        """True when nothing was left open. The caller may still be wrong."""
        return not self.factors and not self.unresolved

    def to_dict(self) -> dict:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "belief": {str(k): v for k, v in self.belief.items()},
            "factors": [{"kind": f.kind, "claims": list(f.claims),
                         "detail": f.detail} for f in self.factors],
            "mentions": [{"start": m.start, "end": m.end, "text": m.text,
                          "entities": list(m.entities),
                          "belief": list(m.belief), "detail": m.detail}
                         for m in self.mentions],
            "unresolved": list(self.unresolved),
            "alignments": [{"start": a.start, "end": a.end, "claim": a.claim,
                            "detail": a.detail} for a in self.alignments],
            "provenance": self.provenance,
            "cost_s": self.cost_s,
            "diagnostics": dict(self.diagnostics),
        }


@runtime_checkable
class Reader(Protocol):
    """``observations -> ReadResult``. The mirror of a kernel."""

    id: str

    def run(self, text: str, *, query: str | None = None,
            context: Sequence[str] = ()) -> ReadResult:
        ...


_READERS: dict[str, Reader] = {}


def register_reader(reader: Reader) -> Reader:
    if reader.id in _READERS:
        raise ValueError(f"reader {reader.id!r} is already registered")
    _READERS[reader.id] = reader
    return reader


def get_reader(rid: str) -> Reader:
    if rid not in _READERS:
        raise KeyError(f"no reader {rid!r}; have {sorted(_READERS)}")
    return _READERS[rid]


def list_readers() -> list[str]:
    return sorted(_READERS)


def result_artifact(result: ReadResult) -> Artifact:
    return Artifact(type="read_result", value=result.to_dict(),
                    schema="sai.reader@1")


def _reader_run(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
                ctx) -> dict[str, Artifact]:
    """Read one observation. Parallel to ``kernel.run@1`` on the other side."""
    reader = get_reader(str(params["reader"]))
    text = inputs["text"].value
    if isinstance(text, dict):
        text = text.get("text", "")
    started = time.perf_counter()
    result = reader.run(str(text), query=params.get("query"),
                        context=tuple(params.get("context") or ()))
    if not result.cost_s:
        result = ReadResult(**{**result.__dict__,
                               "cost_s": time.perf_counter() - started})
    delta = result.delta()
    return {
        "delta": Artifact(type="world_delta",
                          value={"claims": [c.to_dict() for c in delta.claims]},
                          schema="sai.world@1"),
        "claims": Artifact(type="claim_set",
                           value={"producer": result.provenance or reader.id,
                                  "claims": [c.to_dict() for c in result.claims]},
                           schema="sai.world@1"),
        "unresolved": Artifact(type="json", value={
            "unresolved": list(result.unresolved),
            "factors": result.to_dict()["factors"],
            "mentions": result.to_dict()["mentions"]}),
        "report": Artifact(type="json", value=result.to_dict()),
    }


READER_RUN = register_op(OpDef(
    id="reader.run@1", fn=_reader_run, family="parse",
    inputs=(Port("text", "json"),),
    outputs=(Port("delta", "world_delta"), Port("claims", "claim_set"),
             Port("unresolved", "json"), Port("report", "json")),
    pure=False,
    doc="Turn observations into candidate claims plus what was NOT settled. "
        "The unresolved port is separate so a caller that ignores ambiguity has "
        "visibly ignored it rather than never been told."))
