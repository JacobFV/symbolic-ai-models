---
title: Half the residual is non-entities, and none of it is direction
date: 2026-08-19
status: measured
arm: residual-taxonomy
corrects: >
  The status note's next-stretch item naming **relation typing** — current vs
  former, parent vs sibling vs child — as the missing primitive. Direction errors
  are essentially absent.
---

## Taxonomise before building

Three times today a primitive was named by intuition and the measurement said
otherwise. So before building anything for the residual, classify it, using
evidence already on disk: Wikidata's **ended** `P749` for staleness, the
organisation-typing cache for non-entities, the identity cache for unresolved
strings.

37 wrong answers out of 99 answered:

| class | n | share |
|---|---:|---:|
| **not an organisation** | **19** | **0.514** |
| other | 11 | 0.297 |
| stale — Wikidata says the relation ended | 4 | 0.108 |
| unresolved string | 2 | 0.054 |
| the subject itself | 1 | 0.027 |

**Over half the errors are non-organisations**, and a typer for exactly that
already exists. That corrects an earlier reading of "entity typing helps a little"
— it helps a little *as deployed*, because the typer's **false negatives** (it
rejects *BBC*, *Bertelsmann*, *CBS Studios*) remove correct answers alongside the
noise, taking coverage 0.589 → 0.411 while precision goes 0.626 → 0.681. **The
bottleneck is the typer's recall, not the idea.**

## And the residual is not what I predicted

I predicted **direction** — a child or sibling picked as the parent — at 25–40% of
errors. It is essentially **absent**. Reading the eleven `other` cases:

```
Box Office Mojo   guess Amazon        gold IMDb
   "...was bought in 2008 by IMDb, which in turn is owned by Amazon."
Teichiku Records  guess Brother Ind.  gold Xing
   "...itself a subsidiary of Brother Industries."
Volkswagen Group  guess Porsche SE    gold Porsche Automobil Holding SE
Chrysler          guess 'Fiat S'      gold Stellantis
Bellator MMA      guess PFL           gold Paramount Global
```

Four different things, none of them direction:

- **transitive depth** — the intro states a *chain* and the reader takes the far
  end. *Box Office Mojo* is the clean case, and it is also a **missing pattern**:
  `bought by` is not in the pattern list, so the first ownership match is the
  grandparent's `owned by`. Depth and pattern coverage are entangled here.
- **same entity, different name** — *Porsche SE* against *Porsche Automobil
  Holding SE* is a **scoring** failure, not a reader failure.
- **regex truncation** — `Fiat S` from *Fiat S.p.A.*
- **stale gold** — PFL acquired Bellator in 2023; the Wikidata record, not the
  reader, is behind.

## What this says to build

1. **A typer with better recall**, which converts up to 51% of the errors and
   costs coverage today only because it is shallow — one search hit and one
   subclass hop, which is why it loses *BBC*.
2. **More ownership patterns** (`bought by`, `purchased by`, `held by`), which
   fixes at least one apparent depth error by making the near link match first.
3. **Not** relation direction. Nothing in the residual needs it.

And two of the eleven `other` cases are **evaluation** defects — a name variant
and a stale gold record — so the measured 0.696 ceiling is itself a little low.

## What would refute this

- 37 errors, and the `other` bucket is eleven cases read by eye. The 51% is solid;
  the decomposition of the remaining 30% is a reading, not a measurement.
- The non-organisation class is defined by the same typer whose recall is the
  complaint. It is right about *French* and *CPR*; if it is also wrong about some
  of the 19, that class is over-stated and `other` under-stated.
