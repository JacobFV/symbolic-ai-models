---
title: The first arrow is cheap and bad — symbolic extraction from prose wins $/correct-fact by at least 1.77 million times and reaches 53% of a ceiling the task itself imposes, after three attempts to do better bought +0.077
date: 2026-08-18
author: lead
status: provisional
tags: [cost, approach, extraction, openalex, prose, refuted-prediction, ceiling]
---

## What this is

`notes/findings/2026-08-18-the-framing-factor-we-retracted-is-the-amortisation-constant.md`
found that this repo has never priced the first arrow of its own thesis —
`observations -> typed world` — because all 19 catalogued sources arrive already
structured, and there was no corpus on disk on which it could be measured. It
named acquiring one as the highest-value data need.

There is one now, and this is the measurement.

**Getting it.** Three sources tried in order of preference. **CourtListener**
was the best fit — its 77M-edge citation map is *already on disk* as ground
truth and citations appear in opinions as prose — and its v4 API returns **401**;
it now requires a token, and both bulk listings are closed (404 / 403).
**PatentsView**'s bucket listing returns 403. **OpenAlex** is open and
unauthenticated, and it is better than merely available: it ships raw prose and
the structure derived from it *in the same record*. `raw_affiliation_strings` is
text a human typed; `institutions` is that text resolved to ROR identifiers.

`scripts/fetch_openalex_prose.py` put **5,000 works, 5,992,167 characters of
abstracts, and 44,446 affiliation strings** on disk — the first raw prose this
repo has ever held.

## A. The crossover does not transfer, and the dependency is what does

| | GLEIF ownership | OpenAlex prose |
|---|---:|---:|
| corpus | 4.08M tokens | 1.58M tokens |
| **dependency per query** | **41 tokens** | **302.3 tokens** |
| corpus tokens per fact | — | 18.3 |
| **crossover** | **99,512 queries** | **5,242 queries** |

The formula held; the number moved by **19x**. That is what the finding which
introduced it predicted would happen, and it matters how: the crossover is
`corpus / dependency`, and **`corpus` scales with corpus size**, so the crossover
is not a constant and must never be quoted as one across corpora.

The corpus-independent term is the **dependency**, and it is the re-pricing that
was actually asked for: a query's necessary context on prose is **302 tokens
against 41 — 7.4x larger**. The `~5e7` per-query advantage was computed against
an oracle retriever paying for exactly that context, so on prose the retriever
pays 7.4x more and, holding our side fixed, the advantage would *rise*.

Our side does not hold fixed. That is half B.

## B. Extraction agreement, and a ceiling the task imposes

Split by **work**, 3,500 train / 1,500 test, so no string from an evaluated work
built the dictionary. 11,954 held-out affiliation strings.

**Only 15.9% appear verbatim in training** — I predicted 40–60%.

| | n | exact set | Jaccard | precision | recall | **F1** |
|---|---:|---:|---:|---:|---:|---:|
| memoriser, all | 11,954 | 9.2% | 0.117 | 72.8% | 8.8% | 0.158 |
| extractor, all | 11,954 | 13.1% | 0.308 | 34.1% | 36.4% | **0.352** |
| memoriser, **seen** | 1,899 | **58.1%** | 0.738 | 72.8% | 70.7% | **0.717** |
| extractor, seen | 1,899 | 58.1% | 0.738 | 72.8% | 70.7% | 0.717 |
| memoriser, **unseen** | 10,055 | 0.0% | 0.000 | 0.0% | 0.0% | **0.000** |
| extractor, **unseen** | 10,055 | 4.6% | 0.227 | 29.1% | 31.5% | **0.303** |

The two `seen` rows are identical **by construction** — the extractor falls back
to the memoriser whenever the string was seen — and are printed rather than
collapsed so that the fallback is visible rather than inferred.

**The number a memoriser cannot buy is +0.303 F1**, on the 84% of strings it has
never seen. That is the whole of what extraction contributes, and this repo's
oldest trap is reporting the 0.352 instead.

### The ceiling, which was not designed for and is the most useful number here

**On strings the memoriser has seen verbatim, exact-set agreement is only
58.1%.** The same normalised affiliation string maps to *different* ROR sets in
different works, because OpenAlex assigns institutions **per author**, not per
string — an author carries affiliations from sources beyond the one string.

So the label is **not a function of the input**, and **F1 0.717 is a ceiling on
what any string-only extractor can reach on this task**. Anything scoring above
it is using something beyond the string.

Against that ceiling, the extractor's 0.303 on unseen strings is **42%**.

## C. The cost comparison that does not need credentials

`ROADMAP.md` item 0b stamps every accuracy comparison against a language model
NOT QUOTABLE for want of paid API access. This one sidesteps it, by **bounding
the model's side at perfection**:

