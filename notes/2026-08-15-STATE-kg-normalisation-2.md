# STATE — KG normalisation, part 2 (full run, vocab join, derivable re-measure)

**Successor to `notes/2026-08-15-STATE-kg-normalisation.md`.** Read that first;
it holds the decisions already taken, which are not relitigated here. This file
is the working state of the *second* leg and exists to survive context
compaction. Branch: `worktree-agent-aa2e35242d3651d38`.

## What is running / has run

| step | state |
|---|---|
| full normalisation, all sources, TSV + nodes | **RUNNING** (see below) |
| `kg_derivable.py` learns TSV | **done**, validating |
| curriculum-vocabulary join (`kg_vocab_join.py`) | written, waiting on nodes |
| re-measure the derivable population over 1.2 B | blocked on the run |
| closure / inference over the normalised graph | not started |

### The normalisation job

Launched from the **main checkout** (not this worktree) as a detached background
task, PID 3816101, started 12:00:

```
cd /home/brandonin/Documents/symbolic-ai-models
rm -f kg/normalized/v2/transport.tsv.gz kg/normalized/v2/lit.tsv.gz \
      kg/normalized/v2/*.nodes.tsv.gz
OMP_NUM_THREADS=2 nice -n 15 uv run --with pyarrow python \
  scripts/kg_normalize.py ~/Downloads/kg --tsv --nodes
```

- **Log**: `/tmp/claude-1000/-home-brandonin-Documents-symbolic-ai-models/
  abc1e329-c706-4af0-8617-68d765208288/tasks/bkw7ulhz9.output`. It **lags** —
  the pipeline ends in `grep`, which block-buffers to a file, so the log is
  several sources behind the output directory. Judge progress from
  `ls kg/normalized/v2/`, not from the log.
- **The manifest is written once, at the very end.** If the process dies, no
  per-source stats survive and the whole run repeats. That is the standing risk
  and there is no way to checkpoint it without restarting.
- Sources are processed in **alphabetical order**; `_dev-bucket`, `d1`,
  `__r2_data_catalog` and `test` are skipped by default.

## Found while reading, before any number

0. **`part-of` pools its own inverse, and that breaks step 4 before it starts.**
   v2 maps `BFO:0000050` (*part of*), `BFO:0000051` (*has part*) and `contains`
   onto one canonical. Counted exactly from `graph.ndjson.gz`'s `orig_kind`
   column: **95,844 `part-of` and 52,871 `contains`** on the same relation. A
   transitive closure over an edge set whose arrows point both ways derives
   facts that are not true, and closure over `part-of` is exactly what step 4
   proposed. v2 keeps the direction for kinship (`parent-of` 26,721 /
   `child-of` 26,871 are separate canonicals) and destroys it for meronymy, so
   this is an inconsistency inside one schema rather than a considered choice.
   Fixed in the v3 schema written this leg.

0b. **`cskg` ships no node table.** It is the source of essentially every
   determined attribute in the corpus, so joining the curriculum against
   `*.nodes.tsv.gz` alone would have returned a near-zero usable coverage that
   was an artefact of which sources export a node file. Its identifiers are
   ConceptNet URIs — `kg:cskg:/c/en/adipose_tissue/n/wn/body` — and carry the
   lemma, so `kg_vocab_join.label_from_id` reads it from there. That one
   namespace is handled explicitly and every other id stays opaque.

0c. **`graph/log/*.ndjson.gz` are event logs, not node tables.** 965 of them,
   with a top-level `id` and no `source_id`, so `is_node_file` accepts them.
   Their ids are bare UUIDs, which `parse_id` rejects, so they cost a large
   `id:unparseable` count and contribute nothing. The real node table is
   `graph/clique/kg-public/rep/semantic/nodes.parquet`, **1,155,000 labelled
   nodes**, and it is picked up correctly. Worth knowing before reading
   `graph`'s node rejection count as corpus rot — it is the same shape as the
   19.3 M phantom rejections, one level down.

## Two things found while reading, before any number

