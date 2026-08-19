---
title: Soundness costs 13× per correct answer, and discards only wrong ones
date: 2026-08-19
status: measured
arm: price-of-soundness
---

## Why price it at all

The honest milestone reports the collapsing reader at 0.500 on the non-empty
population, answering everything and unable to say which half is wrong. The
carrying policy reaches **soundness 1.000** — never wrong when it answers — but
it runs `k + 1` solves per case where the collapsing reader runs one.

*"Soundness 1.000"* quoted without a price is the same error as *"grounded
1.000"* quoted without a scope, and this thread has already made that one.

## The trade

34 non-empty cases, V=4, interleaved, `hard_distractors=True`:

| policy | answers | correct | soundness | $ total | $/correct |
|---|---:|---:|---:|---:|---:|
| collapse | 34 | **20** | — | 2.70e-07 | 1.35e-08 |
| carry, answer if agreed | 20 | **20** | **1.000** | 4.26e-06 | 2.11e-07 |
| carry, early exit | 20 | **20** | **1.000** | 3.63e-06 | 1.81e-07 |

**Soundness costs 15.6× per correct answer, or 13.4× with early exit.**

## It discards only wrong answers

Collapse is right **20 of 34**. Carry is right **20 of 20**. The *same twenty
correct answers* — every case it refuses is one the collapsing reader would have
got wrong.

That is why the $/correct multiple equals the compute multiple exactly: the
numerator does not move. The policy is free in *answers* and costs 15.6× in
*compute*.

This is stronger than "sound at some coverage cost", which is the normal shape,
and it is a property of this population rather than a theorem —
`test_it_discards_only_wrong_answers` pins it so a future surface that breaks it
announces itself.

## Early exit is exact, and buys less than it looks like it should

One disagreement settles a case as undecided, so every later candidate is spend
on an answer already known not to be given. Stopping there is **exact** — the
decided set is unchanged, which a test asserts — and it moves mean solves from
**16.0 to 13.7**, a 14% saving rather than the near-halving the undecided share
(14/34) might suggest.

The reason: on an undecided case the disagreement usually appears **late**. Most
single-link deletions are inert — measured deletion dependency 0.243 — so the
enumeration works through many harmless candidates before reaching the one that
matters. **Cheap-to-refute cases are not the common case; the load-bearing claim
is a needle.**

An ordering heuristic that tried high-dependency claims first would do better,
and the audit's `deletion_dependency` is exactly the number to order by. Untried.

## What this buys the programme

A system arguing that its reasoning is inspectable rather than inferred should be
able to say what inspectability costs. Here it is **13.4× per correct answer**,
and what it buys is the ability never to be wrong when it speaks — on a surface
where the alternative is right half the time with no signal.

Whether that is worth paying is a question about the application, not about the
system, and it can now be asked with a number attached.

## What would refute this

- A surface where refusal drops correct answers as well as wrong ones. The 20/20
  identity is measured, not proven, and the test names it as the fragile half.
- A cheaper sound policy. Early exit is the obvious one and it buys 14%; ordering
  candidates by measured deletion dependency is the next, and would help exactly
  to the extent that dependency is unevenly distributed across claims of a kind —
  which the `(1−d)ⁿ` work suggests it is.
