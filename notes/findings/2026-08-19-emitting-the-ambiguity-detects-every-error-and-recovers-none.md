---
title: Emitting the ambiguity detects every error and recovers none
date: 2026-08-19
status: measured
arm: ambiguity-at-the-lexical-floor
---

## The regime nobody had measured

`read_content_roles` scores 1.000 on the published surface and falls when every
phrasing is written to **evade its declared anchors**. That gap is the measured
case for lexical generalisation, and directive 19's answer to it is to emit the
alternatives rather than collapse to one. Every previous measurement of that
machinery was taken on the published surface, where the anchors mostly fire and
the open set averages 1.19 worlds. This runs it where the anchors are **silent**:
role assignment is unforced on **252 of 252** cases, mean 2.48 candidate worlds.

400 seeds, 252 non-empty, all phrasings adversarial:

| arm | coverage | wrong | soundness | accuracy overall |
|---|---:|---:|---:|---:|
| collapse (guess by document order) | 1.000 | 73 | 0.710 | **0.710** |
| + role flag (refuse when unforced) | **0.000** | 0 | — | 0.000 |
| **emit, answer on agreement** | 0.361 | **0** | **1.000** | 0.361 |
| emit + certificate | 0.056 | 0 | 1.000 | 0.056 |

*(interleaved; grouped is the same on every emission row and 0.758 for collapse)*

## The answer to the question asked

**Emission recovers no accuracy whatsoever.** The 91 decided cases are a strict
subset of the 179 the collapsing reader already got right — measured as
`collapse is wrong on 73, and on 0 of those do the candidates agree`. What it
recovers is *knowing*: 0.710 accuracy with silent errors becomes 0.361 accuracy
with **zero** errors and 0.639 refusals.

That was the prediction, and it holds more strongly than predicted: the agreeing
set does not merely contain few errors, it contains none, and the disagreeing set
contains every error.

## Why, and it is a theorem rather than a measurement

Let the read world differ from the true world **only** in the role assignment,
and let the enumeration cover that channel. Then the true assignment θ* and the
collapsed assignment are both among the candidates, so:

- **all candidates agree ⇒ the agreed answer is correct** (θ* is one of them);
- **the collapse is wrong ⇒ the candidates disagree** (θ* gives a different
  answer, and θ* is enumerated).

Agreement is a **sound and complete** detector of role error. Neither direction
is a property of this reader. Both hold for any parameter whose candidate set is
enumerated exhaustively, and the empirical content is only the premise —
θ* ∈ candidates, which holds on 504 of 504 cells here (bound ~0.6%).

Two consequences worth carrying:

- **No certificate can improve emission on such a channel — it can only remove
  coverage.** 0.361 → 0.056 buys nothing, because there was nothing left to buy.
- **Coverage is not a tunable.** It is exactly the inert fraction of the
  ambiguity, 0.361, a property of the domain.

## The control, which is the load-bearing half

Turn the `hard_distractors` link channel back on — the reader then also admits
**invented links**, which the role enumeration does not cover — and the same
agreement arm is **40 wrong of 114 decided, soundness 0.649**. The premise fails
and the theorem goes with it. The certificate, which checks link-deletion
insensitivity, restores 1.000 at 0.127 coverage.

So the general statement, and it is the positive form of a lesson this repo has
now hit five times: **soundness is a property of the pairing (channel, check),
never of the check.** Enumeration is sound over what it enumerates. A certificate
is sound over the perturbations it tests. Ask which channels are live before
choosing between them.

Note the direction of the certificate's coverage, which is a warning rather than
a result: it certifies **more** often on the hard surface (0.127) than on the
clean one (0.056), because the phantom links make the graph more 2-edge-connected.
The check is most willing exactly where the reader is least reliable.

## The audit cannot make that choice, and this is the first thing it cannot predict

The obvious move is to let `audit_surface(prose=True)` say which channels are
live. It cannot. Scored on both surfaces, 20 cases each, it is **identical** —
ambiguity mass 0.640, the same four prose signatures, the same 280 flags,
including the `[bridge_on, link, load_limit]` row that is the disused track.
Soundness 1.000 against 0.649 with no difference in the instrument.

The reason is exact: the disused-track sentence carries the link signature on
**both** surfaces. Only the generator's choice of endpoints — regions outside the
network, or two real ones — decides whether admitting it is harmless. **The audit
predicts which channels are ambiguous, not which are erroneous**, and after four
things it does predict, that boundary is worth stating on the instrument.

## A number that was 34 cases

The published floor for the all-adversarial cell is **0.618**. At 400 seeds it is
**0.710**; the grouped cell is stable (0.765 → 0.758). 0.618 was n=34, where two
standard errors is ±0.17.

So the measured case for lexical generalisation on the interleaved surface is
**0.290, not 0.382** — overstated by a third. The direction of the argument is
unchanged and the correction goes on the record because the number does not.

## What would refute this

- The theorem is conditional and the condition is checkable, not assumed: any
  reader error outside the enumerated channel breaks it, and the hard-distractor
  arm is that demonstration rather than a caveat.
- One domain, one channel. The claim that soundness is a property of the pairing
  is general in form and tested at exactly two points.
- Coverage 0.361 is the inert share **of this domain's networks**. A less
  redundant network would make the depot load-bearing more often and drive it
  down; that is the same fragility the carrying finding was named for.
