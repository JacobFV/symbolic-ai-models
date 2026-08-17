---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-an-average-cannot-see-a-sub-population,
          2026-08-16-a-soft-consequence-fixpoint-buys-bits-and-the-iteration-costs-them,
          2026-08-16-first-on-accuracy-eleventh-on-bits,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# A verified rule set is a bad ensemble by construction: half its fills have nothing to disagree about

Combining the two live findings of the week — SoftReason's transferable part
(emit the conclusion mass, not an argmax) and `frontier-003`'s (keep the
renaming-invariant rules) — and then finding out why the combination stops where
it does.

`runs/full179`, same config and seeds as every published row:

| model | lbl acc | **lbl bits** | renamed | drop | type |
|---|---:|---:|---:|---:|---:|
| `frontier-001` | 0.4042 | 7.433 | 0.0345 | 0.3716 | 0.8633 |
| `frontier-003` | 0.4040 | 7.445 | 0.2149 | 0.1906 | 0.8607 |
| `frontier-004` | 0.4009 | 7.464 | 0.2198 | 0.1823 | 0.8491 |
| **`frontier-soft`** | 0.3986 | **7.061** | **0.2218** | 0.1795 | 0.8607 |
| `softreason-onehop` | 0.3193 | **6.148** | 0.3139 | 0.0041 | 0.8482 |
| `corefer-001` | 0.3572 | 6.952 | 0.3499 | 0.0032 | 0.9458 |

## `frontier-004`: the tolerance band did what it said, and it is a small knob

Rank is precision-first, so a `map` ahead of a `copy` by a few thousandths takes
every fill they share — and under a permutation 1,031 of `frontier-001`'s map
rules still fire (the permutation lands symbols on other symbols the table
holds) at **9.4% correct**. A band inside which precisions count as equal lets
the description-length tie-break, which prefers the `copy`, decide.

Pre-registered: renamed rises, plain accuracy falls. **Both held**, monotonically,
on the development split:

| `rank_tolerance` | acc | renamed |
|---:|---:|---:|
| 0.00 | 0.4080 | 0.2112 |
| 0.02 | 0.4034 | 0.2145 |
| 0.05 | 0.4020 | 0.2169 |
| 0.10 | 0.3955 | 0.2184 |

+0.007 of equivariance for −0.013 of accuracy. Real, directional, and small.
`keep_per_guard` was worth 0.18 for 0.0002; this is a hundredth of that. Also
worth recording: `keep_per_guard=1` reproduces `frontier-001` exactly (0.4064 /
0.0320) and `keep_per_guard=2` is identical to 3, so two forms is the whole
effect.

## `frontier-soft`: the readout is worth 0.384 bits and no more

Same induction, same rules, same cross-fit — only the readout. Every matching
rule votes, weighted by what it verified at, instead of the top-ranked one
firing alone.

**Predicted:** bits improve substantially; accuracy moves little either way.
Measured: **7.445 → 7.061**, accuracy −0.0054, and renamed improved too
(0.2149 → 0.2218), which was not predicted. So the decision-list readout was
*part* of what put `frontier` eleventh of twenty-four on bits — and only part.
7.061 is still nowhere near `softreason-onehop`'s 6.148.

## Why it stops there, and this is the reusable half

If the readout were the constraint, flattening the vote should buy more bits.
The `vote_sharpness` curve on the development split, ranked by bits:

| sharpness | acc | bits |
|---:|---:|---:|
| 0.5 | 0.3883 | 6.984 |
| 1.0 | 0.3909 | 6.982 |
| 2.0 | 0.3957 | 6.972 |
| 4.0 | 0.4009 | 6.959 |
| 8.0 | — | best of the six |

**Flat across a sixteen-fold range, and sharper is slightly better.** Flattening
costs 0.013 of accuracy and buys nothing. So the gain came from *several rules
voting at all* rather than from how the mass is spread.

The measurement that explains it — over 2,287 fills where any rule voted:

| distinct symbols proposed by the voting rules | share |
|---:|---:|
| **1** | **0.527** |
| 2 | 0.180 |
| 3 | 0.149 |
| 4+ | 0.144 |

Mean top-share of the mass **0.808**, **median 1.0000**. On more than half the
fills every rule that fires proposes the *same symbol*. There is nothing to be
unsure between, and no readout can manufacture uncertainty that the hypothesis
set does not contain.

> **Verification and diversity are in tension.** A cross-fitted verifier keeps
> rules that agree with the data, and rules that agree with the data agree with
> each other. So a verified rule set is a poor ensemble *by construction* — the
> better the verification, the more its members converge, and the less a
> distribution readout can pay.

That is the same shape as `ensemble-001`, from the other side: that ensemble paid
1.14 bits and the only diversity available was "one member memorises the
vocabulary". Here the diversity is not available at all, because the selection
procedure removed it.

## What this predicts, and what would refute it

If the diagnosis is right, `frontier-soft`'s bits should improve when rules are
kept *because they disagree* rather than only because they verify — an explicit
diversity term in the ranking, which nothing here has. If a diversity term does
**not** move bits, the diagnosis is wrong and the 6.15 gap is about what
`softreason`'s closure computes rather than about how many conclusions it holds.

**Caveat on the whole table.** `frontier-soft` is better than `frontier-003` on
bits and renamed and worse on accuracy, so which is "best" is a choice of metric,
which is the standing lesson here and not a tiebreak this note gets to make.
