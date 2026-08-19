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

## I acquired the bridge, and it buys 29% rather than 68×

The section above ends by calling the cliff *"a data acquisition problem — one
crosswalk file"*. So I acquired one. GLEIF publishes a free daily **ISIN → LEI**
mapping, and for US securities `isin[2:11]` **is** the CUSIP — and 13F holdings
are CUSIP-keyed. That is an exact-identifier join between two filed sources, the
first in this repo that does not go through names.

| | | |
|---|---:|---|
| US CUSIPs carrying an LEI | 2,281,221 | the mapping |
| distinct CUSIPs held across 13F | 33,656 | the workload |
| **bridged** | **7,503 (22.3%)** | 5,436 legal entities reached |
| **ambiguous among the bridged** | **0 (0.0000%)** | an identifier hits or misses |

Ambiguity behaves exactly as predicted — **zero**. Coverage does not: I predicted
40–70% and it is **22.3%**.

And a coverage gap **escalates exactly as an ambiguity does**: a query the bridge
cannot answer still has to go somewhere. So:

| policy | **f** | **advantage** |
|---|---:|---:|
| name join alone *(a different join — see the correction below)* | 14.70% | 6.8× |
| **identifier join alone, per distinct security** | **77.71%** | **1.3×** |
| ~~bridge, then names where it misses~~ | ~~11.42%~~ | ~~8.8×~~ **INVALID** |

> **CORRECTION.** The struck row multiplied the *coverage* of the CUSIP→LEI join
> by the *ambiguity* of the CIK→LEI **name** join. Those are different joins over
> different entity types, and there is no name fallback for a CUSIP because
> CUSIPs are not names. See
> `notes/findings/2026-08-18-three-sources-two-joins-and-an-answer-that-has-to-be-an-interval.md`.
>
> **And coverage has two denominators.** 22.3% is per *distinct security*; per
> *position held* it is **58.8%**, because portfolios concentrate on widely-held
> large caps and those are the issuers that carry an LEI. So the identifier join
> alone is `f = 41.2%` on portfolio workloads, not 77.7%.

> **The bridge does not close the cliff. It converts it from an ambiguity
> problem into a coverage problem, and coverage is the larger of the two.**
> Acquiring exactly the data the previous section asked for buys **1.29×**, not
> 68×.

**So that section's closing claim is mostly wrong**, and this is what replaces
it: the cliff is not about the absence of an identifier, it is about the absence
of an identifier **that covers the workload**. A mapping built for *registered
securities* covers a fifth of what an institutional portfolio actually holds —
the rest being funds, options, foreign lines and small issuers that never needed
an LEI.

The general lesson for federation: **a name join and an identifier bridge fail in
ways that do not compose into a small number.** The name join is universal and
uncertain; the bridge is certain and partial. A federated substrate needs both
plus a policy, and that policy's `f` is the **product** of the two failure rates,
not the smaller of them.

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
