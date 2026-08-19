---
title: Bootstrapping beats the knowledge base for two rounds — a 210-article seed exceeds full distant supervision
date: 2026-08-19
status: measured
arm: bootstrap
---

The bottleneck pricing ended on the case it could not cover: *"a relation nobody
has curated is exactly as expensive as it was in 1984, and this reader has no way
to acquire one."* The classical answer is **bootstrapping** — seed, extract, keep
what you are confident about, refit. This runs it, and the caveat needs revising.

A **10% seed** of the training articles keeps its distant labels; the other 1,892
are treated as unlabelled. Each round the reader reads the unlabelled pool, its
200 most confident extractions become pseudo-labels, and it refits. Logistic
model, so confidence is a probability. Three splits, because a single seed draw
is a single draw. `runs/bootstrap_relation.json`.

## Two rounds beat the knowledge base, on every split

Held-out `parent` accuracy, 292 articles with gold:

| arm | split 31 | split 32 | split 33 | **mean** |
|---|---|---|---|---|
| full distant supervision, 2,102 articles | 0.144 | 0.096 | 0.111 | **0.117** |
| seed only, 210 articles | 0.110 | 0.106 | 0.062 | 0.093 |
| bootstrap round 1 | 0.161 | 0.121 | 0.111 | 0.131 |
| **bootstrap round 2** | **0.175** | **0.163** | **0.142** | **0.160** |
| bootstrap round 3 | 0.154 | 0.131 | 0.170 | 0.152 |
| bootstrap round 4 | 0.144 | 0.131 | 0.142 | 0.139 |

**Round 2 exceeds full distant supervision on all three splits** — +37% relative
on the mean (0.160 against 0.117), from a tenth of the labels plus 400
self-generated ones.

**Predicted semantic drift below the seed by round three. Refuted.** Drift
arrives, but late and mildly: rounds 3 and 4 fall back to 0.152 and 0.139, which
is still above both the seed and the ceiling. Nothing in this run goes below
seed-only.

## How strong the claim is

Per split, round 2 against the ceiling is z = 1.30, 2.32 and 1.14 — one
significant, two not. **The direction is 3/3**, which is a sign test at p = 0.125
on its own. So: a large effect, replicated in direction on every split, and
individually significant on one. That is worth acting on and not worth quoting to
three decimals.

## Why it can beat its own supervision

Distant supervision labels **every sentence containing the gold string**, and most
of those sentences do not state the relation — the ceiling is trained on gold
answers attached to indiscriminate evidence. A pseudo-label attaches the reader's
*own confident answer* to the sentences that produced it, which sharpens the
boundary it already has rather than fighting noise. Self-training here is acting
as a **label denoiser**, not as a data multiplier.

That resolves a tension with an earlier arm. **Multi-instance pruning made things
worse** (0.101 → 0.042) by keeping one sentence per article: it attacked the same
noise by *deleting* data. Self-training attacks it by *adding* self-consistent
data. Same diagnosis, opposite interventions, opposite outcomes — and the
difference is that one removes evidence and the other removes disagreement.

## What this changes

**The pricing finding's caveat is too strong.** A relation nobody has curated is
not "exactly as expensive as 1984"; it costs a **seed of about 200 articles**,
after which self-training reaches — and here exceeds — what a full knowledge base
would have supplied. The bottleneck moved from rules to labels, and this says the
label requirement is a couple of hundred examples rather than a KB.

Two things it does not say:

- **It does not remove the ceiling.** Everything here is between 0.09 and 0.18
  against hand-written patterns at 0.393. Bootstrapping changes what supervision
  costs, not what the reader can do.
- **It does not run past round four**, and the decay from round 2 is real. A
  longer run is the obvious next measurement and the shape suggests it keeps
  falling.

## Eight rounds, and no way to know when to stop

The obvious next measurement, run: eight rounds instead of four, with three
**unsupervised** signals recorded alongside — because the case bootstrapping is
*for* is a relation nobody curated, and that case has no held-out gold to peek at.

| round | held-out accuracy | mean belief | coverage | churn |
|---|---|---|---|---|
| 1 | 0.131 | 0.989 | 0.330 | 0.000 |
| **2** | **0.160** | 0.998 | 0.492 | 0.171 |
| 3 | 0.152 | 0.998 | 0.758 | 0.194 |
| 4 | 0.139 | **1.000** | 0.794 | **0.291** |
| 5 | 0.147 | 0.997 | 0.699 | 0.266 |
| 6 | 0.146 | 0.994 | 0.722 | 0.228 |
| 7 | 0.130 | 0.992 | 0.773 | 0.226 |
| 8 | 0.120 | 0.961 | 0.711 | 0.202 |

**None of the three finds the peak.**

- **Mean belief is saturated from round one** — 0.989 rising to 1.000 — and is
  *highest at round 4*, where accuracy is at a local minimum. Self-training
  inflates confidence regardless of correctness, which is exactly what it should
  be expected to do and exactly why it cannot supervise itself. It also destroys
  the calibration the logistic model was chosen for: a probability that is 0.99
  for everything is a margin again.
- **Coverage** rises and plateaus. No peak.
- **Churn** peaks at round **4**, two rounds after the accuracy peak. Following it
  would stop at the worst round in the first half.

So bootstrapping here **works and cannot be tuned**. That is the practical
finding and it is not fatal, because of where the floor sits:

> Round 8 is 0.120 against a full-knowledge-base ceiling of 0.117 and a seed of
> 0.093. **Every round from 1 to 8 is at or above the ceiling.** Missing the peak
> costs the +37% and returns you to par — not below it.

Stated as advice: run it, take any number of rounds between one and eight, and
the result is between par with a curated KB and 37% better than one. What cannot
be done without gold is find the 37%.

## What would have refuted it

Round 2 landing below the seed on any split — the drift story would then have
been right and bootstrapping unusable without a stopping rule. It landed above
the *ceiling* on all three.
