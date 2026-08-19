---
title: The invisible error is certifiable, even though it is undetectable
date: 2026-08-19
status: measured
arm: scheduling-capability-certificate
---

## Correcting this morning's headline

*"The detectable error is the harmless one"* measured that scheduling's
`has_capability` channel is the worst of the day — one admitted sentence costs
**0.210** accuracy with **all 42** failures in the unsound direction — and that
every detector fires **0.000** on it, because the role is multi-valued and
nothing corroborates it. I concluded that a multi-valued channel leaves only
fixing the reader.

**That was too strong.** Detection needs a second reading of the same fact.
**Insensitivity does not** — it needs only that the answer can be shown not to
depend on the claim, which is exactly what flood's link certificate and
solvency's membership certificate do. I built it for solvency's `owns` this
afternoon and never pointed it at the channel that actually hurts.

## Measured, 200 cases, default regime

| surface | acc | false FEASIBLE | coverage | acc \| cert | wrong \| cert | cover \| feasible | solves | ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| clean | 1.000 | 0 | 0.665 | 1.000 | 0 | 0.056 | 1.80 | 2.28 |
| **hard machine** | 0.790 | **42** | **0.525** | **1.000** | **0** | 0.159 | 3.07 | 3.42 |

**Answering everything gives 0.790 with 42 silent unsound answers. Certifying
gives 1.000 among the certified, 0 unsound, at 52.5% coverage.** Every one of the
42 is refused, because each is feasible *only* through the spurious capability,
so deleting that one flips it.

**43.5% of the coverage is free.** Deleting a `has_capability` can only make an
instance *more* infeasible, so an **infeasible** reading cannot have been caused
by a spurious capability — certified with no extra solve. That is the monotone
half, and it is the half that was already known to transfer to scheduling; the
structural half was measured unsound on 8 of the 9 instances it fired on.

## It is sound, lossy, and the loss is the interesting number

Coverage among **feasible** readings is **0.056** on the clean surface. At slack
0.15 with six jobs and three machines, almost every capability is load-bearing,
so a genuinely feasible instance rarely survives deleting each one in turn. The
certificate is very nearly *"infeasible ⇒ certified"* plus a sliver.

And that sliver **rises to 0.159 on the corrupt surface** — because the spurious
capability *adds redundancy*, giving some job a second capable machine, so
deleting a real capability no longer breaks feasibility. Third instance today of
a certificate looking more confident where the reader is less reliable. Here it
does **not** cost soundness, because the corruption is inside the hypothesis the
check enumerates and the deletion of that one claim is among the tests. That is
the distinction the earlier two cases lacked, and it is worth keeping: **apparent
stability created by a channel the certificate covers is real; created by one it
does not, it is an illusion.**

## The price, in the repo's idiom

Solves per case 1.00 → **3.07**; correct answers 158 → 105. **Price of soundness
4.62×**, against flood's 13.4× before its certificate and 1.0× after.

And it is a case the north star does not reward: `usd_per_solved_above_floor`
counts answers, so refusing 47.5% of them makes the row **worse** however sound it
is. `cost.py`'s own docstring names this gap — *"prices getting the answer right
and prices knowing you are right at zero"* — and this is the cleanest instance of
it yet. Whether 4.62× for soundness is worth paying depends on what a wrong answer
costs, which is a caller's decision and not a property of the system.

## What would refute this

- The hypothesis is **at most one spurious capability**. Two break the argument
  and are untested; the distractor injects exactly one.
- Conditional on the rest of the reading. It says nothing about a spurious
  `needs_capability`, a wrong duration or a wrong capacity — the fifth appearance
  of *a check that reads part of the world inherits that part's errors*, stated
  on the function rather than left to the name.
- Coverage is measured at the default regime. At `HARD_REGIME`, slack 0 and 20
  jobs, capabilities are tighter and the feasible-side coverage should fall
  further, while each certificate costs 20 solves at 17.5 ms. Unmeasured.
