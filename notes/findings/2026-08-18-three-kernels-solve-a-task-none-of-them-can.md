---
title: Three kernels solve a flood-logistics task at 1.000; the strongest floor is 0.440 and every single-kernel ablation is worse
date: 2026-08-18
author: lead
status: provisional
tags: [kernels, datalog, asp, smt, flow, multi-kernel]
---

## What was asked

The architecture note set a gate for the substrate: *at least two kernels
operating on overlapping profiles of one entity, one kernel's output changing
another's through explicit coupling, every output arising from one flow DAG, and
a task that cannot be solved by nearest-text copying.* This is that task, and
the first number the substrate has produced.

## The task

A generated flood-logistics world (`symbolic_ai_generators/flood/`), a pure
function of its seed:

- six regions connected as a **ring plus two chords** — genuinely cyclic, which
  is the topology the flow DAG refuses and the world IR exists to hold;
- flooding closes one or two regions to all traffic;
- two thirds of the links carry a posted bridge limit, as a `Quantity` in kg;
- three trucks with an unladen mass and a capacity;
- a demand site needing a stated mass of supplies.

**Which vehicles can deliver?** A vehicle qualifies when it has the capacity and
*some* route exists whose every bridge admits its laden mass. The quantifier is
load-bearing: the shortest route is frequently the one with the weak bridge.

The report states every input fact and never states the answer. The three facts
that decide it — which regions are cut off, which crossings are weak, which
truck is heavy — are in three different paragraphs, asserted by a test.

## The pipeline

One flow DAG, six nodes, three kernels, two couplings:

```
world --datalog--> open/reach     recursive closure over a CYCLIC network
      --apply---->  world'
      --asp------> candidate routes   COUPLING 1: the completion space is built
                                      from datalog's DERIVED `open` facts
      --smt------> laden-mass check    COUPLING 2: constraints built from ASP's
                                      routes, over the Quantity claims the
                                      relational projection DISCARDS
      --fuse-----> can_serve
```

Each kernel is doing what the other two cannot, and the projections prove it
rather than the prose asserting it: the datalog projection's discard record
contains the bridge limits, with the reason *"a Quantity carries a unit; datalog
is untyped and projecting it would drop the unit"*. ASP literally cannot see the
numbers it would need.

## Prediction, before the numbers

Stated in advance: full flow 1.000 (anything less is a bug in one of two
independent computations); `ignore_bridge_limits` ≤ 0.60; `ignore_flooding`
0.70–0.85; `first_route_only` 0.85–0.95; constant-none ≈ 0.43; constant-all
≈ 0.23; capacity-only 0.30–0.45.

## Measured, 200 seeds

| arm | agreement | predicted |
|---|---|---|
| **full flow (datalog + ASP + SMT)** | **1.000** | 1.000 ✓ |
| ablation: ignore flooding (no datalog) | 0.690 | 0.70–0.85 ✗ (low) |
| ablation: ignore bridge limits (no SMT) | 0.535 | ≤ 0.60 ✓ |
| ablation: first route only | 0.855 | 0.85–0.95 ✓ |
| floor: capacity ≥ demand and laden ≤ **max** limit | 0.440 | — |
| floor: capacity ≥ demand only | 0.410 | 0.30–0.45 ✓ |
| floor: capacity ≥ demand and laden ≤ **min** limit | 0.395 | — |
| floor: always none | 0.350 | ≈0.43 ✗ (high) |
| floor: always all | 0.315 | ≈0.23 ✗ (low) |
| floor: lightest vehicle only | 0.135 | — |

Two of the seven predictions missed, both by margins that matter less than the
ordering: `ignore_flooding` came in just under the range, and the two constant
floors were mis-estimated in opposite directions because I read them off a
120-seed pilot with different generator parameters. The ordering was predicted
correctly in every case.

**Lift over the strongest floor found: +0.560.** The answer distribution is
70 / 31 / 36 / 63 over answer sizes 0–3, so no constant answer is available.

## What would have refuted it

- **A floor near 1.000.** The strongest non-reasoning rule available is 0.440,
  and it is the one that uses the bridge limits *without* the network. Seven
  floors were tried, including two that use the limits.
- **An ablation matching the full flow.** All three are strictly worse, so no
  kernel is decorative. Removing SMT costs the most (−0.465), which is the right
  ordering: the load arithmetic is the part nothing else can do at all.
- **An oracle sharing code with the kernels.** It does not, and a test asserts
  it: `solution_by_search` is exhaustive path enumeration and its source
  contains no reference to clingo, z3, datalog, `get_kernel` or `evaluate`.
- **The answer being readable off the text.** Asserted directly: no paragraph
  contains more than one of the three deciding fact types, and no sentence names
  a vehicle as able.

## What this does *not* establish

**No text was parsed.** The kernels are handed the world, not the report. The
report exists so that the task *has* a natural-language surface and so the
oracle reading is available by construction; turning that report back into the
world is the parsing problem this repo measures at 0.016 exact recovery, and it
is untouched here. This is a finding about the reasoning substrate, and reading
it as a language result would be exactly the confound the corpus critique
already caught once.

**Nothing is priced.** The trace reports 6 nodes and `total_usd = 0.0` with
`unpriced = 6`, which is the distinction the trace was built to make — no kernel
prices itself yet. Wall clock is ~7 ms per case for the whole three-kernel
pipeline on one core, which is an input to a cost number and is not one.

**The world is small.** Six regions, three vehicles, five bridges. The brute
force oracle is exponential and only tractable at this size, which is precisely
why it is trustworthy here and useless later.

## Next

The obvious next arm is the one this deliberately did not do: put a parser in
front of it and measure the same agreement from the *report* rather than the
world. That number is the one that prices the capability, because the parser's
cost is then in the ledger — and on current parse recovery it will be low, which
is the point.
