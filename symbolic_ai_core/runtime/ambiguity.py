"""Computing with a mixture instead of resolving it.

`fuse` retains a disagreement it is not entitled to settle, and since the last
fix that mixture survives serialisation. Nothing read one. A retained
alternative that no consumer can act on is a data structure, not a capability —
and the pressure to collapse it comes back the moment a caller needs an answer.

So this is the consumer: give it the alternatives and a computation, and it
returns **every answer the evidence permits**, with the choices that produce
each. A caller that gets one answer back learns the ambiguity did not matter;
a caller that gets two learns exactly which unresolved conflict it is standing
on.

**The cross product is exponential and this refuses rather than truncating.**
Measured on the GLEIF ownership graph the conflicts do not interact at all —
251 unresolved conflicts touch 253 entities, an amplification of 1.0x, because
92.2% of entities are leaves and a conflicted entity has a median of zero
descendants. That is a property of a wide shallow forest and emphatically not a
general one: the same substrate amplified a 0.05% input error into 0.43% of
answers on the route network, up to 44x, because that graph is dense and nearly
connected. A bound is therefore not paranoia about a case that never happens,
it is the difference between the two topologies this repo has measured.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Mapping, Sequence

__all__ = ["Alternatives", "PossibleAnswers", "AmbiguityExplosion",
           "alternatives_from", "possible_answers"]


class AmbiguityExplosion(RuntimeError):
    """Too many consistent worlds to enumerate. Never silently truncated."""


@dataclass(frozen=True)
class Alternatives:
    """Subject -> the competing values no source was entitled to settle."""

    choices: Mapping[Hashable, tuple[Any, ...]]

    def __post_init__(self) -> None:
        for subject, opts in self.choices.items():
            if len(opts) < 2:
                raise ValueError(
                    f"{subject!r} has {len(opts)} alternative(s): a subject "
                    "with one value is settled and does not belong in a "
                    "mixture, and one with none is a hole rather than a choice")

    def world_count(self) -> int:
        n = 1
        for opts in self.choices.values():
            n *= len(opts)
        return n


@dataclass(frozen=True)
class PossibleAnswers:
    """Every answer the evidence permits, and what each one rests on."""

    answers: Mapping[Any, tuple[Mapping[Hashable, Any], ...]]
    worlds: int = 0

    @property
    def ambiguous(self) -> bool:
        return len(self.answers) > 1

    @property
    def settled(self) -> Any:
        """The single answer, when the ambiguity did not matter."""
        if self.ambiguous:
            raise ValueError(
                f"{len(self.answers)} different answers are consistent with "
                "the evidence; there is no single one to take")
        return next(iter(self.answers))

    def summary(self) -> str:
        return (f"{len(self.answers)} distinct answer(s) over {self.worlds} "
                f"consistent world(s)")


def alternatives_from(unresolved: Iterable[Any], *,
                      value: Callable[[Any], Any]) -> Alternatives:
    """Read a `FusionResult.unresolved` into a choice per subject.

    ``value`` extracts the competing value from a claim, because what counts as
    *the* value is predicate-specific — a parent entity, a quantity, a label —
    and guessing it here is how a fusion layer starts deciding semantics it has
    no business deciding.
    """
    out: dict[Hashable, tuple[Any, ...]] = {}
    for group in unresolved:
        distinct = tuple(dict.fromkeys(value(c) for c in group.claims))
        if len(distinct) > 1:
            out[(group.predicate, group.subject)] = distinct
    return Alternatives(out)


def possible_answers(compute: Callable[[Mapping[Hashable, Any]], Any],
                     alternatives: Alternatives, *,
                     max_worlds: int = 1024) -> PossibleAnswers:
    """Run ``compute`` under every consistent choice and collect the answers.

    ``compute`` receives one assignment — subject to chosen value — and returns
    a hashable answer. Answers are grouped, so a caller sees *how many distinct
    outcomes survive*, not how many worlds were enumerated: 1,024 worlds that
    all give the same number is not an ambiguous result, it is an irrelevant
    conflict, and that distinction is the whole point of computing rather than
    collapsing.
    """
    n = alternatives.world_count()
    if n > max_worlds:
        raise AmbiguityExplosion(
            f"{len(alternatives.choices)} unresolved conflicts give {n:,} "
            f"consistent worlds, over the bound of {max_worlds:,}. Truncating "
            "would return an answer set that looks complete and is not; narrow "
            "the query, or settle a conflict on evidence rather than on the "
            "enumeration order.")
    subjects = sorted(alternatives.choices, key=repr)
    grouped: dict[Any, list[Mapping[Hashable, Any]]] = {}
    for combo in itertools.product(
            *(alternatives.choices[s] for s in subjects)):
        assignment = dict(zip(subjects, combo))
        grouped.setdefault(compute(assignment), []).append(assignment)
    return PossibleAnswers({k: tuple(v) for k, v in grouped.items()}, worlds=n)
