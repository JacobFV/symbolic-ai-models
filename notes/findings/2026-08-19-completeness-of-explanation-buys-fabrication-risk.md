---
title: Completeness of explanation buys fabrication risk
date: 2026-08-19
status: measured
arm: honest-explanations
---

## Inspectability, checked on the honest surface for the first time

`ungrounded` already carries the scope note: it certifies consistency with the
world **as read**, not truth. On the honest surface — where the reader admits a
phantom link on every case — an explanation can therefore cite a claim that is
**false** and pass every check this repo has. Nobody had measured how often.

300 seeds, flood, interleaved. Each answer is rendered from the **read** world and
every `claim:` citation is checked against the **true** one.

| renderer | surface | acc | cites | **false / citation** | any false | **\| correct** | \| wrong | `ungrounded` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| template | clean | 0.985 | 2.01 | 0.0025 | 0.005 | **0.000** | 0.333 | **0.000** |
| template | honest | 0.673 | 2.01 | 0.0025 | 0.005 | **0.000** | 0.016 | **0.000** |
| complete | clean | 0.985 | 11.74 | 0.0117 | 0.066 | 0.052 | 1.000 | **0.000** |
| **complete** | **honest** | 0.673 | 11.56 | **0.0388** | **0.378** | **0.076** | 1.000 | **0.000** |

## Three readings

**A correct answer with a fabricated justification, at 1 in 13.** The complete
renderer cites at least one false fact on **7.6%** of the answers it got
**right**. That is the failure mode a symbolic pipeline is supposed to be immune
to, and it is here.

**It is not a volume effect.** Per citation the complete renderer is **15.5×**
worse on the honest surface — 0.0388 against the template's 0.0025 — because the
extra facts it cites are the **load-bearing set computed from the read world**,
which is exactly where a phantom link lives. Citing more is not the problem;
citing *what the answer depends on* is, when the answer depends on something
invented.

**The template renderer's honesty is surface-independent.** 0.0025 per citation
on both surfaces, and **0.000** fabrication on correct answers in both. It cites
the demand and the site, and the reader gets those right whatever the distractors
do.

And **`ungrounded` flags 0.000 of it**, in every cell. That is its scope note with
a number attached: a check built on the read world cannot see what the reader
invented — the sixth appearance of *a check that reads part of the world inherits
that part's errors*.

## What this does to the earlier finding

*"An explanation that omits nothing material, for 37% more words"* priced
completeness in **length**. That was the wrong currency. The price is **truth**:
0.005 → 0.378 explanations containing a falsehood, and 0.000 → 0.076 on correct
answers.

Whether that trade is worth taking is a caller's decision, as the original note
said — but it can now be stated as one. A two-fact summary that is never wrong
about its two facts, against an eleven-fact account that is wrong somewhere in
one of three.

## A defect found in passing

The renderer's citation scheme is **not uniform**: some sources are a claim index
(`claim:7`) and some are a predicate name (`claim:needs`, `claim:flooded`). A
checker has to resolve both, and a citation that cannot be resolved to a claim
cannot be checked against anything. Recorded rather than fixed, because fixing it
would move every citation offset in the published numbers.

## What would refute this

- One domain and one distractor family. The phantom link is what makes the
  load-bearing set false; a domain whose reader errs on *values* rather than on
  *structure* might fabricate less while being just as wrong.
- The check credits a citation as true if an identical claim exists in the true
  world. A citation that is true but *irrelevant* counts as honest here.
- `claim:needs` and `claim:flooded` are resolved from the cited text; a renderer
  change that cites something other than an entity id there would silently stop
  being checked.
