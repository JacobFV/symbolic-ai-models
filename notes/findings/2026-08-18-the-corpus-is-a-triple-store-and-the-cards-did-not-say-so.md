---
title: 97.7% of the ingested corpus is a bare triple store, and both geo sources declare coordinates they do not hold
date: 2026-08-18
status: provisional
tags: [federation, data, kernels, projection]
---

## What I expected

Going in I knew only that GeoNames' parquet had no coordinate column, found
while trying to give the geo kernel a real source instead of a generated world.
The stated prediction before the audit ran was:

> at least 3 of the 19 snapshots will have a generic edge schema that dropped
> their domain fields.

Then, before the profile audit:

> 0 of 19 support `geo.place`, 0 support `core.time`, 4 support `core.quantity`.

## What I found

Reading the parquet footers of every held snapshot (metadata only — 14 GB
audited in seconds):

| profile | snapshots that can populate it |
|---|---|
| `core.identity` | 19/19 |
| `core.type`, `logic.proposition` | 19/19 |
| `core.quantity` | 6/19 |
| `core.time` | 2/19 |
| `geo.place` | **0/19** |

Rows-weighted, across **1,216,407,910 rows**:

- **96.2%** sit in a literally bare schema — `(source_id, target_id, kind)` or
  `(id, label, kind, body, source_url)` and nothing else.
- **97.7%** carry no field whatsoever beyond identity and relation.
- The 2.3% that do are concentrated in the small sources (fec 95.6%,
  senate-lda 83.6%, usaspending 77.0%, cfpb 74.8%) and in CommandAGI's own KG
  (59.2%). Of the four sources over 100 M rows, only openalex has any domain
  column at all, on 3.1% of its rows.

My "at least 3" was badly under-predicted: 9 snapshots are *wholly* generic and
12 are generic in their dominant file schema. The profile prediction was right
on `geo.place` (0) and `core.time` (2 — and both are `updated_at`, a
*transaction* time, so not one source can supply a valid time), and low on
`core.quantity` — 6, not 4, because openalex and sec-edgar also carry a `value`.

**And no source carries a unit. 6 have a value column; 0 have a unit column.**
`Quantity` refuses to construct without one:

> a Quantity must name its unit; use '1' for dimensionless. An unlabelled
> number is how a metre and a foot get added.

So the honest count for `core.quantity` is 6 *if the ingest is allowed to invent
a unit*, and 0 otherwise. The audit reports the value and unit fields separately
rather than folding them together, so this stays visible.

## The sharper half: the cards declare what the bytes do not hold

Only 4 of the 19 source cards declare profiles at all. Of those 4, **2 declare a
profile their held bytes cannot populate — and they are exactly the two geo
sources**:

| source | declared by the card | absent from the bytes |
|---|---|---|
| geonames | `core.identity`, `geo.place` | `geo.place` |
| openflights | `geo.place`, `geo.network` | both |
| gleif, wikidata | — | — |

100% of the declared geospatial capability in this repo is unbacked by the bytes
on disk.

**The card is not the thing that is wrong.** Upstream GeoNames really does
publish coordinates; `geo.place` is a true statement about the resource. The
bytes here are a lossy projection of it and the loss belongs to the *snapshot*.
Editing the card to match the disk would delete the only record that the
coordinates exist and are re-fetchable — the same mistake as letting a derived
value become a measured one.

The right name for it was already in the repo. The kernel ABI says a projection
`P_K: W → L_K` must record what it discarded, because a kernel that silently
drops the units is indistinguishable from one that never had them. **Ingest is a
projection too** — `P_ingest: upstream → snapshot` — and it had no such record.
`IngestProjection` is that record: `declared ∩ held` retained,
`declared − held` discarded.

## Why it matters more than the numbers

This explains a shape I had recorded as a scoping choice and which was in fact
forced. The geo kernel, the rigid-body kernel and the economy kernel were all
built against *generated* worlds. I wrote that down as "the generated tasks give
a controlled margin". The truth is that **no held source can supply a
coordinate, a unit, or a valid time**, so none of those three kernels could have
run on real data whatever I preferred.

Stated as a capability boundary: the 14 GB drives `datalog` and `asp` — which
need identity, type and relation, and get 1.2 B rows of exactly that — and
cannot drive `smt` with units, `geo`, `rigid` or `economy` at all. That is not a
small caveat on the corpus; it is the corpus's whole shape, and it was invisible
because manifests recorded files, bytes and sha256 and never once a column.

## What would refute it

- A snapshot whose files carry lat/lon that my patterns miss. The patterns are
  deliberately generous (`^lat`, `latitude`, `^lon`, `^lng`, `longitude`) and a
  false positive is the conservative direction here, so a miss would have to be
  an unusual spelling. `test_no_held_source_can_populate_a_coordinate` fails the
  day this stops being true, which is the point of writing it as a test.
- Coordinates packed inside the `body` string rather than in a column. GeoNames'
  body is `feature=L/FLD country=AM pop=0` — feature code, country, population,
  no numbers — so for GeoNames this is checked and negative. I have **not**
  parsed every source's `body`, and a source that hides structure in a text
  column would read as generic here while being richer. That is the live limit
  of this audit.
- Re-fetching GeoNames upstream with coordinates intact would make the discard
  disappear, which is the correct outcome and not a refutation of the reading.

## Built

`symbolic_ai_core/source/columns.py` — footer-only schema reader, field
detection, `profiles_supported`, `IngestProjection`, `audit_snapshots`,
`build_schemas`. `generated/schemas.json` is the measured half of the catalogue,
kept separate from `generated/catalog.json` so the declared half stays buildable
from the repo alone. `symbolic-ai sources --schemas` prints it;
`--rebuild-schemas` re-measures and refuses to write an empty audit.
19 tests in `tests/test_source_columns.py`.
