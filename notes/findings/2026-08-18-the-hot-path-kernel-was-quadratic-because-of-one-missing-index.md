---
title: The hot-path kernel was quadratic for want of one index — 122x faster, and the full 124k-edge closure went from an extrapolated 55 minutes to 6.5 seconds
date: 2026-08-18
status: provisional
tags: [datalog, performance, engine, real-data]
---

## The defect

Yesterday's proof-trace work measured the datalog engine against a
purpose-written closure over the same GLEIF data and found it **495x slower at
250 edges and 5,446x slower at 4,000** — an overhead that *grows*, which is the
signature of wrong asymptotics rather than a slow constant.

The cause was one line. `_index` keyed facts by **predicate only**, so
`ult(X,Z) :- par(X,Y), ult(Y,Z)` bound `Y` from the first literal and then
rescanned **every** `ult` fact to find the ones starting with it. Quadratic work
for linear output, in the kernel the architecture calls "the hot-path relational
workhorse".

## Prediction

An index on argument position would take the 4,000-edge solve from 3,448 ms to
**~100 ms (≈35x)** and turn the quadratic scaling **near-linear**.

## What I found

`FactIndex` now carries `(predicate, position, value)` buckets alongside the
predicate index, and the join picks the **most selective bound position** rather
than the first — so a rule joining on a high-cardinality column beats one
joining on a flag.

| edges | before | after | speedup |
|---|---|---|---|
| 250 | 14.6 ms | 1.3 ms | 11x |
| 500 | 55.1 ms | 3.2 ms | 17x |
| 1,000 | 214.4 ms | 4.9 ms | 44x |
| 2,000 | 854.2 ms | 10.8 ms | 79x |
| 4,000 | 3,448 ms | **28.3 ms** | **122x** |
| 16,000 | — | 336 ms | — |
| 64,000 | — | 2,184 ms | — |
| **124,460 (all of it)** | — | **6,843 ms** | — |

**122x, against a predicted 35x** — under-called, and the speedup grows with
size exactly as an asymptotic fix should.

The capability that matters is the last row. The **full** GLEIF ownership
closure — 124,460 edges, 287,084 derived facts — now runs in under seven
seconds. Extrapolating the old quadratic from 4,000 edges puts it near **55
minutes**, which is why it had never been run.

**The scaling prediction was only half right.** Measured exponent went from
n^2.0 to **n^1.5**, not to linear. The residue is that `_index` is rebuilt over
all known facts every round, so the cost is `rounds x |known| x arity` and the
round count creeps up as chains get deeper. Incremental index maintenance is the
next fix and I am not claiming linear until it is measured.

## How I know it is still correct

An engine optimisation is the change an existing suite polices worst: every test
still passes if the join silently drops a branch, because the tests were written
against programs whose answers the author already believed. So:

- **A naive oracle.** `tests/test_datalog_index.py` carries its own evaluator —
  T_P to a fixed point by brute-force enumeration over all constants,
  exponential and obviously correct — and 25 generated programs (recursion,
  cycles, self-loops, stratified negation) must give byte-identical models.
- **A cross-check at full scale.** Running the closure over all 124,460 edges
  and comparing to the purpose-written walk: **117,123 agree, 0 disagree, 6
  cyclic** — and those 6 are exactly the ownership cycles found independently
  days ago. No entity has more than one parentless ancestor.

Two implementations that share no code agree on 117,123 real cases.

## One visible semantic consequence, and it is not a bug

Candidate ordering changes, so a fact reachable by several derivations may now
be justified by a *different* one of them. The least model is identical — the
oracle proves that — and `proof.py` records one witness per fact, any valid one
being as good. It is written down because a future reader diffing two
derivation trees across this commit would otherwise think something broke.

## What this does not change

No published number moves. `ultimate_parent`'s 0.9785, the fusion result and the
alignment work all used the purpose-written closure, not this engine; the
engine's only appearance in a finding was as the **denominator** in yesterday's
verification ratio, which was already reported against the purpose-written
closure for exactly this reason.

That was luck bought by a habit: yesterday's lesson said to put the best
available alternative in the denominator. Had I not, today's commit would have
invalidated a headline.
