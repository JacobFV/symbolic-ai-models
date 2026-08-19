---
title: The advantage tracks how many identity boundaries a query crosses — 463× within one filed source, 7× across two filed sources, 1.8× from text; the big cliff is inside the filed regime, not at its edge
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

## CORRECTION, same day: "filed" is not one regime, and the cliff is inside it

The table above treats *filed* as a single regime and quotes **463×** for it.
That is a **single-source** number. A query that crosses two filed sources has
no shared identifier to join on — `kg:sec:cik:*` and `kg:lei:*` are disjoint
namespaces — so the join goes through names, and
`notes/findings/2026-08-18-alignment-not-merge-is-load-bearing-and-the-composition-behind-it-is-unpowered.md`
(which **predates this session**) measured **14.7%** of matched SEC filers as
having more than one GLEIF candidate.

| regime | **f** | quality | **advantage** |
|---|---:|---:|---:|
| FILED — GLEIF `ultimate_parent`, single-source | 0.216% | 1.00 | **463×** |
| FILED — same, incl. closure-vs-filed conflicts | 4.274% | 1.00 | 23× |
| **FILED — SEC → GLEIF alignment, CROSS-SOURCE** | **14.7%** | 1.00 | **7×** |
| DERIVED — OpenAlex affiliation → ROR | 56.0% | 0.85 | **1.8×** |

**68× from single-source to cross-source. 4× from cross-source to derived.**

So the dichotomy I published this morning had the cliff in the wrong place. It is
not *filed versus derived* — that last step is worth only 4×. **The cliff is at
the first identity boundary, inside the filed regime, and it costs 68×.**

That matters more than the number, because **crossing boundaries is what a
federated substrate is for.** A system that only answers within one source does
not need federation; the moment it does, `f` jumps by two orders of magnitude and
the advantage falls from 463× to 7×.

The mechanism, restated to be attackable: `f` tracks **how many identity
boundaries a query crosses.** Within one source, using that source's own
identifiers, nothing is contested but genuine real-world disputes. Across two
filed sources with no shared identifier, the join goes through names. From
unstructured text, the whole structure has to be derived.

## Can the 68× cliff be closed? Not by modelling.

The obvious move: 51.3% of ambiguous matches span more than one country, so add
country to the join key and `f` should roughly halve — 14.7% → ~7.2%, advantage
7× → 14×. It cannot be done on available data, and the reason is structural.

- **SEC entity records carry no country.** `body` is empty on all 44,328
  `finance/13f` entities; `cik_name_2026` has only `id`, `label`, `kind`,
  `same_as`.
- **`same_as` is not a bridge.** It is populated 100% and points at
  `kg:company:name:*` — a *name-derived* canonical key. It is the same name join
  materialised, not an independent identifier.
- **No file on disk links a CIK to an LEI.**
- **GLEIF does carry the discriminator** — `jurisdiction`, `legalAddress`,
  `headquartersAddress` — so the 51.3% country signal sits on exactly **one side**
  of the join.
- **And GLEIF carries an external identifier that is not the CIK.** For NVIDIA,
  `registeredAs` is **2862596**, the Delaware register number; its SEC CIK is
  **1045810**.

> **Federation across two filed sources fails here not for lack of identifiers
> but for a surplus of incompatible ones.** SEC identifies by CIK because it
> files *who is filing*; GLEIF identifies by LEI plus a local company-register
> number because it files *who the legal entity is*. Each is rich, neither
> carries the other's key, and the only attribute both sides hold is the **name**
> — which is exactly why `f` is 14.7%, and why it is not a matcher problem.

So the 68× cliff is **irreducible by modelling**. Closing it is a **data
acquisition** problem — a crosswalk — and that is a different kind of task from
anything this repo has attempted. It is also the highest-value acquisition
available: one bridge file would move the federated advantage from 7× toward the
463× the single-source case already reaches.

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
