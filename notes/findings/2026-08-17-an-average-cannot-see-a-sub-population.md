---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-a-rule-is-verified-on-the-population-its-guard-admits,
          2026-08-17-the-scope-is-in-the-path-and-the-guard-costs-045,
          2026-08-16-first-on-accuracy-eleventh-on-bits,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The fourth candidate missed its target and strictly dominated the model it was built from

**The prediction failed. The unpredicted result is the finding, and it is
recorded in that order deliberately** — retrofitting the hypothesis onto the
number that arrived is the one thing this note must not do.

## What was predicted, and what happened to the target

Four candidate causes for `frontier-001` answering only 55% of the derived
non-copyable bucket while its own rule, guard stripped, answers 100%:

| # | candidate | built as | `acc \| derived, not cp` | verdict |
|---|---|---|---:|---|
| — | `frontier-001` | — | 0.531546 | the thing being explained |
| 1 | the proposal gate | `frontier-002` | 0.531546 | **refuted** |
| 2 | first-match-wins ordering | a diagnostic | — | **refuted**, 0.0000 blocked |
| 3 | the guard language's purity ceiling | a diagnostic | — | **refuted**, see below |
| 4 | one resolver kept per guard | `frontier-003` | 0.531546 | **refuted** |

Four candidates, three variants, and the bucket has not moved by one fill.
Candidate 3 was committed as the surviving explanation earlier today and is also
wrong: the ceiling argument said a rule perfect on a rare sub-population cannot
verify because its guard admits too much else. Measured on
`[phead='obj', slot=1]`, which covers 80% of the derived slot, `map:sib@2` is
**1.000 on the derived members** and 0.179 on the rest — **0.625 overall**,
comfortably above the 0.5 threshold. It would have verified. So purity was not
what killed it.

Instrumenting the fit found what did: for that guard a resolver *is* chosen, and
it is **`const` at score 0.993**. `_verify` keeps one resolver per guard, so the
map — the only resolver that answers the derived slot — is discarded for being
0.625 on average against a constant that is 0.993.

That is a real and general defect, and it is why candidate 4 was built:

> **A rule is ranked by its average over the population its guard admits, and an
> average cannot see a sub-population.** One-resolver-per-guard therefore
> discards, silently and by design, every resolver that is excellent on a
> minority and mediocre elsewhere.

`frontier-003` keeps the best rule of *each form* per guard rather than one
overall. And the derived bucket **still does not move**. So the defect is real,
the fix is real, and it is not what was limiting that bucket. Fifth candidate
unidentified; the honest state is that I do not know.

## What it did instead, which nobody predicted

`runs/full179`, same config, same seeds, same floors as every published row:

| model | lbl acc | lbl bits | **renamed** | drop | type |
|---|---:|---:|---:|---:|---:|
| `frontier-001` | 0.4042 | 7.433 | 0.0345 | 0.3716 | 0.8633 |
| **`frontier-003`** | **0.4040** | 7.445 | **0.2149** | **0.1906** | 0.8607 |
| `frontier-nomap` | 0.2954 | 8.541 | 0.2266 | 0.0682 | 0.8633 |
| `corefer-001` | 0.3572 | 6.952 | 0.3499 | 0.0032 | 0.9458 |

**`frontier-003` strictly dominates `frontier-001`**: the same accuracy to
within 0.0002, and **6.2× the accuracy that survives permuting every symbol**.
`frontier-001` should not be preferred to it for any purpose.

**Independently reproduced on the development split** — different episodes
entirely, seeds from 500,000, `configs/rsi_dev.toml`: 0.4064 → 0.4080 accuracy
and 0.0320 → **0.2112** renamed. The effect is not a property of the evaluation
draw.

**The mechanism is visible in the rule census and needs no interpretation.**
Copy rules go **12 → 102** while maps go 344 → 335. Under a symbol permutation a
map's table keys are all unseen, so its rules decline; `frontier-001` had twelve
renaming-invariant rules to fall back on and `frontier-003` has a hundred and
two. Keeping the best *copy* alongside the best *map* costs 0.0002 of accuracy
and buys 0.18 of equivariance.

## What would make this spurious, and the one check that was run

An unpredicted gain is what this repo distrusts most, so: the obvious way for
this to be hollow is that `frontier-003` simply **abstains** more under renaming
and the 0.2149 is `structural_fallback` wearing the model's name — the exact
shape of
`notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md`.

It was run, and it is the opposite of abstention. Share of fills where any rule
fires, and the share of *those* that are right, over 3,497 fills:

| model | | fired | right\|fired | forms firing |
|---|---|---:|---:|---|
| `frontier-001` | plain | 0.6391 | 0.6134 | map 2146, const 72, copy 17 |
| `frontier-001` | **renamed** | **0.3071** | **0.0940** | map 1031, const 25, copy 18 |
| `frontier-003` | plain | 0.6540 | 0.6043 | map 2022, copy 148, const 117 |
| `frontier-003` | **renamed** | **0.5224** | **0.4001** | map 781, **copy 984**, const 62 |
| `frontier-nomap` | renamed | 0.4512 | 0.5051 | copy 1501, const 77 |

Under renaming `frontier-003` **fires more often than `frontier-001`, not less**
— 0.52 against 0.31 — and is right four times as often when it does. So the gain
is rules answering, not rules declining, and the back-off reading is excluded.

The census says exactly what the mechanism predicted: copy firings go **148 →
984** while map firings fall 2,022 → 781. Keeping the copies does two things at
once, and the second was not anticipated — it *adds* correct answers, and it
*displaces* map rules that would otherwise have fired on stale keys. That second
effect is visible in `frontier-001`'s renamed row: 1,031 maps fire and **9.4%**
of them are right, so most of its surviving firings are confidently wrong rather
than absent.

## What this does not claim

It does not claim `frontier-003` reasons better. Its bits are marginally *worse*
(7.445 against 7.433), it is still 0.19 down under renaming where `corefer-001`
is 0.003 down, and on the derived bucket it is the same model. What it claims is
narrow and, within its scope, strong: **for one line of code, the best-scoring
model in the repo stopped throwing away its renaming-invariant rules.**
