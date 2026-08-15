"""Adversarial tests for the `006` kernel, written before it got a model.

The kernel carries the whole line: a gate result is a claim about what
typechecks, and it is worth exactly what the typechecker is worth. So the tests
here are the ones that would catch a kernel that says yes too often — an
over-permissive kernel would report a low prune rate and close the line for the
wrong reason, and an over-eager one would report a high prune rate and open it
for the wrong reason. Both directions are tested.
"""

from __future__ import annotations

import pytest

from symbolic_ai_lean.expr import (App, Const, Lam, Lit, MVar, Pi, Sort, Var,
                                   apps, arrow, arrow_parts, pretty, spine)
from symbolic_ai_lean.kernel import (FUEL, MetaCtx, TypeError_, check, infer,
                                     unify, whnf)

A = Const("A")
B = Const("B")
SIG = {"A": Sort(1), "B": Sort(1), "a": A, "b": B,
       "f": Pi("_", A, B), "g": Pi("_", A, Pi("_", B, A))}


def ctx() -> MetaCtx:
    return MetaCtx()


# ---------------------------------------------------------------- inference
def test_a_constant_has_its_declared_type():
    assert infer(Const("a"), SIG, ctx()) == A


def test_an_undeclared_constant_is_an_error():
    with pytest.raises(TypeError_):
        infer(Const("nope"), SIG, ctx())


def test_applying_a_non_function_is_an_error():
    with pytest.raises(TypeError_):
        infer(App(Const("a"), Const("a")), SIG, ctx())


def test_an_argument_of_the_wrong_type_is_an_error():
    with pytest.raises(TypeError_):
        infer(App(Const("f"), Const("b")), SIG, ctx())


def test_an_argument_of_the_right_type_is_not():
    assert infer(App(Const("f"), Const("a")), SIG, ctx()) == B


def test_partial_application_has_a_function_type():
    """The elaborator's saturation rule depends on this being *visible* rather
    than an error: `g a` is well-typed and its type is a `Pi`, which is exactly
    what tells a value position that a partially applied symbol cannot sit there."""
    got = infer(App(Const("g"), Const("a")), SIG, ctx())
    assert isinstance(got, Pi)


def test_an_unbound_variable_is_an_error():
    with pytest.raises(TypeError_):
        infer(Var(0), SIG, ctx())


def test_a_lambda_gets_a_pi_and_beta_reduces():
    idA = Lam("x", A, Var(0))
    assert infer(idA, SIG, ctx()) == Pi("x", A, A)
    assert whnf(App(idA, Const("a"))) == Const("a")


def test_prop_is_impredicative_like_lean():
    """``∀ x : A, P x`` is a ``Prop`` however large ``A`` is — Lean's rule, and
    the reason every predicate node in the curriculum lands in ``Sort 0``
    regardless of what it quantifies over."""
    sig = dict(SIG, P=Pi("_", A, Sort(0)))
    assert infer(Pi("_", A, App(Const("P"), Var(0))), sig, ctx()) == Sort(0)
    # and a genuinely large arrow is not a Prop: `Type → Type` is `Sort 2`.
    assert infer(Pi("_", Sort(1), Sort(1)), SIG, ctx()) == Sort(2)


def test_check_never_raises():
    assert check(Const("nope"), A, SIG, ctx()) is False
    assert check(Const("a"), A, SIG, ctx()) is True


# -------------------------------------------------------------- unification
def test_unify_assigns_and_undo_restores():
    c = ctx()
    m = c.fresh()
    mark = c.mark()
    assert unify(m, A, c)
    assert c.deref(m) == A
    c.undo(mark)
    assert c.deref(m) == m


def test_unify_is_symmetric_in_metavariables():
    c = ctx()
    m, n = c.fresh(), c.fresh()
    assert unify(m, n, c)
    assert unify(n, A, c)
    assert c.deref(m) == A


def test_rigid_mismatch_fails():
    c = ctx()
    assert unify(A, B, c) is False
    assert unify(Sort(0), Sort(1), c) is False
    assert unify(Lit("x"), Lit("y"), c) is False
    assert unify(Lit("x"), Lit("x"), c) is True


def test_arity_mismatch_fails():
    """The single most load-bearing rejection in the gate: a two-argument
    constant cannot be the same thing as a one-argument one."""
    c = ctx()
    assert unify(arrow([A, A], B), arrow([A], B), c) is False


def test_occurs_check_refuses_a_cyclic_solution():
    c = ctx()
    m = c.fresh()
    assert unify(m, Pi("_", m, A), c) is False


def test_a_failed_unification_leaves_the_caller_to_rewind():
    """`unify` does not rewind on failure; the caller owns the mark. Checking
    fifty-five candidates wants one mark and fifty-five undos."""
    c = ctx()
    m, n = c.fresh(), c.fresh()
    mark = c.mark()
    assert unify(apps(Const("P"), [m, n]), apps(Const("P"), [A, B]), c)
    assert c.deref(m) == A
    c.undo(mark)
    assert c.deref(m) == m and c.deref(n) == n


def test_self_application_does_not_hang():
    """`(fun x => x x) (fun x => x x)` has no normal form. A kernel that loops
    on it hangs a sweep, and the failure looks like a slow machine."""
    omega = Lam("x", A, App(Var(0), Var(0)))
    assert whnf(App(omega, omega), None, 50) is not None


def test_deep_terms_do_not_recurse_off_the_stack():
    e = Const("a")
    for _ in range(200):
        e = App(Const("f"), e)
    head, args = spine(e)
    assert head == Const("f") and len(args) == 1


# ------------------------------------------------------------------ helpers
def test_arrow_and_arrow_parts_are_inverse():
    doms, cod = arrow_parts(arrow([A, B, A], Sort(0)))
    assert doms == [A, B, A] and cod == Sort(0)


def test_pretty_round_trips_a_label_containing_quotes():
    assert pretty(Lit('a"b')) == '"a\\"b"'


def test_instantiate_resolves_everywhere_not_only_at_the_head():
    c = ctx()
    m = c.fresh()
    unify(m, A, c)
    assert c.instantiate(Pi("_", m, App(Const("List"), m))) == \
        Pi("_", A, App(Const("List"), A))
