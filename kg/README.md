# `kg/` — the ingestion working area

**Nothing in here is tracked except manifests, schemas and licences.** The rule
is the one `/runs/**` already encodes for sweeps, applied to a different kind of
bulk: **keep the evidence, drop the corpus.**

This directory is where source corpora are staged, mined and normalised on the
way to producing a small vendored graph. The finished artefact does **not** live
here — it goes in `symbolic_ai_kg/data/`, licensed and sha-pinned, as
`wordnet30-physical.json.gz` (248K) and `cskg-commonsense.json.gz` (612K)
already do.

The rule of thumb: **if a model reads it at sweep time, vendor it. If it is
scaffolding on the way to producing that, it belongs here and only its manifest
survives a clone.**

## Layout

```
kg/
  sources/        raw corpora, staged. ~14 GB, re-fetchable from upstream.
  mined/          fact-mining output, per source. Large, and a pure function
                  of (source, miner, config) — so rebuildable, so untracked.
  normalized/     triples after schema normalisation. Same.
  <any>/manifest.json    TRACKED — what produced this, and how much of it
  <any>/schema.json      TRACKED — the normalisation contract
  <any>/stats.json       TRACKED — counts, for arguing with
```

## Why the manifest is tracked and the data is not

A `manifest.json` is the exact analogue of a run's `summary.json`. Its job is to
answer *"what produced this graph?"* after the fact, without re-running
anything:

- which source files, **at which checksums**;
- which miner, at which version, with which model and config hash;
- how many documents in, how many facts out, **how many rejected and why**;
- which schema version the output conforms to.

This repo's standing rule is that **a number without its floor is not a result.**
A mined fact without its provenance is the same defect one layer down, and it
bites harder here, because the two ingestion paths do not produce facts of equal
quality. A fact recovered from a parse carries argument structure and scope; a
fact mined directly out of prose by a local model carries whatever the extractor
felt like. Pool them without recording which path produced which and you have a
silent quality variable correlated with text type, inherited by every
measurement downstream.

That is not hypothetical. `label_acc` — this repo's central number — spent its
entire history pooling two questions in a 72:28 ratio, and when they were
finally reported apart the published ranking **inverted**: the best model went
from first of twelve to eleventh. **Every fact carries its path, and no table
pools the paths without reporting the split.**

`schema.json` is tracked for a related reason: normalisation is a design
decision, it will be revised, and a graph whose schema is not pinned cannot be
compared against an earlier version of itself.

## What is deliberately *not* here

- **The source corpora as a git object.** ~14 GB, every byte re-fetchable.
- **Anything a sweep imports.** Package data lives in `symbolic_ai_kg/data/`,
  which ships in the wheel; this directory does not.
- **A curriculum.** Registering a KG-derived curriculum is a separate decision
  with its own pre-registration and its own floors — see
  `notes/decisions/2026-08-14-semantic-constraint-from-a-knowledge-graph.md`.

## The measurement this is all for, stated so it does not drift

Coverage was **never** the binding constraint. The curriculum's vocabulary is
~100% covered by every graph tried, and WordNet's 13,810-node projection already
reached it. The first KG arm returned a clean null with **mean −0.0013** on the
quarter that matters, and its control could not have failed by construction.

So more facts, better mined, do not obviously help. What the ingestion is *for*
is making symbols **derivable** — a slot whose value follows from an anchor
through the graph rather than being drawn, which is the only proposal on the
table that could move `acc | not copyable` off **0.003**. A bigger graph with
nothing derivable would reproduce the same null at greater expense.
