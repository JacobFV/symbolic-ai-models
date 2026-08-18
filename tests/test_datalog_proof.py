"""Why a derived fact is true, checked without trusting the engine."""

from __future__ import annotations

import pytest

from symbolic_ai_kernels.datalog import (Atom, Literal, Program, Rule, Var,
                                         evaluate)
from symbolic_ai_kernels.datalog.proof import (Derivation, DerivationError,
                                               derivation_tree,
                                               evaluate_with_derivations,
                                               tree_size, verify_derivation)

X, Y, Z = Var("X"), Var("Y"), Var("Z")
ANCESTRY = Program(rules=(
    Rule(Atom("anc", (X, Y)), (Literal(Atom("par", (X, Y))),)),
    Rule(Atom("anc", (X, Z)), (Literal(Atom("par", (X, Y))),
                               Literal(Atom("anc", (Y, Z)))))))
CHAIN = {("par", "a", "b"), ("par", "b", "c"), ("par", "c", "d")}


class TestDerivationsMatchTheEngine:
    def test_the_same_least_model_as_evaluate(self):
        """Recording provenance must not change what is derived."""
        facts, _ = evaluate_with_derivations(ANCESTRY, CHAIN)
        assert facts == evaluate(ANCESTRY, CHAIN)

    def test_base_facts_have_no_justification(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        assert all(f not in why for f in CHAIN)

    def test_every_derived_fact_has_one(self):
        facts, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        assert all(f in why for f in facts - CHAIN)

    def test_a_deeper_chain_gives_a_deeper_tree(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        near = derivation_tree(("anc", "c", "d"), why)
        far = derivation_tree(("anc", "a", "d"), why)
        assert tree_size(far) > tree_size(near)


class TestVerification:
    def test_a_real_derivation_verifies(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        tree = derivation_tree(("anc", "a", "d"), why)
        assert verify_derivation(tree, CHAIN, ANCESTRY) == tree_size(tree)

    def test_an_invented_leaf_is_refused(self):
        """The attack that matters: without this a tree derives anything by
        asserting its own premises."""
        with pytest.raises(DerivationError, match="not a base fact"):
            verify_derivation(Derivation(("par", "x", "y")), CHAIN, ANCESTRY)

    def test_a_head_that_does_not_follow_is_refused(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        real = derivation_tree(("anc", "a", "d"), why)
        forged = Derivation(("anc", "a", "elsewhere"), real.rule, real.children)
        with pytest.raises(DerivationError, match="grounds to"):
            verify_derivation(forged, CHAIN, ANCESTRY)

    def test_a_rule_outside_the_program_is_refused(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        real = derivation_tree(("anc", "a", "b"), why)
        alien = Rule(Atom("anc", (X, Y)), (Literal(Atom("bogus", (X, Y))),))
        forged = Derivation(("anc", "a", "b"), alien, real.children)
        with pytest.raises(DerivationError, match="not in the program"):
            verify_derivation(forged, CHAIN, ANCESTRY)

    def test_the_wrong_number_of_children_is_refused(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        real = derivation_tree(("anc", "a", "d"), why)
        forged = Derivation(real.fact, real.rule, real.children[:1])
        with pytest.raises(DerivationError, match="body atoms but the node"):
            verify_derivation(forged, CHAIN, ANCESTRY)

    def test_a_body_atom_not_matching_its_child_is_refused(self):
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        real = derivation_tree(("anc", "a", "d"), why)
        swapped = Derivation(real.fact, real.rule,
                             tuple(reversed(real.children)))
        with pytest.raises(DerivationError):
            verify_derivation(swapped, CHAIN, ANCESTRY)

    def test_verification_never_reads_the_closure(self):
        """The property the whole module exists for: the verifier is handed
        the base facts only, and the closure is not in scope."""
        _, why = evaluate_with_derivations(ANCESTRY, CHAIN)
        tree = derivation_tree(("anc", "a", "d"), why)
        assert verify_derivation(tree, frozenset(CHAIN), ANCESTRY) > 0


class TestCyclesAndDepth:
    def test_a_cyclic_relation_still_terminates(self):
        """Ownership cycles exist in filed data. One justification per fact
        bounds the unfolding whatever the graph does."""
        cyc = {("par", "a", "b"), ("par", "b", "a")}
        facts, why = evaluate_with_derivations(ANCESTRY, cyc)
        tree = derivation_tree(("anc", "a", "a"), why)
        assert verify_derivation(tree, cyc, ANCESTRY) == tree_size(tree)

    def test_one_justification_is_kept_not_all(self):
        """Two routes to the same fact; the first found is enough to justify
        it and is bounded, where keeping all is not on a cyclic graph."""
        diamond = {("par", "a", "b"), ("par", "a", "c"),
                   ("par", "b", "d"), ("par", "c", "d")}
        facts, why = evaluate_with_derivations(ANCESTRY, diamond)
        assert isinstance(why[("anc", "a", "d")].body, tuple)
        tree = derivation_tree(("anc", "a", "d"), why)
        assert verify_derivation(tree, diamond, ANCESTRY) == tree_size(tree)
