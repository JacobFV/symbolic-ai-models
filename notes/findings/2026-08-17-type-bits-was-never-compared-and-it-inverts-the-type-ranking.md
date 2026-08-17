---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-17-the-half-bit-is-the-argmax-fit-not-the-hand-formula,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name]
---

# `type_bits` has been in every summary since the beginning and had never been compared, and it inverts the type ranking

`notes/lessons/2026-08-13-a-ranking-is-a-property-of-a-metric.md` was written
because `label_acc` and `label_bits` had both been in every `summary.json` from
the start and only accuracy was ever quoted. The same sentence is true of the
**type** head, and nobody — including me, for nine variants — had checked. The
only prior mention of `type_bits` anywhere in `notes/` is incidental, about a
2×10⁻⁵ difference.

Ranked over 44 rows in `runs/full179`:

| model | type acc | rank | type bits | rank | shift |
|---|---:|---:|---:|---:|---:|
| `corefer-001` | 0.9458 | 1 | **0.3479** | 1 | — |
| `rgt-001` | 0.9154 | 3 | 0.3576 | 3 | — |
| **`gru-001`** | 0.8056 | **31** | **0.7004** | **4** | **+27** |
| `tpr-001` | 0.7896 | 33 | 0.7906 | 6 | +27 |
| `transformer-001` | 0.7787 | 35 | 0.8666 | 10 | +25 |
| `analogy-001` | 0.8110 | 29 | 0.7835 | 5 | +24 |
| `grammar-001` | 0.7984 | 32 | 0.8744 | 11 | +21 |
| `frontier-010` | 0.8666 | **7** | 1.0441 | **24** | **−17** |
| `frontier-008` | 0.8539 | 20 | 1.0789 | 30 | −10 |
| `cart-noop` | 0.8706 | 4 | 0.9993 | 17 | −13 |

**The split is by family.** The neural models are *calibrated and inaccurate* —
`gru` is 31st on accuracy and 4th on bits. The rule-based lines I have been
building all day are the mirror: **accurate and overconfident**. Only
`corefer-001` and `rgt-001` are top on both, and they are exactly the two models
`RESEARCH_LOG.md` records as the only ones with a positive type lift.

This is a correction to my own recent work. I built `frontier-009` and
`frontier-010` to recover the type head, reported "+0.046 lift, best of the
family", and never looked at the other column — where `frontier-010` is 24th of
44 and *worse than the model it was built to improve on* is not true, but worse
than `softreason` (7th–9th), `grammar` (11th) and `gru` (4th) is.

## The mechanism, and it is the one already established

Every type gate in this repo is a **hand formula**. `corefer`'s is
`min(0.15 + 0.8·n/total, 0.95)` over a purity; frontier's is the same shape over
a **Wilson lower bound on precision**, which is a different quantity from the one
the formula was written for.

[[2026-08-17-the-half-bit-is-the-argmax-fit-not-the-hand-formula]] measured that
a hand formula fed something roughly linear in the right quantity leaves ~0.16
bits, and an argmax fit leaves ~0.55. A formula fed a quantity it was not
designed for should sit nearer the larger end.

## `frontier-typemass`: three predictions, all held

| # | predicted | measured |
|---|---|---|
| 1 | `type_bits` below **0.95** from 1.0441 | **0.9342** |
| 2 | `type_acc` moves < 0.01 | 0.8666 → 0.8666, unchanged |
| 3 | every label number **bit-identical** | 0.4414 / 7.141, identical |

Prediction 3 is the control: the label head is untouched, so the row is readable
as the type gate and nothing else. The gain is **0.110 bits**, moving the model
from **24th to 14th** of 44.

## What it does not fix, and this is the honest size of it

`corefer-001` is at **0.3479**. `frontier-typemass` is at 0.9342. Calibration
closed a tenth of a bit; the remaining gap is **0.59 bits and a different order
of thing**. So the overconfidence was real and is now mostly gone, and it was
never the main story — `corefer`'s type head is simply much better, and
`a-ranking-is-a-property-of-a-metric` cuts both ways here: on *this* column the
model I have been improving all day is mid-table, and saying so is the point of
printing it.

**The next question is not calibration.** It is why a backed-off conjunctive
lookup with the pointed-at type as a conjunct reaches 0.35 bits when an induced
rule set with eight guard atoms reaches 0.93 — and that is a question about the
type head's hypothesis language, which is where the label head's story started.
