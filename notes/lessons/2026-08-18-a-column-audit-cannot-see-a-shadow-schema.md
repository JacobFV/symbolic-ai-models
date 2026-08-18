---
title: A column-level audit reads a text column as empty, and every error ran toward the dramatic reading
date: 2026-08-18
tags: [lesson, measurement, data]
---

## The mistake

I audited 19 snapshots by reading parquet column names, concluded **"0 of 19
sources can populate `geo.place`"**, wrote it as the headline of a finding, and
committed it. Openflights had coordinates the whole time, stored as
`lat=-6.0816 lon=145.39` inside a string column named `body`. The next source I
opened after committing had them.

A second error rode along: openflights' card declares `geo.network`, this module
has no rule that could detect a route network, and I counted the undetectable
declaration as a **discard** — a loss the audit had not measured and could not.

## What it cost

About twenty minutes, because the refuter I had written into the note fired
immediately. Had I not written it down, the number "0/19 sources have
coordinates" would have stood as the justification for building the geo kernel
against generated worlds forever, and the justification would have been false.

## The mechanism

Two of them, and the second is the one that generalises.

1. **A schema-level audit sees the schema, and a text column has none.** Column
   names are metadata and metadata is exactly what a schemaless escape hatch
   escapes. Any audit whose unit of observation is the declared structure is
   blind to structure smuggled below it.
2. **Both errors ran in the same direction — toward the more striking finding.**
   Missing the body made the corpus look poorer; miscounting `geo.network` made
   the ingest look lossier. Neither was chosen; that is the point. This repo's
   history is confident wrong readings, and the tell each time is not that an
   error occurred but that the errors *agreed with each other* about which way
   to point.

## The guard

- **Before reporting a capability as absent, read the values, not the schema.**
  Absence is the expensive claim: presence gets checked by the thing that
  consumes it, absence gets believed. One row group per file was enough here.
- **Separate "measured absent" from "no instrument".** A declaration this audit
  has no detector for is `undetermined`, and lives in its own field, so a gap in
  the instrument can never be counted as a finding about the world.
- **When two independent errors point the same way, look for the third.** The
  direction is the signal. Both of these flattered the write-up before anything
  checked them.
- **Write the refuter into the note before committing it.** This one caught its
  own headline within the hour, and that is the whole reason the cost was
  twenty minutes rather than a research direction.
