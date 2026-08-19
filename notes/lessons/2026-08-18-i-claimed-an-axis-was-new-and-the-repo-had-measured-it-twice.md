---
title: I claimed an axis was new, and the repo had already measured it twice — grep `notes/findings/` before claiming novelty, not just `HANDOVER.md`
date: 2026-08-18
author: lead
status: settled
tags: [epistemics, attribution, handover, prior-art]
---

## The mistake

Across three findings this session I built up an existential/universal
asymmetry — a witness is small, stable and cheap to check; its universal
complement is none of those — and wrote it up as something the work had newly
converged on:

> *"Two unrelated arms, one axis. That is now worth treating as a property of the
> substrate rather than as two observations."*

The repo had measured it **twice, before this session started**, and both
findings are ancestors of the commit I started from:

- `notes/findings/2026-08-18-inspectability-is-asymmetric-the-witness-is-247x-cheaper-and-optimality-costs-double.md`
  — on the **same route network**, with the same existential/universal framing:
  witness verification 247x cheaper than solving, optimality certificate **2.0x
  more expensive** than re-solving.
- `notes/findings/2026-08-18-a-datalog-witness-verifies-flat-while-solving-grows-and-most-of-the-ratio-was-my-engine.md`

And `symbolic_ai_kernels/datalog/proof.py`'s module docstring poses, as its own
**stated open question**, the exact question my witness finding answered:

> *"whether that shape is a property of shortest path or of the
> existential/universal distinction itself"*

Worse, in `notes/decisions/2026-08-18-not-running-the-hub-labelling-refuter-because-the-ball-dominates-it.md`
I argued *analytically* that a distance-labelling certificate must quantify over
every edge and therefore lose — and declined to run it. The prior finding had
already **measured** that: 542.4 µs against 274.8 µs to solve. I re-derived a
result the repo had on disk, and used the derivation to skip an experiment that
had already been done.

## Why it happened, and it is only half my fault

**`HANDOVER.md` mentioned neither finding.** `grep -c "247x\|witness" HANDOVER.md`
returned **0** at the start of this session. The handover I inherited had a §3
"Measured. Do not re-derive these." that omitted the two most directly relevant
results in the repo, so the one document written to prevent re-derivation caused
it.

The other half *is* my fault: `notes/findings/` was on disk the whole time, and
one grep for the word I was building a finding around would have found both.

## What it cost

No wrong numbers — everything measured stands, and the prior work makes the
axis *stronger*, not weaker. What was wrong was the **claim of novelty**, which
is a research claim like any other and was made without checking. It also cost
the framing: three findings present as discovery what should have presented as
**answering a question the repo had already posed**, which is a better story and
a true one.

## The guard

**Before writing "this is new" or "two arms, one axis", grep `notes/findings/`
for the concept, not for the number.**

```bash
grep -rli "witness\|<the concept>" notes/findings/ notes/lessons/ notes/decisions/
```

Two seconds, and `HANDOVER.md` is not a substitute — it is a *curated* view and
curation is lossy by design. The general form: **the handover tells you where the
edge is; it does not tell you what is already known.** For that, search the
notebook.

And the reciprocal duty: **when a finding turns out to answer a question already
posed somewhere in the repo, say so in the finding.** A result that closes a
stated open question is worth more than one that arrives from nowhere, and this
session had three of them and claimed none.

## The same root cause, in code rather than in notes

Hours later, checking whether my hand-rolled cost arithmetic agreed with the
repo's, I read `symbolic_ai_core/cost.py` properly for the first time. It exists
to compute exactly what I had been computing by hand all session, and it encodes
a discipline I had skipped: it divides by **`accuracy - floor`**, never by
`accuracy`, so a system at its floor reports *infinite* cost per unit of
capability rather than a small one. `CLAUDE.md` states the same rule in words —
*a lift is quoted against a floor or not quoted at all* — and I had published five
end-to-end query classes with **no floor at all**.

Audited: nothing retracted, but `collaborators` had **29%** of its score bought by
a guess that ignores the query. And the extraction cost-per-correct bound survived
only because that floor genuinely is 0.000 — dividing by accuracy happened to
equal dividing by accuracy-above-floor. **By luck, not by discipline.**

So the guard generalises past `notes/`:

> **Before building an instrument, look for the one the repo already has.** Not
> just for prior *findings* — for prior *code*. A module that computes your
> quantity also encodes the conventions your number has to satisfy to be
> comparable with everything already published, and rolling your own silently
> opts out of them.

The cheap version, and it costs one command:

```bash
ls symbolic_ai_core/ && grep -rl "<the quantity>" symbolic_ai_core/ symbolic_ai_kernels/
```


## Fourth instance, and the count is now the point

Testing whether `f` is small for *all* filed relations or only for GLEIF's, I
needed the ambiguity rate of a cross-source alignment. It was already measured
and published: **14.7%**, in
`notes/findings/2026-08-18-alignment-not-merge-is-load-bearing-and-the-composition-behind-it-is-unpowered.md`,
which predates this session.

Four instances in one session — the witness axis, the accuracy-above-floor
convention, `cost.py`'s *cheap-and-incapable* docstring, and now this. The
pattern is no longer "I should have looked"; it is that **this repo's prior work
is not reachable from the documents an arriving agent reads.** `HANDOVER.md` is
curated and lossy by design, and `RESEARCH_LOG.md` is organised by narrative
rather than by quantity.

The guard that would actually work is an index by **quantity measured**, not by
finding. Until one exists, the standing move before any experiment is:

```bash
grep -rli "<the quantity>" notes/ RESEARCH_LOG.md symbolic_ai_core/ symbolic_ai_kernels/
```

Run it for the *number you are about to produce*, not for the conclusion you
expect.