---
title: source ≠ snapshot ≠ artifact ≠ view ≠ split, and a source card may never assert what is on a disk
date: 2026-08-18
status: decided
tags: [architecture, data, federation, provenance, licensing]
---

## The fork

14 GB of knowledge-graph corpora were sitting in `~/Downloads/kg`, and 23 GB of
derived triples in `kg/normalized/`, with one tracked `manifest.json` describing
both. The question was where to put them. The answer that matters is not the
directory layout — it is **which distinct things had been sharing one word.**

Five, and they have different lifecycles:

```
source    an external evidence-producing resource
snapshot  exact bytes obtained from one source at one time
artifact  anything manufactured from snapshots or other artifacts
view      a declarative projection/sampling, usually virtual
split     an exact membership assignment, immutable once published
```

## The rule that pays for itself fastest

> **A source card says what a resource IS. It may never say what this disk holds.**

`openalex` is not intrinsically *repo-held*. **This checkout** holds a particular
snapshot of it, and a second machine that has none of the bytes disagrees with
that snapshot's `locations` list while agreeing completely with the card. A
`held_inventory:` field on a source card is a claim about one disk wearing the
clothes of a claim about the world, and it is false on every other machine.

So holdings are not a field anywhere in `catalog/`. `SourceRegistry.held()` is
the only thing that asks the filesystem, and **a missing data root is a normal
state** — a fresh clone has every manifest and none of the 14 GB.

## `status` was four variables wearing one name

A single enum holding `repo-held`, `p0`, `restricted`, `ref`, `watch` forces
false exclusivities: `p0` and `restricted` are simultaneously true of plenty of
sources, and the enum quietly loses whichever fact lost the fight. Split:

| field | question |
|---|---|
| `access.class` | how may it be reached |
| `license.redistribution` | may the bytes be passed on |
| `lifecycle` | still published, still updated |
| `priority` | how much do we want it |
| *(snapshot `locations`)* | is it on this disk — **never a source field** |

## Authoring format is not hashing format

```
  *.yaml  (authoritative, hand-written, comments welcome)
     ↓ safe_load
  plain JSON-compatible object
     ↓ validate against ontology/schema/*.json
  canonical JSON (sorted keys, no whitespace, NaN rejected)
     ↓ sha256
  the identity
```

A comment, a reordered key or a reflowed string must not change an identity, and
that is only true if the digest is taken after parsing. `storage.locations` and
`storage.root` are additionally excluded from the hash, because **filesystem
location is never identity** — mirroring a snapshot to S3 must not make it a
different snapshot.

Enums live in `ontology/vocab.yaml` and are deliberately *not* in the JSON
schemas. An `enum` copied into six schema files is six copies of a list that must
agree; a sibling project's hand-copied `vocab.ts` drifted to ten values where its
schema had twelve, and nobody noticed, because the consumer with the short list
simply never matched the two missing cases.

## Bytes keep their upstream layout

```
$SYMBOLIC_AI_DATA/            (default ./data, gitignored)
  sources/<source>/<snapshot-slug>/<upstream layout, verbatim>
  artifacts/<artifact-id>/…
```

Parquet collections, Iceberg tables, NDJSON exports, SQL dumps, BIDS trees and
zarr stores each have a layout their own tools expect. Rewriting them into one
house style breaks every reader upstream ships and buys nothing a manifest does
not already give. **There is no `data/parquet/`** and there will not be one:
format is a property, not an ownership boundary. Ditto `data/eeg/`, `data/geo/`.

## `unresolved` is more restrictive than anything known

Licence closure is **computed from the parents, never authored on the child**,
taking the most restrictive term on each axis — and `unresolved` sorts last. A
derived artifact with one parent whose licence nobody established is unresolved,
not permitted. The alternative is a closure that is wrong in the *permissive*
direction, which is the direction that gets something published it should not
have been.

It cashed immediately. The four `kg-normalized-v*` artifacts come out
`unresolved`, blocked twice over: `commandagi-kg` prohibits redistribution
outright, and `courtlistener`, `gh-archive`, `gutenberg`, `patentsview` and
`senate-lda` have licences nobody established. Six source cards carry
`attribution_confidence: hypothesis` rather than an invented provenance — the
seven patent directories carry `kg:patent:` namespaces and PatentsView's table
shapes, but the pull recorded no upstream release, so the card says so.

## What was rejected

- **One merged mega-KG.** Identity is a *claim* (`Alignment`, with a relation, a
  confidence and a method), not a merge. `wn:dog.n.01`, `wd:Q144` and
  `cn:/c/en/dog` stay three entities.
- **A hardcoded `_SOURCES` dict.** Four entries and four functions was the right
  first seam and does not survive three hundred sources — and cannot express the
  source/snapshot split at all, because a Python function returning a graph has
  nowhere to say *which bytes*.
- **Directories per subject** (`eeg/`, `geo/`, `patents/`) and per kind
  (`sources/datasets/`, `sources/models/`). Both encode a property as ownership.
- **Merging the two staged cuts of the same SEC data.** They overlap on
  different date windows, so they are two streams, and the manifest is the only
  place that will remember why.

## The three double-counts this structure exists to refuse

Each is live in the data as it stands, and none is visible from the bytes:

1. **The three CommandAGI storage formats are one graph.** `graph/` (cold
   NDJSON), `__r2_data_catalog/` (the same tables as Iceberg) and `d1/` (the
   hot-tier SQL dump) agree on 3,054,087 nodes because they are the same export.
   Three independent verifications is what that agreement is *not*.
2. **CSKG is a consolidation of seven upstreams.** An assertion ingested
   directly and through CSKG is one observation seen twice.
3. **The GDELT windows overlap** — 7/14/30/60-day cuts taken on different dates.
   Pooled without deduplication the intersection is counted twice, and the
   intersection is most of the smaller window.
