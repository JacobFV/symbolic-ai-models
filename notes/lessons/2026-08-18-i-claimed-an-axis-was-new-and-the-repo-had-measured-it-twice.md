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
