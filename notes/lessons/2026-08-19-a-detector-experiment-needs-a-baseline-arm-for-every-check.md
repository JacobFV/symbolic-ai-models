---
title: A detector experiment needs a baseline arm for every check
date: 2026-08-19
status: lesson
---

## Four measurement traps in one experiment

Testing whether any check catches **task drift** — a claim kind the reader has no
branch for — I hit four separate ways of measuring the wrong thing, each of which
produced a confident wrong answer before being caught.

**1. The "task change" was not one.** The first version added a *curfew* closing a
region to all traffic. That has the same sentence signature as a flooding report,
and elimination defaults unresolved lone regions to `flooded`, so the reader
landed on the right semantics by accident: **0 of 16 answers wrong.** A task
change must be **inexpressible in the existing world**, or it is a rephrasing.

**2. Firing counted as catching.** With 0 wrong answers, every check that fired
was raising a *false alarm*, and the script reported those as catches.
**A check catches nothing on a case the system got right.**

**3. No baseline arm.** With a real task change, `omits_load_bearing` caught
"22 of 22" — but an earlier finding had measured it firing on **every**
template-rendered paragraph regardless of drift. Its raw rate carries zero
information. **A check signals drift only if it fires more with the drift than
without**, and that needs the clean arm run alongside.

**4. The detector compared unlike things.** `unconsumed` read the
paragraph-structured original and compared it against sentence-joined variants.
`read_content_roles` picks its network paragraph by content, so every world
differed for an unrelated reason and **nothing ever looked unconsumed** — the
detector reported 0/22 while working correctly.

## The guard

**Run the clean arm for every check, not just the treatment.** Three of the four
traps above are the same shape: a number that means nothing without the
counterfactual beside it. Firing rates, catch rates and detector counts are all
differences, and reporting the treatment alone invites reading a baseline as a
result.

And for a detector specifically: **construct the failure so it is inexpressible
in the representation under test.** If the existing machinery can represent the
new thing, the experiment measures the machinery's luck.

## Related

- [[2026-08-19-maintenance-is-the-fourth-thing-the-audit-predicts]] — the same
  turn measured repaired code and reported the damage as zero.
- The exactness audit's rule, *state the bound not the number*, is the same
  instinct applied to sample size rather than to baselines.
