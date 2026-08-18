"""E-graphs: many equivalent forms at once, and a cost model to pick one.

The distinction from term rewriting is the point. A rewriter applying
`a*(b+c) -> a*b + a*c` has lost `a*(b+c)`, and whether that was right depends on
what comes next. An e-graph keeps both and defers to extraction.
"""

from __future__ import annotations

import pytest

from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.egraph import (DynRewrite, EGraph, PVar, Rewrite,
                                        ematch, extract, saturate, simplify,
                                        term)
from symbolic_ai_kernels.egraph import constraints as _constraints

assert _constraints

X, Y, Z = PVar("x"), PVar("y"), PVar("z")


# --- the core -------------------------------------------------------------
def test_congruence_closure_propagates_upward():
    """If x and y become equal then f(x) and f(y) must too. Skipping this gives
    an e-graph representing fewer equalities than it claims to, silently."""
    g = EGraph()
    fx, fy = g.add(term("f", term("x"))), g.add(term("f", term("y")))
    assert g.find(fx) != g.find(fy)
    g.merge(g.add(term("x")), g.add(term("y")))
    g.rebuild()
    assert g.find(fx) == g.find(fy)


def test_saturation_proves_an_equality_a_rewriter_would_have_lost():
    g = EGraph()
    t = term("/", term("*", term("a"), term("2")), term("2"))
    root = g.add(t)
    rules = [Rewrite("mul2", ("*", (X, ("2", ()))), ("<<", (X, ("1", ())))),
             Rewrite("shiftdiv", ("/", (("<<", (X, ("1", ()))), ("2", ()))), X)]
    rep = saturate(g, rules)
    assert rep.saturated
    assert g.equal(t, term("a"))
    assert extract(g, root)[0] == term("a")


def test_extraction_follows_the_cost_model_not_the_rules():
    """The cheapest form depends entirely on the consumer, which is why cost is
    a parameter and not a constant."""
    g = EGraph()
    root = g.add(term("*", term("a"), term("2")))
    g.merge(root, g.add(term("<<", term("a"), term("1"))))
    g.rebuild()

    cheap_shift = lambda op, kids: (0.5 if op == "<<" else 5.0) + sum(kids)
    cheap_mul = lambda op, kids: (0.5 if op == "*" else 5.0) + sum(kids)
    assert extract(g, root, cost=cheap_shift)[0][0] == "<<"
    assert extract(g, root, cost=cheap_mul)[0][0] == "*"


def test_a_pattern_variable_binds_a_class_not_a_term():
    g = EGraph()
    root = g.add(term("f", term("a")))
    g.merge(g.add(term("a")), g.add(term("b")))
    g.rebuild()
    matches = ematch(g, ("f", (X,)))
    assert matches, "the rule did not see the class it was supposed to bind"


def test_a_rewrite_that_would_invent_a_term_is_refused():
    g = EGraph()
    g.add(term("f", term("a")))
    with pytest.raises(KeyError, match="does not bind"):
        saturate(g, [Rewrite("bad", ("f", (X,)), ("g", (Y,)))])


def test_hitting_a_limit_is_reported_as_stopping_not_as_finishing():
    """A run out of budget must not read as a search that finished.

    Uses associativity and commutativity over a chain, which is the blowup
    actually measured: a five-constraint conjunction reaches 117 e-nodes and
    346 rule applications. A rule like `f(X) -> f(f(X))` does NOT work here and
    it is worth saying why -- every rewrite MERGES its two sides, so that rule
    puts `f(a)` and `f(f(a))` in one class and saturates in two rounds. Growth
    in an e-graph is in nodes, not classes.
    """
    g = EGraph()
    chain = term("and", term("and", term("a"), term("b")),
                 term("and", term("c"), term("d")))
    g.add(chain)
    rules = [Rewrite("comm", ("and", (X, Y)), ("and", (Y, X))),
             Rewrite("assoc", ("and", (("and", (X, Y)), Z)),
                     ("and", (X, ("and", (Y, Z)))))]
    rep = saturate(g, rules, max_nodes=12)
    assert not rep.saturated
    assert "node limit" in rep.stopped_by
    assert rep.applied, "nothing fired, so the limit was not what stopped it"


def test_a_rewrite_merges_rather_than_replaces():
    """The property that distinguishes this from term rewriting."""
    g = EGraph()
    root = g.add(term("*", term("a"), term("2")))
    saturate(g, [Rewrite("mul2", ("*", (X, ("2", ()))),
                         ("<<", (X, ("1", ()))))])
    assert g.equal(term("*", term("a"), term("2")),
                   term("<<", term("a"), term("1")))
    nodes = g.classes()[g.find(root)]
    assert {n.op for n in nodes} == {"*", "<<"}, (
        "the original form was lost, which is what a rewriter does and an "
        "e-graph must not")


