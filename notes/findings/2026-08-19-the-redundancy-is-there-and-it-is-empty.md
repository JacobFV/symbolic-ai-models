---
title: The redundancy is there and it is empty — co-occurrence measures topic, not support
date: 2026-08-19
status: measured
arm: blast-radius
---

The blast-radius finding closed on a proposed mitigation: an entity many
companies belong to is an entity many articles mention, so **the redundancy that
makes a hub error expensive should be the redundancy that makes it checkable**,
and the two grow together by construction. This tests it. The elegance was real
and the signal is not.

For an article `X` whose extracted parent is `A`, scan the other 1,660 intros for
one mentioning **both** names. No new reading: a second, independently written
document putting those two names together is outside support; if none does, the
claim rests on one sentence in one article. `runs/hub_corroboration.json`.

## 1. The redundancy is exactly where predicted

| in-degree | answered | **corroborated share** |
|---|---|---|
| 0 | 736 | 0.147 |
| 1–2 | 59 | **0.644** |
| 3+ | 5 | 0.600 |

**Corroboration is available 4.4x more often for hubs**, which is the first half
of the hypothesis and it holds cleanly. Where an error would be expensive, a
second opinion exists.

## 2. And it carries no information at all

| group | claims | precision |
|---|---|---|
| corroborated | 149 | **0.403** |
| uncorroborated | 651 | **0.395** |

`AUC(corroborated → correct) = 0.503`. Chance.

Worse, where it was supposed to matter it points the wrong way: at in-degree 1–2,
corroborated claims are **0.263** against uncorroborated **0.286**.

This is the refutation condition named in advance — *"if corroborated and
uncorroborated claims are equally accurate, co-occurrence is measuring topic
rather than support"* — and it fired.

## 3. Why, and what a real check would need

Two company names appearing in a third article means they are in the same
industry, not that one owns the other. Company intros name competitors,
predecessors, joint ventures and customers, and the corpus is topically clustered
enough that this fires constantly — the same clustering that let BM25 find the
hop-2 article 49% of the time from the question alone.

A corroboration test with content would have to check that the third document
**states the relation**, not that it contains the names. That needs relation
extraction between an *arbitrary pair* of entities, and every reader here is
**subject-relative**: it extracts the parent of the entity the document is about.
An article about a competitor does not state X's parent in a form this reader can
produce, so the cheap version of the check is the only version currently
available, and it is empty.

That is a specific, bounded thing to build if this line is ever worth reopening:
a pair-relative extractor, not a better similarity function.

## 4. What stands

The blast-radius liability stands unmitigated: hub claims are consulted most,
read worst (0.126 against 0.197), and **cannot be cheaply verified**. The
consolation remains that the measured cost is small *in this corpus* (3.5%
relative under ancestor chains) because the graph is shallow — and that is
structure, not a safeguard.

The in-degree signal itself is untouched by this null: it still predicts where
errors are expensive, before any reading, from link structure alone. What it
cannot do is fix them by looking sideways.

## What would have refuted this

Corroborated claims being materially more accurate — the mitigation would then
have been free and available exactly where needed. They were 0.008 better
overall and 0.023 *worse* on the hubs.
