---
title: The composed query gets harder as the world grows — and the learned reader's gap-filling gets seven times more valuable
date: 2026-08-19
status: measured
arm: composed-query
---

`parent(c,p) JOIN country(c,X)` — *which groups control companies in X?* — is the
north-star shape: the answer is stated in no article and exists only after both
relations are read across the whole corpus. It was measured on **168** articles
with hand-written readers at macro F1 **0.138**. The corpus is now **2,502**
articles with country gold on 94% of them, so the same query can be asked on
fifteen times the world. `runs/composed_query_scale.json`, 53 countries with at
least three gold groups.

## Both halves of the prediction were wrong

| arm | `parent` | `country` | JOIN precision | recall | **F1** |
|---|---|---|---|---|---|
| learned | 0.081 | 0.148 | 0.179 | 0.021 | 0.036 |
| char-only | 0.078 | 0.121 | 0.128 | 0.015 | 0.024 |
| hand | 0.143 | 0.650 | 0.140 | 0.067 | **0.089** |
| **union** | 0.151 | 0.684 | 0.179 | 0.083 | **0.109** |
| *hand, 168 articles* | — | — | *0.207* | *0.119* | ***0.138*** |

Predicted recall would track `parent` and **precision would rise** on a larger
world. Precision **fell** (0.207 → 0.140 for the comparable hand arm) and so did
recall (0.119 → 0.067). **The composed query is harder at scale, not easier.**

## Why, and it is a property of composed queries rather than of this reader

A country's gold answer is the set of groups controlling *any* company there, and
that set **grows with the corpus** while per-article reading accuracy does not.
Fifteen times the articles means roughly fifteen times the groups to recover, and
recall is a fraction of a denominator that grew. Precision falls for the mirror
reason: a larger world admits proportionally more wrong parents into the same
answer set.

So a set-valued composed query **does not benefit from a bigger world unless the
reader improves with it**. That is the opposite of the intuition the persistence
argument invites — more documents make the *world* more valuable and the
*set-valued query over it* harder to answer completely. Both can be true at once
and here both are: ingestion still costs $1.50e-04 once against $6.32e-03 per
retrieval query, and the answers are less complete than they were at 168
articles.

> **Corrected the same day by a control I ran on this note's own claims, and
> both are weaker than written.** The two numbers compared above come from
> *different scripts* — different country gold, different minimum group size,
> different code — which is two numbers rather than a comparison. Subsampling
> inside one code path, and then shuffling the corpus because the file is the
> scale corpus followed by 841 **hub** articles that only enter at the largest
> size:
>
> | articles | hand F1 | union F1 | union gain (file order) | union gain (**shuffled**) |
> |---|---|---|---|---|
> | 200 | 0.178 / 0.103 | 0.182 / 0.094 | +2.1% | **−9.3%** |
> | 500 | 0.123 / 0.084 | 0.127 / 0.098 | +3.8% | **+17.0%** |
> | 1,000 | 0.123 / 0.067 | 0.130 / 0.080 | +6.3% | **+18.9%** |
> | 2,502 | 0.089 / 0.089 | 0.109 / 0.107 | +22.7% | **+19.8%** |
>
> **The smooth monotone rise was an ordering artefact.** Shuffled, the union
> *hurts* at 200 articles (−9.3%), jumps to +17% by 500 and then **plateaus** at
> 17–20%. It does not keep growing, and "sevenfold" is not the shape.
> Section 2's claim weakens the same way: shuffled hand F1 goes 0.103 → 0.084 →
> 0.067 → **0.089**, falling and then recovering rather than declining with size.
>
> What survives: **the union is worth about +19% on the composed query once the
> corpus is above a few hundred articles, and is worth nothing below that** —
> which is still the only place in this session where the learned reader's
> contribution grows with corpus size at all, and it now has a floor and a
> ceiling instead of a trend line.

## The result worth keeping

**The union beats the patterns on every column, and its advantage grew sevenfold
with scale.**

| corpus | hand F1 | union F1 | union's gain |
|---|---|---|---|
| 168 articles | 0.138 | 0.142 | **+3%** |
| 2,502 articles | 0.089 | 0.109 | **+22%** |

The gap-filler finding measured the learned reader's value at one hop on a small
corpus and found it real but modest. On a fifteen-fold larger world it is seven
times larger in relative terms, and for the reason that finding named: the
learned reader answers where the patterns abstain, and a bigger corpus contains
proportionally more articles the patterns were not written for.

**That is the first result in this session where the learned reader's advantage
grows with corpus size**, and it is on the composed query rather than the single
one — where six one-hop levers had already been closed.

## What this does not show

- **53 countries, macro-averaged.** The median gold set is large enough that
  recall is dominated by a handful of big countries; a micro-average would be a
  different number and is not reported.
- The `char` arm is included for completeness and is the weakest everywhere; its
  0.121 on `country` against the word reader's 0.148 is the clearest case in this
  session where lexis matters.
- **Nothing here is compared against an LLM.** The comparison is between readers
  on the same world.

## What would have refuted the surviving claim

The union's advantage shrinking at scale, which would have meant the patterns'
coverage grows with the corpus as fast as the classifier's. It grew from +3% to
+22%.
