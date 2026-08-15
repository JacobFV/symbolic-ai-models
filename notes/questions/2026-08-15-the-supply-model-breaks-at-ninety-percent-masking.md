---
date: 2026-08-15
author: lead
status: open
related: [2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-13-slices-have-inverted-results-eight-times]
---

# The supply model predicts the mask-rate curve to 0.005 and then misses by 0.030

`corefer-001`, all 179 lessons, floors refitted at each rate,
`runs/infill-node-r0{15,35,60,90}`.

Hold both conditional accuracies fixed at their `mask_rate=0.15` values
(`acc | copyable` = 0.4936, `acc | not` = 0.0034) and let only the copyable
*share* move. That is the whole model:

    predicted = share * 0.4936 + (1 - share) * 0.0034

| rate | ceiling (= share) | predicted | observed | error |
|---:|---:|---:|---:|---:|
| 0.35 | 0.680 | 0.337 | 0.332 | +0.005 |
| 0.60 | 0.583 | 0.289 | 0.285 | +0.004 |
| **0.90** | **0.302** | **0.151** | **0.181** | **+0.030** |

Two arms at four-thousandths and then a miss six times larger, **in the
direction of the model doing better than pure supply allows.**

## Why this is not being explained yet

The 0.90 split — `acc | copyable` and `acc | not` at that rate — **was never
computed.** The agent that would have computed it hit a session limit. Without
it there are at least two stories with opposite implications:

- **`acc | copyable` rises.** At 90% masking the surviving visible nodes are the
  ones that were easiest to point at anyway, so the copyable bucket gets easier
  through selection. This would be a *survivorship* effect and would make 0.90
  the least informative point on the curve rather than the most.
- **`acc | not` finally becomes non-zero.** With almost everything hidden, the
  back-off and the structural prior carry more of the mixture, and some of what
  they supply lands. This would be the harness contributing, not the model —
  and it is the shape of
  `notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md`.

A third possibility is that the *floor* moved: it drops 0.143 -> 0.126 across the
curve, and the supply model says nothing about the floor.

**These have opposite implications and this repo has been burned before by
explaining a number it had not decomposed.** Left open deliberately.

## What would answer it

**Correction to this note's own first draft, which said "one command".** It is
not. `scripts/copyable_split.py` reloads `model.pt` to reproduce
`evaluate_model`'s draw, and the run directories keep `summary.json` and
`rules.txt` but **not the weights** — deliberately, since *"Keep the evidence,
drop the weights"*. So the 0.90 arm has to be **re-fitted** before it can be
split, which is a real run rather than a rescore. The refuter hit the same wall
on the 0.15 arm and re-ran it from scratch into `runs/refute-node-r015`, where
all twelve summaries came back bit-identical — so the re-fit is known to be
faithful, just not free.

Refit the 0.90 arm, split it, then extend the table in
`notes/findings/2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability.md`
and either close this note or promote whichever story it turns out to be.

Worth doing before anyone cites the mask-rate curve as evidence that ability is
flat, because at the extreme it demonstrably is not.
