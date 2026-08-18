"""An e-graph: many equivalent forms at once, and a cost model to pick one.

Tier 5. Every other kernel in this stack answers *what follows*; this one answers
*what else is the same thing*, and then **which of those is cheapest**.

The distinction from ordinary term rewriting is the whole reason it exists.
A rewriter applies `a*(b+c) -> a*b + a*c` and has now lost `a*(b+c)`; whether
that was the right move depends on what comes next, and it cannot know. An
e-graph keeps both, in one **e-class**, and defers the choice to an extraction
pass with an explicit cost function:

    argmin over e' equivalent to e  of  C(e')

which is the same shape as the routing objective one layer up — and the reason
the decision note ranks this as a kernel that could optimise *the reasoning
program itself* rather than only the terms in it.

Three pieces, and the third is the one naive implementations get wrong:

* **union-find over e-class ids**, so merging two classes is near-constant;
* **a hashcons from e-node to e-class**, so structurally identical nodes land in
  one place;
* **congruence closure** — if ``x`` and ``y`` become equal, then ``f(x)`` and
  ``f(y)`` must become equal too, transitively. That is what ``rebuild`` does,
  and skipping it gives an e-graph that silently represents fewer equalities
  than it claims to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

__all__ = ["ENode", "EGraph", "Pattern", "PVar", "Rewrite", "DynRewrite",
           "Term", "term", "saturate", "extract", "ematch",
           "SaturationReport"]

EClassId = int

#: A term is ``(op, children)``; a leaf is ``(op, ())``. Deliberately not a
#: class -- terms are compared and hashed constantly, and a tuple is both.
Term = tuple


def term(op: Any, *children: "Term") -> Term:
    return (op, tuple(children))


@dataclass(frozen=True)
class ENode:
    """One operator applied to e-*classes*, not to terms."""

    op: Any
    children: tuple[EClassId, ...] = ()

    def canon(self, find: Callable[[EClassId], EClassId]) -> "ENode":
        return ENode(self.op, tuple(find(c) for c in self.children))

    def __repr__(self) -> str:                                # pragma: no cover
        return f"{self.op}({', '.join(map(str, self.children))})"


# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PVar:
    """A pattern variable. Binds an e-class, not a term.

    That is the point: a rule matching ``?x + 0`` binds ``?x`` to a whole
    equivalence class, so the rewrite fires once for every form ``?x`` will ever
    take rather than once per syntactic occurrence.
    """

    name: str

    def __repr__(self) -> str:
        return "?" + self.name


Pattern = Any        #: ``PVar`` or ``(op, tuple[Pattern, ...])``


@dataclass(frozen=True)
class Rewrite:
    """``lhs -> rhs``, applied by *merging* rather than replacing."""

    name: str
    lhs: Pattern
    rhs: Pattern

    def __repr__(self) -> str:                                # pragma: no cover
        return f"{self.name}: {self.lhs} => {self.rhs}"


@dataclass(frozen=True)
class DynRewrite:
    """A rewrite whose right-hand side is *computed* from the match.

    Needed for anything conditional, and constant folding is the case that makes
    it unavoidable: ``a <= 3000 AND a <= 4500`` collapses to ``a <= 3000`` only
    when both bounds are known numbers, and a static pattern cannot say "when
    these two children are literals, compute their minimum".

    ``fn(egraph, subst) -> Term | None``. Returning ``None`` is a *refusal to
    fire*, which is how a conditional rule declines rather than inventing a
    term.
    """

    name: str
    lhs: Pattern
    fn: Callable[["EGraph", Mapping[str, EClassId]], "Term | None"]

    def __repr__(self) -> str:                                # pragma: no cover
        return f"{self.name}: {self.lhs} => <dynamic>"


# ---------------------------------------------------------------------------
# the graph
# ---------------------------------------------------------------------------
class EGraph:
    """E-classes, e-nodes, and the congruence that keeps them honest."""

    def __init__(self) -> None:
        self._parent: list[EClassId] = []
        self._classes: dict[EClassId, set[ENode]] = {}
        self._hashcons: dict[ENode, EClassId] = {}
        #: For each class, the ``(node, owning class)`` pairs that REFERENCE it.
        #: Without this, ``rebuild`` can only re-canonicalise the classes that
        #: were merged, and congruence never propagates upward: merging ``x``
        #: with ``y`` leaves ``f(x)`` and ``f(y)`` apart, silently. The first
        #: version of this file had exactly that bug and a test caught it.
        self._parents: dict[EClassId, list[tuple[ENode, EClassId]]] = {}
        self._pending: list[EClassId] = []

    # ---- union-find ---------------------------------------------------
    def find(self, cid: EClassId) -> EClassId:
        root = cid
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[cid] != root:            # path compression
            self._parent[cid], cid = root, self._parent[cid]
        return root

    def _new_class(self) -> EClassId:
        cid = len(self._parent)
        self._parent.append(cid)
        self._classes[cid] = set()
        self._parents[cid] = []
        return cid

    # ---- building ------------------------------------------------------
    def add_node(self, node: ENode) -> EClassId:
        node = node.canon(self.find)
        existing = self._hashcons.get(node)
        if existing is not None:
            return self.find(existing)
        cid = self._new_class()
        self._classes[cid].add(node)
        self._hashcons[node] = cid
        for child in set(node.children):
            self._parents.setdefault(self.find(child), []).append((node, cid))
        return cid

    def add(self, t: Term) -> EClassId:
        op, children = t
        return self.add_node(ENode(op, tuple(self.add(c) for c in children)))

    def merge(self, a: EClassId, b: EClassId) -> bool:
        """Union two classes. Returns whether anything changed."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if len(self._classes[ra]) < len(self._classes[rb]):
            ra, rb = rb, ra
        self._parent[rb] = ra
        self._classes[ra] |= self._classes.pop(rb)
        self._parents.setdefault(ra, []).extend(self._parents.pop(rb, []))
        self._pending.append(ra)
        return True

    def rebuild(self) -> None:
        """Restore congruence: equal arguments make equal applications.

        Repairs each merged class's **parents**, which is where the propagation
        happens -- re-canonicalising only the merged class itself would leave
        every application of it stale. Without this an e-graph represents fewer
        equalities than it claims to, and the failure is silent: extraction
        still returns *a* term, just not the cheapest equivalent one.
        """
        while self._pending:
            todo = {self.find(c) for c in self._pending}
            self._pending.clear()
            for cid in todo:
                self._repair(cid)

    def _repair(self, cid: EClassId) -> None:
        parents = self._parents.pop(cid, [])
        for node, pcid in parents:
            self._hashcons.pop(node, None)
            canon = node.canon(self.find)
            self._hashcons[canon] = self.find(pcid)
        seen: dict[ENode, EClassId] = {}
        fresh: list[tuple[ENode, EClassId]] = []
        for node, pcid in parents:
            canon = node.canon(self.find)
            prev = seen.get(canon)
            if prev is not None:
                self.merge(prev, pcid)
            else:
                seen[canon] = self.find(pcid)
            fresh.append((canon, self.find(pcid)))
        self._parents[self.find(cid)] = fresh
        # the class's own nodes have to be re-canonicalised too, or the
        # hashcons keeps stale keys pointing into a merged-away class
        nodes = self._classes.get(self.find(cid))
        if nodes is not None:
            self._classes[self.find(cid)] = {n.canon(self.find) for n in nodes}

    # ---- reading -------------------------------------------------------
    def classes(self) -> dict[EClassId, set[ENode]]:
        out: dict[EClassId, set[ENode]] = {}
        for cid, nodes in self._classes.items():
            root = self.find(cid)
            out.setdefault(root, set()).update(n.canon(self.find) for n in nodes)
        return out

    def __len__(self) -> int:
        return len(self.classes())

    def n_nodes(self) -> int:
        return sum(len(v) for v in self.classes().values())

    def equal(self, a: Term, b: Term) -> bool:
        return self.find(self.add(a)) == self.find(self.add(b))


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------
def _match_node(g: EGraph, pat: Pattern, cid: EClassId,
                subst: dict[str, EClassId]) -> Iterator[dict[str, EClassId]]:
    if isinstance(pat, PVar):
        bound = subst.get(pat.name)
        if bound is None:
            yield {**subst, pat.name: g.find(cid)}
        elif g.find(bound) == g.find(cid):
            yield subst
        return
    op, children = pat
    for node in g.classes().get(g.find(cid), ()):
        if node.op != op or len(node.children) != len(children):
            continue
        stack = [subst]
        for sub_pat, sub_cid in zip(children, node.children):
            nxt: list[dict[str, EClassId]] = []
            for s in stack:
                nxt.extend(_match_node(g, sub_pat, sub_cid, s))
            stack = nxt
            if not stack:
                break
        yield from stack