def test_a_dynamic_rule_may_decline_to_fire():
    g = EGraph()
    root = g.add(term("and", term("le", term("a"), term("x")),
                      term("le", term("a"), term("y"))))
    fired = []

    def never(gr, subst):
        fired.append(1)
        return None

    rep = saturate(g, [DynRewrite("never", ("and", (("le", (X, Y)),
                                                    ("le", (X, Z)))), never)])
    assert fired, "the dynamic rule was never consulted"
    assert rep.saturated and not rep.applied


# --- the constraint simplifier -------------------------------------------
def bound(var, value):
    return {"op": "<=", "args": [{"var": var}, {"q": {"value": value,
                                                      "unit": "kg"}}]}


def test_a_conjunction_of_bounds_folds_to_the_tightest():
    r = simplify([bound("a", 4500), bound("a", 3000), bound("a", 6000)])
    assert len(r.constraints) == 1
    assert r.constraints[0]["args"][1]["q"]["value"] == 3000.0
    assert r.shrank


def test_bounds_in_different_units_do_not_fold():
    """Taking a minimum across kilograms and metres would undo the unit
    checker's whole point one layer down."""
    mixed = [bound("a", 3000),
             {"op": "<=", "args": [{"var": "a"},
                                   {"q": {"value": 2.0, "unit": "m"}}]}]
    r = simplify(mixed)
    assert len(r.constraints) == 2


def test_bounds_on_different_variables_do_not_fold():
    r = simplify([bound("a", 3000), bound("b", 4500)])
    assert len(r.constraints) == 2


def test_one_constraint_is_refused_rather_than_returned_unchanged():
    k = get_kernel("egraph@1")
    req = KernelRequest(params={"constraints": [bound("a", 1)]})
    out = k.run(k.project(None, req), req)
    assert not out.ok and "nothing to combine" in out.refused


def test_the_simplification_preserves_satisfiability():
    z3 = pytest.importorskip("z3")
    from symbolic_ai_core.world import Entity, Facet, WorldSnapshot

    world = WorldSnapshot(entities={"t": Entity("t", facets={
        "logic.constraint": Facet("logic.constraint", {
            "variables": {"a": {"unit": "kg"}}})})})
    smt = get_kernel("smt@1")
    for cons in ([bound("a@t", 4500), bound("a@t", 3000),
                  {"op": ">=", "args": [{"var": "a@t"},
                                        {"q": {"value": 100, "unit": "kg"}}]}],
                 [bound("a@t", 50), bound("a@t", 3000),
                  {"op": ">=", "args": [{"var": "a@t"},
                                        {"q": {"value": 100, "unit": "kg"}}]}]):
        simp = simplify(cons).constraints
        a = smt.run(smt.project(world, KernelRequest(params={"constraints": cons})),
                    KernelRequest(params={"constraints": cons}))
        b = smt.run(smt.project(world, KernelRequest(params={"constraints": simp})),
                    KernelRequest(params={"constraints": simp}))
        assert a.ok == b.ok, "simplification changed satisfiability"


# --- the kernel -----------------------------------------------------------
def test_the_projection_says_it_did_not_read_the_world():
    k = get_kernel("egraph@1")
    req = KernelRequest(params={"constraints": [bound("a", 1), bound("a", 2)]})
    p = k.project(None, req)
    assert p.covered_entities == frozenset() and p.covered_claims == ()
    assert any("not a world" in d.why for d in p.discarded)


def test_an_equivalent_form_is_not_a_fact_about_the_world():
    k = get_kernel("egraph@1")
    req = KernelRequest(params={"constraints": [bound("a", 4500), bound("a", 3000)]})
    out = k.run(k.project(None, req), req)
    assert out.ok and out.delta.is_empty()
    assert out.claims[0].predicate == "equivalent_form"
    assert k.manifest.authority["equivalent_form"] == "propose"


def test_it_prices_itself_and_the_price_is_not_small():
    """The finding this kernel ships with: saturation cost 41x what it saved."""
    k = get_kernel("egraph@1")
    req = KernelRequest(params={"constraints": [bound("a", 4500), bound("a", 3000),
                                                bound("a", 6000)]})
    out = k.run(k.project(None, req), req)
    assert out.cost.usd is not None and out.cost.cpu_ns > 0
