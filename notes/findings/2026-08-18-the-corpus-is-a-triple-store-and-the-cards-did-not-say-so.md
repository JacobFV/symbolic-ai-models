---
title: 95% of the ingested corpus is a bare triple store, geonames declares coordinates it does not hold, and my own refuter fired within the hour
date: 2026-08-18
status: provisional
tags: [federation, data, kernels, projection, correction]
---

## What I expected

Going in I knew only that GeoNames' parquet had no coordinate column, found
while trying to give the geo kernel a real source instead of a generated world.
Predictions stated before the numbers landed:

> at least 3 of the 19 snapshots will have a generic edge schema that dropped
> their domain fields.

> 0 of 19 support `geo.place`, 0 support `core.time`, 4 support `core.quantity`.

## The correction, first, because I published the wrong version

The first version of this note led with **"0/19 can populate `geo.place`"** and
**"both geo sources declare coordinates they do not hold"**. Both are wrong, and
they were wrong in the direction that made the finding more dramatic.

I had named the refuter in that very note:

> Coordinates packed inside the `body` string rather than in a column. […] I
> have **not** parsed every source's `body`, and a source that hides structure
> in a text column would read as generic here while being richer.

It fired within the hour, on the next source I opened. Openflights airports
carry `city=Goroka country=Papua New Guinea lat=-6.0816 lon=145.39` — the
coordinates were there the whole time, inside a text column, invisible to an
audit that read column names. Gutenberg's only temporal field is `issued=`,
likewise in a body.

Second error, mine to catch and I did not at first: `geo.network` has **no
detection rule in this module at all**, so reporting it as "discarded" was
neither true nor false but unmeasured. `IngestProjection` now separates
`discarded` (declared, detectable, absent) from `undetermined` (declared, no
detector). That conflation also ran toward the dramatic reading.

## What is actually true

| profile | snapshots that can populate it |
|---|---|
| `core.identity`, `core.type`, `logic.proposition` | 19/19 |
| `core.quantity` | 7/19 (6 by column, +geonames by `pop=`/`area=`) |
| `core.time` | 3/19 (2 by column, +gutenberg by `issued=`) |
| `geo.place` | **1/19** — openflights, via its body |

Rows-weighted, across **1,216,407,910 rows**: **95.1%** sit in files with
neither a domain column nor a body — literally `(source_id, target_id, kind)`
and nothing else. Only 4.88% of rows are even in a file that *has* a body to
hide anything in.

My "at least 3 generic" was still far under: 9 snapshots are wholly generic by
column, 12 by dominant schema. `core.quantity` was predicted 4 and is 7.

**No source carries a unit.** 6 have a value column, 0 have a unit column, and
`Quantity` refuses to construct without one — *"an unlabelled number is how a
metre and a foot get added"*. So `core.quantity` is 7 if the ingest may invent
a unit and 0 otherwise. The audit reports value and unit separately so this
cannot be rounded away.

**Of two `core.time` sources by column, both are `updated_at` — a transaction
time.** Adding gutenberg's `issued=` gives the corpus exactly one valid-time
field in 1.2 billion rows.

## The claim that survives

Of the 4 source cards that declare profiles, **one declares a profile its bytes
cannot populate: geonames, `geo.place`**. 29 million rows of the repo's flagship
gazetteer, whose body carries `pop, feature, country, area, langs, capital,
continent` and not one coordinate. The source that started this is the only
provably lossy ingest in the corpus — a narrower finding than I first published
and a real one.

**The card is not what is wrong.** Upstream GeoNames does publish coordinates;
`geo.place` is a true statement about the resource. The bytes here are a lossy
projection and the loss belongs to the *snapshot*. Editing the card to match the
disk would delete the only record that the coordinates are re-fetchable — the
same mistake as letting a derived value become a measured one.

The right name was already in the repo. The kernel ABI says a projection
`P_K: W → L_K` must record what it discarded, because a kernel that silently
drops the units is indistinguishable from one that never had them. **Ingest is
a projection too** — `P_ingest: upstream → snapshot` — and had no such record.

## The better finding, which I did not predict at all

**There is a shadow schema.** `body` is an untyped string column carrying real
typed fields: coordinates, dates, populations, areas, ICAO codes. It is
invisible to the snapshot manifests, invisible to a column-level audit, and
un-typed at the point of use — every consumer must re-parse it and each one gets
to guess differently about `pop=0` (a real zero? a missing value? "missing can
NEVER become zero" has no defence here).

That is precisely the failure a typed world IR exists to prevent, sitting inside
the corpus this repo built its federation layer around, and no manifest field
could have shown it. It also means every capability claim about this corpus,
including the ones above, is bounded by how well four regexes read a text bag.

## Second correction, same day: the audit understated the corpus too

This note said the 14 GB *"cannot drive `smt` with units, `geo`, `rigid` or
`economy` at all"*. Geo was corrected above — openflights has coordinates in its
body. **Economy is wrong for a different and more interesting reason.**

Ownership consolidation is **relational and needs no units**. GLEIF files
124,460 direct-consolidation edges and 130,355 ultimate-consolidation edges, and
a closure over them scores 0.9785 against independently filed labels — see
`notes/findings/2026-08-18-ownership-closure-and-the-advantage-curve-spans-seven-orders-of-magnitude.md`.

The mistake was in the question. This audit asked **which profiles can be
populated** and then reasoned as if that answered **which questions can be
asked**. A kernel does not need every profile it can consume; it needs the ones
its question requires. The monetary half of the economy kernel is indeed
unreachable here — no unit, no amount — and the *structural* half is 250,000
edges of real filed data.

So the corpus is poorer than the source cards imply and richer than this audit
implied, and both errors are now on record.

## What would refute what is left

- A body key spelling I do not match. `BODY_HINTS` is deliberately narrow —
  `lat`/`latitude`, `lon`/`lng`/`longitude` — because a wide net over an untyped
  bag manufactures capabilities from substrings. Narrow means misses are the
  likely error, so **the residual bias now runs toward understating capability**,
  which is the opposite of the bias in the first version.
- GeoNames coordinates in a per-file variant I did not sample: 6 files sampled
  at 2,000 rows each, all showing the same body grammar. Not exhaustive.
- Structure inside `label` or `source_url` rather than `body`. Unexamined.

## Built

`symbolic_ai_core/source/columns.py` — footer-level schema reader plus bounded
body sampling, `profiles_supported`, `DETECTABLE_PROFILES`, `IngestProjection`
with retained/discarded/undetermined, `audit_snapshots`, `build_schemas`.
`generated/schemas.json` is the measured half of the catalogue, kept separate
from `generated/catalog.json` so the declared half stays buildable from the repo
alone. `symbolic-ai sources --schemas` prints it; `--rebuild-schemas`
re-measures and refuses to write an empty audit. 23 tests.
