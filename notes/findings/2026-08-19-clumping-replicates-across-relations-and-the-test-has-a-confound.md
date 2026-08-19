---
title: Clumping replicates across three relations — and the test has a confound that ranks them
date: 2026-08-19
status: measured
arm: multi-hop-world
---

The promotion queue's open gap was **a second relation**: the hand reader's
clumping was measured only on `parent`. `company_relations.jsonl` had country and
headquarters gold for 168 qids, of which **15** of the 415 chain pairs had it on
both ends — the exact sample size this session wrote a lesson note about. So the
gold was fetched instead: P17 and P159 for all 2,502 articles, 51 batched
requests, **94% with a country and 96% with a headquarters**.

`runs/neighbour_correlation.json`.

## Three relations, and a prediction refuted

`P(parent article read correctly | child article read correctly)` against the
marginal, over 415 pairs:

| relation | reader | P(par) | \| child ok | \| child bad | odds | χ² p | n both |
|---|---|---|---|---|---|---|---|
| `parent` | learned | 0.092 | 0.094 | 0.091 | 1.04 | 0.857 | 5 |
| `parent` | **hand** | 0.171 | **0.288** | 0.146 | **2.36** | **0.006** | 21 |
| `country` | learned | 0.176 | 0.356 | 0.154 | 3.03 | 0.002 | 16 |
| `country` | **hand** | 0.711 | **0.799** | 0.548 | **3.28** | **<0.001** | 215 |
| `headquarters` | learned | 0.212 | 0.243 | 0.206 | 1.24 | 0.595 | 17 |
| `headquarters` | **hand** | 0.198 | **0.339** | 0.174 | **2.43** | **0.006** | 20 |

**Predicted `country` would clump *least* for the hand reader**, because
`read_country` keys on a closed class of nationality adjectives applied uniformly
rather than on phrasing style. It clumps **most**, at p < 0.001 on 215 events.
Refuted — and the reason is not the mechanism.

## The confound, which I did not anticipate and which is measurable

A chain neighbour is not just a differently-written article. For some relations
it has **the same answer**:

| relation | chain pairs sharing a gold value |
|---|---|
| `country` | **271/355 = 0.763** |
| `headquarters` | 103/378 = 0.272 |
| `parent` | **19/415 = 0.046** |

Three quarters of parent-child company pairs are in the **same country**. So
correlated success on `country` can come from *the answer being easy* — `United
States` is read reliably wherever it appears — rather than from the article being
canonically written. The test cannot tell those apart.

That ranks the three relations by **validity, not by effect size**:

- **`parent` is clean** (4.6% answer sharing). A child's parent and its parent's
  parent are different entities almost always.
- **`headquarters` is mildly confounded** (27%).
- **`country` is badly confounded** (76%) and should not be used to test this.

## What survives, and it is more than before

**The hand reader clumps on the two relations where the test is valid** — 2.36 on
`parent` (p=0.006) and 2.43 on `headquarters` (p=0.006). Two relations,
independent gold, same direction, same magnitude. The second-relation gap in the
queue is closed for the pattern reader.

**The learned reader does not clump on either clean relation** — 1.04 and 1.24,
p=0.857 and p=0.595 — and its apparent clumping on `country` (3.03) sits at 76%
answer sharing, which is exactly where the confound is largest. The
readers-differ claim survives on the valid rows and the row that would have
contradicted it is the invalid one.

## What this changes about the measurement

Any correlation measured between **graph neighbours** must report how often those
neighbours share the answer. It is a property of the relation, it ranges from 5%
to 76% here, and at the top of that range the test measures answer difficulty
wearing a correlation's clothes. That is now checked in the script rather than
assumed.

## What would have refuted the surviving claim

The hand reader failing to clump on `headquarters`, the second clean-ish
relation. It clumped at 2.43 with the same p as `parent`.
