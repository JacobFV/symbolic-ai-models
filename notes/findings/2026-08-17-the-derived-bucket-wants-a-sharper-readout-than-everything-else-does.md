---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective,
          2026-08-17-verification-and-diversity-are-in-tension,
          2026-08-17-an-average-cannot-see-a-sub-population,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The sixth candidate found the missing rule, added it, and made the bucket worse

## What the diagnosis was, and it was right

Following the guard from
[[2026-08-17-i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective]] —
locate the discarded thing *before* building a variant — the derived fills
`frontier-001` misses differ from the ones it answers in **exactly one guard
atom**: `nsib=2` against `nsib=4`, with ptype, slot, depth and kids identical.
The derived slot comes in two object layouts and the model has a rule for one.

At `[slot=1, nsib=2]` every surviving rule was `map:sib@0`. What those fills need
is `map:sib@2`, and `keep_per_guard` cannot reach it because those are the **same
form** — the competition that discards the right resolver happens *inside* the
map form, between two paths. That is why `frontier-003` was a null on this
bucket.

`frontier-005` keeps one rule per `(form, path)`. **It works, in the sense that
the rules now exist:** three `map:sib@2` rules at `[slot=1, nsib=2]`, scores
0.858 / 0.797 / 0.703.

## And the bucket got worse

`acc | derived, not copyable`, and I ran the control that separates the two
changes rather than reporting the confounded pair:

| model | readout | `keep_by_path` | treatment | control `-perm` |
|---|---|---|---:|---:|
| `frontier-003` | decision list | no | **0.532** | 0.072 |
| `frontier-soft` | soft vote | no | **0.443** | 0.063 |
| `frontier-005` | soft vote | **yes** | **0.314** | 0.043 |

The readout costs 0.089 and `keep_by_path` costs a further 0.129 on top. Both
harmful, decomposed rather than confounded — which is the one thing I got right
here, having made exactly the opposite mistake this morning on the premise
ladder.

**Sixth candidate, refuted in the opposite direction from the prediction.** I
predicted the extra rule would let the right answer compete. It let more *wrong*
answers compete.

## The measurement that says why, and it is unambiguous

`frontier-005` on the 111 derived non-copyable fills:

| | count |
|---|---:|
| `nsib=4`, argmax right | 33 |
| `nsib=4`, argmax wrong — **truth present in the mass, outvoted** | **28** |
| `nsib=2`, abstained | 50 |

Two separate things, and both matter:

**The vote dilutes a rule that was already right.** On every one of the 28
`nsib=4` failures the correct symbol *is in the conclusion mass* and loses the
argmax to wrong-path maps. Under `frontier-003`'s decision list the single
best-ranked rule fired alone and was right. Adding alternatives added noise, not
information — which is the same fact as
[[2026-08-17-verification-and-diversity-are-in-tension]] seen from the harmful
side: when the verified rules agree, extra voters are redundant; when they
disagree, on this bucket the extras are simply wrong.

**And the `nsib=2` fills still abstain — all 50 of them — although the rule they
need now exists in the model.** So `keep_by_path` put `map:sib@2` into the rule
set and it never fires there. That is a seventh thing to explain and it is
recorded as open rather than guessed at, because guessing is what the last six
candidates were.

## The reading that survives

**The derived bucket wants a sharper readout than every other metric does.** The
pooled numbers prefer the soft vote — `frontier-soft` is 0.384 bits better than
`frontier-003` and slightly more equivariant — and this bucket prefers the
decision list by 0.089. Adding rules helps the pooled score and hurts the bucket.

That is the same shape as the accuracy/bits inversion this repo already knows
([[2026-08-13-a-ranking-is-a-property-of-a-metric]]), one level in: not two
metrics ranking models inversely, but **two sub-populations wanting opposite
readouts from one model**. `frontier-003` remains the best model in the family on
this bucket at 0.532, and nothing built after it has beaten it there.

## Also fixed, and it was a live bug

`_Rule` gained a `tol` slot with the tolerance band, and `rank` read it
directly. A `__slots__` object unpickled from a checkpoint written before the
slot existed simply does not have it, so **every fitted model under `runs/`
raised `AttributeError` the moment anything ranked its rules**. Fitting and
scoring were unaffected; only reopening a published model broke — the same shape
as the `nn.Module._apply` collision, and just as invisible to a sweep. Fixed
with `getattr`, and `tests/test_models.py::test_a_rule_reloads_when_the_class_has_grown_a_slot`
deletes the slot to reproduce it.
