---
date: 2026-08-13
author: lead
status: provisional
related: [2026-08-13-language-conditioning-recovers-typology-not-genealogy,
          2026-08-13-forty-two-languages-are-now-renderable,
          2026-08-13-language-id-above-the-parser]
---

# Graded against WALS on 46 languages: the representation reads script, not typology

The first result in this repo scored against an oracle **nobody here wrote** —
640 rows of WALS coding, plus `family`, `macroarea` and `script`, for 46
languages across 15 families and 8 scripts. 1,035 pairs.
`runs/wals46_perlang/typology.json`.

| oracle | Mantel r | p |
|---|---:|---:|
| **script** | **+0.1796** | **0.0104** |
| WALS rendered (14 features — positive control) | +0.0861 | 0.0364 |
| family | +0.0576 | 0.0130 |
| **WALS held-out (4 features — the test)** | **+0.0440** | **0.3659** |
| macroarea | +0.0049 | 0.9318 |

Partial Mantel, script controlled:

| | r | p |
|---|---:|---:|
| WALS rendered (positive control) | +0.0997 | 0.0212 |
| **WALS held-out (the test)** | **+0.0271** | **0.5773** |
| family | +0.0826 | 0.0342 |

## The reading

**Pre-registered expectation confirmed.** Script is the strongest single
correlate. The four WALS features the renderer *never reads* — the only ones
that could show learning rather than arithmetic — are **not significant**
(p=0.37) and remain so once script is partialled out (p=0.58). The
representation has not learned typology.

**The positive control behaves, which is what licenses reading the rest.** The
14 features the renderer consumes correlate at +0.086 and *strengthen* under
script control to +0.100. `derive_profile` builds word order out of exactly
those features, so recovering them is arithmetic — but it proves the instrument
can detect typological signal when it is present, so the null on the held-out
four is about the representation and not about the method.

**Unexpected: `family` is significant and strengthens under script control**
(+0.058 → +0.083, p=0.034). There is a weak genealogical signal that is not
merely orthographic. This directly revisits the earlier six-pack result, where
Indo-European ranked at the median and Spanish's nearest neighbour was Chinese —
on 7 packs of which five were European and two were English. With 46 languages
across 15 families a real if small family signal appears. It is weak enough to
need replication before anything is built on it.

## What it cost to measure, and what that limits

Four attempts to fit one model across all 46 languages died at exit 137 before
printing a line. Measured rather than retried: episodes are ~1 GB, the fit
scales at ~0.4 GB per language, ~4 minutes projected — memory was never the
story, and 137 was the process group being killed. The fix was granularity, not
scale: `scripts/wals_perlang.py` fits **one language per step, 6 s each, written
to its own JSON immediately**, so an interruption costs one language.

**The cost of that, stated plainly: this is the bucketed design, not the
conditioned one.** Each language gets its own tokenizer and its own fit. For a
per-language reliability estimate the two agree — the conditioned model keys
`claw_evidence` by language anyway — but **no claim about conditioning can be
read off this run**.

Two further bounds. The derived grammars are tier 4 (word order from WALS, no
morphology), so the prose differs less across languages than real languages do.
And nothing independent has challenged this; `status: provisional` until
something has.

## What a representation that recovered typology would need

Not claw reliabilities. Those are a 14-dimensional summary of *how often each
structural operator fires*, and word order is about **which of two nodes the
prose mentions first** — a quantity `Surface.position` already computes and the
surface claws discard. The order-relation representation the typology script was
written for is the next thing to try, and it is the one that could move the
held-out four.
