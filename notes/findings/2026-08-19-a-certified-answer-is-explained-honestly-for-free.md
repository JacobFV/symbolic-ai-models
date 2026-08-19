---
title: A certified answer is explained honestly, for free
date: 2026-08-19
status: measured
arm: certified-explanations
---

## Two threads that had never met

Certification buys **soundness**: 0 wrong at 48.8% coverage on flood's honest
surface. Explanation fidelity was measured separately: 0.378 of complete
explanations contain a falsehood, 70% of them link citations. Nobody had asked
whether they are the same cases.

300 seeds, honest surface, complete renderer:

| population | share | accuracy | **any false citation** | **link citations** | citations |
|---|---:|---:|---:|---:|---:|
| all | 1.000 | 0.673 | 0.378 | 0.48 | 11.56 |
| **certified** | 0.469 | **1.000** | **0.022** | **0.00** | 10.88 |
| not certified | 0.531 | 0.385 | **0.692** | 0.91 | 12.16 |

**A certified answer cites no link at all, and its explanation contains a
falsehood 17× less often** — 0.022 against 0.378, from the same check, with no
extra work.

## The alignment is structural, not a coincidence

`certifies_insensitive` holds when **no single link deletion changes the answer**.
`render_complete` cites the **load-bearing** set — the claims whose deletion
*would* change it. On a certified case those sets cannot overlap on links, so a
certified explanation has none to get wrong.

That the two agree was the refutation condition, and it did not fire: if certified
explanations had gone on citing links at the same rate, `load_bearing_cheap` and
`certifies_insensitive` would have been disagreeing about what the answer depends
on, and this repo ships them as complementary.

The residual **0.022** is the role channel — three cases in 141 where a wrong
depot certifies. `certifies_role_independent` requires every candidate assignment
to certify, which covers most of that channel and not all of it, which is exactly
what the earlier measurement said.

## What it does to the price

`break_even_wrong_cost` put flood's certificate at **W = 0.60**: a wrong answer
must cost 0.6 of a right one before refusing pays. That priced **soundness only**.
The same refusal also removes 94% of the explanation's falsehoods, so any weight at
all on the explanation being true lowers the threshold. The certificate is
cheaper than it was priced.

That is the useful shape of the result: two properties this repo treats as
separate — *is the answer right* and *is the account of it true* — turn out to be
bought by one check, because both are questions about **what the answer depends
on**.

## What would refute this

- One domain, one certificate, one renderer. The alignment follows from
  `load_bearing_cheap` and `certifies_insensitive` being defined over the same
  perturbation; a certificate defined over a different one would not align.
- The 0.022 residual is three cases. The bound on it is wide.
- Coverage is 0.469, so this says nothing about the other half of the cases,
  where the explanation is wrong 69% of the time and there is no check.