def ematch(g: EGraph, pat: Pattern) -> list[tuple[EClassId, dict[str, EClassId]]]:
    """Every ``(class, substitution)`` where ``pat`` matches."""
    out = []
    for cid in list(g.classes()):
        for s in _match_node(g, pat, cid, {}):
            out.append((cid, s))
    return out


def _instantiate(g: EGraph, pat: Pattern, subst: Mapping[str, EClassId]
                 ) -> EClassId:
    if isinstance(pat, PVar):
        try:
            return g.find(subst[pat.name])
        except KeyError:
            raise KeyError(
                f"rewrite right-hand side uses ?{pat.name}, which its left-hand "
                f"side does not bind; that rule would invent a term") from None
    op, children = pat
    return g.add_node(ENode(op, tuple(_instantiate(g, c, subst)
                                      for c in children)))


# ---------------------------------------------------------------------------
# saturation
# ---------------------------------------------------------------------------
@dataclass
class SaturationReport:
    """Whether it *saturated*, or merely stopped. Not the same thing.

    A run that hit its iteration or node limit has an e-graph representing some
    of the equalities, and extraction from it is a lower bound on what the rules
    could have found. Reporting "done" for both is how a search that ran out of
    budget reads as a search that finished.
    """

    iterations: int = 0
    saturated: bool = False
    stopped_by: str = ""
    applied: dict[str, int] = field(default_factory=dict)
    classes: int = 0
    nodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"iterations": self.iterations, "saturated": self.saturated,
                "stopped_by": self.stopped_by, "applied": dict(self.applied),
                "classes": self.classes, "nodes": self.nodes}


