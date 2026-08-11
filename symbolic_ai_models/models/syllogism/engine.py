"""A forward-chaining reasoning engine over the parser's logical forms.

Saturate the premise set under the classical categorical rules, then answer the
query by lookup. No search, no heuristics: an answer is either derived or
`unknown`. Every derived statement keeps the rule and parents that produced it, so
the harness can show its work.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import Categorical, Fact, Statement

YES, NO, UNKNOWN = "yes", "no", "unknown"


@dataclass
class Derivation:
    statement: Statement
    rule: str
    parents: tuple[Statement, ...] = ()

    def __str__(self) -> str:
        if not self.parents:
            return f"{self.statement}    [{self.rule}]"
        via = " + ".join(str(p) for p in self.parents)
        return f"{self.statement}    [{self.rule}: {via}]"


@dataclass
class Answer:
    value: str
    derivation: list[Derivation] = field(default_factory=list)
    reason: str = ""


def _contradicts(a: Statement, b: Statement) -> bool:
    """Whether `b` is the direct denial of `a` (used to answer `no`)."""
    if isinstance(a, Fact) and isinstance(b, Fact):
        return (
            a.individual == b.individual
            and a.predicate == b.predicate
            and a.negated != b.negated
        )
    if isinstance(a, Categorical) and isinstance(b, Categorical):
        if a.subject != b.subject or a.predicate != b.predicate:
            return False
        pair = frozenset({a.quantifier, b.quantifier})
        # A-O and E-I are the contradictories; A-E are contraries, incompatible
        # under the existential import the subalternation rule already assumes.
        return pair in (
            frozenset({"all", "some_not"}),
            frozenset({"no", "some"}),
            frozenset({"all", "no"}),
        )
    return False


class Engine:
    """Closes a premise set under the categorical rules, up to `max_rounds`."""

    def __init__(self, max_rounds: int = 6) -> None:
        self.max_rounds = max_rounds

    def saturate(self, premises: list[Statement]) -> dict[Statement, Derivation]:
        known: dict[Statement, Derivation] = {}
        for premise in premises:
            known.setdefault(premise, Derivation(premise, "premise"))
        for _ in range(self.max_rounds):
            new = [d for d in self._step(known) if d.statement not in known]
            if not new:
                break
            for derivation in new:
                known.setdefault(derivation.statement, derivation)
        return known

    def _step(self, known: dict[Statement, Derivation]) -> list[Derivation]:
        cats = [s for s in known if isinstance(s, Categorical)]
        facts = [s for s in known if isinstance(s, Fact)]
        out: list[Derivation] = []

        def emit(statement: Statement, rule: str, *parents: Statement) -> None:
            out.append(Derivation(statement, rule, parents))

        for a in cats:
            # Simple conversion: E and I propositions convert.
            if a.quantifier == "no":
                emit(Categorical("no", a.predicate, a.subject), "conversion(E)", a)
            elif a.quantifier == "some":
                emit(Categorical("some", a.predicate, a.subject), "conversion(I)", a)
            # Subalternation: a universal over a non-empty term yields the particular.
            if a.quantifier == "all":
                emit(Categorical("some", a.subject, a.predicate), "subalternation", a)

        for a in cats:
            for b in cats:
                if a is b or a.predicate != b.subject:
                    continue
                middle, minor, major = a.predicate, a.subject, b.predicate
                if minor == major:
                    continue
                del middle
                if a.quantifier == "all" and b.quantifier == "all":
                    emit(Categorical("all", minor, major), "barbara", a, b)
                elif a.quantifier == "all" and b.quantifier == "no":
                    emit(Categorical("no", minor, major), "celarent", a, b)
                elif a.quantifier == "some" and b.quantifier == "all":
                    emit(Categorical("some", minor, major), "darii", a, b)
                elif a.quantifier == "some" and b.quantifier == "no":
                    emit(Categorical("some_not", minor, major), "ferio", a, b)

        for fact in facts:
            if fact.negated:
                continue
            for cat in cats:
                if cat.subject != fact.predicate:
                    continue
                if cat.quantifier == "all":
                    emit(
                        Fact(fact.individual, cat.predicate),
                        "instantiation(A)",
                        fact,
                        cat,
                    )
                elif cat.quantifier == "no":
                    emit(
                        Fact(fact.individual, cat.predicate, negated=True),
                        "instantiation(E)",
                        fact,
                        cat,
                    )
        return out

    def ask(self, premises: list[Statement], query: Statement | None) -> Answer:
        if query is None:
            return Answer(UNKNOWN, [], "no query in the fragment this parser accepts")
        known = self.saturate(premises)
        if query in known:
            return Answer(YES, self._trace(known, query), "derived")
        denial = next((s for s in known if _contradicts(query, s)), None)
        if denial is not None:
            return Answer(NO, self._trace(known, denial), f"contradicted by {denial}")
        return Answer(UNKNOWN, [], "not derivable from the premises")

    def _trace(
        self, known: dict[Statement, Derivation], target: Statement
    ) -> list[Derivation]:
        """The derivations `target` depends on, premises first."""
        order: list[Derivation] = []
        seen: set[Statement] = set()

        def walk(statement: Statement) -> None:
            if statement in seen or statement not in known:
                return
            seen.add(statement)
            derivation = known[statement]
            for parent in derivation.parents:
                walk(parent)
            order.append(derivation)

        walk(target)
        return order
