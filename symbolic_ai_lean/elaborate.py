"""Elaboration: a masked term graph becomes a signature, and a hole becomes a
question the kernel can answer.

What this module is for, in one sentence: **given a hole, which symbols of the
episode produce a term that typechecks?** Nothing here scores a candidate; the
kernel says *possible* or *impossible* and the choosing is left to the learned
half, which is the whole shape of the ``006`` line.

The type discipline
-------------------

Types are ``Expr``s, as in Lean, and the object language is first-order.

============  =====================================================
term type     type rule
============  =====================================================
``pred``      ``T[i] = Prop``
``rel``       ``T[i] = Prop``
``node``      ``T[i] = Prop``
``num``       ``T[i] = Nat``
``str``       ``T[i] = Str``; its exploded children are ``Chr``
``char``      ``T[i] = Chr``
``list``      ``T[i] = List α`` and every child is ``α``
``nil``       ``T[i] = List α``
``tuple``     ``T[i] = Tup τ₁ … τₙ`` — arity is part of the type
``record``    ``T[i] = Rec φ₁ … φₙ``
``field``     ``T[i] = Fld "name" τ`` — the name is *in* the type
``ident``     ``T[i]`` is whatever the symbol's declaration says
``token``     as ``ident``
``app``       as a fully applied function over its named arguments
============  =====================================================

and one rule that ties them together: **a symbol has one declaration per
episode**, so every occurrence of ``event`` unifies the argument types of every
other occurrence. That is the only place discrimination can come from — a hole
inherits the type its parent's declaration demands of that slot, and a candidate
brings the type its own occurrences forced on it.

Two further constraints, both of which are typing rules rather than heuristics:

* **Saturation.** The type of a value node is not a ``Pi``. In Lean terms, an
  argument position is inhabited by a value, and ``α → β → Prop`` is a ``Sort``
  rather than a value of one. This is what makes "a binary predicate cannot go
  where a leaf goes" a type error rather than a preference — and it is also,
  measured, the single strongest thing the kernel does, which is why the gate
  reports an **arity-only floor** beside it. A filter that is a disguised arity
  check should be called an arity check.
* **Field names are distinct within a record**, exactly as a Lean ``structure``
  cannot declare one field twice.

Committing, and how far
-----------------------

The interesting knob is what the elaborator does with what it has *not* seen.
Three settings, a ladder from sound to committing:

``open``
    Unsolved metavariables stay unsolved and a candidate the episode never
    declared is unconstrained. This never rejects a filler that has any
    well-typed completion, so it is the sound arm: a rejection here is a proof.
``declared``
    As ``open``, but a candidate with no declaration in the term namespace is
    an *unknown identifier*, which is what real Lean would say. Field names are
    a separate namespace, so this is mostly the rule "a field name is not a
    term".
``closed``
    Every metavariable the visible term witnesses is defaulted to a distinct
    base type before any candidate is tried. The signature becomes rigid and
    unification becomes equality: a filler is possible only if it already
    occurs somewhere the same type is demanded. Strongest, and the one that can
    cut the gold answer out — which is exactly what the pre-registered gold
    survival arm exists to detect.

Nothing here reads a hidden label. The elaboration is built from the visible
nodes alone, and the candidate check is a speculative unification against it,
rolled back afterwards; ``tests/test_lean_elaborate.py`` pins that the verdicts
do not change when the hidden labels are replaced with different ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal, Sequence

from symbolic_ai_core.data.graph import Graph

from .expr import App, Const, Expr, Lit, MVar, Pi, Sort, apps, arrow
from .kernel import MetaCtx, unify, whnf

__all__ = ["Elaboration", "elaborate", "Mode", "NAT", "STR", "CHR", "LIST",
           "TUP", "REC", "FLD", "UNIT", "SYMBOL_TYPES", "FIELD_PARENTS"]

Mode = Literal["open", "declared", "closed"]

NAT = Const("Nat")
STR = Const("Str")
CHR = Const("Chr")
UNIT = Const("Unit")
LIST = Const("List")
TUP = Const("Tup")
REC = Const("Rec")
FLD = Const("Fld")
PROP = Sort(0)

#: Term types whose label names a **constant** — one declaration per episode,
#: shared by every occurrence. ``field`` is deliberately absent: a field name is
#: part of the record's type, not a constant, exactly as in a Lean ``structure``.
SYMBOL_TYPES = frozenset({"pred", "rel", "node", "app", "ident", "token",
                          "num", "str", "char"})

#: A hidden child of one of these is a ``field`` node, so its label is a name
#: rather than a symbol. Knowable without looking at the hidden node.
FIELD_PARENTS = frozenset({"record", "app"})

#: Term types that carry no symbol at all.
STRUCTURAL_TYPES = frozenset({"list", "tuple", "record", "nil"})

_MAX_ROUNDS = 8


@dataclass
class Elaboration:
    """The solved state of one episode's visible term."""

    graph: Graph
    hidden: frozenset[int]
    ctx: MetaCtx
    #: ``T[i]`` — the type of node ``i``, as an ``Expr`` (usually a metavariable).
    T: list[Expr]
    #: The episode's local signature: symbol -> declared type.
    decl: dict[str, Expr]
    #: Names the elaborator gave up on, because two occurrences demanded
    #: incompatible types. Their candidates are unconstrained, which is the
    #: sound direction. Reported, never hidden — this is the coverage number.
    demoted: frozenset[str]
    #: Nodes whose own rule had to be dropped for the same reason.
    untyped: frozenset[int]
    children: list[list[int]]
    mode: Mode
    #: metavariable index -> the value nodes whose type is exactly that meta.
    _meta_nodes: dict[int, list[int]] = field(default_factory=dict)
    #: For a hidden field node, the metavariable standing for its name.
    _name_meta: dict[int, MVar] = field(default_factory=dict)

    # -- what a hole is ---------------------------------------------------
    def is_field_hole(self, i: int) -> bool:
        p = self.graph.parent[i]
        return (0 <= p < len(self.graph) and p not in self.hidden
                and self.graph.types[p] in FIELD_PARENTS)

    def candidate_labels(self, i: int) -> list[str]:
        """Every symbol a copying pointer could reach from node ``i``.

        The same set ``corefer-001`` scores: every **visible** node other than
        ``i``. Nodes carrying no symbol are dropped, which is the conservative
        choice — rejecting the empty label of a ``list`` node is not a
        discrimination win and counting it would flatter the prune rate.
        """
        out: dict[str, None] = {}
        for j in range(len(self.graph)):
            if j == i or j in self.hidden:
                continue
            if self.graph.types[j] in STRUCTURAL_TYPES:
                continue
            if self.graph.labels[j]:
                out.setdefault(self.graph.labels[j], None)
        return list(out)

    def candidate_nodes(self, i: int) -> list[int]:
        """The same set, as nodes — what the pointer actually ranks."""
        return [j for j in range(len(self.graph))
                if j != i and j not in self.hidden
                and self.graph.types[j] not in STRUCTURAL_TYPES
                and self.graph.labels[j]]

    # -- the kernel's verdict ---------------------------------------------
    def accepts(self, i: int, label: str) -> bool:
        """Does filling hole ``i`` with ``label`` produce a term that typechecks?

        Speculative: every assignment made here is rolled back before returning,
        so the elaboration is unchanged and the next candidate sees exactly the
        same state. The cost is one unification against a small type, which is
        what makes ~55 candidates per hole affordable.
        """
        return self.verdict(i, label) == "ok"

    def verdict(self, i: int, label: str) -> str:
        """Why the kernel said what it said.

        ``ok`` | ``undeclared`` | ``mismatch`` | ``saturation`` | ``duplicate
        field`` | ``wrong name``. Reported rather than summed away: a filter
        that prunes 40% by unifying types and one that prunes 40% by refusing
        unknown identifiers are different mechanisms with the same number, and
        only one of them is about types.
        """
        ctx = self.ctx
        mark = ctx.mark()
        try:
            return self._verdict(i, label)
        finally:
            ctx.undo(mark)

    def _verdict(self, i: int, label: str) -> str:
        ctx = self.ctx
        if self.is_field_hole(i):
            # A record's field names are distinct, as in a Lean structure.
            p = self.graph.parent[i]
            for s in self.children[p]:
                if s != i and s not in self.hidden and self.graph.labels[s] == label:
                    return "duplicate field"
            name = self._name_meta.get(i)
            if name is not None and not unify(name, Lit(label), ctx):
                return "wrong name"
            return "ok"

        declared = self.decl.get(label)
        if declared is None:
            # Two different things arrive here and only one of them is an error.
            #
            # A **demoted** symbol was seen and the elaborator gave up on it,
            # because two of its occurrences demanded incompatible types. That
            # is the elaborator having no information, and turning no
            # information into a rejection is unsound. Measured before this
            # branch existed: it was **221 of the 232** gold answers the
            # `declared` arm cut, i.e. almost the whole of that arm's apparent
            # over-rejection, and it would have been read as a fact about the
            # curriculum rather than about this function.
            #
            # A symbol with **no term occurrence at all** is a genuine unknown
            # identifier, which is what real Lean would say — the curriculum's
            # field names are a separate namespace, exactly as a Lean
            # `structure`'s fields are.
            if label in self.demoted:
                return "ok"
            return "ok" if self.mode == "open" else "undeclared"

        want = arrow([self.T[c] for c in self.children[i]], self.T[i])
        if not unify(declared, want, ctx):
            return "mismatch"
        # Saturation: no value node may have acquired a function type. Only
        # nodes whose type metavariable was assigned in this speculative step
        # can have, and the trail is empty until this step begins, so it names
        # exactly those.
        if _is_pi(self.T[i], ctx):
            return "saturation"
        for m in ctx.trail:
            for j in self._meta_nodes.get(m, ()):
                if _is_pi(self.T[j], ctx):
                    return "saturation"
        return "ok"


