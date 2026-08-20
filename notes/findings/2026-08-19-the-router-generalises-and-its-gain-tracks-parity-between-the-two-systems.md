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
one dominates — and re-pairing against a different floor moves the gain in the
predicted direction both ways (see the refuter below). The precondition is
checkable before building anything: measure both systems, and if one is nearly
twice the other, the routing is not worth the wiring.

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

## The refuter was named, run, and confirms the mechanism from both sides

The router was paired with `prep_org`, chosen before the numbers landed, but
`prep` is the stronger floor on unseen (0.184 against 0.139). Re-pairing:

| pairing | reader | floor | ratio | oracle headroom | router gain | captured |
|---|---|---|---|---|---|---|
| employer unseen, `prep_org` | 0.247 | 0.139 | 1.78 | +0.057 | +0.019 | 33% |
| employer unseen, **`prep`** | 0.247 | 0.184 | **1.34** | +0.063 | **+0.025** | 40% |
| employer seen, `prep_org` | 0.236 | 0.192 | **1.23** | +0.148 | **+0.060** | 41% |
| employer seen, `prep` | 0.236 | 0.184 | 1.28 | +0.052 | +0.028 | 54% |

A stronger partner on unseen moved the gain **up** (+0.019 → +0.025), and a
weaker partner on seen moved it **down** (+0.060 → +0.028). The mechanism
predicts both directions, which is more than the original four rows could show.

**But the sharper statement is not about the ratio.** Capture sits in a narrow
band — **33% to 63% across six pairings** — so the router reliably takes roughly
**half of whatever oracle headroom exists**. The ratio matters only because it
predicts the *headroom*: near-parity systems disagree more usefully. The honest
law is therefore two-step and the second step is the shaky one — capture is
stable and well-measured, while "parity produces headroom" rests on six points
with one clear outlier (employer-seen at `prep_org`, ratio 1.23 but headroom
+0.148, more than twice its neighbours).

So: **estimate the oracle headroom, halve it, and that is the router.** Whether
parity is a reliable way to predict headroom in advance is not established here.

## Limits

n=158 unseen, n=250 seen, one corpus. Both relations come from the same 850
biographies, so "two relations" is not two domains. The floors were written by
the same person who wrote the reader's features, which is the conflict the
broken-cue floor already demonstrated is real.
