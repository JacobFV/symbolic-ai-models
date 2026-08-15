"""`006`: Lean as the intermediate representation.

The third seam of the repo, opened in
``notes/decisions/2026-08-14-the-ir-is-a-knob.md``. The sibling package
``symbolic_ai_atomspace`` takes the other candidate; the two were chosen to
differ on the axis that matters — **what the representation can refuse**. An
atomspace scores a bad answer low. A kernel rejects it.

A masked node becomes a **hole**, and prediction becomes elaboration: which
fillers produce a term that typechecks? Nothing in this repo has ever had a model
that could say *that answer is impossible for a structural reason*.

Pre-registration, including the gating diagnostic that can close this line in an
afternoon before a model is written:
``notes/decisions/2026-08-14-lean-ir-preregistration.md``. The short version is
that the pointer's constraint is measured to be discrimination rather than
recall — sixteen points of candidate recall bought 0.000 accuracy — so a
typechecker helps only if it prunes candidates *without* pruning the gold one,
and that is one number needing no model.

Real Lean 4 is the outside conformance oracle, run out of band and skipped when
absent. The kernel here is native, small and total, because it runs inside a
sweep and real Lean cannot.
"""

from __future__ import annotations

from .elaborate import Elaboration, elaborate
from .expr import (App, Const, Expr, Lam, Lit, MVar, Pi, Sort, Var, apps,
                   arrow, pretty, spine)
from .kernel import MetaCtx, check, infer, unify, whnf
from .translate import expr_to_graph, graph_to_expr

__all__ = ["Expr", "Sort", "Const", "Lit", "Var", "MVar", "App", "Lam", "Pi",
           "apps", "arrow", "spine", "pretty",
           "MetaCtx", "unify", "whnf", "infer", "check",
           "graph_to_expr", "expr_to_graph", "elaborate", "Elaboration"]
