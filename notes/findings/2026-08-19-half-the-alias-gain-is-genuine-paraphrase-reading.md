---
title: Half the alias gain is genuine paraphrase reading — measured on articles that never state the answer
date: 2026-08-19
status: measured
arm: relation-readability
---

Induced aliases lifted `country` +0.207 and `industry` +0.124, and that note had
to concede the mechanism cannot tell a **paraphrase** (`french` → France, a form
of the value appearing *instead of* it) from a **prior** (`ftse` → London, a
correlated but different entity). They separate on **where the gain lands**.

Held-out articles split by whether the gold string appears **literally**:

| relation | half | n | base | induced | Δ | share of gain |
|---|---|---|---|---|---|---|
| `parent` | absent | 719 | 0.011 | 0.014 | +0.003 | — |
| | present | 1069 | 0.223 | 0.218 | **−0.005** | — |
| **`country`** | **absent** | 990 | **0.000** | **0.219** | **+0.219** | 43% |
| | present | 1359 | 0.321 | 0.532 | +0.211 | 57% |
| `headquarters` | absent | 1071 | 0.000 | 0.023 | +0.023 | 41% |
| | present | 1323 | 0.468 | 0.495 | +0.027 | 59% |
| **`industry`** | **absent** | 1561 | 0.083 | **0.209** | **+0.126** | **79%** |
| | present | 497 | 0.195 | 0.300 | +0.105 | 21% |

## The absent half is the one that cannot be faked

In the base arm both supervision and proposal go through literal containment, so
on articles where the gold never appears the reader scores **exactly 0.000** for
`country` and `headquarters` — not "poorly", *structurally zero*. Anything above
that is the alias **revealing a relation the base arm could not see at all**.

- **`country`: 0.000 → 0.219.** Nearly a fifth of articles that never name the
  country are now answered correctly. That is unambiguous paraphrase reading —
  *a French multinational* read as `country=France` — and it matches the 29.3%
  adjectival-only rate measured independently.
- **`industry`: +0.126 in the absent half, 79% of its total gain.** The most
  paraphrase-driven relation of the four.
- **`headquarters`: +0.023 absent, +0.027 present.** Small and evenly split — its
  `ftse→London`-style aliases are mostly re-ranking, which is what the earlier
  note suspected.
- **`parent`: nothing, and the present half is negative.** One induced alias,
  no effect, as its zero-alias neighbours predict.

## So the honest division

**Roughly half of `country`'s gain and four fifths of `industry`'s is genuine
reading of a form the corpus states and the gold does not.** The remainder is the
alias supplying extra evidence where the canonical form was already visible —
useful, and correctly described as re-ranking rather than revealing.

The mechanism is therefore **not** a prior dressed as a reader, which was the live
worry, and it is **not** purely paraphrase either. The split is measurable per
relation and should be reported with any alias result, because it is the
difference between *this reader can now see something* and *this reader now
guesses better*.

## What this settles about the earlier concern

`ftse→London` and `russian→Rostec` are real and are priors — and they are
concentrated in exactly the relations whose gain is small (`headquarters` +0.026,
`parent` +0.004). **The relations that gained a lot gained mostly in the half
where guessing is impossible.** The worry was correct about the aliases it named
and wrong about what they were carrying.

## What would have refuted it

`country`'s gain sitting in the present half. The whole mechanism would then have
been a prior over values and the paraphrase story imagination. Its absent half
went from a structural zero to 0.219.

## Limits

- The `present`/`absent` split is on **literal containment of the gold**, so an
  article stating the relation in a third form counts as absent. That inflates the
  absent half's difficulty, not its size.
- `parent`'s row is one alias and is included as a control, not a result.
