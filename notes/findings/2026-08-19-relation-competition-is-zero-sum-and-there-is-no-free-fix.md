---
title: Relation competition is real, large, and zero-sum — there is no free fix
date: 2026-08-19
status: measured
arm: relation-competition
---

`owned_by` reads **0.006** fitted with seven relations and **0.058** fitted with
two — a 10x swing from nothing but how supervision is shared. Distant supervision
labels a sentence for whichever gold string it contains, and when two relations
are both present the longest match wins, so a sentence naming a parent *and* an
owner is a positive for one and a **false negative** for the other.

**The mechanism is confirmed:** of 936 articles carrying both `parent` and
`owned_by` gold, **687 — 73.4% — give them the same value**. Identical strings
tie, the tie breaks on tuple order, and `parent` is listed first.

Three supervision policies, seven relations:

| relation | joint (all 7) | binary (alone) | joint + **multi-label** | vs joint |
|---|---|---|---|---|
| `parent` | **0.151** | 0.131 | 0.070 | **0.5x** |
| `country` | 0.184 | 0.184 | 0.178 | 1.0x |
| `headquarters` | 0.254 | **0.288** | 0.276 | 1.1x |
| `founder` | **0.107** | 0.097 | 0.087 | 0.8x |
| `industry` | **0.117** | 0.091 | 0.066 | 0.6x |
| **`owned_by`** | 0.005 | 0.053 | **0.067** | **13.3x** |
| `legal_form` | 0.002 | 0.002 | 0.003 | 1.5x |
| **total correct** | **1669** | 1711 (1.03x, **seven fits**) | 1516 (**0.91x**, one fit) |

## Every policy is wrong somewhere

**Predicted binary would win everywhere and most on the overlapping relations.**
Half right: it wins 7.6x–10x on `owned_by` and **loses** on four of seven, for a
net **1.03x at seven times the fitting cost**.

**Multi-label — making a shared sentence a positive for every relation it states —
rescues `owned_by` completely** (0.005 → 0.067, beating even binary) and **halves
`parent`** (0.151 → 0.070). Net **0.91x**. It does not create supervision; it
**redistributes** it, and the relations that were winning the tie-break pay for
the one that was losing.

> **Relation competition is zero-sum.** The tie-break allocates a fixed pool of
> sentences. Every policy tested moves the pool around, and the totals differ by
> less than 10% while individual relations move by 13x.

## What to actually do

- **Fit jointly by default.** It is the best total at one fit, and beats binary on
  four of seven.
- **Fit a starved relation separately.** A relation whose gold values coincide
  with another's — measurable in advance, 73.4% here — will be starved by the
  tie-break, and a single extra fit recovers 10x for it.
- **Do not use multi-label as a general policy.** It is the intuitive fix and it
  is a net loss.

The screening question is cheap: **how often do two relations share a gold value
on the same article?** Above some threshold, expect the later-listed one to be
starved, and give it its own fit.

## What would have refuted this

Multi-label winning overall. It was the principled fix — *X, a subsidiary of Y*
really does state both that Y is the parent and that Y is an owner — and it costs
9% of the total.

## Limits

- **One corpus, seven relations, one tie-break rule** (longest gold string, ties
  by tuple order). A different rule redistributes differently.
- `legal_form`'s row is 2–3 correct answers and carries nothing.
- The joint column here differs slightly from earlier runs (parent 0.151 against
  0.143) because this fits with `alias_heads` and proposer-routed supervision;
  comparisons within the table are like-for-like.
