---
title: False containment refuted — `owned_by` is the most classifier-bound relation measured, and `legal_form` is genuinely unreadable
date: 2026-08-19
status: measured
arm: relation-readability
---

Two relations resisted every model-free screen. `legal_form` was **correctly
rejected** by `containment < floor`. `owned_by` **passed every screen and failed
anyway**, and the explanation offered was **false containment** — the gold string
(`BlackRock`, `The Vanguard Group`) appearing for reasons other than ownership.
That explanation was labelled as untested. An **oracle classifier** tests it: it
bypasses the classifier entirely, so what it reaches is what the containing
sentences can actually yield.

| relation | learned | **oracle classifier** | floor | oracle/learned |
|---|---|---|---|---|
| `parent` | 0.150 | 0.406 | 0.010 | 2.7x |
| `country` | 0.192 | 0.455 | 0.298 | 2.4x |
| `headquarters` | 0.223 | 0.439 | 0.045 | 2.0x |
| `founder` | 0.107 | 0.262 | 0.006 | 2.4x |
| `industry` | 0.029 | 0.165 | 0.061 | 5.7x |
| **`owned_by`** | **0.006** | **0.300** | 0.060 | **51.4x** |
| **`legal_form`** | **0.000** | **0.034** | **0.116** | — |

## `owned_by`: false containment is wrong

Its oracle reaches **0.300** — comparable to `parent`'s 0.406 and
`headquarters`' 0.439, and **five times its floor**. The sentences containing
`BlackRock` do state the ownership relation often enough to answer three in ten
articles. **The relation is there.**

What fails is the classifier, and it fails harder than anywhere else measured:
a **51x** gap between what a perfect sentence decision would reach and what the
learned one does. Every other relation sits at 2.0x–5.7x.

So the last unexplained failure is not a corpus property at all — it is the same
classifier bound as everywhere else, at an extreme. **The hypothesis this note
was written to test is refuted**, and the honest replacement is duller: nothing
about `owned_by` is special except how badly the classifier does on it.

## `legal_form`: genuinely unreadable, and the screen was right for the right reason

Its oracle is **0.034**, against a floor of **0.116**. Even a *perfect* sentence
classifier, reading every sentence that contains the gold, loses to answering
*joint-stock company* every time.

The model-free screen rejected it on `containment 0.050 < floor 0.116`. The
oracle now confirms the rejection was correct **and** that it was correct for the
stated reason rather than by luck: the ceiling really is below the floor.

## What this changes

- **There is no separate "false containment" failure mode** on this corpus. Two
  relations that looked unexplained are one genuinely-unreadable relation and one
  extreme case of the bound already known.
- **The classifier bound is now measured on seven relations**, 2.0x to 51.4x,
  and is the binding factor in all of them.
- The model-free screen keeps its exact status: it proved one relation impossible
  and correctly stayed silent on one that a better classifier could read.

## An honest confound

The learned column here fits with **all seven relations competing** in distant
supervision, so a sentence naming both a parent and an owner is labelled for
whichever gold string is longer. `owned_by` reads 0.006 here against **0.058** in
the two-relation run. The oracle is unaffected — it does not use the classifier —
so the 51.4x is an upper bound on the gap and the direction is not in doubt, but
the exact multiple is inflated by competition this table introduced.

## What would have refuted the conclusion

`owned_by`'s oracle landing near its learned rate, or below its floor. It lands at
0.300, five times the floor and in the same band as the relations that work.
