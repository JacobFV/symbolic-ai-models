"""The position index, checked against a naive evaluator that cannot be wrong.

An engine optimisation is exactly the change the existing suite is worst at
policing: every test still passes if the join silently drops a branch, because
the tests were written against programs whose answers the author already
believed. So this file carries its own oracle -- a naive fixed point, written
for obviousness rather than speed -- and compares the two on generated
programs.
"""

from __future__ import annotations

import itertools
import random

import pytest

from symbolic_ai_kernels.datalog import (Atom, FactIndex, Literal, Program,
                                         Rule, Var, evaluate)


def naive_evaluate(program: Program, facts) -> set:
    """T_P to a fixed point by brute force. No index, no delta, no cleverness.

    Enumerates every substitution over the constants in play. Exponential in
    the number of variables and obviously correct, which is the trade this
    oracle exists to make.
    """
    known = set(facts)
    consts = {c for f in known for c in f[1:]}
    for r in program.rules:
        consts |= {t for lit in r.body for t in lit.atom.terms
                   if not isinstance(t, Var)}
    changed = True
    while changed:
        changed = False
        for rule in program.rules:
            names = sorted({t.name for lit in rule.body
                            for t in lit.atom.terms if isinstance(t, Var)}
                           | {t.name for t in rule.head.terms
                              if isinstance(t, Var)})
            for combo in itertools.product(sorted(consts), repeat=len(names)):
                subst = dict(zip(names, combo))
                ok = True
                for lit in rule.body:
                    grounded = lit.atom.ground(subst)
                    present = grounded in known
                    if present == lit.negated:
                        ok = False
                        break
                if ok:
                    head = rule.head.ground(subst)
                    if head not in known:
                        known.add(head)
                        changed = True
    return known


X, Y, Z = Var("X"), Var("Y"), Var("Z")


class TestIndexMechanics:
    def test_an_unbound_atom_falls_back_to_the_predicate(self):
        idx = FactIndex({("p", "a", "b"), ("p", "c", "d"), ("q", "a", "a")})
        assert len(idx.candidates(Atom("p", (X, Y)), {})) == 2

    def test_a_bound_position_narrows_to_a_bucket(self):
        idx = FactIndex({("p", "a", "b"), ("p", "c", "d"), ("p", "a", "e")})
        assert len(idx.candidates(Atom("p", (X, Y)), {"X": "a"})) == 2

    def test_a_constant_term_narrows_without_a_substitution(self):
        idx = FactIndex({("p", "a", "b"), ("p", "c", "d")})
        assert len(idx.candidates(Atom("p", ("a", Y)), {})) == 1

    def test_the_most_selective_bound_position_wins(self):
        """Joining on a high-cardinality column must beat joining on a flag."""
        facts = {("p", f"k{i}", "flag") for i in range(50)}
        facts.add(("p", "k0", "flag"))
        idx = FactIndex(facts)
        got = idx.candidates(Atom("p", (X, Y)), {"X": "k7", "Y": "flag"})
        assert len(got) == 1

    def test_an_absent_value_returns_nothing_immediately(self):
        idx = FactIndex({("p", "a", "b")})
        assert idx.candidates(Atom("p", (X, Y)), {"X": "zzz"}) == ()

    def test_predicate_access_still_reads_the_old_way(self):
        idx = FactIndex({("p", "a", "b")})
        assert len(idx.get("p")) == 1 and idx.get("nope") == ()

    def test_candidates_is_a_superset_of_the_matches(self):
        """The index may only NARROW; correctness still rests on _match."""
        facts = {("p", "a", "b"), ("p", "a", "c"), ("p", "z", "b")}
        idx = FactIndex(facts)
        cands = set(idx.candidates(Atom("p", (X, Y)), {"X": "a"}))
        real = {f for f in facts if f[1] == "a"}
        assert real <= cands


class TestAgainstTheOracle:
    @staticmethod
    def _random_program(rng: random.Random) -> tuple[Program, set]:
        consts = ["a", "b", "c", "d"]
        base = {("e", rng.choice(consts), rng.choice(consts))
                for _ in range(rng.randint(2, 6))}
        rules = [Rule(Atom("t", (X, Y)), (Literal(Atom("e", (X, Y))),)),
                 Rule(Atom("t", (X, Z)), (Literal(Atom("e", (X, Y))),
                                          Literal(Atom("t", (Y, Z)))))]
        if rng.random() < 0.5:
            rules.append(Rule(Atom("s", (X, Y)),
                              (Literal(Atom("t", (X, Y))),
                               Literal(Atom("e", (X, Y)), negated=True))))
        return Program(rules=tuple(rules)), base

    @pytest.mark.parametrize("seed", range(25))
    def test_the_indexed_engine_matches_a_naive_fixed_point(self, seed):
        rng = random.Random(seed)
        program, base = self._random_program(rng)
        assert evaluate(program, base) == naive_evaluate(program, base)

    def test_a_cycle_gives_the_same_model_both_ways(self):
        program, _ = self._random_program(random.Random(0))
        cyc = {("e", "a", "b"), ("e", "b", "c"), ("e", "c", "a")}
        assert evaluate(program, cyc) == naive_evaluate(program, cyc)

    def test_a_self_loop_gives_the_same_model_both_ways(self):
        program, _ = self._random_program(random.Random(1))
        loop = {("e", "a", "a")}
        assert evaluate(program, loop) == naive_evaluate(program, loop)

    def test_negation_agrees_with_the_oracle(self):
        program = Program(rules=(
            Rule(Atom("t", (X, Y)), (Literal(Atom("e", (X, Y))),)),
            Rule(Atom("odd", (X,)), (Literal(Atom("t", (X, Y))),
                                     Literal(Atom("skip", (X,)), negated=True))),
        ))
        base = {("e", "a", "b"), ("e", "b", "c"), ("skip", "b")}
        assert evaluate(program, base) == naive_evaluate(program, base)
