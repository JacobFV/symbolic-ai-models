"""No flow node may manufacture an asserted claim from a result that settled nothing.

Found by hand in two places -- `scheduling/ops.py` turned `not result.ok` into
``polarity="negative", modality="asserted"``, and `flood/ops.py` did the same
across candidate routes -- so a solver that ran out of time would have entered
"this schedule is NOT feasible" into the world as a fact no kernel established.

Both were latent: nothing passed a budget, so nothing could be exhausted. The
ASP unsat/exhausted conflation one layer up was latent the same way, and the fix
for it is what made these reachable. That is the argument for a structural check
rather than two fixes: the next such node will be written before anything
budgets it, and by then the bug is invisible again.

The check is deliberately narrow. It looks for functions that both consume a
kernel result and construct a claim with a **polarity**, and requires them to
mention ``conclusive`` or ``settled``. A node that emits only what the kernel
returned cannot fabricate anything, because a kernel that establishes nothing
returns no claims -- so this targets exactly the one way a node can invent a
fact: by reading an *absence* of a positive answer as a negative one.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

ROOTS = ("symbolic_ai_generators", "symbolic_ai_kernels", "symbolic_ai_core",
         "symbolic_ai_tasks", "symbolic_ai_adapters")
REPO = pathlib.Path(__file__).resolve().parent.parent

#: The fields that mean "a kernel settled the question".
SETTLED = ("conclusive", "settled", "proved_impossible", "exhausted")


def _functions_with_source():
    for root in ROOTS:
        for path in sorted((REPO / root).rglob("*.py")):
            try:
                tree = ast.parse(path.read_text())
            except SyntaxError:                               # pragma: no cover
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield path, node


def _reads_result_ok(fn: ast.AST) -> bool:
    """`something.ok` or `something.refused` -- a kernel result being judged."""
    return any(isinstance(n, ast.Attribute) and n.attr in ("ok", "refused")
               for n in ast.walk(fn))


def _builds_a_polarity_claim(fn: ast.AST) -> bool:
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and any(
                kw.arg == "polarity" for kw in n.keywords):
            return True
    return False


def _mentions_settlement(fn: ast.AST) -> bool:
    return any(isinstance(n, ast.Attribute) and n.attr in SETTLED
               for n in ast.walk(fn)) or any(
        isinstance(n, ast.Name) and n.id in SETTLED for n in ast.walk(fn))


SUSPECTS = [(p, f) for p, f in _functions_with_source()
            if _reads_result_ok(f) and _builds_a_polarity_claim(f)]


def test_the_check_finds_the_functions_it_is_meant_to_police():
    """A structural test that matches nothing is not a guard, it is a comment.

    Both known sites -- flood's `_check_loads` and scheduling's `_solve` --
    must still be in scope, or the AST patterns have drifted away from the
    code they were written for.
    """
    names = {f.name for _, f in SUSPECTS}
    assert {"_check_loads", "_solve"} <= names, (
        f"the guard no longer sees the functions it was written for: {names}")


@pytest.mark.parametrize("path,fn", SUSPECTS,
                         ids=[f"{p.stem}:{f.name}" for p, f in SUSPECTS])
def test_a_polarity_claim_is_gated_on_settlement(path, fn):
    assert _mentions_settlement(fn), (
        f"{path.relative_to(REPO)}:{fn.lineno} {fn.name}() judges a kernel "
        f"result and builds a claim with a polarity, without ever checking "
        f"whether the kernel settled anything. An absent positive answer is "
        f"not a negative one -- see "
        f"notes/findings/"
        f"2026-08-18-two-generators-would-have-asserted-infeasibility-from-a-timeout.md")


def test_the_pattern_would_have_caught_the_original_bug():
    """The guard is only worth having if it fires on the code it was written
    against, so this reconstructs the pre-fix shape and checks it is caught."""
    before = ast.parse(
        "def _solve(inputs, params, ctx):\n"
        "    result = asp.run(projection, request)\n"
        "    feasible = result.ok\n"
        "    claim = Claim('feasible_schedule', {},\n"
        "                  polarity='positive' if feasible else 'negative',\n"
        "                  modality='asserted')\n"
        "    return claim\n").body[0]
    assert _reads_result_ok(before) and _builds_a_polarity_claim(before)
    assert not _mentions_settlement(before), "the guard would have missed it"
