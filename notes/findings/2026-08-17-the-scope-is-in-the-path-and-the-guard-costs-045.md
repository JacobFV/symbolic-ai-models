---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-binding-story-was-right-for-the-wrong-reason,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-16-four-arms-and-none-of-the-headline-mechanisms-transferred]
---

# `frontier-001` answers 55% of the derived bucket; its own rule answers 100% and the guard is what stops it

The open question from
[[2026-08-17-the-binding-story-was-right-for-the-wrong-reason]] was whether
`frontier-001`'s scope lives in its **guard** (`[slot=1, nsib=4]`) or in its
**path** (`map:sib@2`). Direct ablation of the winning rule, on the 111 derived
non-copyable fills of a four-draw sub-population:

| | acc \| derived, not copyable |
|---|---:|
| the full fitted model | 0.5495 |
| **guard stripped entirely, path and table kept** | **1.0000** |
| table kept, path replaced by a uniformly random visible node | 0.0631 |

**The scope is entirely in the path.** `sib@2` reaches the object's own kind
sibling, which is the object-scoped rung of the premise-selection ladder, and it
answers the bucket perfectly. Replace it with a random premise and the same
table scores 0.063 — below the blind marginal of 0.167 — which is the same
collapse the isolated selection rung shows.

**The guard is pure cost here.** `[slot=1, nsib=4]` fails to match 45% of the
derived positions, and those abstain. The 0.532 published in
[[2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]]
is a *recall* number and the recall is limited by the guard, not by the map.

## The caveat that stops this being an improvement

**A guard-free rule is not better; it is untested.** With an empty guard that
rule fires at *every* hidden node in all 179 lessons, not only the derived ones,
and nothing here measures what that costs on the other 99.8% of positions. The
guard exists to stop the rule firing where it should not. So the correct
statement is that the guard is **miscalibrated for this bucket**, not that guards
are useless, and "strip the guard" is not the fix.

## The mechanism, and it is a property of the search rather than of this rule

The lattice proposes a guard only if its support **among the residual fills**
clears `min_support = 12`. The derived slot is **0.20% of graph positions** —
about 170 of the 86,805 fills the model is fitted on, spread over 11 lessons. A
guard specific enough to pick out the derived positions and nothing else
therefore cannot clear the threshold in any round, so it is never proposed, and
the derivation is absorbed into the coarsest guard that happens to cover part of
it.

Stated generally, because it is not about this rule:

> **Rare structure cannot earn its own hypothesis under an absolute support
> threshold.** The search does not fail to find it; the search is not permitted
> to consider it. The rarer the phenomenon, the coarser the guard it ends up
> living under, and the lower its recall — which reads from the outside as a
> model that partially understands something.

That is a hazard with no guard on it yet, and it applies to every threshold in
this repo that counts occurrences rather than shares.

## What to run next, and what not to conclude

The prediction that follows: the derived-bucket score should **rise** as
`min_support` falls and **fall** as it rises, while the pooled score barely
moves. The RSI loop's round zero is weakly consistent — `min_support=6` had the
second-highest pooled accuracy of seventeen candidates (0.4116 against the
default's 0.4064) — but it never looked at the derived bucket.

**No knob is adopted from that curve.** The derived-bucket measurement runs on
evaluation seeds, so it may be read as a mechanism test with a stated direction
and must not be read as a search for the best value; a value chosen there would
be a value fitted against evaluation, which
`scripts/rsi_loop.py` exists to make impossible elsewhere.
