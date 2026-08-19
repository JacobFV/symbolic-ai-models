---
title: OpenAlex abstracts do not state their affiliations — a second genre is not available from what is on disk
date: 2026-08-19
status: dead
---

The critical path asks for **a second genre** so that the real-text results —
the Heaps exponents, the frame-sparsity story, the crossover extrapolation — can
be told apart from facts about company prose. `data/sources/openalex-prose/`
holds 5,000 scientific abstracts with gold `affiliations` from OpenAlex, which
looked like exactly that: different genre, different relation, gold already
attached.

**It does not work, and the check cost one command.** Of 4,152 abstracts with
affiliations, **152 mention the affiliation at all** — 3.7%. An affiliation is
*metadata about* a paper, not something the abstract says. Distant supervision by
containment has nothing to attach to, and a ceiling of 0.037 makes every
downstream number meaningless.

The same objection applies to the other fields: `topics` and `year` are metadata,
`cited_by_count` is a statistic. Nothing in this corpus is a relation the prose
*states*.

Nothing else on disk supplies prose plus stated-relation gold either — `gleif`
and the `kg-*` artifacts are structured records with no text, `gutenberg` is text
with no gold, `courtlistener` has text and citation structure that would need its
own extraction target defined first.

## What partly answers the question anyway

The exponent measurement was already run on **three relations within the
Wikipedia genre**, and it does not come out constant:

| relation | full-path β | content-word β |
|---|---|---|
| `parent` | 0.830 | **0.641** |
| `headquarters` | 0.933 | **0.702** |
| `country` | 0.920 | **0.921** |

`country` does not benefit from the content-word representation at all, because a
country is written *adjacent* to a city — *New Delhi, India* — with no lexical
trigger to key on. So **β ≈ 0.65 is not a constant of relation extraction**; it
is a property of relations that have a lexical trigger, and the crossover
extrapolation built on it inherits that condition.

That is a weaker answer than a second genre would give, and it is the answer
available. A genuine second genre needs a corpus where the relation is *stated*,
and building one is a fetch-and-annotate job rather than something waiting on
disk.
