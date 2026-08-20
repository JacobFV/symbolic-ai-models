---
title: A lexical proposer cannot generalise a long-tailed inventory — 21 suffixes recover 0.8%, and the answer must be syntactic
date: 2026-08-19
status: provisional
arm: suffix-generalisation
refutes:
  - my registered prediction that opening the suffix gate would lift unseen proposal above 0.30
---

## Why this was run

The control arm left `occupation` reading **0.615** on seen values and **exactly
0.000** on unseen ones, with the collapse attributed entirely to **proposal**
while containment stayed at **0.582**. The obvious next move looked like building
a new proposer — but `PhraseMentions` already carries the mechanism. It induces
**productive suffixes** (`... industry`, `... services`) precisely so an unseen
value is proposable from a head it has seen. The gate is `min_share=0.15`, set
when the target inventory was `industry` — a handful of values.

So the cheap question first: does the existing mechanism work once its threshold
is not tuned for a five-value inventory?

**Registered prediction: yes.** At `min_share <= 0.01`, unseen proposal above
0.30 and end-to-end above 0.10, at some cost to precision on the seen slice.

## What was measured

847 biographies, 494 distinct occupations, 4-fold, `runs/suffix_generalisation.json`.

| min_share | suffixes | unseen propose | unseen measured | seen measured |
|---|---|---|---|---|
| 0.15 (shipped) | 0 | 0.000 | 0.000 | 0.600 |
| 0.05 | 1 | 0.000 | 0.000 | 0.600 |
| 0.02 | 4 | 0.000 | 0.000 | 0.600 |
| 0.01 | 7 | 0.000 | 0.000 | 0.613 |
| 0.005 | 11 | **0.008** | 0.000 | 0.616 |
| 0.002 | 21 | **0.008** | 0.000 | 0.609 |

Unseen containment is **0.582** at every row. The answer is in the text and stays
there.

## The result: refuted, and the mechanism is structurally wrong for this shape

**Prediction refuted.** Opening the gate by 75× — 0 suffixes to 21 — moves unseen
proposal from 0.000 to **0.008**. End-to-end stays at **exactly 0.000** at every
threshold. The second prediction is refuted too: there is no precision cost on the
seen slice, which drifts 0.600 → 0.616 → 0.609. Opening the gate is **free and
useless**, which is the least useful combination available.

The mechanism is not mis-tuned; it is the wrong mechanism. The induced heads at
0.02 are `cyclist`, `scientist`, `teacher` — and **zero** held-out gold values end
in any of them. That is the whole story: a productive suffix generalises an
inventory whose values *share heads*, like `automotive industry` /
`pharmaceutical industry`. Occupations do not share heads. They **are** heads —
494 of them across 847 articles, long-tailed, and a threshold low enough to admit
the tail admits it one value at a time, which is memorisation with extra steps.

## What this actually establishes

The reading arm has now measured, in one relation, all four factors and both
kinds of limit:

- the reader **reads the frame** — 98.6% of the rate survives renaming every
  value to an invented token;
- containment on unseen values is **0.582**, so the information is present;
- and the gap between those two facts is a proposer that can only offer strings
  drawn from a **lexical** inventory, by exact phrase or by shared head.

Both available lexical routes are now measured and both are zero. So the
component that would close a **0.582 × 0.89 × 0.89 ≈ 0.46** gap cannot be lexical
at all: it has to propose the noun phrase **by its position in the frame** — the
thing the reader has already been shown to read — rather than by recognising it.

That is a sharper target than "build a better proposer", and it is the first time
this arm has had a component specified by what was ruled out rather than guessed.

## What would refute this

A lexical inventory drawn from *outside* the training fillers — WordNet's
`person` hyponyms would supply several thousand occupation nouns — recovering the
unseen slice. That would mean the limit was inventory *size*, not the lexical
approach, and this repo's standing rule is that external resources like WordNet
are givens rather than things to re-derive. It is the obvious next experiment and
it is cheap.

## Limits

One relation, one domain, single fetch. `min_share` was swept and **nothing was
selected from the sweep** — no knob was fitted, because every row gave the same
answer. The 0.46 figure is arithmetic from measured factors, not an achieved rate.
