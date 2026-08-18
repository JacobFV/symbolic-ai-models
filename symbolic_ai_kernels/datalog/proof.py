"""Why a derived fact is true, and what checking that costs.

The routing task found inspectability to be **asymmetric**: a witness verified
247x cheaper than solving, while certifying optimality cost twice as much as
re-solving. The stated open question was whether that shape is a property of
shortest path or of the existential/universal distinction itself, and datalog is
where to find out — because a derivation tree is the textbook case where
verification should be linear in the *derivation* and independent of the
*database*, which shortest path's witness is not quite.

Two things live here, deliberately **beside** :func:`~.engine.evaluate` and not
inside it. Recording provenance costs memory proportional to the closure and
slows the fixed point, and a published number carrying `evaluate`'s name must
keep meaning what it meant.

* :func:`evaluate_with_derivations` — the same least model, plus one
  justification per derived fact.
* :func:`verify_derivation` — checks a tree against the program and the base
  facts, touching **nothing else**. No index, no closure, no trust in whatever
  produced it.

The universal half has no tree. *"`p(a)` is not derivable"* is a claim about the
whole fixed point under closed-world semantics, and nothing smaller than
recomputing it establishes that — which is the same wall the distance
certificate hit, arrived at from the other direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .engine import (Atom, Fact, Program, Rule, Var, _index, _match, _round,
                     _solve, strata)

__all__ = ["Derivation", "Justification", "evaluate_with_derivations",
           "derivation_tree", "verify_derivation", "DerivationError",
           "tree_size"]


class DerivationError(Exception):
    """A derivation tree does not justify its own conclusion."""


@dataclass(frozen=True)
class Justification:
    """The single rule application that first produced a fact."""

    rule: Rule
    body: tuple[Fact, ...]


@dataclass(frozen=True)
class Derivation:
    """A fact, and either the base it came from or the step that derived it."""

    fact: Fact
    rule: Rule | None = None
    children: tuple["Derivation", ...] = ()

    @property
    def is_base(self) -> bool:
        return self.rule is None


def tree_size(d: Derivation) -> int:
    return 1 + sum(tree_size(c) for c in d.children)


def evaluate_with_derivations(program: Program, facts: Iterable[Fact], *,
                              max_rounds: int = 10_000
                              ) -> tuple[set[Fact], dict[Fact, Justification]]:
    """The least model, plus **one** justification per derived fact.

    One, not all: a fact reachable by several derivations keeps the first found,
    which is enough to justify it and bounded in memory. Keeping every
    derivation is what a provenance semiring does, it answers a different
    question — *how many ways* — and it is unbounded on a cyclic graph.
    """
    known = set(facts)
    why: dict[Fact, Justification] = {}

    def record(layer: Sequence[Rule], k: set[Fact], idx, delta_idx) -> set[Fact]:
        new: set[Fact] = set()
        for r in layer:
            if not r.body:
                f = r.head.as_fact()
                if f not in k and f not in new:
                    new.add(f)
                    why[f] = Justification(r, ())
                continue
            positives = [i for i, l in enumerate(r.body) if not l.negated]
            slots = positives if delta_idx is not None else [-1]
            for slot in slots:
                for subst in _solve(r.body, 0, {}, k, idx, delta_idx, slot):
                    f = r.head.ground(subst)
                    if f in k or f in new:
                        continue
                    new.add(f)
                    why[f] = Justification(
                        r, tuple(lit.atom.ground(subst) for lit in r.body
                                 if not lit.negated))
        return new

    for layer in strata(program):
        idx = _index(known)
        delta = record(layer, known, idx, None)
        known |= delta
        rounds = 0
        while delta:
            rounds += 1
            if rounds > max_rounds:                        # pragma: no cover
                raise RuntimeError("datalog did not converge")
            idx = _index(known)
            new = record(layer, known, idx, _index(delta))
            known |= new
            delta = new
    return known, why


def derivation_tree(fact: Fact, why: Mapping[Fact, Justification], *,
                    max_depth: int = 1000) -> Derivation:
    """Unfold a fact's justification into a tree. Base facts are the leaves."""
    j = why.get(fact)
    if j is None:
        return Derivation(fact)
    if max_depth <= 0:                                     # pragma: no cover
        raise DerivationError(f"derivation of {fact} exceeded max_depth")
    return Derivation(fact, j.rule,
                      tuple(derivation_tree(b, why, max_depth=max_depth - 1)
                            for b in j.body))


def verify_derivation(d: Derivation, base: frozenset[Fact] | set[Fact],
                      program: Program | None = None) -> int:
    """Check a tree against the base facts. Returns the number of nodes checked.

    Reads the tree and the base set, and **never** the closure — which is the
    whole point, and why this stays flat as the derived model grows.

    A leaf must be a base fact. Inventing a leaf is the one attack that matters:
    without this check a tree could "derive" anything by asserting its premises.
    """
    if d.is_base:
        if d.fact not in base:
            raise DerivationError(
                f"leaf {d.fact} is not a base fact: a derivation may not assume "
                "its own premises")
        return 1
    if program is not None and d.rule not in program.rules:
        raise DerivationError(f"rule {d.rule} is not in the program")
    subst: dict[str, str] = {}
    positives = [lit.atom for lit in d.rule.body if not lit.negated]
    if len(positives) != len(d.children):
        raise DerivationError(
            f"rule {d.rule.head.pred} has {len(positives)} positive body "
            f"atoms but the node has {len(d.children)} children")
    for atom, child in zip(positives, d.children):
        m = _match(atom, child.fact, subst)
        if m is None:
            raise DerivationError(
                f"body atom {atom} does not match child fact {child.fact}")
        subst = m
    if d.rule.head.ground(subst) != d.fact:
        raise DerivationError(
            f"rule head grounds to {d.rule.head.ground(subst)}, not {d.fact}")
    return 1 + sum(verify_derivation(c, base, program) for c in d.children)