| | per affiliation string |
|---|---:|
| symbolic extractor | 14,091 ns, **$7.83e-11** |
| model, input tokens only, zero output, perfect extraction | 30.4 tok, **$4.56e-04** |
| raw ratio | **5,829,003x** |

Dividing each by the accuracy it achieves gives **cost per correct extraction**,
and since a model cannot exceed F1 1.0:

> **The symbolic extractor wins cost-per-correct-fact by at least 1,766,210x,
> whatever the model scores.** At F1 0.9 it is 1,962,455x; the bound is
> insensitive because our side is eleven orders below.

## What this actually says, which is not flattering

**The first arrow is cheap and bad.** F1 0.303 on unseen strings builds a world
that is mostly wrong, and winning `$/correct-fact` by a million times does not
repair that — a reasoner over a 30%-correct world produces 30%-correct answers
at whatever price. Every advantage this repo has published sits downstream of an
arrow that, the first time it was measured, performed like this.

That is the honest state of the bet, and it is what the morning's finding
predicted would be found: the advantage is real where structure is **already
filed**, and this is the first measurement of what happens when it is not.

## D. The floor was tested, and it barely moved

The claim above that 0.303 is a floor was the obvious thing to attack, so it was
attacked immediately — `scripts/first_arrow_ladder.py`, same split, same seed,
same evaluation, with the v0 row required to reproduce 0.303 or the ladder is
not measuring the same thing. It does.

| rung | F1 unseen | **% of ceiling** | precision | recall |
|---|---:|---:|---:|---:|
| v0  component vote (the published floor) | 0.303 | 42.2% | 29.1% | 31.5% |
| v1  + IDF weighting | 0.377 | 52.6% | 39.9% | 35.7% |
| v2  + word-overlap fallback | 0.366 | 51.0% | 36.1% | 37.1% |
| **v3  + specificity-first** | **0.379** | **52.9%** | **54.7%** | 29.1% |
| *ceiling (memoriser on seen strings)* | *0.717* | *100%* | *72.8%* | *70.7%* |

**Three principled improvements bought +0.077 and left 47% of the ceiling
unreached.** The weakness is real, not an artefact of a lazy first attempt, and
the headline stands rather than softening.

Two things inside the ladder are worth more than its top line:

**v2 made it worse, and the reason is one this repo already knows.** The
word-overlap fallback fires exactly where component matching found nothing —
where the extractor knows least — and its guesses cost more precision
(39.9% → 36.1%) than the recall they bought. **Abstaining beats guessing**,
which is the same shape as the largest harness effect in this repo's history,
abstention falling back to the structural prior.

**F1 is insensitive to the operating point and the frontier is the object.** v3
moves precision 29.1% → 54.7% and recall 35.7% → 29.1% for a flat F1. For
building a world that will be *reasoned over*, v3 is the rung to ship despite
that: a world with fewer wrong facts is worth more than one with more facts, and
this repo's stated engineering rule is fail-loudly rather than guess.

## What would refute it

- **0.379 is still a floor, only a better-tested one.** ROR's own reconciliation
  service, a learned matcher, or the full institution-name gazetteer would all do
  better than a dictionary built from 3,500 works, and none was tried. The
  correct reading is "symbolic string matching reaches 53% of the task ceiling",
  and the honest open question is whether the residual 47% is reachable by
  anything that is not a model.
- **The anchor is agreement, not truth.** OpenAlex's resolution is itself an
  automated extractor. Every number in halves B and C is *agreement with
  OpenAlex*, and calling it accuracy would repeat the `airport_country`
  circularity found in this repo the same day, where a task's ground truth was
  one side of the disagreement it was scored against.
- **The model's side is unmeasured.** $4.56e-04 is input tokens at published
  rates with zero output and perfect extraction — a lower bound on its cost, and
  the accuracy it would reach is exactly the blocked comparison. The 1.77M bound
  survives that only because it assumes the model is perfect.
- **One task, one corpus, 5,000 works.** Affiliation linking is a
  short-string task; extraction from *sentences* — events, relations, citations
  — is a different problem and is the one CourtListener would have tested.

## Reproduce

```bash
uv run python -u scripts/fetch_openalex_prose.py --works 5000   # ~90s, 16.3 MB
uv run python -u scripts/first_arrow_prose.py                   # ~20s
uv run python -u scripts/first_arrow_ladder.py                   # ~30s, section D
```

`runs/first_arrow_prose.json` and `runs/first_arrow_ladder.json`; predictions,
design refinements and outcomes in `notes/autonomy/predictions.jsonl` under
`first-arrow-on-prose-openalex` and `first-arrow-extractor-ladder`.
