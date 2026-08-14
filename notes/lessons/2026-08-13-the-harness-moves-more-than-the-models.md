---
date: 2026-08-13
author: lead
status: measured
related: [2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# Models span 0.1 lift; the shared substrate spans 0.15 to 2.0

When a number moves a lot, the first hypothesis is that the contract changed —
not that the reasoning improved. This is the list to check, because "suspect the
harness" is useless without one.

- **`structural_fallback`** — a memorising component every rule-based model
  inherits. Worth +0.019 to `vsa-002` and **all** of its renaming sensitivity
  (+0.029 with, +0.002 without). It **flipped the sign** of the language-
  conditioning effect: `lang − ctx` is +0.0052 with it and −0.0027 without. For
  the *reaching* VSA variants it is negative — it was compensating for a
  retrieval that could not find anything.
- **`symbol_backoff` gets a structural `context_prior` and `type_backoff` does
  not**, so an abstaining model falls to the *global* type marginal. `corefer`
  abstaining on type cost **−1.950** type lift.
- **A shared calibrator priced the type head with the label head's confidence** —
  **−1.96 type lift, on three models at once.** One mistake in a base class is
  every subclass wrong simultaneously: the cost of sharing, and the mirror image
  of its benefit.
- **The tokenizer silently deleted underscores.** `'foo_bar_baz'` → `'foobarbaz'`.
  Nine of 85 answer strings were **unreachable by any model**, so `exact_match`
  on those lessons was pinned at zero for reasons unrelated to any model.
- **The agents floor fitted its reference policies differently from the scored
  agent** (one environment and no seed, versus four and `cfg.seed`). A reference
  policy beat *itself* by 0.025, and that was the only positive number in the
  table.
- **`cmd_sweep` silently ignored its config's `out`**, so every configless sweep
  landed in `runs/sweep` where `--resume` could skip models on another run's
  summaries.

**The general shape:** a shared component is invisible precisely because it is
shared — it moves every row together, so nothing looks anomalous. Attribute a
gain to a model only after checking what the substrate contributed, and report
model numbers **with and without** the shared floor where one exists.
