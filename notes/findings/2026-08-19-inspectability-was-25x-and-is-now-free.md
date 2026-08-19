---
title: Inspectability was 25× and is now free
date: 2026-08-19
status: measured
arm: load-bearing-completeness
---

## Strict completeness was the wrong bar

`incomplete` demands the answer be **rebuildable** from the paragraph. The shipped
renderer scores 0.000, and so would any explanation a person would read — a
paragraph reciting 28 facts is worse output, not better. Strict completeness is a
diagnostic and cannot be an objective.

The forgiving version, which the last finding named: does the paragraph cite
every claim **whose deletion changes the answer**?

| | |
|---|---:|
| claims per world | 28.4 |
| **load-bearing** | **10.8 (38%)** |
| shipped renderer covers | **9%** |
| shipped renderer complete | **0 / 18** |

Reachable — 11 facts is a paragraph, not a recitation — and currently unmet. What
is load-bearing is mostly the vehicles (mass 2.11, capacity 2.11 per case) and
the query (depot, needs, demand, 1.00 each); **flooding is load-bearing only 0.22
times per case**, because the network is usually redundant.

## But finding the set cost 25× the answer

One solve per claim: **235 ms/case against 9.1 ms** for the answer it explains.
That is the same shape the soundness work hit — enumeration is affordable until
you want it per claim — so the same fix applies.

## The cheap version, and two attempts at it

Each kind admits an argument that needs no flow solve. Over 73 non-empty cases:

| | exhaustive | cheap |
|---|---:|---:|
| time | 247 ms/case | **0.22 ms/case** |
| recall | — | **1.000** |
| precision | — | 0.881 |

**1140× faster, recall 1.000.** The only over-claim is `flooded` (1.4 per case),
and over-claiming is the safe direction: citing a claim that did not matter makes
a paragraph longer, not wrong. Recall is the property that must hold, and a test
asserts it per claim rather than in aggregate.

**It took two corrections to get there, both the same mistake.** The first version
tested links by **connectivity** — is this a cut edge? — and missed 0.83
load-bearing links per case. A link matters when removing it lowers the
**bottleneck** below a vehicle's threshold; it does not have to disconnect
anything. That is the identical wrong proxy that fired **0 of 270 times** when it
was tried for ordering candidate deletions several findings ago. The second
version tested limits by arithmetic on the largest threshold and missed 0.33 of
each limit kind, for the same reason: a limit binds for a *particular* vehicle on
a *particular* route.

Both were fixed by recomputing the bottleneck without the claim, which is a
Dijkstra rather than a flow solve.

## What this closes

> **Inspectability cost 25.5× and now costs 1.03×** — 0.22 ms against a 9.1 ms
> answer.

That is the same arc as soundness, which went 13.4× by enumeration to 1.0× by
certificate. Both times the expensive version was a per-item enumeration and the
cheap version was a structural argument over the same quantity the kernel already
computes.

The renderer is not yet complete — that is a separate change, and this supplies
the set it would need to cite.

## What would refute this

- Recall 1.000 over 73 cases bounds the miss rate at **4.1%**, not zero. The test
  checks every claim of every case rather than sampling, which is stronger than
  the aggregate, but 40 seeds is still 40 seeds.
- The per-kind arguments are flood's. Scheduling has no polynomial
  characterisation of its decision, so the same construction would need the
  monotone half only — exactly the split the certificate generality finding
  measured.
