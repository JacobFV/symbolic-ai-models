---
title: An explanation that omits nothing material, for 37% more words
date: 2026-08-19
status: measured
arm: complete-renderer
---

## Closing the output half

Three findings established the shape: `ungrounded` certifies that nothing false
was **said** and cannot see what was left **out**; the shipped renderer cites 2.0
of 28.4 claims and 9% of the load-bearing set; and the load-bearing set is now
computable at **1.03×** the cost of the answer.

What was missing was a renderer that uses it.

| renderer | grounded | **omits nothing load-bearing** | words |
|---|---:|---:|---:|
| template | 1.000 | **0.000** | 79 |
| **complete** | **1.000** | **1.000** | **108** |

**Complete coverage for +37% length.** That is a paragraph, not a recitation,
which was the whole question — the strict bar was rejected precisely because
nothing readable could meet it.

## Two checks, and being clear which is which

- `incomplete` — **the diagnostic.** Can a reader rebuild the answer from the
  paragraph alone? Nothing a person would read meets it, and it exists to show
  that grounding does not imply sufficiency.
- `omits_load_bearing` — **the objective.** Does the paragraph cite every claim
  whose deletion changes the answer? Reachable, and now met.

Measuring the new renderer against the strict bar would have been measuring it
against something already shown unmeetable. Keeping both, and naming which is
which, is the point.

## A prediction that was wrong in the useful direction

I expected strict rebuildability to stay at **0.000** for the complete renderer,
since the load-bearing set is 38% of claims and rebuilding needs a world. It
reaches **0.727**. The claims that *matter* turn out to be nearly the claims you
*need* — which is a fact about this domain worth noticing, not a general one: the
remaining 27% fail because reconstruction also wants network structure that no
single deletion touches.

## The arc this closes

| property | by enumeration | by structural argument |
|---|---:|---:|
| soundness | 13.4× | **1.0×** |
| inspectability | 25.5× | **1.03×** |

Both halves of "reasoning you can check" started as per-item enumerations over
the kernel and ended as arguments over the quantity the kernel already computes.
The renderer is the first place that arc produces output a reader sees rather
than a number in a table.

## What would refute this

- `omits_load_bearing` inherits `load_bearing_cheap`'s recall, measured 1.000
  over 73 cases and bounded at **4.1%**. A missed claim there is an explanation
  that omits something material while reporting that it does not.
- +37% is flood's number. A domain where most claims are load-bearing would make
  the complete renderer a recitation, and the check would then be telling you the
  task does not admit a short honest explanation — which is still worth knowing.
