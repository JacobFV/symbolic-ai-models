"""What something says, including when what it says is another claim.

A claim is **n-ary with named roles and may nest**. That is the whole reason
this is not a triple store. *Casey believes that Lara performed exam 17* is one
claim whose ``content`` role is another claim; expressed as triples it becomes a
pile of reification nodes that no two consumers agree on, and the nesting — the
part that carries the meaning — lives in a convention rather than in the data.

Every claim also carries the two times, a modality, a polarity, a confidence and
its provenance. None of those are optional extras:

* **polarity** — a source that says *not* something is not a source that said
  nothing, and dropping the negation is how a knowledge base ends up asserting
  the opposite of its input.
* **modality** — *asserted*, *hypothesised*, *believed-by*, *desired*. A planner
  and a physics kernel need to tell an intention from a measurement.
* **two times** — ``valid_time`` is when it holds in the world, and
  ``transaction_time`` is when this system learned it. Published economic and
  political series are revised; a store with one time silently lets a backtest
  read a value that did not exist on the day it claims to have decided.
* **confidence** — ``None`` means *not stated*, which is not the same as 1.0. An
  imputed certainty is indistinguishable downstream from a measured one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..artifact.value import Interval, Provenance
from .entity import EntityRef, Quantity

__all__ = ["Claim", "Alignment", "POLARITIES", "MODALITIES",
           "ALIGNMENT_RELATIONS", "role_to_dict", "role_from_dict"]

POLARITIES = ("positive", "negative")

#: What kind of speech act this claim is. ``asserted`` is the default and the
#: only one a naive consumer may treat as a fact about the world.
MODALITIES = ("asserted", "hypothesised", "believed", "desired", "obliged",
              "possible", "counterfactual", "questioned")

#: How two identities from two sources may be related. **``exact_match`` is not
#: the default**: an alignment asserted at full strength is a merge wearing a
#: claim's clothes, and merges are what this layer exists to avoid.
ALIGNMENT_RELATIONS = ("exact_match", "close_match", "broad_match",
                       "narrow_match", "related", "possibly_same",
                       "contradicts", "supersedes")


def role_to_dict(v: Any) -> Any:
    """Serialise a role filler, keeping its kind. See :class:`EntityRef`."""
    if isinstance(v, Claim):
        return {"claim": v.to_dict()}
    if isinstance(v, (EntityRef, Quantity)):
        return v.to_dict()
    if isinstance(v, (list, tuple)):
        return {"list": [role_to_dict(x) for x in v]}
    return {"literal": v}


def role_from_dict(d: Any) -> Any:
    if not isinstance(d, dict):
        raise TypeError(f"a role filler is a tagged dict, got {type(d).__name__}")
    if "claim" in d:
        return Claim.from_dict(d["claim"])
    if "entity" in d:
        return EntityRef(d["entity"])
    if "quantity" in d:
        q = d["quantity"]
        return Quantity(value=q["value"], unit=q["unit"], stderr=q.get("stderr"))
    if "list" in d:
        return [role_from_dict(x) for x in d["list"]]
    if "literal" in d:
        return d["literal"]
    raise ValueError(f"unrecognised role filler {sorted(d)}")


@dataclass(frozen=True)
class Claim:
    """One proposition, with named roles that may themselves be propositions."""

    predicate: str
    roles: Mapping[str, Any] = field(default_factory=dict)
    polarity: str = "positive"
    modality: str = "asserted"
    confidence: float | None = None
    valid_time: Interval = field(default_factory=Interval)
    transaction_time: Interval = field(default_factory=Interval)
    scope: str = ""
    assumptions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    provenance: Provenance = field(default_factory=Provenance)

    def __post_init__(self) -> None:
        if self.polarity not in POLARITIES:
            raise ValueError(f"polarity {self.polarity!r} not in {POLARITIES}")
        if self.modality not in MODALITIES:
            raise ValueError(f"modality {self.modality!r} not in {MODALITIES}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence} is not a probability")

    # ---- structure ---------------------------------------------------
    def entities(self) -> tuple[str, ...]:
        """Every entity id this claim mentions, at any nesting depth."""
        out: list[str] = []

        def walk(v: Any) -> None:
            if isinstance(v, EntityRef):
                out.append(v.id)
            elif isinstance(v, Claim):
                for x in v.roles.values():
                    walk(x)
            elif isinstance(v, (list, tuple)):
                for x in v:
                    walk(x)

        for v in self.roles.values():
            walk(v)
        return tuple(out)

    def depth(self) -> int:
        """Nesting depth. A flat claim is 1."""
        inner = [v.depth() for v in self.roles.values() if isinstance(v, Claim)]
        return 1 + max(inner, default=0)

    # ---- wire --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "roles": {k: role_to_dict(v) for k, v in sorted(self.roles.items())},
            "polarity": self.polarity, "modality": self.modality,
            "confidence": self.confidence,
            "valid_time": self.valid_time.to_dict(),
            "transaction_time": self.transaction_time.to_dict(),
            "scope": self.scope, "assumptions": list(self.assumptions),
            "evidence": list(self.evidence),
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Claim":
        p = d.get("provenance") or {}
        return cls(
            predicate=d["predicate"],
            roles={k: role_from_dict(v) for k, v in (d.get("roles") or {}).items()},
            polarity=d.get("polarity", "positive"),
            modality=d.get("modality", "asserted"),
            confidence=d.get("confidence"),
            valid_time=Interval(**(d.get("valid_time") or {})),
            transaction_time=Interval(**(d.get("transaction_time") or {})),
            scope=d.get("scope", ""),
            assumptions=tuple(d.get("assumptions") or ()),
            evidence=tuple(d.get("evidence") or ()),
            provenance=Provenance(
                producer=p.get("producer", ""), inputs=tuple(p.get("inputs") or ()),
                source=p.get("source", ""), source_version=p.get("source_version", ""),
                license=p.get("license", ""), method=p.get("method", "")),
        )


@dataclass(frozen=True)
class Alignment:
    """That two source-native identities may be the same thing.

    This is a claim about identity, and it is *uncertain knowledge like any
    other* — improvable by a kernel, refutable by a later source, and never
    applied destructively. The two ids keep their namespaces; nothing here
    rewrites either side.
    """

    left: str
    right: str
    relation: str = "possibly_same"
    confidence: float | None = None
    method: str = ""
    evidence: tuple[str, ...] = ()
    provenance: Provenance = field(default_factory=Provenance)
    #: The sources the two ids belong to, when the caller knows them. Stating
    #: them is always better than the fallback below, which is a guess.
    left_source: str = ""
    right_source: str = ""

    def _namespace(self, ident: str, stated: str) -> str:
        """Which source an id belongs to.

        Prefer what the caller stated. The fallback reads the id, and reading
        an id is **guessing**: it worked for ``wn:dog.n.01`` and failed the
        first time real bytes arrived, because this repo's own corpus writes
        ``kg:sec:cik:320193`` and ``kg:lei:2138…`` — a shared vendor prefix and
        then the source. Splitting on the first colon called both ``kg`` and
        refused every genuine cross-source alignment in 3.3 million entities.

        So the fallback takes the first *two* segments when there are three or
        more, which fits both shapes, and is documented as a heuristic rather
        than trusted as identity. ``filesystem location is never identity``
        has a sibling: **a string prefix is never identity either.**
        """
        if stated:
            return stated
        parts = ident.split(":")
        return ":".join(parts[:2]) if len(parts) >= 3 else parts[0]

    def __post_init__(self) -> None:
        if self.relation not in ALIGNMENT_RELATIONS:
            raise ValueError(f"alignment relation {self.relation!r} not in "
                             f"{ALIGNMENT_RELATIONS}")
        left_ns = self._namespace(self.left, self.left_source)
        right_ns = self._namespace(self.right, self.right_source)
        if left_ns == right_ns:
            raise ValueError(
                f"{self.left} and {self.right} are both in {left_ns!r}: an "
                "alignment relates identities from *different* sources, and "
                "one within a source is a statement about that source's own "
                "modelling. If the namespaces were inferred wrongly, state "
                "left_source and right_source explicitly")

    def as_claim(self) -> Claim:
        return Claim(predicate=self.relation,
                     roles={"left": EntityRef(self.left),
                            "right": EntityRef(self.right)},
                     modality="asserted", confidence=self.confidence,
                     evidence=self.evidence,
                     provenance=Provenance(
                         producer=self.provenance.producer,
                         inputs=self.provenance.inputs,
                         source=self.provenance.source,
                         source_version=self.provenance.source_version,
                         license=self.provenance.license,
                         method=self.method or self.provenance.method))

    def to_dict(self) -> dict[str, Any]:
        return {"left": self.left, "right": self.right,
                "relation": self.relation, "confidence": self.confidence,
                "method": self.method, "evidence": list(self.evidence),
                "provenance": self.provenance.to_dict()}
