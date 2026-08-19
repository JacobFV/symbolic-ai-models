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

## Shrinking `f`, and what it is worth at fixed quality

The finding above names `f` as the lever, so the obvious next move is to shrink
it. The silent tier — strings where nothing in the registry matched — was
diagnosed against the gold institution's own registry names:

| why a silent string stayed silent | share |
|---|---:|
| **gold name genuinely absent from the string** | **68.7%** |
| loses the longest-match race via one rare token | 28.2% |
| gold name is a single token | 2.1% |
| normalisation (`1Georgetown University`) | 1.0% |

Two fixes followed, both mechanical:

- **Match registry names against the whole phrase, not comma-separated
  components.** ROR's canonical name is *"Purdue University West Lafayette"*, the
  affiliation component is *"Purdue University"*, and containment was being asked
  in the wrong direction — the city that completes the name sits three components
  later in the same string.
- **Gather candidates through the K rarest *known* tokens, not one.** The single
  rarest token in a long address is a postcode no registry name contains, so the
  lookup returned nothing. That alone accounted for 28.2% of what remained.

**Silent tier 12.3% → 5.7%. Symbolic-only quality 0.527 → 0.565.**

And now the comparison that matters, because reading a new headline number
against an old one at a *different operating point* is this repo's oldest trap:

| quality target | advantage before | advantage after | **gain** |
|---:|---:|---:|---:|
| 0.60 | 13.6× | **28.7×** | **2.11×** |
| 0.65 | 8.1× | 8.7× | 1.08× |
| 0.70 | 4.4× | 4.6× | 1.05× |
| 0.75 | 3.0× | 3.1× | 1.03× |
| **0.85** | **1.8×** | **1.8×** | **0.98×** |
| 0.95 | 1.2× | 1.2× | 1.00× |

> **Improving the cheap layer doubles the advantage at low quality, buys 3–8% in
> the middle, and buys nothing at deployable quality.** Once most of the work
> escalates, the extractor's accuracy is irrelevant to the price. The symbolic
> layer's quality matters exactly where nobody would ship it.

That is the honest state of the bet: **1.8× at 0.85 quality, and no amount of
work on the extractor moves it.** The lever that would is the *escalation cost* —
a smaller model, a retrieval step, anything that makes the expensive half less
expensive — not the cheap half's accuracy.

### A near miss, recorded

I first computed that table from hand-transcribed tier shares that summed to
**0.954** instead of 1.0, and it reported that the improvements made things
*worse* at every target above 0.60. That is a counterintuitive result with a
plausible mechanism, which is exactly the kind this repo publishes — and I nearly
did. It was caught by checking that the shares summed to one. **Read the numbers
from the run file, not from the terminal.**

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
