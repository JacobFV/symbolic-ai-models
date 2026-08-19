"""The reader contract, and `reader.run@1`."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from symbolic_ai_core.artifact.value import Artifact
from symbolic_ai_core.flow.port import Port
from symbolic_ai_core.flow.registry import OpDef, register_op
from symbolic_ai_core.world import Claim, WorldDelta, WorldSnapshot

__all__ = ["ReadResult", "Reader", "Candidate", "Alignment",
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
class Candidate:
    """One alternative reading the reader declined to collapse.

    ``exclusive`` says whether the alternatives are mutually exclusive. That flag
    is not decoration: agreement across candidates is a sound and complete error
    detector when they *are* -- and carries no information when they are not.
    Measured on real prose, where multi-candidate cases are 1.2% same-entity and
    agreement precision (0.603) is no better than taking the first (0.626).
    """

    slot: str
    claims: tuple[Claim, ...]
    exclusive: bool = True
    detail: str = ""


@dataclass(frozen=True)
class ReadResult:
    """What a reader produces. Deliberately not a `WorldSnapshot`.

    A snapshot is a settled world. Handing one back means every distinction the
    reader could not make has already been guessed, and the guess is invisible.
    """

    claims: tuple[Claim, ...] = ()
    candidates: tuple[Candidate, ...] = ()
    unresolved: tuple[str, ...] = ()
    alignments: tuple[Alignment, ...] = ()
    confidence: Mapping[int, float] = field(default_factory=dict)
    provenance: str = ""
    cost_s: float = 0.0
    detail: Mapping[str, Any] = field(default_factory=dict)

    def delta(self) -> WorldDelta:
        return WorldDelta(claims=self.claims)

    def settled(self) -> bool:
        """True when nothing was left open. The caller may still be wrong."""
        return not self.candidates and not self.unresolved

    def to_dict(self) -> dict:
        return {
            "claims": [c.to_dict() for c in self.claims],
            "candidates": [
                {"slot": c.slot, "exclusive": c.exclusive, "detail": c.detail,
                 "claims": [x.to_dict() for x in c.claims]}
                for c in self.candidates],
            "unresolved": list(self.unresolved),
            "alignments": [{"start": a.start, "end": a.end, "claim": a.claim,
                            "detail": a.detail} for a in self.alignments],
            "confidence": {str(k): v for k, v in self.confidence.items()},
            "provenance": self.provenance,
            "cost_s": self.cost_s,
            "detail": dict(self.detail),
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
            "candidates": result.to_dict()["candidates"]}),
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
