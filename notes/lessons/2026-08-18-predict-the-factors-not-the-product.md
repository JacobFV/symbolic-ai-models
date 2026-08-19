---
title: Predict the factors, not the product — a magnitude prediction on a quantity that is a product of two independent ones cannot be scored
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, prediction-ledger, calibration]
---

## The mistake

Pre-registered: *"45–70% of ambiguous filers will be determined at group level by
closure over GLEIF relationships"*, with the mechanism written out and a
refutation criterion at 30%.

The answer is **18.2%**, which by my own criterion refutes the mechanism. It does
not. The quantity is a **product**:

```
determined  =  P(the mechanism holds)  x  P(the graph covers the candidates)
   18.2%    =         81.3%            x          22.4%
```

The mechanism is **stronger** than I predicted; the coverage is far thinner than
I assumed without noticing I was assuming anything. A single number for the
product could not distinguish "corporate name-sharing crosses groups" from
"GLEIF records relationships for a tenth of its entities", and those have
opposite consequences — the first says stop, the second says the ceiling is a
data-recording limit and closure works wherever structure exists.

## Why the shading correction did not save it

The previous three predictions applied a deliberate downward shade, after
thirteen consecutive over-optimistic magnitude calls, and two of them came out
correct-to-under. This one was still 3× over. **The error was not magnitude, it
was specification**: no amount of shading fixes a prediction about the wrong
quantity.

## The guard

Before registering a magnitude, ask: **is this quantity a product of factors that
could move independently?** If it is:

- register a value for **each factor**, and
- register the **conditional** as the headline, because that is the one the
  mechanism is actually about, and
- treat the marginal as a **joint statement about mechanism and data**, scored
  as neither.

The tell is a refutation criterion that would fire for two incompatible reasons.
Mine would have: *"below 30% means name-sharing crosses corporate groups"* is
false at 18.2%, and I would have believed it.

Related: `notes/lessons/2026-08-18-magnitude-predictions-over-optimistic-thirteen-to-nil.md`,
`notes/lessons/2026-08-18-a-ratio-whose-ceiling-depends-on-k-cannot-compare-two-ks.md`
— both are the same shape: *the statistic, not the guess, was the problem.*
