# `manifests/` — concrete objects, and their lineage

A source card says what a resource *is*. Everything here says what *exists*.

```
manifests/snapshots/<source>/<slug>.yaml     exact bytes, obtained once
manifests/snapshots/<source>/<slug>.files.tsv  per-file digests, when there are many
manifests/artifacts/<id>.yaml                something manufactured
manifests/views/                             a projection/sampling, usually virtual  (empty)
manifests/splits/                            an immutable membership assignment      (empty)
```

`views/` and `splits/` are empty and are here deliberately: they are the two
places a "dataset" usually turns into `processed_v7_final_REAL/`, and having the
directory named is cheaper than explaining later why a view is not a copy.

## Where the bytes are

Not here. Bulk lives under the **data root** — `$SYMBOLIC_AI_DATA`, defaulting
to `./data`, which is gitignored:

```
data/
  sources/<source>/<snapshot-slug>/<upstream layout, preserved verbatim>
  artifacts/<artifact-id>/…
```

**The layout inside a snapshot is the upstream's, untouched.** Parquet
collections, Iceberg tables, NDJSON exports, BIDS trees and zarr stores each
have a layout their own tools expect; rewriting them into one house style breaks
every reader upstream ships and buys nothing a manifest does not already give.
There is no `data/parquet/` and there will not be one — format is a property,
not an ownership boundary.

**A missing data root is a normal state.** A fresh clone holds every manifest
and none of the 14 GB. `SourceRegistry.held()` is the only thing that asks the
disk, and it returns `False` rather than raising.

## `locations` is not identity

`manifest_hash` is taken over the canonical JSON of the manifest **minus**
`storage.locations` and `storage.root`. Mirroring a snapshot to S3, or moving
the data root to another disk, must not make it a different snapshot. That is
the same reason the digest is taken after YAML parsing rather than over the
file: a comment or a reordered key is not a new object either.

## What a snapshot is for

So that a run can bottom out in **exact bytes**. Each snapshot carries a
per-file `sha256`; where the file count would make the YAML unreadable (the
CommandAGI export is 2,114 files) the rows move to a `.files.tsv` sidecar and
the manifest keeps `files_digest`, a hash over the canonical form of those rows,
so the sidecar cannot drift unnoticed.

## Two things the manifests record that a later reader could not recover

Both are already true of this pull and neither is visible from the bytes:

- **The three CommandAGI storage formats are one graph.** `graph/` (cold NDJSON
  and parquet), `__r2_data_catalog/` (the same tables as Iceberg) and `d1/` (the
  hot-tier SQL dump) agree on 3,054,087 nodes because they are the same
  export. Quoting that agreement as three independent verifications is exactly
  the composite-source double-count this layer exists to refuse — and CSKG is
  the same shape one level up, being itself a consolidation of seven upstreams.
- **The GDELT and SEC windows overlap.** 7/14/30/60-day GDELT cuts taken on
  different dates, and two 13F/insider cuts over different date ranges. Pooled
  without deduplication they double-count the intersection, and the intersection
  is most of the smaller window.