def _is_pi(e: Expr, ctx: MetaCtx) -> bool:
    return isinstance(whnf(e, ctx), Pi)


# ---------------------------------------------------------------------------
# building the elaboration
# ---------------------------------------------------------------------------
def elaborate(g: Graph, hidden: Iterable[int] = (), *,
              mode: Mode = "open") -> Elaboration:
    """Solve the visible term's types. Never reads a hidden node's label."""
    hidden = frozenset(int(i) for i in hidden)
    n = len(g)
    children: list[list[int]] = [[] for _ in range(n)]
    for i, p in enumerate(g.parent):
        if 0 <= p < n:
            children[p].append(i)

    demoted: set[str] = set()
    untyped: set[int] = set()
    for _ in range(_MAX_ROUNDS):
        ctx = MetaCtx()
        T: list[Expr] = [ctx.fresh() for _ in range(n)]
        decl: dict[str, Expr] = {}
        name_meta: dict[int, MVar] = {}
        bad_symbol, bad_node = _solve(g, hidden, children, ctx, T, decl,
                                      name_meta, demoted, untyped)
        if bad_symbol is None and bad_node is None:
            break
        if bad_symbol is not None:
            demoted.add(bad_symbol)
        if bad_node is not None:
            untyped.add(bad_node)
    else:                                             # pragma: no cover
        pass

    elab = Elaboration(graph=g, hidden=hidden, ctx=ctx, T=T, decl=decl,
                       demoted=frozenset(demoted), untyped=frozenset(untyped),
                       children=children, mode=mode, _name_meta=name_meta)
    if mode == "closed":
        _close(elab)
    # The solved state is the baseline, not something a candidate may undo. With
    # the trail empty, `ctx.trail` after a speculative unification names exactly
    # the metavariables that candidate assigned.
    ctx.trail.clear()
    elab._meta_nodes = _meta_index(elab)
    return elab


