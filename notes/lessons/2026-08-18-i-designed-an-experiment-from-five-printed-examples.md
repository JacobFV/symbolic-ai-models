---
title: I designed an experiment from five printed examples, and the population did not look like them
date: 2026-08-18
author: lead
status: settled
tags: [slices, experiment-design, composition, silent-failure]
---

## The mistake

An error breakdown printed five sample strings from the 1,251 cases where a
symbolic extractor's output was disjoint from the truth:

```
Department of Materials Science and Engineering, University of Wisconsin,
  1509 University Avenue, Madison, WI 53706, USA
Department of Biological Sciences, University of Lancaster, Bailrigg, Lancaster
Botanisches Institut der Universität, Kaiserstraße 12, Karlsruhe, Germany
```

All three name a **city**, and the city is exactly what separates thirteen ROR
"University of Wisconsin" campuses. So the diagnosis wrote itself: the failure is
disambiguation, the evidence is geography, and geography is sitting unread in the
input. I promoted it to the top of `HANDOVER.md` §7 as *"the single
highest-value arm in the repo right now"*, on the strength of five printed lines.

The population does not look like them. **65% of ambiguous components — 2,227 of
3,429 — carry no geographic evidence at all** at the granularity needed. Built
three ways (relaxed admission, strict city-or-region admission, re-ranking only),
the geo view landed at **−0.007, −0.001 and −0.036** against simply abstaining.

## What it cost, and what saved it

About an hour, and it would have cost a published claim. What saved it was a
**control written before the run**: *how often does the second view override the
first, and how often is it right when it does?* Answer: it changed 9.8% of
answers and was better on 23.0% of them, worse on 46.4%. That prints the word
DECORATION rather than leaving a small regression to be explained away as noise.

## Why this one stings

This repo's **oldest and most expensive documented mechanism is the slice
inversion** — `notes/lessons/` and the memory index both record that every
confident wrong reading here came from a small slice or a sampling fixture. I
walked into it while writing a finding that cites the abstention lesson twice,
in the same file, about the same task.

Reading a sample is not the error. **Designing from one is.** A slice may form a
hypothesis and may never size it.

## The guard

**Before promoting a diagnosis to an experiment, count the population it claims
to explain.** One line of code, and here it was already computable: the
`geo_silent` counter that later explained the null could have been printed from
the error breakdown itself, before any of the three variants were written.

Concretely, when an error breakdown suggests a cause:

1. define the signal the cause predicts (here: "the string names a place the
   registry records");
2. **count how many of the failures carry it** — not how many of the five you
   printed;
3. that count is the experiment's ceiling. If it is 35%, no method built on that
   signal can recover more than 35%, and that is worth knowing before building
   three of them.

The general form: **a diagnosis derived from a slice must be sized on the
population before it is built on.**
