---
title: I searched for the mechanism and published a negative; the file was named after its purpose and I never saw it
date: 2026-08-18
author: lead
status: provisional
tags: [lesson, data-discovery, negative-claims]
---

## The mistake

Published, in a finding and in `HANDOVER.md` §3: **"No file on disk links a CIK
to an LEI."** It is false. `data/sources/wikidata/.../idbridges_full_p0.parquet`
holds 69,679 `same-as` edges whose targets are **lei 53,198 / isin 9,936 /
sec 3,660 / asx 2,846 / ticker 39**, and 2,113 wikidata entities carry both a
`sec` and a `lei` edge — a CIK→LEI bridge joined on identifiers at both ends.

## How the search missed it

I looked for the **mechanism**: a `same_as` column in the SEC tables and in the
GLEIF tables. Finding it name-derived in one and absent in the other, I
generalised from *these two sources do not bridge each other* to *nothing on
disk bridges them*. The bridge was in a **third** source, in a file named after
what it does.

`grep -ril "bridge\|crosswalk\|same.as" data/sources/ --include=*.parquet` would
not have worked (binary), but `find data/sources -name '*bridge*'` would have
returned it in under a second, and `ls` of the wikidata directory would have
shown a file called `idbridges_full` sitting next to `backbone_full`.

## The general shape

> **A negative existential over a corpus cannot be established by checking the
> places you expected the thing to be.** Two sources failing to share a key says
> nothing about whether a third party publishes the mapping — and publishing
> such mappings is precisely what wikidata, GLEIF and ROR *are*.

The domain makes this worse rather than better: identifier federation is a
business, so the prior that *somebody* maintains any given crosswalk should have
been high, not low. I had the opposite prior and stated it as measured fact.

## The guard

Before writing "no file on disk does X":

1. `find data/sources -iname '*<purpose-word>*'` for the words a maintainer would
   use — bridge, crosswalk, xref, mapping, sameas, links, ids.
2. Enumerate the **namespaces** every source emits, not the columns. One
   `set(id.split(':')[1] for ...)` per file would have shown `wikidata → sec` and
   `wikidata → lei` immediately, and that is the shape a bridge has regardless of
   what the file is called.
3. State it as **"I did not find one"**, with the search recorded, unless the
   corpus was enumerated exhaustively.

Related: [[suspect-the-shared-substrate-first]],
`notes/lessons/2026-08-18-claiming-an-axis-was-new-that-the-repo-had-measured-twice.md`.
