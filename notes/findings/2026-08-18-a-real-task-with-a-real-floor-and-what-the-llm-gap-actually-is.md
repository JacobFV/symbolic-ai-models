---
title: The first real-data task with a beatable floor — and the symbolic advantage falls from 1,500,000x to 6,800x when the LLM actually knows the answer
date: 2026-08-18
status: provisional
tags: [real-data, cost, geo, floor, openflights]
---

## Why this task

The shortest-path finding earlier today produced a 1.5-million-fold cost
advantage and no `$/solved-episode-above-floor` number, because shortest path
has no floor worth beating: every method that answers it answers it exactly. A
cost ratio on a task nobody can fail is the cheapest possible win.

This task can be failed. **Given only an airport's coordinates, which country is
it in?** 5,995 airports, 222 countries, ground truth from openflights' own
`in-country` edges — which the route adapter had *discarded* as a different
relation, so they arrive as labels rather than as features.

It was chosen because **an LLM is genuinely competitive at it.** A model that
knows world geography should do well here, which is the opposite of the
shortest-path setup and the reason this comparison is worth more.

## Predictions, before the numbers

1. 1-NN on coordinates: **above 0.92**.
2. Ground-truth anchor (the leaked `country=` body string): **~1.00**.
3. Shuffled-coordinate control: **collapses to the floor, ~0.21**.

## What I found

| | |
|---|---|
| floor (always the modal country, US) | **0.2087** — as predicted |
| 1-NN on coordinates alone | **0.9078** — predicted >0.92, **wrong** |
| 3-NN / 5-NN | 0.9074 / 0.8996 |
| anchor, first run | **0.9715** — predicted 1.00, **wrong, and it was my bug** |
| anchor, after the fix | **1.0000** |
| control: labels shuffled | **0.0597** |
| control: coordinates shuffled | **0.0649** |

Both controls land *below* the floor, which is the right behaviour and worth
saying: 1-NN copies a random neighbour's random label, and that is worse than
always guessing the commonest country. A control that merely fell to the floor
would be weaker evidence than one that falls through it.

## The anchor earned its keep in the first ten minutes

The anchor exists to score ~1.0 by reading the leak; if it does not, the task is
broken before any method touches it. It scored 0.9715, and the 171 disagreements
were all of one shape:

```
body says 'United'   edge says GB   x108
body says 'South'    edge says KR   x25
body says 'United'   edge says AE   x11
```

Not a data problem — **my parser**. The body is a space-delimited `key=value`
bag and my regex took values up to the next space, so `country=United States`
became `United`. The fix reads each value to the start of the *next key*, and
the anchor went to exactly 1.0000 with zero disagreements.

Note what this says about the shadow schema, beyond "it is untyped": the grammar
is **only recoverable because no value in this corpus contains an `=`**. It is
ambiguous in principle. An untyped bag does not merely lose the type, it can
lose the parse.

The earlier reachability finding is unaffected — routes never read a body — but
the adapter was wrong and shipped, and only an anchor that had to be *exactly*
1.0 would have caught it. An anchor permitted to be approximately right catches
nothing.

## The cost ledger, which is the point

| system | $/solved-above-floor | ms/action | basis |
|---|---|---|---|
| 1-NN geodesic | **$8.46e-09** | 1.1 | measured |
| LLM $1/Mtok, *assuming equal accuracy* | $5.72e-05 | — | assumed |
| LLM $15/Mtok, *assuming equal accuracy* | $8.58e-04 | — | assumed |

**~6,800x against a Haiku-class model, ~101,000x against an Opus-class one.**

Set beside this morning's shortest-path result — ~1,500,000x — the shape of the
real claim appears:

> The symbolic advantage is not a constant. It scales with **how much of the
> answer lives in structure the model would have to be given** rather than in
> knowledge it already has. Shortest path needs 233k tokens of graph in context;
> a country lookup needs a coordinate. Same substrate, same corpus, a 220-fold
> difference in the size of the win.

## The part that cuts against me

The LLM rows assume it matches 0.9078 exactly, and the cost model stamps them
`NOT QUOTABLE` for precisely that reason. **An LLM would plausibly beat 0.9078
here** — it knows Puerto Rico is US, that Kaliningrad is Russia, and where
borders run, none of which 1-NN can represent. The 553 misses are concentrated
in large countries with long borders (US 27, RU 22, CA 15, AR 13, BR 13, CN 13),
which is exactly the population a knowledgeable model would get right.

So 6,800x is the price ratio at *assumed* equal capability, and the honest
statement is that the accuracy comparison is **unmeasured**. If the LLM reaches
0.96, its above-floor rate is 8% better and the ratio falls to ~6,300x while the
symbolic method is simply worse at the task. That is a live possibility and I am
not going to write it out of the finding.

## What would refute it

- Measuring the LLM's actual accuracy. Not done; it is the obvious next step and
  the one that could reverse the reading of the last row.
- A better symbolic method. 1-NN is the weakest thing that could work; real
  boundary polygons would likely exceed 0.99 and are a licence question, not a
  research one.
- The floor is the modal country. A stronger floor — nearest *capital*, or
  longitude banding — would cut the above-floor margin and raise every $/solved
  number. This repo has been burned by a too-low floor before.
