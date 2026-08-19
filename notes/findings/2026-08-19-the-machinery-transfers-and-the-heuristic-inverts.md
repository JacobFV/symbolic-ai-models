---
title: The reader machinery transfers to a structurally opposite task at 1.000 — and the rule that was correct in flood costs 0.150 there, with identical extraction
date: 2026-08-19
author: lead
status: provisional
tags: [reader, text-to-world, transfer, bitemporal, world-ir]
---

## The test

Flood is routing over a network, a subset answer, two expensive kernels.
Solvency is one boolean per group, a trivial kernel, and a **bitemporal** core:
`valid_time` is the quarter a figure is about, `transaction_time` is when it could
have been known, and a figure filed after the decision date must not be used
however current it is.

That inverts a rule the flood reader learned. There a superseded load limit was a
**distractor** and *take the latest number* was correct. Here the revision is the
substance and *take the latest* is exactly wrong.

> **The same surface feature is a trap in one domain and the answer in the
> other.** That is what makes this a transfer test rather than a second
> implementation.

`symbolic_ai_generators/solvency/surface.py` renders each case as four aligned
paragraphs — group structure, filings as first reported, subsequent revisions,
the covenant test — with **12 of 12 claims aligned**, a divested-subsidiary
distractor, and dates in two formats across variants so temporal normalisation is
a step rather than a string match.

## Result

`scripts/solvency_transfer.py`, 60 cases. Every arm recovers
`(members, filings, threshold, decision_date)` from text alone, then runs the
task's own `decide`.

| arm | V=1 | V=2 | V=3 | V=4 |
|---|---:|---:|---:|---:|
| **signature reader (date-aware)** | **1.000** | **1.000** | **1.000** | **1.000** |
| latest value — **the flood rule** | 0.850 | 0.850 | 0.850 | 0.850 |
| first filed — ignore revisions | 0.900 | 0.900 | 0.900 | 0.900 |
| majority class (floor) | 0.583 | | | |

**Filing recall is 1.000 for all three arms at V=4.**

### Two things follow

**1. The machinery transfers.** Type-signature routing works unchanged on a task
with no routing, no subset answer and no coreference: two member ids and no
number is an ownership claim, one member plus one USD figure plus one date is a
filing, a bare figure is the threshold, a bare date is the decision. Flat across
four phrasings and two date formats. Exact span→claim alignment, the arm harness,
and the surface pattern all carried over without modification.

**2. The heuristic does not, and the difference is not extraction.** All three
arms recovered **every filing identically** — recall 1.000. The 15-point gap is
*entirely* in how `transaction_time` is used.

> **A representation that carries transaction time gets this right; one that
> carries only values cannot, however good the extraction.** That is the
> sharpest argument the world IR has been given so far, and it came from a task
> chosen to be structurally opposite to the one the IR was exercised on.

The flood rule is not useless here — 0.850 against a 0.583 floor — it is
*confidently wrong on 15% of cases*, which is the failure mode a reader cannot
detect from inside its own output.

## Caveats stated plainly

- **Solvency is easier for a reader than flood.** No coreference, cleaner
  signatures, no entity ids the text withholds. 1.000 is a claim that the
  machinery *transfers*, not that the two tasks are of equal difficulty.
- **The date-aware policy is hand-written**, as the flood rule was. What
  transferred is the extraction architecture; the temporal policy is a per-domain
  decision, which is exactly the point — and it argues that the reader should
  *emit* the time and let a kernel decide, rather than resolve it itself.
- **60 cases, one generator.** The 0.150 gap is a property of how often the
  post-decision revision crosses the threshold in this generator's parameters.

## What this leaves open

The theory has not been transferred, only the machinery. Untested on solvency:

- Is `F` again the **trivial-answer share** — here the cases whose verdict is the
  same under every reading?
- Is the ambiguity budget again concentrated on the claim that **sizes** the
  answer (in flood, the demand; here, plausibly the threshold or the decision
  date)?

Both are measurable with what now exists.

## Reproduce

```bash
uv run pytest tests/test_solvency_surface.py
uv run python -u scripts/solvency_transfer.py
```
