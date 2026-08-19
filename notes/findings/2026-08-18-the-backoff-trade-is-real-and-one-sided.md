---
title: The back-off trade is real and one-sided — it buys up to +0.030 accuracy and costs 0.04× of a metric capped at 1.49×, and the guard that should have caught the inversion did not fire
date: 2026-08-18
author: lead
status: provisional
tags: [models, cost, instruments, harness, prediction-refuted, control]
---

## The claim under test

`notes/findings/2026-08-18-a-model-can-only-certify-to-the-extent-it-is-usually-right.md`
established `aim = (1 − a_abstained)/(1 − base)` and noted a consequence: the
ceiling `1/(1 − base)` is attained only when abstained positions score **zero**,
so strengthening the structural back-off — which this repo did deliberately, and
which raised accuracy — should *lower* certifiability.

Going in, I talked myself out of that. Turning the back-off **off** lowers
`a_abstained` (numerator up, aim up) *and* lowers `base` (denominator up, aim
down), so I predicted the base effect would dominate and the back-off would win
**both** axes for at least 3 of 4 models.

## Measured

`scripts/backoff_vs_certifiability.py`, four models, the repo's standard config
(`n_train = 20`, all 179 lessons — the same one 612 runs on disk use).

| model | back-off | label_acc | acc\|voted | acc\|abst | **aim** | $/solved>floor |
|---|---|---:|---:|---:|---:|---:|
| **ilp-001** | **on** | **0.312** | 0.475 | 0.059 | 1.37× | **$3.28e-12** |
| ilp-001 | off | 0.291 | 0.477 | 0.001 | **1.41×** | $3.76e-12 |
| **syllogism-001** | **on** | **0.146** | 0.207 | 0.068 | 1.09× | **$1.98e-10** |
| syllogism-001 | off | 0.116 | 0.205 | 0.001 | **1.13×** | **inf** |
| ruleinduce-001 | on | 0.329 | 0.391 | 0.030 | 1.45× | $2.99e-12 |
| ruleinduce-001 | off | 0.329 | 0.397 | 0.003 | 1.49× | $2.98e-12 |
| routes-001 | on/off | 0.323 | 0.329 | 0.000 | 1.48× | $3.08e-12 |

**0 of 4 win both axes; 2 of 4 trade; 2 of 4 are neutral.** My prediction is
refuted and the claim I had talked myself out of was correct.

### And `ruleinduce-001` shows the mechanism exactly

`label_acc` is **identical** to three decimals with the back-off on and off,
because the prior **helps where the model abstains** (0.003 → 0.030) and **hurts
where it votes** (0.397 → 0.391), and at this config the two cancel. The prior is
attached at *every* hidden node, not only abstained ones, which is why it can hurt
a confident vote at all.

## The trade is real and economically one-sided

The back-off buys **+0.021** (ilp) and **+0.030** (syllogism) of label accuracy
and costs **0.04×** of aim — out of a metric **capped at 1.49×** for models this
inaccurate. And for `syllogism-001` the accuracy difference is the difference
between beating its 0.143 floor and **not**: with the back-off off it scores
0.116 and its cost per unit of capability reads `inf`.

> **§3t's consequence is true and irrelevant.** Strengthening the back-off does
> lower certifiability, by 0.04× of a number that cannot exceed 1.49×, while
> buying the difference between a system that beats its floor and one that does
> not. The accuracy column wins decisively, which is what it is for.

## The guard did not fire, and that is the instrument finding

`targeting_regime()` — added two cycles ago precisely to catch "aiming better by
answering worse" — **printed nothing** on this table. It compared the **global**
aim winner against the **global** rate winner, and `ruleinduce-001` off held
both. The inversions here are **pairwise within a model**:

```
ilp-001 bo-off   aim 1.41x   rate 0.2907
ilp-001 bo-on    aim 1.37x   rate 0.3124
```

Strengthened to find **any** inverted pair and report the sharpest. It now says:

```
!! TARGETING REGIME: aim x ranks ilp-001 bo-off (1.41x, rate 0.2907) above
   ilp-001 bo-on (1.37x, rate 0.3124) -- aiming better by answering worse.
   aim x = (1 - a_flagged)/(1 - rate), so anything that lowers the rate raises
   it: relaxing a certificate until it is unsound, or weakening a back-off.
```

That is the **third** strengthening of a ratio guard this session, and the second
found by *using* the instrument on real rows rather than by constructing a
fixture. The message also no longer asserts the certificate story as though it
were the only cause.

## What would refute it

- **Four models, one config.** The effect sizes are small (+0.021, +0.030) and
  two models show nothing at all. A model that leans harder on the prior would
  show a larger trade, and none was sought.
- **`n_train = 20` is the repo's standard**, used by 612 runs, so this is on the
  same footing as everything published — but it is one budget, and the
  docstring's historical claim that the back-off took `ruleinduce` from 0.076 to
  its current score does **not** reproduce here: toggling the flag today moves
  `ruleinduce`'s accuracy by 0.000. Whatever produced that gain, the flag alone
  does not reproduce it, and I did not chase why.
- **Only the label head**, and only escalation as the use of certification.
- **`aim` is capped at 1.49× only because these models are inaccurate.** On a
  system at 0.9 accuracy the same 0.04× loss would sit inside a ceiling of 10×
  and might matter. The one-sidedness is a property of this operating point.

## Reproduce

```bash
uv run python -u scripts/backoff_vs_certifiability.py
uv run pytest tests/test_cost_targeting.py
```

`runs/backoff_vs_certifiability.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `backoff-accuracy-vs-certifiability`.
