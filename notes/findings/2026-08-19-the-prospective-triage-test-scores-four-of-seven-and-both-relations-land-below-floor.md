---
title: The prospective triage test scores four of seven — and both relations land below their floor
date: 2026-08-19
status: measured
arm: relation-readability
---

The triage statistics were three-for-three on the five relations they were derived
from, which is not a test. `legal_form` and `owned_by` were fetched afterwards,
their statistics computed, and the predictions **recorded in
`notes/autonomy/predictions.jsonl` before any reader was fitted on either**.

| relation | n | containment | lexicon gap | proposal\|cap | positional |
|---|---|---|---|---|---|
| `legal_form` | 1832 | 0.054 | 0.150 | 0.076 | **7.0x** |
| `owned_by` | 1199 | 0.547 | 0.012 | 0.657 | 1.8x |

| relation | arm | correct | floor | **above floor** | k/n |
|---|---|---|---|---|---|
| `legal_form` | capitalised + literal sup. | 0.000 | 0.116 | −0.116 | 0/1832 |
| | phrase + proposer sup. | 0.004 | 0.116 | −0.111 | 8/1832 |
| | **+ induced aliases** | **0.110** | 0.116 | −0.006 | 201/1832 |
| | + position | 0.113 | 0.116 | **−0.003** | 207/1832 |
| `owned_by` | capitalised + literal sup. | 0.036 | 0.060 | −0.024 | 43/1199 |
| | phrase + proposer sup. | 0.054 | 0.060 | −0.006 | 65/1199 |
| | + induced aliases | 0.058 | 0.060 | −0.002 | 70/1199 |
| | + position | 0.058 | 0.060 | **−0.002** | 70/1199 |

## Four of seven

| # | prediction | outcome |
|---|---|---|
| 1 | `legal_form` baseline near 0.00 | **✓** exactly 0.000 |
| 2 | phrase proposer + routed supervision "pays largely" | **✗** 0.000 → 0.004 |
| 3 | aliases pay on `legal_form` (gap 0.150) | **✓** 0.004 → **0.110** |
| 4 | position pays **most of any relation** (7.0x prior) | **✗** +0.003 |
| 5 | aliases ≈ 0 on `owned_by` (gap 0.012) | **✓** +0.004 |
| 6 | position ≈ 0 on `owned_by` (1.8x) | **✓** +0.000 |
| 7 | `owned_by` baseline in 0.10–0.18 | **✗** 0.036–0.058 |

**The statistics predicted *which* lever moves and failed on *how much*.** Every
"this will do nothing" call was right; two of three "this will pay" calls were
wrong about size, and the baseline estimate was wrong by a factor of three.

## And both relations end below their floor

`legal_form`'s best arm is **−0.003 below** a majority-class floor of 0.116;
`owned_by`'s is **−0.002 below** 0.060. Every arm of both, including the ones that
gained a lot, is worse than answering the commonest value.

So the alias gain on `legal_form` — 0.004 → 0.110, the second largest single
improvement in the arm — **buys nothing useful.** It moves a reader from far below
floor to level with it. This is the second time on this corpus that the floor has
changed the meaning of a result and the first time it has cancelled one entirely.

## Why position failed where the statistic was strongest

`legal_form`'s 7.0x positional ratio is the steepest measured, and it bought
+0.003. The ratio is computed on a **containment of 0.054** — the positive base
is 99 articles' worth of sentences, and a ratio over a base that small is not a
prior, it is a small sample. `founder`'s 2.8x rests on containment 0.424 and paid.

**The positional statistic needs a minimum base and did not have one.** That is a
correction to the statistic, not to the method, and it is the kind of thing only a
prospective test finds.

## What survives

- **The negative predictions are reliable.** Three for three: when a statistic
  says an intervention will do nothing, it does nothing. That is genuinely useful
  — it is what stops work being spent.
- **The positive predictions are directionally right and quantitatively poor**, and
  one of them was based on a statistic computed over too small a base.
- **Neither new relation is worth extracting**, which the model-free ceiling said
  in advance for `legal_form`: 0.054 x 0.076 = **0.004** under the capitalised
  proposer. The screening statistic did its job; the reader then failed to clear
  a floor that no statistic in the set predicts.

**The floor should join the triage set.** It costs one line, it is model-free, and
it would have said before any of this that `legal_form` needs 0.116 to be worth
anything.

## What would have refuted the method entirely

`owned_by` responding to aliases or position. It responded to neither, exactly as
its gap of 0.012 and ratio of 1.8x said. The method's discriminative half works;
its predictive half needs the floor and a base-size guard.
