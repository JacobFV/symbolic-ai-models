---
title: A reader keyed on entity-type signatures is exactly flat across four phrasings — 0.971 recall at every V while pattern and lexical arms go to 0.000 — and its single failure is coreference through a superlative
date: 2026-08-18
author: lead
status: provisional
tags: [reader, text-to-world, generalisation, coreference, deterministic-vs-learned]
---

## The idea

Both earlier arms were **lexical**: a pattern set and a cue-word router, each
written against a phrasing, and four phrasings per kind took both to 0.000.

The world IR offers something paraphrase does not touch — the **type signature**
of what a sentence mentions: how many regions, how many vehicles, how many
quantities. Signatures alone are ambiguous:

```
(2 regions, 0 qty)   ->  link  OR  bridge_on
(1 vehicle, 1 qty)   ->  mass  OR  capacity
(1 region,  0 qty)   ->  flooded OR depot OR needs
(0 entities, 1 qty)  ->  capacity-by-pronoun OR demand
```

**Paragraph position resolves all but link/bridge_on**, and that last resolves
*structurally*: every bridge carries a load limit, so the bridge pairs are
exactly the pairs appearing in the quantities paragraph. Nothing in the reader
inspects a content word.

## It is exactly flat

`scripts/reader_generalisation.py`, 40 cases:

| reader | V=1 | V=2 | V=3 | **V=4** |
|---|---:|---:|---:|---:|
| rules, full | **1.000** | 0.000 | 0.000 | 0.000 |
| lexical cue routing | 0.136 | 0.000 | 0.000 | 0.000 |
| **type signature** | 0.318 | 0.318 | 0.318 | **0.318** |

Claim recall **0.971** and dependency recall **0.946** at *every* V, to three
decimals. Phrasing-invariant by construction, and it shows.

> **There is a regime crossover.** On a fixed surface the hand-authored reader
> wins outright, 1.000 against 0.318. The moment the surface varies at all it is
> the only reader above zero.

## Its failure is a single mechanism

| kind | present | missing | recall | spurious |
|---|---:|---:|---:|---:|
| **capacity** | 120 | **33** | **0.725** | 0 |
| link | 320 | 0 | 1.000 | **40** |
| flooded, bridge_on, load_limit, mass, depot, needs, demand | — | 0 | **1.000** | 0 |

**Everything with a distinct type signature is recovered exactly.** Two failures
remain and both are understood:

- **link, 40 spurious — exactly one per case.** The disused track between two
  regions outside the affected area has the signature of a link in the
  infrastructure paragraph. It costs precision and nothing else, because it
  connects an isolated component that no route can use.
- **capacity, 33 of 120 missing.** The pronoun sentence *"It can take a further
  N kg"* attaches by **recency**, and its antecedent is named by a **superlative**
  — *"X is the lightest of them"*. Recency picks the last vehicle in the roster;
  the referent is the lightest. The one that loses its capacity drops out of the
  fleet entirely, which is the domain-fact fragility the fidelity finding
  predicted, arriving from the reader side.

## Where determinism stops

The programme asks *which parts of world construction can be deterministic, and
which require learned ambiguity resolution*. This is a clean boundary:

> **Type signature and position recover every claim whose role is fixed by what
> it mentions and where it sits. They stop exactly at reference that is mediated
> by meaning** — a superlative naming its antecedent by a property rather than
> by position.

And the fix is not available cheaply. A rule for *"lightest"* is lexical and dies
under paraphrase (*smallest*, *least heavy*, *lowest kerb weight*) in the same
way the pattern arm did. **This is the first place in the front where a lexical
resource or a learned component is not a shortcut but the only mechanism
available.**

## Why 0.318 and not 0.673

The per-kind law predicts `0.725^1.20 ≈ 0.673` from the capacity recall alone,
against a measured **0.318**. The gap is the same one the law has shown before:
a missing *attribute* removes an entity from the answer's domain, which is worse
than the exchangeable loss the law assumes. Consistent with the law's now-stated
scope — it works on pure recall loss and over-predicts when the loss is
structured.

## What would refute it

- **The section headings are lexical.** The reader keys paragraphs by
  `SITUATION REPORT` / `ROAD NETWORK` / … Those are section labels rather than
  phrasings, but a surface that dropped or varied them would break it, and the
  honest claim is invariance to *sentence* phrasing, not to document format.
- **Position is doing a lot of work**, and it is a property of this generator's
  five-paragraph template. A document with facts in arbitrary order would leave
  the signature ambiguities unresolved — which is the case where the reader
  should **emit** the ambiguity rather than guess, and that is untested.
- **40 cases, one domain, four hand-written variants.**

## Reproduce

```bash
uv run python -u scripts/reader_generalisation.py
```
