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
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Iterator, Mapping, Sequence

__all__ = ["Alternatives", "PossibleAnswers", "AmbiguityExplosion",
           "alternatives_from", "possible_answers", "possible_answers_scoped",
           "exposure", "rank_by_exposure", "Bounds", "additive_bounds"]


class AmbiguityExplosion(RuntimeError):
    """Too many consistent worlds to enumerate. Never silently truncated.

    Carries ``read`` — the conflicts the refused query actually depends on —
    when :func:`possible_answers_scoped` raised it. A refusal that names them
    is actionable ("settle these twelve and the answer exists"); a bare refusal
    is not, and a caller reduced to parsing the message for them would be a
    contract shipping in a string.
    """

    #: Class-level defaults so the whole-world refusal in `possible_answers`,
    #: which has no query-specific read set to report, still answers `.read`.
    read: tuple[Hashable, ...] = ()
    worlds: int = 0


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
    #: The conflicts the computation actually read. Empty when every conflict
    #: in the mixture was enumerated, which is what :func:`possible_answers`
    #: does; :func:`possible_answers_scoped` fills it in, and it is the more
    #: useful half of the answer — it names which disagreements a caller is
    #: standing on rather than which ones exist somewhere in the world.
    read: tuple[Hashable, ...] = ()

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


def exposure(node: Hashable, children: Mapping[Hashable, Sequence[Hashable]],
             *, max_visit: int = 1_000_000) -> int:
    """How many answers change if a conflict lands on ``node``.

    The node itself plus everything reachable beneath it. One means the
    disagreement is local and enumerating it costs nothing; a thousand means a
    single unresolved conflict rewrites a thousand answers.

    **This is the number the last finding got wrong by reporting a median as a
    property.** Measured over GLEIF, exposure has median **1** and a maximum of
    **3,848** within a single relation — four orders of magnitude — and the 251
    real conflicts happened to sit at median positions. "Ambiguity does not
    propagate in this graph" was true of those conflicts and false of the graph:
    it has hubs, and a manager with 1,258 funds is exactly the entity whose
    ownership is most worth arguing about.

    So the cost of retaining a conflict is **not uniform**, and a flat bound on
    worlds cannot express that. Rank by this first, and spend evidence on the
    expensive ones.
    """
    # Seeded with the node itself, so a node reachable from itself is counted
    # once. Ownership cycles are real in this data -- six of them -- and
    # counting the start node twice would report an exposure of 3 for a
    # two-entity loop.
    seen: set[Hashable] = {node}
    stack = list(children.get(node, ()))
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        if len(seen) > max_visit:                             # pragma: no cover
            raise AmbiguityExplosion(
                f"exposure of {node!r} exceeded {max_visit:,} nodes; the graph "
                "is not a forest and this walk does not terminate usefully")
        stack.extend(children.get(x, ()))
    return len(seen)


def rank_by_exposure(alternatives: Alternatives,
                     children: Mapping[Hashable, Sequence[Hashable]],
                     *, subject_of: Callable[[Hashable], Hashable]
                     ) -> tuple[tuple[Hashable, int], ...]:
    """Conflicts, most consequential first.

    ``subject_of`` maps a choice key to the graph node it sits on, because the
    key carries a predicate and a subject tuple and only the caller knows which
    part indexes the graph.

    The point is to make an expensive conflict visible **before** enumeration
    rather than at it: `possible_answers` refuses an explosion, which is the
    right failure and a late one.
    """
    return tuple(sorted(
        ((key, exposure(subject_of(key), children))
         for key in alternatives.choices),
        key=lambda kv: (-kv[1], repr(kv[0]))))


class _Recording(MappingABC):
    """An assignment that remembers which conflicts were looked at.

    The trick the scoped enumeration rests on: a computation already declares
    which disagreements it depends on, by reading them. Nothing needs to be
    annotated, and no static analysis of the query is required — hand it a
    mapping that records, run it once, and the read set is the answer.

    Unpinned subjects return their **first** alternative, so a first pass is a
    real run of the computation rather than a probe: it produces an answer and
    a read set, and the caller re-runs with the read set pinned. That answer is
    discarded, because it was computed against defaults for conflicts that
    turned out to matter.

    ``__iter__`` records **every** subject. A computation that iterates the
    assignment has, as far as this can tell, looked at all of it, and quietly
    recording nothing there is how an exact method becomes an approximate one.
    """

    def __init__(self, pinned: Mapping[Hashable, Any],
                 choices: Mapping[Hashable, tuple[Any, ...]]) -> None:
        self._pinned = pinned
        self._choices = choices
        self.read: set[Hashable] = set()

    def __getitem__(self, key: Hashable) -> Any:
        if key in self._pinned:
            self.read.add(key)
            return self._pinned[key]
        opts = self._choices[key]                     # KeyError: not a conflict
        self.read.add(key)
        return opts[0]

    def __iter__(self) -> Iterator[Hashable]:
        self.read.update(self._choices)
        return iter(self._choices)

    def __len__(self) -> int:
        return len(self._choices)


