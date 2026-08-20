---
title: The reader knows when to defer — AUC 0.880 on discordant items — and that is worth more than its answer
date: 2026-08-19
status: provisional
arm: selector
refutes:
  - my registered prediction that the confidence would not separate discordant items
---

## Why this was run

The paired arm found the learned reader and a two-line morphological rule fail on
different items — agreement 0.772 unseen, 0.705 seen — so an oracle knowing which
to believe would gain **+0.103** and **+0.102**, larger than any single
intervention in this arm including the WordNet swap. The cheapest possible
selector is the reader's **own confidence**, which it already emits.

Measured as AUC over the **discordant items only** — the population a selector
actually has to sort. Pooled AUC would be flattered by the easy agreements, and
this repo has been burned by pooled-versus-per-question AUC before.

**Predicted: it does not separate them**, AUC below 0.60, because the confidence
is calibrated on the classifier's *label* decision while the disagreements live in
the **ranker's** choice among candidates.

## What was measured

`runs/selector_probe.json`.

| slice | n | discordant | reader | floor | oracle | **AUC discordant** | AUC pooled | trivial selector | headroom captured |
|---|---|---|---|---|---|---|---|---|---|
| unseen | 184 | 42 | 0.288 | 0.310 | 0.413 | **0.880** [0.769, 0.991] | 0.768 | **0.370** | **57.9%** |
| seen | 847 | 250 | 0.536 | 0.444 | 0.638 | **0.715** [0.652, 0.778] | 0.737 | 0.540 | 3.5% |

## The result: refuted, and it restores a capability the last finding took away

**The confidence separates the discordant items at AUC 0.880 on novel
vocabulary.** My prediction was wrong and the mechanism I gave for it was wrong:
the confidence tracks something the ranker's errors respect, not just the
classifier's label decision.

The unseen slice is also the one place in this arm where **AUC on discordant
items exceeds pooled AUC** (0.880 against 0.768) — the reverse of the usual
pattern. Confidence is *most* informative exactly where the two systems fight,
which is the property a router needs and the opposite of what a merely
well-calibrated score would give you.

**A trivial rule captures 57.9% of the headroom on unseen values**: believe the
reader unless it disagrees with the floor and its own confidence is below the
median disagreement. That takes novel-vocabulary reading from **0.310 to 0.370**
— a **+0.060** gain over the best single system, on a slice where the previous
finding established the reader alone has **no measurable lift at all**.

So the retraction stands and is not softened: *as an answerer* the reader adds
nothing on novel vocabulary. But **as a judge of when to defer it is worth
+0.060**, and that is a capability the two-line rule cannot supply on its own.
Charged to the system rather than the component — which is this repo's stated
accounting rule — novel-vocabulary reading is back above floor.

## The asymmetry is the point

The selector pays **57.9%** on unseen and **3.5%** on seen. That is not a defect;
it is the ideal shape. Where the reader is already the stronger system (seen:
0.536 against 0.444) a median-threshold rule mostly defers *wrongly*, and there is
little to win. Where the reader is weakest — novel vocabulary, exactly where
learning cannot help — the router recovers most of what is available.

**The router adds most where the learned component adds least.** That is the
argument for a hybrid made from the measurement rather than from taste, and it is
the first time in this arm a combination has beaten both of its parts.

## What would refute this

The 0.880 rests on **19 versus 23 items**. Its interval reaches 0.991, which is
not a plausible AUC and is a sign the sample is too small rather than that the
effect is enormous. A larger unseen slice is the first thing to get, and the
finding should not be promoted before it.

Also unrun: the threshold is the **median of disagreements on the test items
themselves**, which is fitted on the thing being scored. A held-out threshold
will be worse, and by an unknown amount. That is a real flaw in the 0.370 and it
is stated rather than buried — the AUC is the honest number here, the selector
rate is optimistic.

## Limits

One relation, one domain. n=184 unseen. Threshold fitted in-sample. The floor and
the reader share a candidate set, so both inherit WordNet's 52% coverage.
