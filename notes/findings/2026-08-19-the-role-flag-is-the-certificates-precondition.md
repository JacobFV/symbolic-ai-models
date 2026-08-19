---
title: The role flag is the certificate's precondition, not an independent check
date: 2026-08-19
status: measured
arm: role-enumeration
---

## The improvement that should have worked

The role flag refuses whenever the lone-region assignment is unforced — **29
refusals to remove 3 errors**, ten times more conservative than the failure. The
obvious fix is to stop treating *unforced* as *unsafe*: emit the candidate
assignments and refuse only when they **disagree on the answer**.

The candidate set is small — the unresolved regions, typically two — so it costs
**1.19 solves per case** on average.

| policy | answers | coverage | wrong | accuracy |
|---|---:|---:|---:|---:|
| answer everything | 252 | 1.000 | 81 | 0.679 |
| role flag (refuse unforced) | 223 | 0.885 | 75 | 0.664 |
| role **enumeration** | 237 | 0.940 | 78 | 0.671 |
| **flag + certificate** | 120 | 0.476 | **0** | **1.0000** |
| **enumeration + certificate** | 130 | 0.516 | **1** | 0.9923 |

**48% of unforced assignments are inert** — the ambiguity is real and does not
change the answer — so the flag was indeed throwing away coverage for nothing,
and enumeration recovers it: 0.476 → 0.516 paired.

**And the pair stops being sound.**

## Why, and it is structural

Seed 83. `needs` is read correctly, the true assignment **is** among the three
candidates, and all three agree — on the wrong answer. The error is the **phantom
link**, which every candidate shares.

That is the certificate's job. It returned `True` anyway, because it was computed
on the collapsed world where `depot = region_1`:

> **`certifies_insensitive` reads the roles to build its graph.** It checks
> whether depot and site stay connected in each qualifying vehicle's admissible
> subgraph. With the wrong depot, it answers that question about the wrong
> graph.

So the two detectors are **not independent**. The role flag's over-conservatism
is exactly what guarantees the certificate is asked about the right graph. It is a
**precondition**, not a second opinion.

This corrects last finding's remark that coverage is "roughly the product of the
two, so they are close to independent". The *numbers* multiply — 0.885 × 0.556 =
0.492 against 0.476 observed — and the *logic* does not.

## What follows

Enumeration is **measured and rejected**, with the reason recorded rather than
the number alone. Keeping the flag costs 4 points of coverage (0.516 → 0.476) and
buys the property the whole policy exists for.

More usefully, it names a rule for the pipeline: **a check that reads part of the
world inherits that part's errors.** The certificate consumes the roles, so it
cannot validate them; anything downstream of a reader can only certify what it
does not itself depend on.

That is the same shape as the grounding scope result — `ungrounded` builds its
admissible edges from the flow's own output, so it cannot catch reader errors —
and it is the third time this pipeline has produced it. Worth stating as a
property of layered checks rather than as three separate surprises.

## What would refute this

- A certificate that did not consume the roles — one arguing insensitivity over
  *all* role assignments at once. That would be independent of the flag and
  could replace it, and it is the version worth building if coverage ever
  matters more than the 4 points at stake here.
- 0 wrong in 120 still bounds the pair's error at 2.5%, not zero. Nothing here
  changes that.
