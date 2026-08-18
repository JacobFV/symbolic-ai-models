---
title: Not running the hub-labelling refuter — any certificate whose dependency is the whole edge set is dominated by the ball, and both candidates are
date: 2026-08-18
author: lead
status: decided
tags: [certificates, decision, not-run, literature]
---

## The fork

`HANDOVER.md` §7 item 3, written by me four hours ago, proposed the newest
finding's own refuter:

> Meet-in-the-middle may not be optimal, and 2-hop covers / hub-labelling
> schemes are a real literature built for exactly "certify a shortest-path
> distance cheaply". If one stays small at `d = 10`, the whole
> witness/complement asymmetry weakens and the kernel contract changes.

I read the literature before building it, and the reading changed the question.
`CLAUDE.md` says that an experiment whose write-up you could draft first should
be recorded as a prediction rather than run. This is one, and here is the draft.

## The argument

Maintenance cost is governed by `P_hit ~ |dependency| / |corpus|`
(`notes/findings/2026-08-18-the-certificate-is-worth-nothing-per-quarter-and-1342x-per-filing.md`).
So the ranking of two certificates for the same claim is the ranking of their
dependencies, and:

> **Any certificate whose dependency is the whole edge set has `P_hit = 1` and is
> invalidated by every update. The ball's dependency is a subset of the edge
> set. So the ball dominates, for every `d` below the diameter.**

That is not a measurement, it is a containment. Both candidates fall to it:

**The LP dual / feasible potential.** The lower bound `dist(s,t) >= d` is
certified by node potentials `π` with `π(v) - π(u) <= w(u,v)` on every edge and
`π(t) - π(s) = d`. Its size is `~n` and — attractively — **constant in `d`**, so
it beats the ball on certificate *size* at large `d`. But its validity is a
conjunction over **every edge**: one inserted edge can violate it. Dependency is
`E`, `P_hit` is 1, and it loses on the only axis that matters here.

**Hub labelling / 2-hop covers.** Per query the lookup is `|L(u)| + |L(v)|`, and
it is genuinely small. But the *lower bound* is sound only because the labeling
has the **2-hop cover property** — the labels of any two vertices contain a
vertex on their shortest path — and that is a **global invariant over the whole
graph**. Verifying it from scratch is APSP-equivalent. So a hub label is a
**trusted index, not a self-contained certificate**: it relocates the coNP cost
from per-query to globally amortised. Its dependency, as an object that must
survive a corpus update, is again `E`.

The literature agrees about the direction of fragility and it is the same
direction the witness is fragile in. Edge **insertions** admit local repair —
if a distance changes, every new shortest path travels via the inserted edge, so
repair is a pruned search from the affected hubs. Edge **deletions** leave stale
labels that *underestimate* distance, i.e. silently unsound, which is strictly
worse than invalidated.

There is also a pleasing consistency check: optimal hub labelling is NP-complete
and is a special case of **set cover** — the same problem whose witness /
optimality split gave the 95x in the first place.

## What I am therefore claiming, and not claiming

**Claiming:** neither candidate beats the ball as a *maintenance* certificate,
because both depend on the whole edge set. The witness/complement asymmetry
measured on the route network survives its named refuter.

**Not claiming:** that no cheaper lower-bound certificate exists. One plausible
family was not disposed of by this argument and is genuinely open —
**separator-based certificates**. Any `s`–`t` path must cross a balanced
separator, so a hierarchical cut argument could certify a lower bound from the
separator plus distance bounds on each side, and a separator's size does **not**
grow with `d`. On a road network separators are `O(sqrt(n))`; on a small-world
airline network they are large. That would make the existence of a cheap
lower-bound certificate **a property of the graph's separator structure**, which
is exactly the shape of every other topology result in this repo (the wide
shallow GLEIF forest against the dense route network).

## What would make this worth running after all

- A graph with good separators — a road network, not an airline network. The
  route network is the wrong corpus to test a separator certificate on, and
  running it there would produce a null that proves nothing.
- Any per-query hub-label certificate that is **self-contained** — checkable
  without trusting an invariant the checker did not verify. I do not believe one
  exists, and that belief is the falsifiable part of this note.

Recorded in `notes/autonomy/predictions.jsonl` as `cert-lower-bound-candidates`
so that a later contradiction is a finding rather than a surprise.
