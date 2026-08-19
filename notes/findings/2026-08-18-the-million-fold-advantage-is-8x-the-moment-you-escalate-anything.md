---
title: The million-fold advantage becomes 8.1× the moment anything escalates — and 2.0× at usable quality, because the escalated fraction sets the price and the extractor cannot tell what it knows
date: 2026-08-18
author: lead
status: provisional
tags: [cost, north-star, escalation, extraction, refuted-prediction, headline-correction]
---

## The comparison nobody would actually make

Every cost number in this repo — including the four I put through the repo's own
ledger an hour ago at **1.1M×–2.5M×** — compares a **cheap-and-wrong** system
against an **expensive-and-assumed-perfect** one. Nobody deploys either. The
choice anyone would make is a **hybrid**: let cheap structure answer what it can
and escalate the rest.

The arithmetic of that is brutal and was sitting in plain sight. A model answer
costs $4.535e-03 and ours costs ~2.2e-09, so if a fraction `f` escalates, the
hybrid costs about `f × 4.535e-03` and

> **the advantage is `1/f`.**

Escalating half the work gives 2×. A twentieth gives 20×. **The million-fold
numbers exist only at `f = 0`, which is the same as saying they exist only at
52.6% quality.**

## The frontier

`scripts/escalation_frontier.py`, 6,489 held-out affiliation strings never seen
verbatim. The model's contribution is entered at **perfect accuracy** — the same
generous assumption the ledger uses, and for the same reason: the comparison is
blocked on credentials and a bound that assumes the opponent is perfect needs
none.

| policy | **f escalated** | quality | $/answer | **advantage** |
|---|---:|---:|---:|---:|
| symbolic only, escalate nothing | 0.0% | 0.526 | 2.20e-09 | **2,061,364×** |
| **escalate SILENT only** | **12.3%** | **0.650** | 5.58e-04 | **8.1×** |
| escalate AMBIGUOUS only | 38.3% | 0.712 | 1.74e-03 | 2.6× |
| escalate silent + ambiguous | 50.6% | 0.835 | 2.29e-03 | **2.0×** |
| model only | 100% | 1.000 | 4.54e-03 | 1.0× |

**Escalating the 12.3% of cases where the extractor produces nothing at all
collapses the advantage from 2,061,364× to 8.1×.** Reaching 83.5% quality costs
2.0×. The symbolic layer buys **2× at usable quality**, not a million-fold.

## The extractor cannot tell what it knows

The whole escalation idea rests on the cheap layer identifying its own hard
cases. Three tiers, taken from the extractor's *own structure* rather than a
fitted score — every matched component naming exactly one institution
(`certain`), at least one naming several (`ambiguous`), or nothing matching at
all (`silent`):

| tier | share | **F1** | precision | recall |
|---|---:|---:|---:|---:|
| `certain` | 49.4% | **0.666** | 65.8% | 67.4% |
| `ambiguous` | 38.3% | 0.516 | 49.2% | 54.3% |
| `silent` | 12.3% | **0.000** | 0.0% | 0.0% |

I predicted the confident tier would score **0.85–0.95** and pre-registered
*"high-confidence accuracy below 0.7"* as the result that would change my mind.
It is **0.666**. By my own criterion, stated before the run: **the extractor is
confident and wrong a third of the time.** Certain beats ambiguous by only
+0.150 F1, so the signal separating them is weak.

### The one thing that does work, and it is the opposite of the obvious

**Silence is a better escalation signal than ambiguity.**

| escalate | quality gained | per unit escalated |
|---|---:|---:|
| **silent** | +0.123 | **1.00** |
| ambiguous | +0.185 | 0.48 |
| both | +0.308 | 0.61 |

Escalating the silent tier is **perfectly efficient** — those cases score 0.000,
so every unit of model spend buys a unit of quality and nothing is re-bought.
Escalating the ambiguous tier wastes **half** the spend, because those cases were
already 0.516 right. **Escalate where the system produces nothing, not where it
is unsure.**

That inverts the intuition the tiering was built on, and it is the actionable
half of this finding.

## What this corrects

**The programme's headline metric has been the wrong one.** Cost ratio *at fixed
quality* is the comparison anyone would make, and by that measure the number is
**2×–8×**, not 10⁶. The million-fold figures are not arithmetically wrong — they
price a system nobody would deploy.

And the repo said so first, again. `symbolic_ai_core/cost.py`'s own module
docstring:

> *Cheap-and-incapable is not a point on the cost curve; it is a point off the
> capability axis entirely.*

That is the **third** time this session a result reproduced something already in
the repo — after the witness/complement axis sitting in `notes/findings/`, and
the accuracy-above-floor convention sitting in this very file. The lesson note
covering it now has two instances; this is the third.

## What would refute it

- **The model is assumed perfect on escalated cases.** If it scores 0.9 rather
  than 1.0 the quality column drops and the advantage rises slightly — the
  direction is favourable to us and the magnitude is small, because `1/f`
  dominates.
- **Three tiers, not a tunable threshold.** A real escalation policy would have a
  continuous confidence score and could pick any `f`; this measures three points
  on that curve. The *shape* — 1/f, with silence the efficient tier — is the
  claim.
- **One extraction task.** `f` is a property of how much of a workload cheap
  structure covers, and affiliation linking may be unusually hard or unusually
  easy. The right generalisation is that **every symbolic system's advantage is
  bounded by 1/f for its own f**, which is worth stating whether or not this
  particular 12.3% transfers.
- **Escalation could be cheaper than a full model call.** A smaller model, or a
  retrieval step, would raise the ceiling above 8.1× without changing the shape.

## Reproduce

```bash
SYMBOLIC_AI_PROSE_SNAPSHOT=openalex-prose-2026-08-18-authorship \
  uv run python -u scripts/escalation_frontier.py
```

`runs/escalation_frontier.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `the-escalation-frontier`.