def _solve(g: Graph, hidden: frozenset[int], children: list[list[int]],
           ctx: MetaCtx, T: list[Expr], decl: dict[str, Expr],
           name_meta: dict[int, MVar], demoted: set[str],
           untyped: set[int]) -> tuple[str | None, int | None]:
    """One pass of constraint generation. Returns the first thing that failed.

    Failing is not fatal and not a verdict about the episode: two occurrences of
    one symbol demanding incompatible types means the evidence is inconsistent,
    and the sound response is to stop constraining that symbol, not to reject
    every candidate that mentions it.
    """
    def ty(i: int) -> Expr:
        return ctx.fresh() if i in untyped else T[i]

    def eq(a: Expr, b: Expr) -> bool:
        return unify(a, b, ctx)

    for i in range(len(g)):
        if i in untyped:
            continue
        kids = children[i]
        if i in hidden:
            # The only thing knowable about a hole is where it sits. A hidden
            # child of a record or an app is a field node, so its type has the
            # `Fld` shape with the name left open.
            p = g.parent[i]
            if 0 <= p < len(g) and p not in hidden and g.types[p] in FIELD_PARENTS:
                m = ctx.fresh()
                name_meta[i] = m
                child_ty = ty(kids[0]) if kids else UNIT
                if not eq(T[i], apps(FLD, [m, child_ty])):
                    return None, i
            continue

        t, label = g.types[i], g.labels[i]
        own: Expr | None = None
        if t in ("pred", "rel", "node"):
            own = PROP
        elif t == "num":
            own = NAT
        elif t == "str":
            own = STR
            for c in kids:
                if not eq(ty(c), CHR):
                    return None, c
        elif t == "char":
            own = CHR
        elif t == "list":
            a = ctx.fresh()
            if not eq(T[i], App(LIST, a)):
                return None, i
            for c in kids:
                if not eq(ty(c), a):
                    return None, c
            continue
        elif t == "nil":
            if not eq(T[i], App(LIST, ctx.fresh())):
                return None, i
            continue
        elif t == "tuple":
            if not eq(T[i], apps(TUP, [ty(c) for c in kids])):
                return None, i
            continue
        elif t == "record":
            if not eq(T[i], apps(REC, [ty(c) for c in kids])):
                return None, i
            continue
        elif t == "field":
            child_ty = ty(kids[0]) if kids else UNIT
            if not eq(T[i], apps(FLD, [Lit(label), child_ty])):
                return None, i
            continue

        if own is not None and not eq(T[i], own):
            return None, i
        if t in SYMBOL_TYPES and label and label not in demoted:
            want = arrow([ty(c) for c in kids], T[i])
            prev = decl.get(label)
            if prev is None:
                decl[label] = want
            elif not eq(prev, want):
                return label, None

    # Saturation, on the solved state: a value node whose type came out a
    # function type means one symbol was used both saturated and unsaturated.
    for i in range(len(g)):
        if i in hidden or i in untyped or g.types[i] == "field":
            continue
        if _is_pi(T[i], ctx):
            label = g.labels[i]
            if label and g.types[i] in SYMBOL_TYPES and label not in demoted:
                return label, None
            return None, i
    return None, None


