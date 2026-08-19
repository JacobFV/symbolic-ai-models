---
title: An explanation can say where it is not honest
date: 2026-08-19
status: measured
arm: uncorroborated-citations
---

## Where the fabrications actually are

The complete renderer cites a false fact on 37.8% of honest-surface explanations
and on 7.6% of the answers it got **right**. Broken down by the predicate the
citation rests on, 300 seeds, 2,266 citations:

| predicate | cited | false | rate |
|---|---:|---:|---:|
| mass | 528 | **0** | 0.0000 |
| capacity | 528 | **0** | 0.0000 |
| needs | 392 | **0** | 0.0000 |
| demand | 196 | **0** | 0.0000 |
| bridge_on | 18 | **0** | 0.0000 |
| load_limit | 18 | **0** | 0.0000 |
| flooded | 295 | 13 | 0.0441 |
| depot | 196 | 13 | 0.0663 |
| **link** | **95** | **61** | **0.6421** |

**Six predicates are perfectly honest over 1,680 citations.** Two thirds of every
cited `link` is phantom, and links are 70% of all the falsehoods while being 4% of
the citations.

That is not a property of this surface. It is **the day's arity law, read off the
citations**: `link` is multi-valued with no second source, so detection fires
0.000 on it; `depot`/`flooded` are the role channel, which the role flag does
catch; and everything corroborated by a value registry or by adjacency is at
**zero**.

## So mark it

`render.uncorroborated(answer, world, forced=…)` returns the citations resting on
a claim nothing here can check: `link` always, plus `depot`/`flooded` when the
reader's `role_assignment_forced` is False.

| | |
|---|---:|
| citations | 2,266 |
| false citations | 88 |
| **flagged as uncorroborated** | **171 (7.5%)** |
| **false citations flagged** | **88 / 88 = 1.000** |

**Every fabrication, inside 7.5% of the text.** A 13× concentration, with no
false negatives.

## What that changes about inspectability

The complete renderer **cannot be made honest** — nothing in this repo checks a
link, and the arity law says nothing can, because the channel has no second
reading. What it can do is stop presenting eleven facts as if they were one kind
of thing:

> *"Here are eleven facts, four of which nothing corroborates."*

That is a different and more defensible claim than *"here are eleven facts"*, and
it is exactly as strong as the corroboration structure underneath it — which is
measurable offline, per predicate, before any explanation is written.

It also gives the fabrication result its constructive close. The trade priced
earlier — a two-fact summary that is never wrong about its two facts, against an
eleven-fact account wrong somewhere in one of three — is no longer the only
choice. The eleven-fact account with its four risky facts named is a third option,
and it is the honest one.

## What would refute this

- The recall is 1.000 because **all** 88 falsehoods happen to be link, depot or
  flooded. A reader that erred on a *value* — a misread mass — would fabricate
  inside a predicate this marks as corroborated, and the marker would miss it
  silently. The value registry is what stops that here, and it is a generator
  artefact.
- 171 flagged for 88 true positives is a precision of 0.51. Half the flags are
  citations that happen to be right.
- One domain. The partition is derived from flood's corroboration structure and
  has to be re-derived per domain; what transfers is the *method* — flag the
  channels the arity law says have no second reading.
