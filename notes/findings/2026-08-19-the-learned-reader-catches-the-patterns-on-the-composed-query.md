---
title: The learned reader catches the hand patterns on the composed query — while still behind on both its parts
date: 2026-08-19
status: measured
arm: composed-query
---

`parent(c,p) JOIN country(c,X)` — *which groups control companies in X?* — is the
north-star shape: stated in no article, existing only in a world assembled from
all of them. It was last measured before the reading arm's work.

| arm | `parent` | `country` | JOIN precision | recall | **F1** | was |
|---|---|---|---|---|---|---|
| learned | 0.099 | 0.381 | **0.255** | 0.058 | **0.092** | 0.036 |
| hand | 0.143 | 0.650 | 0.140 | 0.067 | 0.089 | 0.089 |
| **union** | 0.157 | 0.704 | 0.190 | 0.091 | **0.118** | 0.109 |

## The learned reader improved 2.6x and drew level

**0.036 → 0.092.** Predicted "more than proportionally, toward 0.12–0.16" on the
grounds that composition multiplies; measured 2.6x, which is close to the product
of its factor gains (1.2x on `parent`, 2.6x on `country` in this configuration)
and below the predicted band.

The result that was not predicted: **it now matches the hand patterns on the
composed query — 0.092 against 0.089 — while remaining well behind on both
individual relations** (0.099 against 0.143, 0.381 against 0.650).

## How something behind on both parts ties on their join

The join is **set-valued**: for each country, the set of groups controlling any
company there. The hand reader answers far more articles, so it proposes many more
(country, parent) pairs — and its **join precision is 0.140 against the learned
reader's 0.255**. Higher relation recall, lower joined precision.

This is the mirror of the clumping result. A reader whose errors **clump** does
well on a *chain*, because the two hops it needs tend to be the same kind of
article: measured at ratio 1.56 on two-hop questions. The same clumping is a
liability on a *set-valued join*, because correct answers concentrate on a
subgraph and the countries outside it are answered badly or not at all.

> **Error topology has opposite signs for the two composed shapes.** Clumping
> helps a chain and hurts a set. Choosing a reader on single-relation accuracy
> picks the wrong one for both, in opposite directions.

## The union is the best composed-query number this repo has

**0.118**, up from 0.109, with the best recall of the three (0.091). It inherits
the hand reader's coverage and the learned reader's precision, which is the same
gap-filling result found at one hop, now measured where the two error topologies
also combine.

## Limits

- **One join, one corpus.** `parent × country` on 2,502 articles.
- The `parent` figure here (0.099) is below the 0.144 measured in the
  single-relation arm, because this run fits with `RELS = (parent, country)` and
  a per-relation proposer; the comparison inside this table is like-for-like and
  across tables it is not.
- The precision/recall trade is not decomposed per country; the claim that
  clumping concentrates correct answers on a subgraph is an interpretation
  consistent with the earlier measurement, not a fresh measurement of it.
