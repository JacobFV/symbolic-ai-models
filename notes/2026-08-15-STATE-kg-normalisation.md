# STATE — KG normalisation, 2026-08-15

**This file exists to survive context compaction.** It is the working state of an
in-flight job, not a finding. Anyone picking this up cold should read it first,
then `notes/findings/2026-08-15-the-usable-kg-is-ten-thousand-entities-not-a-billion-triples.md`
for why it is being done, and `kg/README.md` for what is tracked.

## What is running right now

A full normalisation of the ingest corpus, launched as a **detached background
shell job**, not an agent:

```
uv run --with pyarrow python scripts/kg_normalize.py ~/Downloads/kg --tsv --nodes
```

- Output: `kg/normalized/v2/<source>.tsv.gz` (edges) and `<source>.nodes.tsv.gz`.
- Expect **~15 GB gzipped** over ~1.2 B rows. 952 GB free at launch.
- Progress is the stdout log; each source prints one line as it completes.
- **If the job is gone and the manifest is incomplete, just re-run the same
  command.** It rewrites per-source outputs and merges into the existing
  `manifest.json`, so a partial run is resumable by repetition.

## Where the pipeline stands

| step | state |
|---|---|
| inventory all 26 sources | **done** — `kg/sources/manifest.json`, 1,214,852,868 triples |
| schema v2 (123 kinds → 10 groups, 8 rejected) | **done** — `kg/normalized/schema.json` |
| normalise 6 priority sources (NDJSON) | **done** — 216 M triples |
| measure the derivable population | **done** — `kg/normalized/v2/stats*.json` |
| **normalise all sources + nodes (TSV)** | **RUNNING** |
| join node labels to the curriculum vocabulary | not started |
| inference / closure over the normalised graph | not started |

## The three numbers that matter

1. **1,214,852,868** triples in the corpus; **no unstructured text** in the edge
   tables — every source is already `(source_id, target_id, kind)`.
2. **9,849** entities are both anchorable *and* carry a single-valued determined
   attribute. That is the usable population for derivability.
3. Adding Wikidata's 194,756,799 triples multiplied anchorable entities **163x**
   (732,339 → 119,125,858) and moved the usable population by **+0**. Scale is
   measured not to be the constraint; *statements about what follows from being
   something* are, and general KGs are not built to carry them.

## Decisions already taken, so they are not relitigated

- **`body` is dropped, `label` is kept.** Node bodies are median **36 chars**,
  70% opening `Source: OBO Foundry ontology`, 23,883 distinct openings per 190k
  sampled — templated provenance, not prose. Mining them recovers what the
  structured columns already say. `label` is kept because it is the **only join
  key to the curriculum's vocabulary**, which is words rather than `kg:` ids.
- **Eight relations are rejected and counted, not mapped** — `/r/RelatedTo`
  (989,268), `about`, `derived-from`, `relates-to`, `described-at`,
  `/r/HasContext`, the claim-reification triple, `in-reporter`. Reasons per entry
  in the schema.
- **`__r2_data_catalog`, `d1` and `test` are skipped** — the first two are the
  same graph re-exported, and normalising them would double-count every edge
  under a second source name.
- **Edge vs node files are detected by columns, never by filename.** Guessing by
  name read 965 node/log files as edge lists and produced 19.3 M phantom
  rejections that looked like corpus rot and were entirely a script bug.

## Open, and NOT decided — do not assume otherwise

**No embedding has been chosen for this graph, and none has been discussed.** The
word "embedding" in `notes/decisions/` refers to *graph-derived role* embeddings
for the VSA models — Laplacian eigenmap and heat-kernel signature over the
curriculum's term trees — which is a different object entirely. The KG's own
`README` mentions a Cloudflare Vectorize index, but that belonged to the source
system, was not exported, and is not ours.

Two measured results bear on whether a semantic node embedding is even wanted:
`vsa_seeded-002` was a null (−0.007 accuracy) against a random codebook, and
capacity spent on symbol identity is measured as wasted here (`ilp` +0.198 with
74 counts against `ctw` −0.040 with 819,990). So an embedding is an open
question with evidence pointing *against*, not a settled plan.

## What to do next, in order

1. Let the normalisation finish; check the manifest for per-source kept
   fractions and unmapped kinds.
2. **Join `nodes.tsv.gz` labels against the curriculum's vocabulary.** This is
   the step that makes the graph usable at all, and it has never been done — the
   first pass threw the node tables away.
3. Re-run `scripts/kg_derivable.py` over the full set (it currently reads
   `*.ndjson.gz`; it needs a TSV reader).
4. Only then consider closure/inference — transitive `is-a`, inverse relations,
   composing `is-a` with `has-property` to derive attributes never stated
   directly. That is rule application, not extraction, and it is where new facts
   would actually come from.
