"""What a generator needs from a knowledge source, said out loud.

``essay.py`` already takes ``kg: Any`` and reaches into it by name —
``getattr(kg, spec["accessor"])(n)``, ``kg.pos[n]``, ``kg.word(n)``, ``len(kg)``.
That is generic in the sense that anything with those attributes works, and *not*
generic in the sense that nothing says what they are. A source missing
``properties_of`` does not fail; it produces essays with one fewer section, and
a corpus quietly two-thirds the intended richness is indistinguishable from one
that is exactly right.

So the contract becomes explicit, and it is a **capability set** rather than a
base class:

* a source declares nothing — capabilities are *detected*, by asking whether the
  accessor exists and returns something for a sample of nodes;
* a generator declares what it requires, and
  :func:`require_capabilities` refuses loudly when they are absent, naming the
  ones that are missing and what will be lost.

Detection rather than declaration is deliberate. A source that declares
``properties_of`` and returns an empty tuple for every node has the capability
in name only, and that is exactly the case this repo already has: WordNet
carries **zero** property assertions while CSKG carries 30,513, and both expose
the method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable

__all__ = ["KnowledgeSource", "Capability", "CAPABILITIES", "capabilities_of",
            "require_capabilities", "CapabilityError", "CapabilityReport"]


class CapabilityError(KeyError):
    """A generator asked for something the source cannot supply."""


@dataclass(frozen=True)
class Capability:
    """One accessor a generator may depend on, and what is lost without it."""

    name: str
    lost: str

    def __str__(self) -> str:
        return self.name


#: Every accessor a generator in this repo currently reaches for. Keyed by the
#: attribute name so detection is a ``getattr``, and carrying what a source that
#: lacks it costs — a message worth more than the boolean, because the caller's
#: decision is whether to proceed without it.
CAPABILITIES: dict[str, Capability] = {
    c.name: c for c in (
        Capability("hypernyms", "no placement section: nothing says what a "
                                "topic is a kind of"),
        Capability("hyponyms", "no varieties section"),
        Capability("parts_of", "no composition section"),
        Capability("substances_of", "no substance section"),
        Capability("members_of", "no membership section"),
        Capability("properties_of", "no qualities section — and this is the "
                                    "one WordNet has none of"),
        Capability("abilities_of", "no behaviour section"),
        Capability("siblings", "no contrast section, and therefore no "
                               "near-miss distractors"),
        Capability("word", "nodes cannot be realised as text at all"),
        Capability("pos", "part of speech is unavailable; topic selection "
                          "cannot filter to nouns"),
    )
}


@runtime_checkable
class KnowledgeSource(Protocol):
    """The minimum. Everything else is a detected capability, not a requirement."""

    def __len__(self) -> int: ...

    def word(self, n: int) -> str: ...


@dataclass(frozen=True)
class CapabilityReport:
    """Which capabilities a source has, and how *populated* each one is.

    ``present`` is "the attribute exists". ``populated`` is "it returned
    something for at least one sampled node", and the two come apart in the case
    that matters: an accessor that exists and is empty everywhere is a section
    that silently never appears.
    """

    source: str
    present: frozenset[str]
    populated: frozenset[str]
    coverage: Mapping[str, float]
    n_sampled: int

    def has(self, *names: str) -> bool:
        return all(n in self.populated for n in names)

    def missing(self, names: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted(set(names) - self.populated))

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "present": sorted(self.present),
                "populated": sorted(self.populated),
                "coverage": {k: round(v, 4) for k, v in sorted(self.coverage.items())},
                "n_sampled": self.n_sampled}


def capabilities_of(kg: Any, *, name: str = "", sample: int = 512,
                    names: Sequence[str] | None = None) -> CapabilityReport:
    """Detect what a source can actually do, by asking it.

    Sampling rather than exhausting, because a source may hold millions of
    nodes and the question is whether a capability is *usable*, not exactly how
    often. The sample is a deterministic stride so two calls agree.
    """
    wanted = list(names or CAPABILITIES)
    n = len(kg)
    step = max(1, n // max(sample, 1))
    nodes = list(range(0, n, step))[:sample]

    present, populated, coverage = set(), set(), {}
    for cap in wanted:
        attr = getattr(kg, cap, None)
        if attr is None:
            coverage[cap] = 0.0
            continue
        present.add(cap)
        if not callable(attr):
            # `pos` is a sequence, not a method; a non-empty one is populated.
            populated.add(cap)
            coverage[cap] = 1.0 if len(attr) else 0.0
            continue
        hits = 0
        for i in nodes:
            try:
                got = attr(i)
            except Exception:
                continue
            if got is not None and (not hasattr(got, "__len__") or len(got)):
                hits += 1
        coverage[cap] = hits / len(nodes) if nodes else 0.0
        if hits:
            populated.add(cap)
    return CapabilityReport(source=name or type(kg).__name__,
                            present=frozenset(present),
                            populated=frozenset(populated),
                            coverage=coverage, n_sampled=len(nodes))


def require_capabilities(report: CapabilityReport, required: Iterable[str], *,
                         who: str = "") -> None:
    """Refuse loudly, naming what is missing and what it costs.

    The alternative — proceeding with fewer sections — produces a corpus that
    is quietly thinner than intended and reads exactly like one that is not.
    """
    missing = report.missing(required)
    if not missing:
        return
    losses = "; ".join(f"{m}: {CAPABILITIES[m].lost}" if m in CAPABILITIES
                       else m for m in missing)
    raise CapabilityError(
        f"{who or 'this generator'} requires {list(missing)} from source "
        f"{report.source!r}, which does not populate them. {losses}. "
        f"Populated: {sorted(report.populated)}")
