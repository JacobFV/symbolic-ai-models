---
title: The advantage is a property of the structure's provenance, not of the technology — 463× where it was filed, 1.8× where it had to be derived, from the same formula
date: 2026-08-18
author: lead
status: provisional
tags: [cost, north-star, escalation, provenance, gleif, openalex, direction]
---

## Why

The cost arc closed with a hard negative
(`the-million-fold-advantage-is-8x-the-moment-you-escalate-anything`): the
advantage is `1/f`, neither the extractor's accuracy nor the escalated prompt
moves it, and at 0.85 quality the symbolic layer buys **1.8×**.

That finding named its own escape hatch in a single clause — *a task where `f` is
naturally small, regulatory data, where structure is already filed* — and left it
untested. This tests it, from numbers that were on disk before the session began.

**`f` is the fraction of queries the symbolic system cannot settle.** In a derived
domain that is everything the extractor got wrong: **56%** at 0.85 quality. In a
filed domain there is no extraction step to fail — the regulator did it and is
legally accountable for it — so `f` is only what the *data itself* leaves
undetermined, which `HANDOVER.md` §3 records at **0.216%** and **4.274%**.

## The dichotomy

Same formula, same technology, same price sheet.

| regime | **f** | quality | model $ | ours $ | **advantage** |
|---|---:|---:|---:|---:|---:|
| **FILED** — GLEIF `ultimate_parent`, filed-vs-filed | **0.216%** | 1.00 | 6.15e-04 | 1.56e-11 | **463×** |
| **FILED** — same, incl. closure-vs-filed conflicts | 4.274% | 1.00 | 6.15e-04 | 1.56e-11 | **23×** |
| **DERIVED** — OpenAlex affiliation → ROR | **56.0%** | 0.85 | 4.53e-03 | 2.20e-09 | **1.8×** |

**259× between regimes** on the strict filed comparison, **13×** on the
conservative one. The only thing that changes is **whether the structure was
filed or had to be derived**.

## What this does to the session's conclusion

It turns a dead end into a direction. The negative stands exactly as measured —
on a derived-structure task, at deployable quality, the symbolic layer buys 1.8×
and nothing available moves it. But that is a statement about **where the work
was pointed**, not about the approach:

> **The advantage is a property of the domain's structure-provenance.** Where a
> filer, a registry or a regulator has already paid the extraction cost and
> externalised it, `f` collapses to a fraction of a percent and the advantage is
> two to three orders of magnitude. Where structure must be derived from
> observation, `f` is half the workload and the advantage is a factor of two.

This also reconciles the two halves of the session that looked contradictory. The
repo's earlier advantages — measured on GLEIF and SEC, both **filed** — were
real. The extraction arm's 1.8× is also real. They are the same formula evaluated
in two regimes, and quoting either without naming the regime is the error.

## Two caveats that belong next to the number

- **Quality 1.0 in the filed regime is relative to the filing.** The task's
  ground truth *is* the filed ultimate parent, which is the same circularity as
  OpenAlex being its own anchor. It is a better anchor — a legally accountable
  filer beats an automated extractor — but it is not truth, and a filing that is
  wrong makes the symbolic answer confidently wrong with it.
- **`f` counts undetermined answers as escalations, and they may not be.** This
  repo's ambiguity machinery returns the *alternatives enumerated* rather than a
  guess, and a caller that can act on a retained mixture escalates none of them.
  On that reading `f` is lower still and 463× is conservative.

## What would refute it

- **One filed task and one derived task.** The dichotomy is a two-point line. A
  filed domain with a high undetermined rate, or a derived domain where
  extraction is nearly solved, would both compress it.
- **The filed `f` is a property of GLEIF's conflict rate**, which this repo
  measured on one relation of one registry. `ultimate_parent` is unusually clean;
  a filed relation with more contradictory filers has a larger `f`.
- **The comparison assumes the opponent must pay per query.** A model that
  ingests the filed corpus once and answers from weights changes the arithmetic
  entirely, and nothing here measures that.
- **Neither regime's quality is measured against a language model**, which is
  still `ROADMAP.md` 0b and still blocked on credentials.

## Reproduce

```bash
uv run python -u scripts/regime_dichotomy.py     # instant; arithmetic on published numbers
```

`runs/regime_dichotomy.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `the-regime-dichotomy`.
