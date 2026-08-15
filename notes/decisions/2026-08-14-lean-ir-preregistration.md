---
date: 2026-08-14
author: lead
status: provisional
related: [2026-08-14-the-ir-is-a-knob,
          2026-08-14-atomspace-metta-ir-preregistration,
          2026-08-13-abstention-on-repair-is-below-chance]
---

# `006`: Lean as the IR — pre-registration, and the one diagnostic that gates it

Written **before any of it is built**. Unlike `005`, this line has a cheap
measurement that can kill it in an afternoon, and that measurement comes first.

## The idea in one line

Render the curriculum's term graph as a **typed Lean term**, make a masked node a
**hole**, and let the typechecker say which candidate fillers are even possible.
Prediction stops being "score 8,192 symbols" and becomes **elaboration**.

Nothing in this repo has ever had a model that can say *that answer is
impossible for a structural reason*. Every model here scores every candidate and
picks the best; a kernel rejects.

## The gating diagnostic, and it runs before any model is built

The pointer's constraint is measured and it is **discrimination, not recall**:

| top_k | stage-1 recall (train) | dev copy accuracy |
|---:|---:|---:|
| 10 | 82.7% | 0.4036 |
| 20 | 93.1% | 0.4043 |
| 40 | 98.7% | 0.4012 |

Sixteen points of recall bought 0.000. Every candidate added gets found by stage
two and then not chosen. The median masked node has **55 candidates**.

So the only way a typechecker helps is if it **removes candidates without
removing the right one**. That is one number, and it needs no model:

> For each masked node, of the candidates that the current pointer considers, how
> many produce a term that typechecks — and is the gold answer among them?

Two quantities, both on **held-out training episodes**, eval untouched:

- **prune rate** — median share of the 55 rejected by the kernel;
- **gold survival** — how often the true filler typechecks.

Pre-registered reading, fixed now:

| prune rate | gold survival | verdict |
|---|---|---|
| < ~30% | any | **the line is dead.** The signature is too weak to discriminate and the IR is a re-encoding with no filter. Write the null and close it. |
| high | < ~95% | **worse than dead.** The kernel is cutting the right answer out. Abstention on this repo's tasks scores *below chance* on `repair`, so a filter that over-rejects is negative value, not neutral. |
| high | high | **the first mechanism anyone has proposed that attacks discrimination.** Build the model. |

That table is the whole reason to prefer `006` over more pointer features: five
candidate-level features in a row have failed, and every one of them added
*evidence*. This adds a *constraint*, which is a different move.

## What gets built, if the gate opens

`symbolic_ai_ir/lean.py`, native:

- **`Expr`** — `Sort | Const | Var | App | Lam | Pi`, plus a small inductive
  signature for the curriculum's node types (`pred`, `rel`, `app`, `record`,
  `field`, `list`, `tuple`, `num`, `str`, `ident`, `char`).
- **A typechecker** over that signature. Small, total, and tested — this is the
  component the whole line rests on, so it gets adversarial tests before it gets
  a model.
- **`graph_to_expr` / `expr_to_graph`**, the identity over **all 179 lessons**.
- **Models `lean-006`, …**, beside every existing row.

Real Lean 4 is the **outside conformance oracle** — emit `.lean` source, run
`lean` on it when a toolchain exists, assert agreement with our kernel, skip
otherwise. Same shape as WALS: the value of an oracle is that we did not write
it. It never runs inside a sweep.

## The trap this line walks straight into, named in advance

**The type head becomes correct by construction, and that is not a result.**
`type_acc` has a floor of 0.860 because node type is nearly determined by tree
shape. Under an elaborator the type of a hole is *derived*, not predicted — so a
`type_acc` near 1.000 measures that we implemented a typechecker, not that
anything reasoned.

This is exactly the mistake `symbolic_ai_parsers` already made and had to
retract: the tree alignment made every aligned node's head correct by
construction, and UAS came out 0.95 for a parser that did no parsing. So:

**`006` is scored on the label head.** `type_acc` under the Lean IR is asserted
as a test and never quoted as a lift. If anything about it is reported, it is
reported as "how many nodes the elaborator could type at all", which is a
coverage number.

## What would refute the line

- **The gating diagnostic fails**, on either arm above. Cheapest possible death,
  which is why it is first.
- **The round trip is not the identity on all 179 lessons.**
- **Pruning helps recall and not accuracy.** The measured pattern is that
  candidate-set changes do not move this pointer. If a kernel that removes half
  the candidates *also* moves accuracy by 0.000, then discrimination is not about
  the candidate set at all and that is a genuinely new and useful thing to know —
  worth a note either way.
- **Cost.** Typechecking 55 candidates per masked node, over 2,632 scored fills,
  inside a CPU budget of ~200k tok/s. If the kernel is the bottleneck the line
  can still be right and unaffordable, and both have to be said. Price it on the
  inner loop, as `scripts/vsa_dim_curve.py` does.

## What stays learned

The kernel says which fillers are *possible*; it does not say which is *meant*,
and typically several will typecheck. So the `vsa-003/004` extract/re-insert pair
does the choosing, over a candidate set the kernel has already filtered — which
is the same two-stage shape as `corefer`, with a sound filter where `corefer` has
a learned stage-one score.

That comparison is the cleanest experiment the line offers, and it is worth
naming now: **`corefer`'s stage one is a learned generator at 82.7% recall; the
kernel is a sound filter at whatever the diagnostic says.** Swapping one for the
other, holding stage two fixed, is a controlled measurement of "learned candidate
generation" against "derived candidate constraint".