def possible_answers_scoped(compute: Callable[[Mapping[Hashable, Any]], Any],
                            alternatives: Alternatives, *,
                            max_worlds: int = 1024) -> PossibleAnswers:
    """Every answer the evidence permits, paying only for the conflicts read.

    :func:`possible_answers` enumerates the whole mixture, so 251 retained
    GLEIF conflicts give 2^251 worlds and *every* query is refused — including
    "who ultimately owns this one company", whose answer depends on one of
    them. That bound is a property of the world; the cost of a query should be
    a property of the **query**.

    So: run ``compute`` against a recording assignment, collect the subjects it
    read, enumerate exactly those, and repeat until a pass reads nothing new —
    which terminates because the read set only grows and the mixture is finite.
    The answer is exact, not an approximation of the full enumeration: the
    conflicts outside the read set cannot change an answer that never consulted
    them.

    The alternative anyone reaches for first — propagate a *set* of possible
    values per node and take unions — is cheaper still and is wrong whenever a
    query reads one conflict twice, because the product of two independently
    derived sets contains combinations no single world produces. That failure
    is measured in
    ``notes/findings/2026-08-18-a-query-pays-for-the-conflicts-it-reads.md``
    rather than argued.

    ``compute`` must be deterministic and must depend on the mixture only
    through the mapping it is handed; a computation that reaches around it for
    a conflicted value is unmeasurable here and its read set will be a lie.
    """
    choices = alternatives.choices
    relevant: tuple[Hashable, ...] = ()
    while True:
        n = 1
        for s in relevant:
            n *= len(choices[s])
        if n > max_worlds:
            explosion = AmbiguityExplosion(
                f"the query reads {len(relevant)} of "
                f"{len(choices)} unresolved conflicts, giving {n:,} consistent "
                f"worlds, over the bound of {max_worlds:,}. This is a query "
                "that genuinely depends on all of them, not the whole-world "
                "product — narrow it, settle a conflict on evidence, or use "
                "`additive_bounds` if the answer is a sum of independent "
                "contributions.")
            explosion.read = relevant
            explosion.worlds = n
            raise explosion
        grouped: dict[Any, list[Mapping[Hashable, Any]]] = {}
        newly: set[Hashable] = set()
        for combo in itertools.product(*(choices[s] for s in relevant)):
            pinned = dict(zip(relevant, combo))
            recorder = _Recording(pinned, choices)
            answer = compute(recorder)
            newly |= recorder.read.difference(relevant)
            grouped.setdefault(answer, []).append(pinned)
        if not newly:
            return PossibleAnswers({k: tuple(v) for k, v in grouped.items()},
                                   worlds=n, read=relevant)
        relevant = tuple(sorted(set(relevant) | newly, key=repr))


@dataclass(frozen=True)
class Bounds:
    """The range an additive answer can take, and what makes it wide."""

    low: float
    high: float
    low_choice: Mapping[Hashable, Any]
    high_choice: Mapping[Hashable, Any]
    #: ``(subject, how much of the width it contributes)``, widest first. The
    #: point of carrying it: a bound with no attribution says the answer is
    #: uncertain and nothing about which disagreement to go and settle.
    width_by_subject: tuple[tuple[Hashable, float], ...] = ()
    base: float = 0.0

    @property
    def width(self) -> float:
        return self.high - self.low

    @property
    def determined(self) -> bool:
        """Whether the mixture leaves the answer undetermined at all."""
        return self.high == self.low


def additive_bounds(alternatives: Alternatives,
                    contribution: Callable[[Hashable, Any], float], *,
                    base: float = 0.0) -> Bounds:
    """Exact bounds on ``base + sum_s contribution(s, choice(s))``.

    The case scoped enumeration does not cover: a query that genuinely reads
    every conflict in the mixture. Counting how many aligned filers are
    US-domiciled reads all ~1,000 ambiguous alignments at once, so
    2^1000 worlds is not an artefact of enumerating too much — it is the size
    of the answer's real dependency, and no scoping can shrink it.

    It is still answerable, because the terms are independent: the world that
    minimises the sum is the one that minimises every term, found subject by
    subject in linear time. These are the true extremes, not an interval
    relaxation — each is realised by the assignment returned alongside it.

    The independence is enforced by the **interface**: ``contribution`` sees a
    subject and a chosen value and nothing else, so a term that depends on two
    conflicts cannot be expressed here. That is deliberate — such a term makes
    the term-by-term minimum unreachable, and a bound that is not attained is a
    different and weaker claim than the one this returns.
    """
    low = high = base
    low_choice: dict[Hashable, Any] = {}
    high_choice: dict[Hashable, Any] = {}
    widths: list[tuple[Hashable, float]] = []
    for subject, opts in alternatives.choices.items():
        scored = [(float(contribution(subject, v)), v) for v in opts]
        lo = min(scored, key=lambda sv: sv[0])
        hi = max(scored, key=lambda sv: sv[0])
        low += lo[0]
        high += hi[0]
        low_choice[subject] = lo[1]
        high_choice[subject] = hi[1]
        if hi[0] != lo[0]:
            widths.append((subject, hi[0] - lo[0]))
    widths.sort(key=lambda kv: (-kv[1], repr(kv[0])))
    return Bounds(low=low, high=high, low_choice=low_choice,
                  high_choice=high_choice, width_by_subject=tuple(widths),
                  base=base)
