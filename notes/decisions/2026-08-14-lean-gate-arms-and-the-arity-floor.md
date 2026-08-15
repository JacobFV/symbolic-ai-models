---
date: 2026-08-14
author: agent-lean-006
status: provisional
related: [2026-08-14-lean-ir-preregistration, 2026-08-14-the-ir-is-a-knob,
          2026-08-13-a-control-that-could-fail,
          2026-08-13-slices-have-inverted-results-eight-times]
---

# The gate has three arms and a floor, and all four are fixed before the full run

An addendum to `2026-08-14-lean-ir-preregistration.md`, written **before** the
179-lesson diagnostic and after the kernel was built. It moves no threshold. The
pre-registered table stands exactly as written:

| prune rate | gold survival | verdict |
|---|---|---|
| < ~30% | any | the line is dead |
| high | < ~95% | worse than dead |
| high | high | build the model |

What the pre-registration could not fix in advance, because it was written
before the type discipline existed, is **which filter the table is applied to**.
Building the kernel turned up one knob that spans the entire prune/survival
trade-off, and the honest response is to fix the arms now rather than to pick
the flattering point afterwards.

## The knob: what the elaborator does with what it has not seen

All three arms share one type discipline (`symbolic_ai_lean/elaborate.py`).
They differ only in how much they commit to the visible evidence.

| arm | unsolved metavariables | a candidate the episode never declared |
|---|---|---|
| `open` | stay open, unify freely | possible |
| `declared` | stay open | **unknown identifier** — rejected |
| `closed` | defaulted to distinct base types | rejected |

`open` is the sound arm: a rejection is a proof that no well-typed completion
exists. `declared` is what real Lean would say — an undeclared constant is an
error, and the curriculum's field names live in a different namespace from its
term constants, so this is mostly the rule "a field name is not a term".
`closed` commits hardest: the signature becomes rigid, unification becomes
equality, and a filler is possible only if it already occurs somewhere the same
type is demanded.

**The verdict table is applied to each arm separately**, and the line opens if
*any* arm clears both thresholds. Reporting only the best arm would be picking a
point after seeing the number, so all three go in the table with their controls.

## The floor, and why the line does not get to skip it

The strongest single rule in the kernel is **saturation** — the type of a value
node is not a `Pi`, so a binary predicate cannot go where a leaf goes. That is a
real typing rule, and it is also, in effect, an arity check.

So the diagnostic reports an **arity floor**: reject a candidate iff no visible
occurrence of it has the hole's number of children. No types, no unification, no
Lean, and it is computable by any of the nineteen models already in the sweep.

> **If the kernel does not beat the arity floor, the kernel *is* the arity floor,
> and the finding is that the Lean IR is an arity check with Lean branding.**

`notes/lessons/2026-08-13-a-control-that-could-fail.md` is the reason: a control
of the same shape as the real thing, but meaningless, corrected four separate
published results here. This one is not meaningless — it is the cheapest thing
that could produce the same number, which is the more dangerous kind.

Two more controls, both fixed now:

- **`shifted`** — the kernel run against a *different hole of the same episode*.
  Same episode, same signature, same cardinality, wrong question. Gold survival
  must fall to the matched-random level. If it does not, the prune rate is a
  property of the candidate set and not of the hole.
- **`matched random`** — the gold survival of a filter that keeps the same
  *number* of labels, chosen meaninglessly. A kernel that prunes 60% and
  survives 60% has done nothing at all.

And one asserted as a test rather than a number: **renaming invariance**. Rename
every symbol consistently and every verdict must be identical, symbol for
symbol. `ensemble-001`'s 1.14-bit headline died to that control (0.467 → 0.038).

## What I expect, written down before the number

- `open`: prune 0.30–0.45, gold survival above 0.99. Dominated by saturation.
- `declared`: prune 0.45–0.55, gold survival 0.92–0.97 — the risk is a gold whose
  only visible occurrence is a field name.
- `closed`: prune 0.70–0.85, gold survival 0.70–0.85. Too committing.
- **The arity floor within 0.05 of `open`.** This is the prediction I most
  expect to be embarrassed by and it is the one that decides what the line is.
- Cost: far inside the budget. The check is one unification against a small type
  with a rollback trail, not a re-elaboration.

## Disclosure: a 20-lesson slice was run first, and it is not evidence

While debugging the harness I ran the diagnostic over the first 20 lessons at
`n=2` — 352 holes. It is written down here because it exists and because this
repo's rule is that a slice may form a hypothesis and may never be reported as
one; hiding it would be worse than declaring it. It said `open` 0.291/0.996,
`declared` 0.416/0.928, `closed` 0.795/0.719, arity floor 0.367/0.992 — i.e. no
arm clearing both thresholds, and the arity floor *out-pruning* the sound arm.

**Slices have inverted results ten times in this repo**, and 20 lessons is 11%
of the curriculum, so that reading has no standing. The full run decides. What
the slice legitimately buys is the prediction above, and the commitment that if
the full run says the same thing, the answer is the null and not a search for a
fourth arm.
