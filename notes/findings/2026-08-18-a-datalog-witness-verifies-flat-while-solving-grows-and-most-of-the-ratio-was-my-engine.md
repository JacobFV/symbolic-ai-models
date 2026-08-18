---
title: A datalog witness verifies in constant time while solving grows — but 99.98% of the headline ratio was my own engine being slow
date: 2026-08-18
status: provisional
tags: [proof-trace, datalog, inspectability, cost, negative-result]
---

## The question this answers

Yesterday's finding measured inspectability on shortest path and found it
asymmetric: a witness verified **247x** cheaper than solving, while certifying
optimality cost **2.0x more** than re-solving. Its named open question was
whether that shape belongs to shortest path or to the existential/universal
distinction, and it predicted datalog would do better, *"because a derivation
tree's verification should be linear in the derivation, not the database."*

## Predictions

1. Datalog witness verification **more than 1,000x cheaper** than solving.
2. The ratio **grows roughly linearly** with database size, because verification
   is flat and solving is not.
3. Non-derivability costs about as much as solving.

## Built

`symbolic_ai_kernels/datalog/proof.py`, deliberately **beside**
`engine.evaluate` and not inside it — recording provenance costs memory
proportional to the closure and slows the fixed point, and a published number
carrying `evaluate`'s name has to keep meaning what it meant.

`evaluate_with_derivations` returns the same least model plus **one**
justification per derived fact (not all: keeping every derivation answers *how
many ways*, and is unbounded on a cyclic graph — and ownership cycles are real
in this data). `verify_derivation` checks a tree against the program and the
base facts, touching nothing else. The check that matters is that **a leaf must
be a base fact**; without it a tree derives anything by asserting its premises.

## What I found, and the correction inside it

GLEIF ownership closure, `ult(X,Z) :- par(X,Y), ult(Y,Z)`, at five database
sizes. Mean derivation tree: **2.0–2.1 nodes**.

| edges | my engine | purpose-written closure | engine overhead | verify | vs engine | **vs a competent solver** |
|---|---|---|---|---|---|---|
| 250 | 14.6 ms | 0.03 ms | 495x | 1.26 µs | 11,629x | **23x** |
| 500 | 55.1 ms | 0.06 ms | 917x | 1.20 µs | 46,054x | **50x** |
| 1,000 | 214.4 ms | 0.12 ms | 1,756x | 1.20 µs | 178,423x | **102x** |
| 2,000 | 854.2 ms | 0.26 ms | 3,292x | 1.28 µs | 665,691x | **202x** |
| 4,000 | 3,448 ms | 0.63 ms | 5,446x | 1.28 µs | 2,702,920x | **496x** |

**The first ratio I computed was 2.7 million to one.** It is nearly all my own
engine. `_index` in `engine.py` keys facts by **predicate only**, so the join in
a recursive rule rescans every `ult` fact for every `par` fact — quadratic work
for linear output. Against a purpose-written closure doing the identical job the
honest ratio is **23x to 496x**.

**Prediction 1 is refuted** at any size below a few thousand edges. 23x, not
1,000x.

**Prediction 2 holds cleanly**: 16x more data gives 21.6x more ratio.
Verification stays at 1.20–1.28 µs across the whole range while solving grows
linearly at best, so **the value of carrying a witness increases with scale** —
which is the property that matters for a 1.2-billion-row corpus and is the real
answer to yesterday's question.

**Prediction 3 is unmeasured.** Closed-world non-derivability requires the fixed
point by construction, so I believe it, and believing it is not measuring it. It
stays open rather than being written up as though it were established.

## What this actually says

The comparison with shortest path is not "datalog is better". At 4,000 edges the
datalog witness is 496x cheaper and the routing witness was 247x; at 250 edges
the datalog witness is 23x, far *worse*. **What differs is the slope, not the
level.** Shortest-path's ratio is bounded by how much of the graph BFS explores
before its early exit; datalog's grows with the database because a derivation
tree does not know how large the database is.

So yesterday's rule survives with a sharper statement: **the existential half is
cheap to justify, and how cheap depends on how much work the solver had to do
that the witness gets to skip.** That quantity grows with data for a closure and
is capped by early termination for a search.

## The engine defect this exposed

`_index` keys only by predicate. An index on `(predicate, first argument)` would
make the recursive join a lookup rather than a scan, and the overhead table says
that is worth 495x at 250 edges and 5,446x at 4,000 — growing, so worse at
every real scale. That is a real, actionable defect, it is not in the critical
path of any published finding (`ultimate_parent` uses the purpose-written
closure, which is what the 0.9785 was measured with), and it is the next thing
to fix in this kernel.

## What would refute it

- The purpose-written closure exploits a property of *this* relation — each
  entity has at most one direct parent, so the "closure" is a walk up a forest.
  A relation with genuine fan-out has no such shortcut and the engine's
  disadvantage would be smaller. The 23x–496x is therefore a **lower** bound on
  the ratio for harder programs, and the 2.7-million-x an upper bound that no
  one should quote.
- Trees here are tiny (2.0 nodes) because ownership chains are shallow. A deep
  or bushy derivation verifies more slowly and the flatness claim is really
  "flat in the database, linear in the derivation" — which is the claim, but
  the data does not stress the second half.