def saturate(g: EGraph, rules: Sequence[Any], *, max_iters: int = 30,
             max_nodes: int = 10_000) -> SaturationReport:
    """Apply every rule everywhere until nothing changes, or a limit bites."""
    report = SaturationReport()
    for i in range(max_iters):
        report.iterations = i + 1
        matches = [(r, ematch(g, r.lhs)) for r in rules]
        changed = False
        for rule, found in matches:
            for cid, subst in found:
                if isinstance(rule, DynRewrite):
                    built = rule.fn(g, subst)
                    if built is None:
                        continue          # a conditional rule declining to fire
                    new = g.add(built)
                else:
                    new = _instantiate(g, rule.rhs, subst)
                if g.merge(cid, new):
                    changed = True
                    report.applied[rule.name] = report.applied.get(rule.name, 0) + 1
        g.rebuild()
        if not changed:
            report.saturated = True
            report.stopped_by = "saturated"
            break
        if g.n_nodes() > max_nodes:
            report.stopped_by = f"node limit {max_nodes}"
            break
    else:
        report.stopped_by = f"iteration limit {max_iters}"
    report.classes, report.nodes = len(g), g.n_nodes()
    return report


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------
def extract(g: EGraph, root: EClassId, *,
            cost: Callable[[Any, Sequence[float]], float] | None = None
            ) -> tuple[Term, float]:
    """The cheapest term in ``root``'s class under ``cost``.

    ``cost(op, child_costs)`` is the whole cost model, and it is a *parameter*
    because the cheapest form depends entirely on what will consume it: fewest
    nodes for a reader, fewest multiplications for a solver, fewest kernel calls
    for a router. A fixed cost function would be an assumption about the
    consumer baked into the optimiser.
    """
    cost = cost or (lambda op, kids: 1.0 + sum(kids))
    classes = g.classes()
    best: dict[EClassId, tuple[float, ENode]] = {}
    for _ in range(len(classes) + 1):
        changed = False
        for cid, nodes in classes.items():
            for node in nodes:
                kid_costs = [best[g.find(c)][0] for c in node.children
                             if g.find(c) in best]
                if len(kid_costs) != len(node.children):
                    continue
                c = cost(node.op, kid_costs)
                cur = best.get(cid)
                if cur is None or c < cur[0]:
                    best[cid] = (c, node)
                    changed = True
        if not changed:
            break
    root = g.find(root)
    if root not in best:                                      # pragma: no cover
        raise ValueError(f"no finite-cost term in class {root}; every e-node in "
                         f"it is cyclic")

    def build(cid: EClassId) -> Term:
        _, node = best[g.find(cid)]
        return (node.op, tuple(build(c) for c in node.children))

    return build(root), best[root][0]
