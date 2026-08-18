---
title: There is no universal inference language — each kernel gets a projection, and the projection records what it discarded
date: 2026-08-18
status: decided
tags: [architecture, kernels, logic, datalog, asp, smt, lean]
---

## The fork

Having settled that the world IR is universal-ish (see
`2026-08-18-flow-is-a-dag-the-world-is-not.md`), the obvious next question is
*which logic*. Symbolic AI has spent forty years asking it. The answer taken here
is that the question is wrong:

> **Logic is a computational representation selected for the structure of the
> subproblem.** The world IR is universal-ish; inference languages are
> kernel-specific *projections* of it.

Concretely, instead of

```
universal IR == one logic language
```

we build

```
                   ┌─> datalog projection ──> semi-naive fixed point
                   ├─> asp projection ──────> clingo
world_ir ──────────├─> smt projection ──────> z3
                   ├─> lean projection ─────> lean
                   ├─> egraph projection ───> equality saturation
                   └─> physics projection ──> rigid body / geo / ...
```

with two typed maps per kernel:

- **P_K : World → L_K** — the projection into the kernel's language.
- **R_K : L_K → WorldDelta** — the result translated back as claims and a delta.

## The one thing that makes this honest: the projection declares its losses

A projection is lossy by construction. An ASP projection of a world containing a
covariance matrix and continuous rigid-body geometry cannot represent either, and
the failure mode is not that it crashes — it is that it *silently proceeds*, and
the answer comes back looking like an answer about the whole world.

So `P_K` returns a **`Projection`**, not just a program: the kernel-language
text, the entity/claim ids it covered, and a **discard record** naming what it
dropped and why. `R_K` may only assert deltas over what was covered. A claim
whose support was discarded is not a claim the kernel is entitled to make, and
the runtime can say so rather than the reader having to notice.

This is the same discipline as the licence closure one layer down: the thing that
was not established has to stay visible, because the alternative is a result that
is wrong in the flattering direction.

## Inference semantics is metadata, not convention

Once several kernels coexist, the same textual rule means different things. `not p`
is at least four different world states:

1. a proof of ¬p;
2. an inability to prove p;
3. p's probability below a threshold;
4. p's absence from a database.

Classical, intuitionistic, open-world, closed-world, monotonic, non-monotonic,
defeasible, probabilistic, temporal, modal, causal, constraint — a claim or rule
carries which one it was asserted under, and a projection into a kernel with
incompatible semantics is a **refusal**, not a best effort. This is the logical
analogue of the unit and coordinate-frame checks the flow layer already makes,
and it fails in exactly the same silent way when it is left to convention.

## The stack, and what each tier is actually for

| tier | kernel | the thing it is unusually good at |
|---|---|---|
| 0 | lookup, unification, traversal, pattern match, term rewrite | native primitives, already here |
| 1 | **datalog** | huge relational closure, incremental maintenance |
| 2 | **ASP** (clingo) | defaults, exceptions, non-monotonic reasoning, world completion, planning |
| 3 | **SMT** (z3) | arithmetic + logic + arrays, constraint satisfaction |
| 4 | **Lean** | exact typed mathematics, machine-checked proof |
| 5 | e-graphs | equality saturation, choosing the cheapest equivalent form |
| 6 | rigid body, geo, economy | specialised worlds behind narrow contracts |
| 7 | omegaclaw, learned models, LMs | heuristic cognition |

Two of these change how the whole system is shaped.

**Datalog is the workhorse, and it is the least glamorous entry on the list.**
If a world holds millions of relations and rules like
`ancestor(x,z) :- parent(x,y), ancestor(y,z)`, you do not want a proof assistant
proving each query — you want a database engine doing `D_{t+1} = T_P(D_t)` to
closure, and then *incrementally maintaining* it: a `WorldDelta` arrives, five
facts change, and the affected consequences update rather than the world being
re-derived. That maps exactly onto the delta-and-claims contract the kernel ABI
already has, and it is the reason datalog is built first and natively rather than
being the fourth external toolchain.

**The exploratory reasoner does not need to be sound; the verifier does.**

```
omegaclaw / ASP / search / LM
        ↓  candidate derivation
     Lean / SMT
        ↓  proof, or refutation
```

Lean is the court of final appeal for exact claims and is priced accordingly. It
is a terrible tool for *china probably responds negatively*, and asking it to be
one is how formalisation effort eats a research programme.

**ASP is ranked above Lean for actual agent cognition**, which is the ranking
this note most expects to be argued with. The argument for it: reality here
contains incomplete information, defaults, exceptions, mutually exclusive
hypotheses and combinatorial constraints, and `flies(X) :- bird(X), not
abnormal(X)` is closer to commonsense than classical monotonic theorem proving.
More usefully, ASP natively solves **world completion** — find assignments to the
unknown parts of a partial symbolic world satisfying these rules — which is
already the shape of this repo's central task. Missing scene nodes, missing
claims, hypothetical outcomes, scheduling and planning are all that problem.

## Cyc: import the lessons, not the runtime

Cyc's *representational* architecture is the most relevant prior art for
`world_ir`: predicates of arbitrary arity, nested propositions, contextualisation
via microtheories, and an ontology built to represent commonsense reality rather
than to fit into triples. `holds_during(2026, controls(government_x, territory_y))`
is exactly the shape the claim type has to carry, and Cyc's own critique of
triple-only representation is the argument this repo's world IR is built on.

But CycL is not adopted as the internal representation, and Cyc is not a
dependency. It accumulated decades of ontology-specific machinery; importing the
conceptual lessons is cheap and inheriting the runtime is not. Its terms of
service also prohibit automated bulk access, so "download Cyc" was never an
adapter strategy — it is an `access: query_only_or_licensed` source if it is
anything.

## What was rejected

- **One universal logic.** Named above; this note exists to refuse it.
- **A probabilistic logic as the foundational uncertainty representation.**
  ProbLog, MLNs and PSL are worth study, but different kernels natively produce a
  probability, a confidence, an interval, a distribution, a covariance, a
  possibility set, a hard constraint, a proof, or nothing. The `Claim`
  abstraction has to be broader than any one of those, and the runtime routes
  compatible uncertainty objects to compatible kernels.
- **An external toolchain in the hot path.** Standing rule in `ROADMAP.md`, and
  it holds: clingo, z3 and Lean are all optional, and a kernel whose toolchain is
  absent **refuses loudly**. It does not silently fall back to a weaker kernel,
  because a fallback is how a broken component reads as a working one.
- **Building all seven at once.** Datalog is native and first, because it needs
  no dependency, it is the highest-volume path, and it is the one whose
  incremental form matches the delta contract.

## What would show this was wrong

If, after the first multi-kernel task, the projections turn out to be where all
the complexity went — if `P_K` for two kernels is longer than either kernel — then
the world IR is at the wrong altitude and should have been closer to one of the
kernel languages. The countable version: total lines in `symbolic_ai_kernels/*/
project.py` exceeding the kernels themselves.
