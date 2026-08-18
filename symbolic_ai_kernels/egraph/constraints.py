"""Equality saturation over the SMT constraint language, and its cost model.

Named ``constraints`` and not ``simplify`` because the package re-exports a
function called ``simplify``, and a module sharing a name with an exported
function is a module you cannot import: ``import pkg.simplify as S`` binds the
function, and every attribute access on it fails somewhere far from the cause.

The e-graph's consumer here is the SMT kernel, so the terms are the JSON
constraint form :mod:`symbolic_ai_kernels.smt.project` reads, and the cost model
counts what a solver pays for: one unit per node, so fewer and shallower
constraints extract cheaper.

The rule set is small on purpose. The interesting one is the conjunction fold —

    a <= L1  AND  a <= L2   ==   a <= min(L1, L2)

which turns a route crossing *k* bridges into a single bound. It has to be a
**dynamic** rewrite because it fires only when both bounds are literals; a static
pattern cannot say "compute their minimum".
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .egraph import (DynRewrite, EGraph, PVar, Rewrite, Term, extract,
                     saturate, term)

__all__ = ["to_term", "from_term", "RULES", "node_cost", "simplify",
           "SimplifyResult"]

A, B, L, M = PVar("a"), PVar("b"), PVar("l"), PVar("m")


def to_term(expr: Mapping[str, Any]) -> Term:
    """The JSON constraint form as an e-graph term."""
    if "var" in expr:
        return term(f"var:{expr['var']}")
    if "q" in expr:
        return term(f"lit:{float(expr['q']['value'])}:{expr['q'].get('unit', '1')}")
    if "const" in expr:
        return term(f"lit:{float(expr['const'])}:1")
    op = str(expr["op"])
    return term(op, *(to_term(a) for a in expr.get("args") or ()))


def from_term(t: Term) -> dict[str, Any]:
    op, kids = t
    if isinstance(op, str) and op.startswith("var:"):
        return {"var": op[4:]}
    if isinstance(op, str) and op.startswith("lit:"):
        _, value, unit = op.split(":", 2)
        return {"q": {"value": float(value), "unit": unit}}
    return {"op": op, "args": [from_term(k) for k in kids]}


def _literal(g: EGraph, cid) -> tuple[float, str] | None:
    """The numeric value of a class, when it holds one. Units must match."""
    for n in g.classes().get(g.find(cid), ()):
        if n.children or not isinstance(n.op, str) or not n.op.startswith("lit:"):
            continue
        _, value, unit = n.op.split(":", 2)
        return float(value), unit
    return None


def _fold_and_le(g: EGraph, subst: Mapping[str, Any]) -> Term | None:
    """``a<=L AND a<=M`` -> ``a<=min(L,M)``, when both bounds are literals.

    Refuses on a unit mismatch rather than taking a minimum across kilograms and
    metres, which would be the unit checker's whole point undone one layer down.
    """
    lo, hi = _literal(g, subst["l"]), _literal(g, subst["m"])
    if lo is None or hi is None or lo[1] != hi[1]:
        return None
    tightest = min(lo[0], hi[0])
    return term("<=", _class_term(g, subst["a"]),
                term(f"lit:{tightest}:{lo[1]}"))


def _class_term(g: EGraph, cid) -> Term:
    """A representative term for a class, for building a dynamic right side."""
    t, _ = extract(g, cid, cost=node_cost)
    return t


#: One unit per node. A solver pays roughly per assertion and per operator, and
#: a cost model is a *parameter* precisely because the cheapest form depends on
#: who consumes it -- fewest nodes for z3 is not fewest nodes for a reader.
def node_cost(op: Any, kids: Sequence[float]) -> float:
    return 1.0 + sum(kids)


RULES = [
    DynRewrite("and-le-min", ("and", (("<=", (A, L)), ("<=", (A, M)))),
               _fold_and_le),
    Rewrite("and-idem", ("and", (A, A)), A),
    Rewrite("and-comm", ("and", (A, B)), ("and", (B, A))),
    Rewrite("and-assoc", ("and", (("and", (A, B)), L)),
            ("and", (A, ("and", (B, L))))),
]


class SimplifyResult:
    """What saturation found, and what it cost to find it."""

    def __init__(self, constraints, report, before, after):
        self.constraints = constraints
        self.report = report
        self.nodes_before = before
        self.nodes_after = after

    @property
    def shrank(self) -> bool:
        return self.nodes_after < self.nodes_before

    def to_dict(self) -> dict[str, Any]:
        return {"n_constraints": len(self.constraints),
                "nodes_before": self.nodes_before,
                "nodes_after": self.nodes_after,
                "saturation": self.report.to_dict()}


def simplify(constraints: Sequence[Mapping[str, Any]], *,
             max_iters: int = 12) -> SimplifyResult:
    """Saturate the conjunction of ``constraints`` and extract the cheapest form.

    Returns a *list* again, because the SMT kernel asserts a list — the
    conjunction is an internal representation and handing back a single nested
    `and` would make every downstream diagnostic report one constraint.
    """
    if len(constraints) < 2:
        from .egraph import SaturationReport
        n = sum(_count(to_term(c)) for c in constraints)
        return SimplifyResult(list(constraints), SaturationReport(
            saturated=True, stopped_by="nothing to combine"), n, n)

    g = EGraph()
    conj = to_term(constraints[0])
    for c in constraints[1:]:
        conj = term("and", conj, to_term(c))
    root = g.add(conj)
    before = _count(conj)
    report = saturate(g, RULES, max_iters=max_iters)
    best, _cost = extract(g, root, cost=node_cost)
    return SimplifyResult(_split(best), report, before, _count(best))


def _count(t: Term) -> int:
    return 1 + sum(_count(k) for k in t[1])


def _split(t: Term) -> list[dict[str, Any]]:
    op, kids = t
    if op == "and" and len(kids) == 2:
        return _split(kids[0]) + _split(kids[1])
    return [from_term(t)]
