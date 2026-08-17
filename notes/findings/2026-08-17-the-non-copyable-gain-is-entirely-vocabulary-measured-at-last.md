---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-15-a-floor-outside-the-models-hypothesis-class,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-17-composing-two-winners-from-two-metrics-gives-a-loser-on-a-third]
---

# Crossing the renaming test with the copyable split: the non-copyable gain is entirely vocabulary, and the equivariance difference is entirely in the *other* bucket

This repo has run two instruments separately since the beginning. The **renaming
check** is pooled — one accuracy over every fill. The **copyable split** is run
only on the original episodes. So the question the whole `frontier` line raises —
*is 0.325 on the non-copyable bucket reasoning or vocabulary?* — has never been
asked directly, although `RESEARCH_LOG.md`'s theorem implies the answer.

`scripts/copyable_split.py --renamed` crosses them.

## The table

`runs/full179`, 5,233 fills, copyable share 0.722, same draw the runs published:

| model | `acc\|cp` | `acc\|not` | **renamed `acc\|cp`** | **renamed `acc\|not`** |
|---|---:|---:|---:|---:|
| `frontier-floortype` | 0.495 | **0.325** | **0.055** | **0.003** |
| `frontier-typepoint` | 0.490 | **0.314** | **0.306** | **0.003** |
| `frontier-nomap` | 0.381 | 0.073 | 0.317 | 0.000 |
| `corefer-001` | 0.494 | 0.003 | 0.492 | 0.000 |
| floor (structure only) | 0.158 | 0.106 | **0.002** | **0.003** |

## Two things, and the first was predicted by the repo years of notes ago

**1. The non-copyable gain is entirely vocabulary.** `frontier`'s 0.325 → **0.003**,
which is the *renamed floor*. Every model lands at 0.000–0.003 there. This is
`RESEARCH_LOG.md`'s claim — *naming a symbol that no visible node carries requires
storing symbol identities across episodes* — measured directly for the first
time rather than argued from the pooled column. It is a confirmation, not a
discovery, and it is worth having because the alternative reading (that
`frontier` had found some structural route to the non-copyable quarter) was live
and is now closed.

The renamed **floor** is the other half of the same point: a memorising lookup
goes 0.1432 → **0.0022** pooled. Nothing in that bucket survives a permutation,
model or floor.

**2. The equivariance difference between the `frontier` variants lives entirely
in the copyable bucket, and that was not predicted.** `frontier-floortype` and
`frontier-typepoint` differ only in `keep_by_path` and `keep_per_guard`. Their
renamed pooled accuracies are 0.047 and 0.221 — and the non-copyable halves are
*identical* at 0.003. The whole 0.174 is:

| renamed `acc \| copyable` | |
|---|---:|
| `frontier-floortype` | **0.055** |
| `frontier-typepoint` | **0.306** |
| `frontier-nomap` | 0.317 |
| `corefer-001` | 0.492 |

So keeping more than one rule per guard does not buy any *reasoning* that
survives renaming. It buys back the model's ability to **point** — the copy rules
that a map otherwise crowds out — and pointing is exactly the renaming-invariant
operation. `frontier-floortype` at 0.055 has almost no pointer left; `corefer`, a
pointer and nothing else, is at 0.492 and barely moves.

That reframes the trade measured in
[[2026-08-17-composing-two-winners-from-two-metrics-gives-a-loser-on-a-third]].
It is not "equivariance for accuracy". It is **"how much of the copy head
survives having a map head bolted on"**, and the answer for the floor-only
configuration is: almost none of it.

## What this does not say

It does not say the maps are worthless — they are what takes the derivability
channel, and 0.325 against a 0.106 floor on the original episodes is a real score
on the original vocabulary. It says that score is *about this vocabulary*, which
is what the renaming column is for and what the model's own docstring has claimed
since it was written. The novelty here is the **per-bucket** crossing, not the
direction.

`grammar-001` could not be included: its checkpoint imports
`symbolic_ai_models.models.grammar`, a module path that no longer exists, so it
cannot be loaded at all. That is a separate and unrelated rot worth a note of its
own.
