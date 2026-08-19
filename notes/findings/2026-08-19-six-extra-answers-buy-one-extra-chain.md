---
title: Six extra answers buy one extra chain — added coverage does not compose
date: 2026-08-19
status: measured
arm: multi-hop-world
---

Two readers with **different failure correlations** were available on the same
415 chains: the hand patterns clump (two-hop ratio 1.56 against independence,
p=0.042) and the learned reader does not (ratio 1.00, z=−0.01). The
gap-filler finding recommends their union — patterns where they answer, the
classifier where they abstain. What that union does on a *composed* query is not
predictable from either part, so it was measured.

`union = hand or learned` is a **strict superset** of `hand` by construction: it
differs only where the patterns abstain. So this needs counting, not a test.

| arm | one hop | two hop | independence prediction |
|---|---|---|---|
| learned | 50/415 = 0.120 | 6/415 = 0.014 | 6.0 |
| hand | 73/415 = 0.176 | 20/415 = 0.048 | 12.8 |
| **union** | **79/415 = 0.190** | **21/415 = 0.051** | 15.0 |

## Six and one

The union answers **6 more chain-starts** than the patterns alone — articles the
patterns skipped and the classifier read correctly, with no losses, because the
union only fills abstentions. Those six buy **one** additional complete chain.

That is the whole result and it is exact. Composition needs the *partner* article
read as well, and the six new starts mostly point at partners nobody read. Five of
six extra first hops are wasted.

## Why, and it joins three threads

A chain's second article is a **parent company** — a hub — and hubs are the
articles measured to read worst (0.126 against 0.197; mean in-degree 0.124 for
wrong articles against 0.076 for correct). So added coverage at the *leaves*
cannot compose: the constraint is at the *hubs*, and both readers are weakest
exactly there.

This also explains a number that would otherwise look like a regression. The
union's clumping ratio falls **1.56 → 1.40** and stops being significant
(z=1.58, p=0.11) — not because the union is better behaved, but because six extra
first hops raise `p₁²` from 12.8 to 15.0 expected while adding one observed. **A
reader that gains coverage without gaining composability looks more independent
by arithmetic**, which is a warning about reading that ratio as a property of a
system rather than of a pairing.

## What this says to do

**Coverage at the leaves is nearly worthless for composed queries.** If composed
answers are the goal, reading effort belongs on high-in-degree articles — the
same conclusion the blast-radius finding reached from cost, arrived at here from
composability. In-degree remains available *before any reading*, from link
structure alone, which is the only actionable signal any of these arms has
produced.

The corresponding warning: every coverage improvement in this session's real-text
arms was measured at one hop. **None of them should be assumed to carry to two.**

## What would have refuted it

The six extra starts buying four or five extra chains — coverage would then
compose roughly linearly and leaf-level reading would be worth as much as hub
reading. They bought one.
