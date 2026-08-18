"""The incremental path, and the contract it did not honour until now.

The engine's docstring promised that a delta costs "proportional to what it
actually changed rather than to the size of the world". Measured on the real
GLEIF model -- 285,596 facts -- adding a single edge that derives two facts cost
1,230 ms against 6,967 ms to recompute everything: a 5.7x saving on a two-fact
change, falling to 1.4x by two hundred edges. The claim was false as
implemented.

Two causes, both fixed here, and the tests below pin the behaviour rather than
the timing: an index rebuilt over the whole model on every round, and a join
that started at the first literal even when the new facts were bound to the
second.
"""

from __future__ import annotations

import random

import pytest

from symbolic_ai_kernels.datalog import (Atom, IncrementalModel, Literal,
                                         NonMonotoneAddition, Program, Rule,
                                         Var, evaluate)
from symbolic_ai_kernels.datalog.engine import _delta_first

X, Y, Z = Var("X"), Var("Y"), Var("Z")
CLOSURE = Program(rules=(
    Rule(Atom("t", (X, Y)), (Literal(Atom("e", (X, Y))),)),
    Rule(Atom("t", (X, Z)), (Literal(Atom("e", (X, Y))),
                             Literal(Atom("t", (Y, Z)))))))


class TestDeltaFirstOrdering:
    def test_the_delta_literal_moves_to_the_front(self):
        body = CLOSURE.rules[1].body
        order, must = _delta_first(body, 1, object())
        assert order[0] is body[1] and must == 0

    def test_negated_literals_stay_after_every_positive(self):
        """Safety: a negated literal's variables must be bound by the time it
        is reached, or `not p` becomes a search instead of a lookup."""
        body = (Literal(Atom("a", (X, Y))), Literal(Atom("b", (Y,)),
                                                    negated=True),
                Literal(Atom("c", (Y, Z))))
        order, _ = _delta_first(body, 2, object())
        neg_at = [i for i, l in enumerate(order) if l.negated]
        pos_at = [i for i, l in enumerate(order) if not l.negated]
        assert max(pos_at) < min(neg_at)

    def test_without_a_delta_the_body_is_untouched(self):
        body = CLOSURE.rules[1].body
        order, must = _delta_first(body, -1, None)
        assert order is body and must == -1


class TestModelAgreesWithRecomputation:
    def test_adding_one_edge_gives_the_same_model(self):
        base = {("e", "a", "b"), ("e", "b", "c")}
        m = IncrementalModel(CLOSURE, base)
        m.add({("e", "c", "d")})
        assert m.facts == evaluate(CLOSURE, base | {("e", "c", "d")})

    @pytest.mark.parametrize("seed", range(20))
    def test_random_deltas_agree_with_recomputation(self, seed):
        rng = random.Random(seed)
        consts = ["a", "b", "c", "d", "e"]
        base = {("e", rng.choice(consts), rng.choice(consts))
                for _ in range(rng.randint(2, 6))}
        delta = {("e", rng.choice(consts), rng.choice(consts))
                 for _ in range(rng.randint(1, 4))}
        m = IncrementalModel(CLOSURE, base)
        m.add(delta)
        assert m.facts == evaluate(CLOSURE, base | delta)

    def test_a_sequence_of_deltas_agrees_with_one_recomputation(self):
        """Where an incremental engine usually rots: state accumulating wrong
        over many steps, each individually plausible."""
        rng = random.Random(7)
        consts = [f"n{i}" for i in range(8)]
        base = {("e", "n0", "n1")}
        m = IncrementalModel(CLOSURE, base)
        allf = set(base)
        for _ in range(15):
            d = {("e", rng.choice(consts), rng.choice(consts))}
            m.add(d)
            allf |= d
        assert m.facts == evaluate(CLOSURE, allf)

    def test_a_delta_that_closes_a_cycle_agrees(self):
        base = {("e", "a", "b"), ("e", "b", "c")}
        m = IncrementalModel(CLOSURE, base)
        m.add({("e", "c", "a")})
        assert m.facts == evaluate(CLOSURE, base | {("e", "c", "a")})

    def test_re_adding_a_known_fact_derives_nothing(self):
        base = {("e", "a", "b")}
        m = IncrementalModel(CLOSURE, base)
        assert m.add({("e", "a", "b")}) == set()


class TestReturnValue:
    def test_it_returns_what_was_newly_derived(self):
        m = IncrementalModel(CLOSURE, {("e", "a", "b")})
        got = m.add({("e", "b", "c")})
        assert ("t", "a", "c") in got and ("t", "a", "b") not in got

    def test_the_added_base_facts_come_back_too(self):
        m = IncrementalModel(CLOSURE, {("e", "a", "b")})
        assert ("e", "b", "c") in m.add({("e", "b", "c")})


class TestNonMonotone:
    def test_an_addition_reaching_a_negated_predicate_is_refused(self):
        """A wrong incremental result is indistinguishable from a right one,
        so this refuses rather than guessing."""
        prog = Program(rules=(
            Rule(Atom("t", (X, Y)), (Literal(Atom("e", (X, Y))),)),
            Rule(Atom("ok", (X,)), (Literal(Atom("t", (X, Y))),
                                    Literal(Atom("bad", (X,)), negated=True))),
        ))
        m = IncrementalModel(prog, {("e", "a", "b")})
        with pytest.raises(NonMonotoneAddition, match="unsound"):
            m.add({("bad", "a")})

    def test_the_refusal_names_the_rebuild(self):
        prog = Program(rules=(
            Rule(Atom("ok", (X,)), (Literal(Atom("s", (X,))),
                                    Literal(Atom("bad", (X,)), negated=True))),
        ))
        m = IncrementalModel(prog, {("s", "a")})
        with pytest.raises(NonMonotoneAddition, match="IncrementalModel"):
            m.add({("bad", "a")})