def _close(elab: Elaboration) -> None:
    """Default every metavariable the visible term witnesses to its own base type.

    "Witnessed" is load-bearing. A hole whose parent is itself hidden has a type
    nothing visible mentions, and defaulting *that* would reject every candidate
    for no reason — the rigidity has to come from evidence, not from the hole.
    """
    ctx = elab.ctx
    witnesses: list[Expr] = [elab.T[i] for i in range(len(elab.graph))
                             if i not in elab.hidden and i not in elab.untyped]
    witnesses += list(elab.decl.values())
    seen: list[int] = []
    for w in witnesses:
        _collect_metas(w, ctx, seen)
    for k, m in enumerate(seen):
        ctx.bind(m, Const(f"?b{k}"))


def _collect_metas(e: Expr, ctx: MetaCtx, out: list[int],
                   fuel: int = 4_000) -> None:
    stack = [e]
    while stack and fuel > 0:
        fuel -= 1
        x = ctx.deref(stack.pop())
        if isinstance(x, MVar):
            if x.idx not in out:
                out.append(x.idx)
        elif isinstance(x, App):
            stack.append(x.fn)
            stack.append(x.arg)
        elif isinstance(x, (Pi,)):
            stack.append(x.dom)
            stack.append(x.body)


def _meta_index(elab: Elaboration) -> dict[int, list[int]]:
    """Which value nodes' types *are* a given metavariable.

    Used by the saturation check: after a speculative unification only the
    metavariables on the trail can have changed, so this maps them straight to
    the nodes that would have acquired a function type.
    """
    out: dict[int, list[int]] = {}
    for i in range(len(elab.graph)):
        if elab.graph.types[i] == "field" or i in elab.untyped:
            continue
        t = elab.ctx.deref(elab.T[i])
        if isinstance(t, MVar):
            out.setdefault(t.idx, []).append(i)
    return out
