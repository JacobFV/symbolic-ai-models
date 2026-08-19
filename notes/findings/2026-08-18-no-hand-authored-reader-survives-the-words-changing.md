---
title: One extra phrasing per claim kind takes the rules reader from 1.000 to 0.000 — no hand-authored reader survives surface variation, and the per-kind law predicts the collapse to 0.008
date: 2026-08-18
author: lead
status: provisional
tags: [reader, text-to-world, generalisation, negative-result, law-confirmed]
---

## Why this had to be run

The previous cycle put a rules reader at **1.000** on the five-paragraph
surface and called that a fairness check. It is, and it is nothing else: **I
wrote those patterns for that exact phrasing**, so the arm is arm zero for a
different template — precisely the artefact `read.py`'s own docstring warns
about, reproduced one level up by me.

A benchmark on which a hand-written pattern set scores 1.000 cannot measure
reading. So each claim kind now carries **four alternative phrasings**, varying
lexicon rather than word order — *weighs* / *kerb weight* / *unladen* / *tare* —
drawn per case deterministically. The readers are **unchanged**: their patterns
and cue words were written against variant 0 only.

## The curve

`scripts/reader_generalisation.py`, 40 cases. Alignment completeness is checked
at every `V`, so a fall is a reader failure and not a broken ground truth.

| reader | V | claim R | dep R | **non-empty** | alignment |
|---|---:|---:|---:|---:|---|
| rules, full | 1 | 1.000 | 1.000 | **1.000** | ok |
| **rules, full** | **2** | **0.542** | 0.522 | **0.000** | ok |
| rules, full | 3 | 0.362 | 0.396 | 0.000 | ok |
| rules, full | 4 | 0.280 | 0.284 | 0.000 | ok |
| lexical cue routing | 1 | 0.930 | 0.914 | 0.136 | ok |
| lexical cue routing | 2 | 0.518 | 0.550 | 0.000 | ok |
| lexical cue routing | 4 | 0.256 | 0.248 | **0.000** | ok |

> **A single extra phrasing per kind is enough. The rules arm goes 1.000 →
> 0.000 while its recall only halves.**

Recall tracks `1/V` almost exactly — 0.542, 0.362, 0.280 against 0.50, 0.33,
0.25 — which is what a reader matching one of `V` phrasings must get.

## The per-kind law predicts it, and this is its first clean success

The flat law `S = q^k` was demoted last cycle to *screen, not predictor*. The
per-kind form is `S = Π_kind q_kind^{d_kind}`. With one pattern set against `V`
phrasings, `q_kind = 1/V` for every kind, so

```
S  ≈  (1/V)^{Σ d_kind}  =  V^(−6.95)
```

using the ablation-measured mean dependency of **6.95** claims. At `V = 2` that
is **0.008**; measured **0.000** over 22 non-empty cases. At `V = 4`, `4^−6.95 =
1e−4`.

So the law's failure mode is now characterised: it works when the loss is
**pure recall** and over-predicts when a reader recovers claims with the
**wrong value** (the lexical arm at V=1, 0.476 predicted against 0.136). That is
a sharper statement than "screen, not predictor".

## The result

> **No hand-authored reader survives the words changing.** A pattern set and a
> cue-word router are both written against a phrasing, and four phrasings per
> kind takes both to the floor. The argument for a learned or retrieval-based
> reader is now a measurement rather than an assertion.

It also restores the benchmark's headroom: at `V ≥ 2` everything measured so far
scores **0.000**, so there is a full 0→1 range for a mechanism that actually
generalises.

## What would refute it

- **A reader author would write patterns for all four variants.** True, and that
  is the point: the cost of a hand-authored reader scales with the surface
  diversity it must cover, and real prose is not four variants. The curve prices
  that scaling; it does not claim the patterns *could not* be extended.
- **Four variants I wrote myself.** They vary lexicon and syntax and are checked
  to preserve the alignment, but they are not sampled from real reports.
- **The lexical arm is one design.** Cue words that survive paraphrase — say,
  embeddings or a synonym registry — would degrade more slowly. That is the
  obvious next arm and it is now measurable against a benchmark with room.
- **40 cases, one domain.**

## Reproduce

```bash
uv run python -u scripts/reader_generalisation.py
```
