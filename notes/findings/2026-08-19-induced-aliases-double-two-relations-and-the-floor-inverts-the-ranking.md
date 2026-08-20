---
title: Induced aliases double two relations — and the floor inverts the ranking
date: 2026-08-19
status: measured
arm: relation-readability
---

Head-stripping turns `automotive industry` into the alias `automotive` and cannot
touch `country`, whose derivations are suppletive. **Label association can**: a
word appearing in articles whose gold is `Japan` and rarely elsewhere is an alias
for `Japan` whatever its spelling. Induced per fold from training articles only,
used both to propose (reporting the canonical value) and to supervise, since the
previous finding showed the two must move together.

| relation | aliases | baseline | **induced** | Δ | example aliases |
|---|---|---|---|---|---|
| `parent` | 1 | 0.140 | 0.144 | +0.004 | `russian→Rostec` |
| `country` | 93 | 0.182 | **0.390** | **+0.207** | `ftse→United Kingdom` |
| `headquarters` | 44 | 0.254 | 0.280 | +0.026 | `england→London` |
| `founder` | **0** | 0.098 | 0.098 | **+0.000** | — |
| `industry` | 142 | 0.114 | **0.238** | **+0.124** | `records→phonographic industry` |

The prediction held on every row: `country` gains most, `industry` gains again on
top of head-stripping, and the three whose values are named literally are flat.
**`founder` induces zero aliases** — a person is not referred to by a derived
word — which is the cleanest control the mechanism could have.

## Then the floor, which this repo insists on and which I nearly skipped

| relation | majority floor | commonest value | induced | **above floor** |
|---|---|---|---|---|
| `headquarters` | 0.045 | new york city | 0.280 | **+0.235** |
| `industry` | 0.061 | automotive industry | 0.238 | **+0.177** |
| `parent` | 0.010 | the walt disney company | 0.144 | +0.134 |
| `founder` | 0.006 | government of russia | 0.098 | +0.092 |
| **`country`** | **0.298** | **united states** | 0.390 | **+0.092** |

**`country`'s floor is 0.298** — always answering *United States* is right nearly
a third of the time. So:

- the **baseline 0.182 is below its own floor** — the reader was worse than a
  constant;
- the induced arm's **0.390 is +0.092 above it**, which is real and is the
  difference between useless and useful, but is not "more than doubles";
- and by the measure that matters, **`country` is the weakest relation of the
  five**, tied with `founder` — an exact inversion of the raw-accuracy ranking
  where it looked second-best.

The headline gain and the headline relation were both artefacts of quoting
accuracy without its floor, on a relation whose answer distribution is extremely
skewed. This repo's own lesson note says to audit the floor before quoting a lift;
this is the sixth time it has changed a reading and the first time it changed a
ranking.

## What is genuinely established

- **Distributional alias induction works and is general.** It recovers what
  morphology cannot see, and it self-limits: relations whose values are named
  literally induce almost no aliases and gain almost nothing.
- **`industry` end to end**: 0.000 (impossible) → 0.025 → 0.097 → **0.238**, all
  from measurements rather than guesses, and **+0.177 above floor** — the second
  strongest relation measured.
- **`headquarters` is the strongest** at +0.235 above floor, and was never the
  relation any headline pointed at.

## What is not

Some induced aliases are **priors, not paraphrases**: `ftse→London` and
`british→London` encode *British companies are usually headquartered in London*,
and `russian→Rostec` is a correlation with one conglomerate. Those raise accuracy
by guessing well rather than by reading, and the mechanism cannot currently tell
the two apart. The honest description is *a learned prior over values, conditioned
on cheap surface cues* — useful, and not the same as reading the relation.

## What would have refuted it

`founder` gaining. It induces zero aliases and moves by zero, which is what the
mechanism predicts for a relation whose values are only ever named outright.
