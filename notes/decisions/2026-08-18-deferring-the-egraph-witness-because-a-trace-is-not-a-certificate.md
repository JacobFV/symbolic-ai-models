---
title: Deferring the e-graph witness — a merge log is a trace, not a certificate, and the real thing is proof-producing congruence closure
date: 2026-08-18
author: lead
status: decided
tags: [egraph, witness, decision, not-built]
---

## The fork

`tests/test_witness.py::TestWitnessCoverage` classifies `egraph@1` as **could
carry a witness and does not**: its claim is `equivalent_form`, whose witness is
the rewrite sequence, and `SaturationReport` counts rule applications
(`applied[rule.name] += 1`) while keeping no ordered path. It is the only cell in
that map that is a genuine gap rather than a category error, so it was the
obvious next build.

## Why not, yet

The cheap version is a **merge log** — `(rule, class_a, class_b)` in firing order
— and it is not a witness under the contract this repo just adopted.
`Witness.verifies` must say how a reader checks the claim **without re-running
the kernel**, and replaying every merge *is* re-running the kernel. It would also
be an over-approximation of the dependency by exactly the shape measured at
6,591x in
`2026-08-18-the-read-set-over-reads-by-6591x-and-the-answer-is-maintainable-at-13987x.md`:
most logged rewrites have nothing to do with the two terms whose equivalence is
being justified.

The real object is a **proof-producing union-find**: every merge carries the rule
and substitution that justified it, congruence merges carry their child
justifications, and an explanation for `a ⟺ b` is the path between them in that
proof forest. That is what egg does, it is roughly 150 lines against a
389-line module, and it touches `merge`/`rebuild`, which every other e-graph
number in this repo depends on.

So the trade is: **real engineering with a known outcome**, against experiments
whose outcome is not known. `CLAUDE.md` ranks those the other way round, and the
repo has a cheaper falsifier sitting unrun.

## What the witness would be worth, so a later session can judge

Measured value of witnesses elsewhere here: **247x** cheaper verification than
solving (routing), **95x** cheaper maintenance than the universal half (set
cover). An e-graph explanation would let a consumer accept a simplification
without re-saturating, which is the same shape. It is worth building — it is not
worth building *before* the experiments that could change what the substrate
should be doing.

## What would move it up the list

- A flow that **consumes** a simplification and currently has to trust it. There
  is none today; `egraph@1` is called and its output is read as an artifact.
- Evidence that e-graph results are **maintained across corpus updates**, which
  is where a witness pays 95x. Nothing currently re-runs saturation on a delta.

Either of those turns this from a capability with no consumer into one with a
measured price, which is the bar `CLAUDE.md` sets for abstractions.
