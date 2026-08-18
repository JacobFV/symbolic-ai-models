---
title: Downstream sensitivity cannot be declared — two predictors refuted, and the statistic that might work costs more than the measurement
date: 2026-08-18
status: provisional
tags: [kernel-abi, composition, error-propagation, negative-result, geo]
---

## The gap this closes

Yesterday's composition finding ended by naming a hole in the kernel ABI. A
manifest carries a **per-kernel tolerance** — `geo@1` is accurate to ~0.5% — and
that number, though true, is not the one a caller needs, because callers
compose. On the openflights routing task the same 0.5% metric error produced
amplification of 1.6x, 8.3x and 44.0x at three different range limits.

The obvious repair is to make the manifest carry the amplification, or a
function of some cheap property of the data. **This is the attempt to do that,
and it failed twice.**

## Prediction 1: amplification tracks connectivity

Rationale from the earlier finding: at a tight limit the surviving network is
fragmented so a bad edge corrupts only its component; near-connected, every long
leg lies on enormous numbers of shortest paths. Predicted **Spearman ≥ 0.9**
between reachable fraction and amplification.

Ten range limits, ~390,000 pairs each:

| limit | edges surviving | reach fraction | legs flipped | answers changed | amplification |
|---|---|---|---|---|---|
| 500 | 0.213 | 0.038 | 0.0351% | 0.0597% | 1.7x |
| 750 | 0.334 | 0.098 | 0.0810% | 0.4905% | 6.1x |
| 1,000 | 0.443 | 0.157 | 0.0864% | 0.1479% | 1.7x |
| 1,500 | 0.613 | 0.277 | 0.0405% | 0.1245% | 3.1x |
| 2,000 | 0.736 | 0.366 | 0.0513% | 0.4375% | 8.5x |
| 3,000 | 0.856 | 0.543 | 0.0486% | 3.1590% | **65.0x** |
| 4,000 | 0.911 | 0.864 | 0.0189% | 0.8855% | 46.9x |
| 6,000 | 0.946 | 0.972 | 0.0378% | 0.1867% | 4.9x |
| 10,000 | 0.992 | 0.980 | 0.0054% | 0.2202% | 40.8x |

**Spearman 0.650. Refuted.** And the sequence 1.7, 6.1, 1.7, 3.1, 8.5, 65.0,
46.9, 4.9, 40.8 is not a noisy monotone trend — it is not a trend. The tidy
mechanism I offered yesterday for *why* amplification rises with connectivity
survives as an explanation of the endpoints and does not predict the middle.

## Prediction 2: it tracks the centrality of whatever flipped

If aggregate density does not explain it, the identity of the perturbed edge
should: a flipped hub route moves many answers, a flipped backwater moves none.
Predicted **Spearman ≥ 0.85** using degree-product as an edge-centrality proxy.

| statistic | Spearman against the observed change rate |
|---|---|
| max degree-product of flipped legs | **+0.333** |
| summed degree-product of flipped legs | **+0.283** |
| number of flipped legs | **+0.067** |

**Refuted, and harder than the first.** The *number* of perturbed edges is very
nearly uncorrelated with the damage they do, which is the single most useful
sentence here: **the size of a perturbation says almost nothing about the size
of its consequence.**

## What follows, and it is not a caveat

Degree-product is a weak proxy; true edge betweenness might well predict this.
That is the decisive argument rather than a limitation:

> **Brandes on this graph costs more than measuring the sensitivity directly.**
> Edge betweenness over 3,257 nodes and 37,042 edges is O(VE) ≈ 1.2e8 operations;
> the direct measurement is a few hundred traversals and finished in seconds.

When the statistic that would let you *predict* the answer is more expensive
than *computing* the answer, prediction is not the design. So downstream
sensitivity is an **experiment**, in the same shape as the margin profiler:
perturb the input the way a real degradation would, run the real computation,
count how many answers moved.

## Built

`symbolic_ai_core/runtime/sensitivity.py` — `profile_sensitivity`,
`input_delta_rate`, `SensitivityReport`. Generic over the computation, so any
kernel or composition can be probed. Three decisions worth naming:

- **Amplification is `None`, never `0.0`, when no input moved.** A perturbation
  that changed nothing tells you nothing, and 0.0 reads as "this composition is
  insensitive" — a claim the experiment did not make.
- **Input deltas compare over the union of keys**, so a perturbation that
  deletes or invents an input counts as a change rather than shrinking the
  denominator and understating itself.
- **An absent answer is a value.** "unreachable" against "three hops" is a
  change; treating absence as a gap would drop exactly the cases a perturbation
  creates.

## What would refute it

- One graph, one perturbation family. Haversine-vs-Vincenty is small, unbiased
  and well-behaved; a systematic or heavy-tailed input error would behave
  differently and I have not tried one.
- The change-rate estimates rest on a handful of flipped edges — 2 at the
  10,000 km limit. The *rate* is measured over hundreds of thousands of pairs
  and is stable, but which edges happen to sit near a threshold is idiosyncratic
  to this data, and that idiosyncrasy is most of what the table shows.
- Sampling matters more than it looks: profiling the same composition over 6,000
  sampled pairs gives 10.4x where 810,000 pairs give 8.5x. Small-count
  statistics remain this repo's oldest way of being confidently wrong, and the
  profiler reports raw counts alongside every rate so the reader can see n.
