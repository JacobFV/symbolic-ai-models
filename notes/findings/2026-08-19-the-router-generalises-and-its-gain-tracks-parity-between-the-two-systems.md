---
title: The router generalises to a second relation — and its gain tracks how close the two systems are
date: 2026-08-19
status: provisional
arm: router-second-relation
confirms:
  - the router is not a property of `occupation`
notes:
  - a broken floor produced the opposite conclusion first, in the same session that recorded the lesson about broken floors
---

## Why this was run

Everything in the router arm was `occupation` — one relation, one frame, one
value type, one external inventory. `employer` changes all four: values are
organisation names with no morphological signature, there is no obligatory
opener, WordNet's `noun.person` is useless, and the proposer has to be
capitalised runs.

## The false negative, and it came first

The first run reported the reader at 0.247, a floor at **0.025**, and a router
gain of **+0.000** — printing *"the router does NOT generalise: it was a property
of occupation."*

That conclusion was my floor's, not the data's. Diagnosing it the way
`notes/lessons/2026-08-19-a-suspiciously-weak-floor-is-a-finding-about-the-floor.md`
prescribes — asking what the largest score the code could produce is:

| | |
|---|---|
| employment cue fires anywhere in the document | 0.240 |
| gold employer contained in the intro | 0.592 |
| gold proposed by capitalised runs | 0.476 |
| **gold within 40 chars of a cue** | **0.036** ← the floor's ceiling |

The floor scored 0.025 against a structural ceiling of 0.036 — **69% of the best
it could ever do**. The misses said why: real biographies write *"Senior
Investigator **at** X"*, *"Director-General **of** X"*, *"studying under Linnaeus
**at** Uppsala University"*. A bare preposition after a role noun, not an
employment verb.

## What was measured, with a fair floor

Five floors, all zero-supervision, subject's own name excluded.
`runs/router_second_relation.json`.

| floor | unseen | seen |
|---|---|---|
| nearest capitalised run after a preposition (`prep`) | **0.184** | 0.184 |
| capitalised run with an organisational head (`org`) | 0.139 | 0.188 |
| both (`prep_org`) — the one the router was paired with | 0.139 | **0.192** |
| employment-verb cue (`cue`) — the broken one | 0.025 | 0.028 |
| longest capitalised run (`longest`) | 0.019 | 0.044 |

| slice | reader | floor | oracle | **router** | gain over best | captured |
|---|---|---|---|---|---|---|
| unseen (n=158) | 0.247 | 0.139 | 0.304 | **0.266** | **+0.019** | 33.3% |
| seen (n=250) | 0.236 | 0.192 | 0.340 | **0.296** | **+0.060** | 57.7% |

## The result: it generalises, and the gain has a mechanism

**The router beats the best single system on both slices of a second relation**,
with different values, a different frame, a different proposer and a different
inventory. Four slices across two relations, all positive.

And the size is not arbitrary — **it tracks how close the two systems are**:

| case | reader | floor | ratio | oracle headroom | router gain |
|---|---|---|---|---|---|
| occupation unseen | 0.288 | 0.310 | **1.08** | +0.103 | **+0.065** |
| employer seen | 0.236 | 0.192 | 1.23 | +0.148 | **+0.060** |
| occupation seen | 0.536 | 0.444 | 1.21 | +0.102 | +0.048 |
| employer unseen | 0.247 | 0.139 | **1.78** | +0.057 | **+0.019** |

The router pays most where the two systems are nearest to parity and least where
one dominates. That is not a surprise once stated, but it converts the router
from a trick into something with a **precondition you can check before building
it**: measure both systems, and if one is nearly twice the other, the routing is
not worth the wiring.

It also retires my earlier framing that "the router adds most where the learned
component adds least". That was one observation read as a rule. It adds most
where the two are **closest**, which on `occupation` happened to be where the
reader was weak and on `employer` is where the reader is strong.

## Predictions

- **Confirmed:** the reader beats the floor outright on `employer` (0.247 vs
  0.139), unlike `occupation` where the floor won — organisation names carry no
  morphology for a suffix rule to grip.
- **Confirmed:** the router's unseen margin is smaller than occupation's
  (+0.019 against +0.065).
- **Refuted:** oracle headroom is not uniformly near +0.10 — it is +0.057 on
  employer-unseen and +0.148 on employer-seen. Headroom is a property of the
  pairing, not a constant.

## What would refute this

The router was paired with `prep_org`, chosen before the numbers landed, but
**`prep` is the stronger floor on the unseen slice** (0.184 against 0.139).
Pairing the router with the better floor is untested and could move the +0.019
either way — a stronger partner raises the oracle but shrinks the reader's
unique wins. That is the first thing to run.

## Limits

n=158 unseen, n=250 seen, one corpus. Both relations come from the same 850
biographies, so "two relations" is not two domains. The floors were written by
the same person who wrote the reader's features, which is the conflict the
broken-cue floor already demonstrated is real.
