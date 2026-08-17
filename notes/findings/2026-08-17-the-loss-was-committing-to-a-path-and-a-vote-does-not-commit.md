---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-pointer-lifts-the-ceiling-past-corefer-and-the-constraint-moves-to-selection,
          2026-08-17-verification-and-diversity-are-in-tension,
          2026-08-17-the-derived-bucket-wants-a-sharper-readout-than-everything-else-does,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The selection loss was committing to a path, and a vote does not commit — the first frontier row that is top-ten on bits

The pointer moved the constraint from representation to selection. Decomposing
`frontier-point` on the 1,985 renamed copyable fills **where the answer is
reachable** says exactly which part of selection:

| | share |
|---|---:|
| right | 0.6463 |
| **fired on a path that does not hold the answer** | **0.2902** |
| right path, resolver wrong | 0.0635 |
| **no rule fired** | **0.0000** |

It never abstains, and the resolver is almost never the problem. **Nearly all the
loss is first-match-wins committing to one path when another matching rule reads
the one that holds the answer.** A vote does not commit.

## `frontier-pointsoft`

| | `frontier-point` | **`frontier-pointsoft`** | `corefer-001` |
|---|---:|---:|---:|
| `label_acc` | 0.4460 | 0.4372 | 0.3572 |
| **`label_bits`** | 7.092 | **6.457** | 6.955 |
| `type_acc` | 0.8760 | 0.8760 | 0.9458 |
| renamed pooled | 0.2480 | **0.2670** | 0.3499 |
| **renamed `acc \| copyable`** | 0.340 | **0.371** | 0.492 |

And the decomposition moved exactly where the prediction said it would:

| | `frontier-point` | `frontier-pointsoft` |
|---|---:|---:|
| right | 0.6463 | **0.6907** |
| committed wrong / outvoted | **0.2902** | **0.2413** |
| resolver wrong / truth never voted for | 0.0635 | 0.0680 |

+0.044 into "right", −0.049 out of "committed to the wrong path", and the third
category unmoved. That is the mechanism claimed, and not a general improvement
wearing its name.

## The bits result is the largest of the day and was not the point

**7.092 → 6.457.** That is **7th of 46** on `label_bits`, and every model above it
scores between 0.169 and 0.319 on accuracy where this scores **0.437**:

| | acc | bits |
|---|---:|---:|
| `grammar-001` | 0.187 | 6.089 |
| `softreason-onehop` | 0.319 | 6.148 |
| `rgt-001` | 0.241 | 6.182 |
| … | | |
| **`frontier-pointsoft`** | **0.437** | **6.457** |

So it is the first row here that is strong on both columns at once, which
`a-ranking-is-a-property-of-a-metric` has spent this whole repo saying is not how
these models behave. Worth stating plainly: **that was not what the experiment was
for.** It was aimed at renamed copyable accuracy, predicted +0.03 there, and got
it; the 0.635 bits came along and is the larger number.

## The predicted cost, stated in advance

The soft readout was measured *worse* on the derived bucket (0.532 → 0.443)
because it dilutes a rule that is right, and the pre-registration said to expect
roughly that again here. Two populations, opposite preferences — the derived
bucket wants a sharper readout and the copyable bucket wants a softer one, which
is
[[2026-08-17-the-derived-bucket-wants-a-sharper-readout-than-everything-else-does]]
restated with the pointer underneath it.

## What is next, and it is now a weighting problem

On **24.1%** of reachable fills the truth **is** in the vote set and loses. That
is not coverage and not representation — the right symbol is proposed and
outweighed. `vote_sharpness` is the knob, and its curve was measured flat on bits
*before the pointer existed*, on a model whose rules mostly agreed. With eleven
paths and a pointer the vote set is genuinely diverse for the first time, so that
curve is worth re-running and the earlier flat reading should not be assumed to
carry over.
