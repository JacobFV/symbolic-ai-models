---
title: WordNet populates two of the essay generator's eight rhetorical sections nowhere, a third almost nowhere, and CSKG fills exactly the two it cannot
date: 2026-08-18
author: lead
status: provisional
tags: [substrate, generator, knowledge-source, refuted-prediction]
---

## How it was found

Making the essay generator's implicit contract explicit. `essay.py` takes
`kg: Any` and reaches into it by name — `getattr(kg, spec["accessor"])(n)` — so
it is generic in the sense that anything with those attributes works and *not*
generic in the sense that anything says what they are. Writing that contract
down as a **detected capability set** (`symbolic_ai_core/data/knowledge_source.py`)
meant measuring what the registered sources actually populate, and the
measurement said something nobody had written down.

Detection rather than declaration is the load-bearing choice: a source that
exposes `properties_of` and returns an empty tuple for every node has the
capability in name only.

## Measured

Share of sampled nodes for which each section's accessor returns anything:

| section | accessor | wordnet | cskg |
|---|---|---|---|
| placement | `hypernyms` | 0.729 | 0.639 |
| varieties | `hyponyms` | 0.270 | 0.248 |
| composition | `parts_of` | 0.377 | 0.102 |
| substance | `substances_of` | 0.168 | 0.006 |
| membership | `members_of` | **0.004** | **0.000** |
| qualities | `properties_of` | **0.000** | 0.084 |
| behaviour | `abilities_of` | **0.000** | 0.037 |
| contrast | `siblings` | 0.580 | 0.600 |

And on the topics an essay is actually drawn from — nouns with ≥3 populated
sections, 400 sampled:

| section | wordnet | cskg |
|---|---|---|
| placement | 0.113 | 0.938 |
| varieties | 0.613 | 0.762 |
| composition | 0.098 | 0.117 |
| substance | 0.005 | 0.010 |
| membership | 0.003 | **0.000** |
| qualities | **0.000** | 0.405 |
| behaviour | **0.000** | 0.230 |
| contrast | 0.925 | 0.990 |

| | wordnet | cskg |
|---|---|---|
| rich topics | 1,074 | 2,467 |
| of nodes | 13,810 (7.8%) | 30,315 (8.1%) |

## What it means

**Every essay corpus this repo has generated is missing three of its eight
rhetorical sections.** `qualities` and `behaviour` have never fired at all on
WordNet, and `membership` fires on 0.3% of topics. The generator has eight
section templates; five of them have ever been seen.

That is a substrate fact of the kind this repo's own lessons say outweighs model
differences, and it was invisible because nothing failed. A missing section is
not an error — it is one fewer paragraph, and a corpus five-eighths as
rhetorically varied as intended reads exactly like one that is not.

**The two sources are complementary, not interchangeable.** CSKG fills exactly
the two sections WordNet cannot, at 0.405 and 0.230 of rich topics. This does
*not* overturn the 2026-08-15 decision to skip a CSKG **curriculum** arm — that
was about the flatness of its `IsA` taxonomy for variable binding, a different
use — but it does say the essay generator's best source is neither of them
alone.

## Prediction, and what missed

Predicted before the numbers: WordNet would yield far more rich topics than
CSKG, because the repo's own note calls CSKG's taxonomy flat and noisy.
**Wrong.** The rates are nearly identical (7.8% vs 8.1%) and CSKG has 2.3× more
in absolute terms. Flatness costs CSKG on `composition` and `substance`, not on
whether a topic clears the three-section floor at all.

The zero results were expected — `symbolic_ai_kg`'s own docstrings say WordNet
carries no property assertions and CSKG carries 30,513 — but nobody had joined
that to the essay generator's section list, which is the whole content of this
note.

## What would have refuted it

- **The audit reporting zeros because the audit is broken.** WordNet's
  `placement` is 0.729 and `contrast` 0.580 on the same instrument, so it is not
  a detector that returns nothing.
- **The zeros being a sampling artefact.** The stride sample covers 512 nodes of
  13,810; the section-level count is over 400 *rich topics* independently, and
  both give exactly 0.000.
- **The accessor existing but being called wrongly.** `Declared`, a test double
  exposing every accessor and returning `()` from all of them, is detected as
  present-but-unpopulated — which is the same shape as WordNet's real behaviour
  and the reason detection is not declaration.

## What follows

The generator now refuses **before generating anything** when a source cannot
supply the five capabilities it genuinely needs, naming what is missing and what
is lost. It deliberately does **not** refuse for the other three: WordNet
populates two of them nowhere, and refusing would refuse every corpus this repo
has measured. `sections_available(kg)` reports them instead, so a corpus can
carry its own coverage rather than being assumed complete.

The obvious next arm is a **composed** source — WordNet's taxonomy and
meronymy with CSKG's properties and abilities — which would be the first essay
corpus able to fill seven of eight. It is also the first place the federation
layer's composite double-count warning becomes live, since CSKG already contains
WordNet.
