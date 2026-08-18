---
title: The first powered composition — the single-kernel answer is right 14% of the time, and a 0.05% metric error becomes a 0.43% answer error
date: 2026-08-18
status: provisional
tags: [composition, geo, real-data, error-propagation, openflights]
---

## Why this task

The SEC-to-GLEIF composition failed at n=3, and the reason was density, not
design: 3.7% of GLEIF carries ownership edges, so the join between "ambiguous
alignment" and "has an owner" was empty. That answered "this pair cannot tell
us", not the architectural question.

Openflights has two dense halves of one source — 6,072 airports with real
coordinates, 37,042 scheduled routes — and a question needing both. **Given an
aircraft range limit, which airports are how many legs apart?** A leg longer
than the limit cannot be flown, so `geo` decides which edges exist and the graph
search runs on what survives. Neither kernel alone answers it.

## Prediction

Graph-only (ignore the limit) would agree with the composed answer on **~60%**
of pairs at a 2,000 km limit; the metric substitution would flip ~0.3% of legs
and change ~1% of answers.

## Result 1: composition is load-bearing, and by more than I thought

Measured over **810,000 (source, target) pairs** — 250 multi-source traversals
rather than sampled pairs, because the first estimates rested on 7 to 32 events
and small counts are this repo's oldest way of being confidently wrong:

| range limit | legs that survive | graph-only agrees with the composed answer |
|---|---|---|
| 1,000 km | 44.3% | **0.0604** |
| 2,000 km | 73.6% | **0.1437** |
| 4,000 km | 91.1% | **0.3012** |

**0.1437 at 2,000 km, against a predicted 0.60.** The single-kernel answer is
not a near-miss heuristic that a correction could rescue; it is answering a
different question and agrees mostly by accident. That is a direct answer to
"does composition earn its complexity", on real data, in the affirmative.

## Result 2: the composition amplifies its inputs' error, and I did not predict the shape

The geo kernel's own docstring says the spherical approximation is *"0.5% out —
fine for 'which is nearer' and not fine for a fuel budget"*. This task is a fuel
budget, so substituting haversine for Vincenty is the experiment that claim
invites. Over 37,042 real legs the stated error checks out: **median 0.159%,
p99 0.504%, max 0.559%.**

What that does to the answer:

| limit | legs flipping the threshold | answers changed (810k pairs) | amplification |
|---|---|---|---|
| 1,000 km | 32 (0.0864%) | 1,117 (0.1379%) | **1.6x** |
| 2,000 km | 19 (0.0513%) | 3,459 (0.4270%) | **8.3x** |
| 4,000 km | 7 (0.0189%) | 6,742 (0.8323%) | **44.0x** |

An error in a kernel's output does not stay the size it was. Nineteen
misclassified legs out of thirty-seven thousand move four answers in a thousand.

**And the amplification rises as the flip rate falls**, which is the part I would
have got backwards. The explanation is structural: at 1,000 km the surviving
network is fragmented, so a misclassified leg corrupts only its own component;
at 4,000 km the network is nearly connected and every remaining long leg is a
hub-to-hub route lying on enormous numbers of shortest paths. **The closer a
graph is to connected, the more each individual edge decides**, so the *safest*
place to be imprecise is where the constraint bites hardest — the opposite of
the intuition that a tighter budget demands more precision.

## What this says about the architecture

The kernel ABI's discard record and the fusion registry are both premised on
kernels being composed rather than used alone. This is the first real-data
measurement of what that premise costs and buys:

- **Buys:** a single-kernel answer to a two-kernel question is right 14% of the
  time. Composition is not ceremony.
- **Costs:** a 0.05% input error becomes a 0.43% output error, and the factor
  depends on the *topology* the composition runs over, not only on the
  kernels. A tolerance declared per-kernel — which is what the manifest carries
  today — cannot express that. **The manifest can say a kernel is accurate to
  0.5%; it cannot say what that means three nodes downstream**, and this
  measurement says the difference between those two numbers is 1.6x to 44x
  depending on the data.

That is a real gap in the ABI and it is the thing I would build next.

## What would refute it

- One network, one topology. The amplification factor is a property of the
  route graph's density profile; a different graph gives different numbers and
  I have not shown the *direction* generalises, only the mechanism.
- The 0.1437 agreement counts `None` (unreachable within 8 hops) as an answer.
  Pairs that are unreachable under both readings count as agreeing, which is
  generous to the single-kernel baseline — the true disagreement is higher.
- Haversine versus Vincenty is a small, well-behaved error. A biased or
  heavy-tailed input error would amplify differently and probably worse.
