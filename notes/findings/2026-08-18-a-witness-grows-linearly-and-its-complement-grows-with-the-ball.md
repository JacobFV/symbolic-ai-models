---
title: A witness grows linearly in the answer and its complement grows with the search ball — 148x apart on a graph with diameter, 0.2x apart on one without, which is why the 13,987x was an artefact of the instance
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, cost, incremental, openflights, self-correction, refuted-prediction]
---

## Why this was run

`2026-08-18-the-read-set-over-reads-by-6591x-and-the-answer-is-maintainable-at-13987x.md`
maintained a **complete** shortest-path answer at 13,987x and, in the same
breath, named what would break it:

> The hand-derived minimal certificate is only derived for hops ≤ 2, which is
> every case in this sample. The co-holding graph is nearly complete — any two
> filers holding one common large-cap are one hop apart — so this corpus cannot
> exercise deep paths at all. On a graph with real diameter the minimal
> optimality set is the ball of radius `d−1`, which grows. **That is the
> experiment that would break this.**

This is that experiment, run four hours later against my own headline, on the
openflights route network: 3,225 airports with outbound legs, 27,262 flyable
legs at a 2,000 km range limit, 400 random pairs.

**It breaks it.**

## Measured

`scripts/cert_diameter.py`. The witness is the path's edges. The **minimal
optimality dependency** is what a proof of "no path shorter than `d`" must
consult — the destination must be shown to lie outside the ball of radius `d−1`
— computed **meet-in-the-middle**, at radii `⌈(d−1)/2⌉` forward and `⌊(d−1)/2⌋`
backward. That is the *strongest honest* version: the naive one-sided ball would
have inflated every number below in the direction of the hypothesis.

| d (hops) | n | witness | minimal optimality (median) | max | ratio | % of graph |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 1 | **0** | 0 | 0.0x | 0.00% |
| 2 | 17 | 2 | 4 | 29 | 2.0x | 0.01% |
| 3 | 49 | 3 | 9 | 94 | 3.0x | 0.03% |
| 4 | 53 | 4 | 152 | 5,828 | **38.0x** | 0.56% |
| 5 | 52 | 5 | 250 | 4,074 | 50.1x | 0.92% |
| 6 | 39 | 6 | 876 | 9,182 | **146.0x** | 3.21% |
| 7 | 49 | 7 | 4,179 | 12,582 | 597.0x | **15.33%** |
| 8 | 58 | 8 | 5,732 | 13,546 | 716.6x | 21.03% |
| 10 | 29 | 10 | 8,745 | 15,180 | **874.5x** | **32.08%** |
| 12 | 9 | 12 | 6,537 | 16,298 | 544.8x | 23.98% |

Hops p50 **6**, p90 10, max 12.

```
this graph      witness 6.2 edges,  minimal optimality   925 edges,  ratio  148x
13F co-holding  witness 2.5 edges,  minimal optimality   0.5 keys,   ratio  0.2x
```

**Control:** the 21 pairs at `d <= 2` have a median minimal optimality of **3
edges** — small, and comparable to 13F. The two graphs agree where they overlap,
so the divergence across `d` is a property of depth and not of the corpus.

## What this settles, across four corrections in one day

The claim went through three versions and the third is the one to keep.

| version | verdict |
|---|---|
| "the certificate pays where the computation is expensive relative to its dependency" | **wrong** — speedup and survival are anticorrelated and cancel |
| "the lever is the **logical form** of the claim" (after set cover's 95x) | **too strong** — collapsed to 1.4x on 13F shortest path |
| "the lever is the **true dependency** of the claim" (after the 6,591x over-read) | **too weak** — it says nothing about what makes a dependency small |

What the four experiments together say:

> **An existential claim's minimal dependency is the size of its witness, which
> grows linearly in the answer. Its universal complement's is the size of the
> search space that has to be excluded, which grows with the ball.**

Logical form decides the **growth rate**; the instance decides whether you have
travelled far enough along it to notice. On 13F's co-holding graph every pair is
one or two hops apart, so the two curves have not yet separated and the *whole
answer* is cheap to maintain. On a graph with a real diameter they separate by
two to three orders of magnitude by `d = 6`, and past `d = 7` the optimality
certificate is 15–32% of the corpus — which is to say, no certificate at all.

So the bound/answer asymmetry is the **general** case and the 13,987x was the
special one. `2026-08-18-an-optimum-is-two-claims...` was closer to right than
the note that corrected it, for a reason neither note had.

## What to build, finally

- **A kernel should return a witness.** It is `d` edges, `k` filers, one model —
  always small, always checkable, and always available where the answer is
  existential. This is now supported by three measurements rather than one.
- **A kernel should not pretend to return a minimal dependency for a universal
  claim.** It is the excluded search space, it grows, and on a real graph it is
  a third of the corpus. Returning the recorded read set *instead* is worse than
  returning nothing, because it is up to 6,591x wrong and looks right.
- **Maintaining a bound is the product.** Three separate results in this repo now
  say the cheap half of a problem is the useful half — `additive_bounds`, the
  solver rung where the maximum is closed-form and the minimum NP-hard, and this.
  That is no longer a coincidence worth noting; it is the design.

## What would refute this

- **One graph, one range limit, one metric.** The 2,000 km limit is what makes
  the diameter; at 12,000 km the network is nearly complete and this table would
  look like 13F's. The claim is about the *shape of the two curves*, and a
  corpus that never leaves `d <= 2` cannot see it — which is exactly the trap the
  previous finding fell into.
- **No update stream, and none was invented.** This measures dependency *size*,
  not an advantage. Converting it to a maintenance advantage needs a real delta
  for this corpus and there is not one; multiplying by an injected churn rate
  would only report a rate somebody chose.
- **Meet-in-the-middle may not be optimal.** A cleverer certificate for "no
  shorter path" — a distance labelling, a hub-labelling scheme — could read far
  less. If one exists that stays small at `d = 10`, the whole asymmetry weakens.
  That is a real literature (hub labelling, 2-hop covers) and it has not been
  tried here.

## Reproduce

```bash
uv run python -u scripts/cert_diameter.py     # ~1 min
```

`runs/cert_diameter.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `cert-diameter-breaks-the-minimal-certificate`.
