---
title: Every evaluation here runs on text this repo wrote
date: 2026-08-19
status: idea
---

## The observation

`data/sources/` holds **37 GB** of real corpora — openalex, courtlistener,
patentsview, sec-edgar, gutenberg, stackexchange, gdelt, geonames, gleif, cskg —
and **every reader, audit, certificate and cost number in this repo is measured
on text the repo generated itself**, with distractors the author wrote.

Today that stopped being an abstract worry twice over. The distractor result
showed the generated surfaces were defanged in all three domains. Then the one
component claimed to be domain-independent, run against 36,223 sentences of real
abstracts, turned out to be **85% false positives**, and the dominant error was a
construction that does not occur in any generated surface at all — the passive of
*use*, *"is used to obtain"*, which no amount of care with the synthetic corpus
could have surfaced.

**The cheap version of this test cost one script and corrected a shipped
component.** That is the argument for doing more of it, not a reason to think the
job is done.

## What is cheap and what is not

Cheap, and worth doing next:

- **Any domain-independent predicate can be run on real prose immediately.**
  Firing rate plus per-cue composition is the whole method, and it needs no
  ground truth. `scripts/gate_on_real_prose.py` is the template.
- **Genre matters and one corpus is not a measurement.** Scientific abstracts
  over-represent the passive and under-represent narrative past. The solvency
  domain imitates **financial filings**, so `sec-edgar` and `courtlistener` are
  the genres whose cue distribution actually bears on it, and they will weight
  `former`, `ceased`, `withdrawn` far higher.

Not cheap, and the thing to be honest about: a **reader** on real text needs
ground truth, and none of these corpora ship claim-aligned spans. The structured
sources (13F holdings, GLEIF, geonames) have facts without prose; the prose
sources have prose without facts. Pairing them is a project, not an arm.

## The version that might work

`sec-edgar` has both: structured 13F holdings *and* the filings they come from.
A reader whose ground truth is the structured table, on prose nobody here wrote,
would be the first end-to-end number in this repo that is not self-generated. It
is the obvious frontier and it is a real build.

The intermediate step, which is one script: take a structured source and a prose
source about the same entities (GLEIF legal entity names against courtlistener or
openalex text) and measure how often the **signature** discipline — entity
prefixes, numbers, dates, value vocabularies — even applies to real sentences.
The audit's whole predictive record rests on signatures being computable, and
that has only ever been checked on text built to make them computable.