1. **`scripts/kg_derivable.py` would have double-counted six sources.** It
   globbed `*.ndjson.gz`; the full run writes `*.tsv.gz`, and the six sources
   normalised before the format switch are on disk in **both** forms. Teaching it
   TSV without teaching it to prefer one form per source would have silently
   doubled cskg, entity, geo, graph, lit and transport. `inputs()` now picks TSV
   over NDJSON per source and records which it used in `stats.json`.

2. **The published "~100% of the curriculum's vocabulary is covered" has a
   194-word denominator, not the curriculum's 423.** `scripts/kg_coverage.py`
   hand-classifies four tables (`STRICT` 69, `WIDE` 180, `PROPER` 14, `NONCE`
   86); the repo also ships
   `symbolic_ai_data.grammar.compile.curriculum_vocabulary()`, which returns
   **423** words and is importable, plus `rendered_vocabulary()` at 749. All 194
   are a subset of the 423, so **229 coinable words were never in the coverage
   measurement**. Not a refutation of that finding — its own comment says the
   classification is a judgement reported as a range — but the join in step 2
   reports **both** denominators, because quoting only the 194 repeats an
   exclusion nobody chose deliberately and quoting only the 423 is incomparable
   to the record.

## Written this leg

- `scripts/kg_derivable.py` — TSV reader, per-source form selection, anchors
  counted as 64-bit blake2b hashes in a `uint64` array instead of a Python set
  of ~10^8 strings, 4-way parallel. **Validation gate: it must reproduce
  216,472,379 / 119,125,858 / 78,642 / 15,977 / 9,849 on the six NDJSON sources
  before any number from it is believed.**
- `scripts/kg_vocab_join.py` — the join that has never been done. Two matchers
  (`exact`, `token`) reported apart, and four controls that can fail: `nonce`
  (permissiveness), `anagram` (same length and alphabet, no meaning),
  `dict-uniform` and `dict-lenmatched` from `/usr/share/dict/american-english`.
  The dictionary controls are **not** frequency-matched, so that confound is
  two-sided and the comparison that does not depend on it is the conditional
  *usable | matched*.

## Predictions on the record, before the numbers land

- **The lead's, on step 3:** the full 1.2 B will **not** move 9,849 materially,
  because determined attributes come almost entirely from CSKG's 3.98 M rows and
  the remaining bulk is citation structure. I agree, and add the specific
  reason the remaining sources cannot move it: `cpc`/`wipo`/`patents` are
  classification (`classified-as`, not a determiner), `gleif`/`sec*`/`finance`
  are holding structure, `gdelt` is inter-actor events, `gharchive` is
  actor-acts-on-repo. **None of the three unmapped dialects is a determiner
  vocabulary**, so extending the schema to admit them cannot move the usable
  population either — it can only move `entities_anchorable`, which is already
  measured not to be the constraint.
- **The one thing that could refute the lead, and it is a definition not a
  corpus fact.** Wikidata's `has-part` (P527) is ~1.8% of `entity`'s 259.8 M
  rows on the sampled inventory, i.e. of order 4.6 M rows, and it was unmapped
  in v2. ConceptNet's `/r/HasA` — the same relation in the other dialect — *is*
  in `kg_derivable.DERIVE`. So if `has-part` were admitted as a determined
  attribute, the usable population could move by orders of magnitude, and the
  correct reading would be **"9,849 is a function of the determiner definition
  as much as of the corpus"**, not "the corpus is richer than measured". v3
  therefore maps `has-part` to its **own** canonical and does **not** fold it
  into `has-a`, so `DERIVE` is bit-identical across v2 and v3 and the two
  measurements are comparable. Whether `has-part` should count is asked as its
  own arm, one change at a time.
- **On step 2, and this one I do not know the answer to:** coverage against a
  1.2 B-triple corpus's node labels should be high, but *usable* coverage —
  a word finding a node that is anchorable **and** determined — is bounded by
  the 9,849, and 9,849 CSKG concepts against ~400 curriculum words is a
  collision problem, not a coverage problem. If it comes back high, the
  interesting question is whether the dictionary control comes back just as
  high, in which case the graph is covering English and not the curriculum.
