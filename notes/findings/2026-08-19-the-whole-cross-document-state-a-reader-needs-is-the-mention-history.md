---
title: The whole cross-document state a reader needs is the mention history — and it buys a bit-identical world at 8.3x lower reading cost
date: 2026-08-19
status: measured
arm: persistent-world
---

The economic case for a persistent world is arithmetic and not worth an
experiment: `cost/query = C_ingest/N_uses + C_update + C_reason + C_generate`, so
a fact extracted once and reused a million times is priced differently from a
transformer re-reading it a million times. What is **not** known is whether the
incrementally maintained world is the *same world*. A store that quietly drifts
from what a full re-read would say is worse than no store, because the drift is
invisible and permanent.

Documents are delivered one chunk at a time. Three arms, compared after the last
delivery:

- **re-read** — parse everything received so far, on every arrival. The ceiling,
  and the cost that grows with the corpus.
- **persistent** — read each new chunk alone, apply its delta to one world.
- **persistent+ctx** — same, with earlier chunks passed as `context`, scanned for
  **mentions only** and never for claims.

40 held-out documents per domain. `runs/persistent_world.json`.

## 1. Paragraph delivery tests nothing, and that is worth recording

| granularity | domain | persistent == re-read | end-to-end |
|---|---|---|---|
| paragraph | all three | 1.000 | 1.000 |

Every reference in these surfaces is paragraph-local, so splitting on blank lines
crosses none of them. The first run of this arm reported 1.000 everywhere and had
measured nothing — the honest reading of a clean result is sometimes that the
instrument was not pointed at anything.

## 2. Sentence delivery: flood breaks, and breaks exactly where predicted

| domain | arm | == re-read | end-to-end | ms/doc | speedup |
|---|---|---|---|---|---|
| solvency | re-read | 1.000 | 1.000 | 33.68 | 1.00x |
| | persistent | 1.000 | 1.000 | 1.49 | 22.7x |
| scheduling | re-read | 1.000 | 1.000 | 53.17 | 1.00x |
| | persistent | 1.000 | 1.000 | 1.65 | 32.2x |
| flood | re-read | 1.000 | 1.000 | 145.97 | 1.00x |
| | persistent | **0.000** | **0.250** | 3.43 | 42.5x |
| | **persistent+ctx** | **1.000** | **1.000** | 17.56 | **8.31x** |

The blind arm loses `capacity` on 40 of 40 documents and `demand` on 40 of 40 —
**exactly and only** the two predicates whose subject is a pronoun resolved
against the previous sentence. Nothing else moves. Predicted in advance, down to
the predicate names.

Passing prior text as context restores a claim-for-claim identical world at
**8.31x** less reading than re-parsing the corpus per arrival.

## 3. Minting survives the split with no help at all

flood's `bridge_on` and `load_limit` are stated in different paragraphs about an
entity that appears in no sentence. They are absent from the loss list **even in
the blind arm**: the identity `~region_1|region_2` is minted from the mentions in
its own sentence, so two documents that never share a name and never see each
other agree on what they are talking about. That is the property minting was
built for, and delivering the paragraphs separately is its first real test.

## 4. What this specifies

**The entire cross-document state this reader needs is the mention history.** Not
the parses, not the claims, not the world — a list of names in the order they
were written. Everything else about incremental ingestion came out identical for
free.

Two honest limits on the 8.31x:

- The context arm **re-scans** prior text on each arrival, so it is still
  quadratic in corpus length. A reader that carried the mention list forward
  would be linear, and the blind arm's 42.5x is what that costs — the two
  bracket a properly stateful implementation.
- The `Reader` protocol takes `context: Sequence[str]`, which is a stand-in for
  the state object it should take. That is now a specified gap in the ABI rather
  than a guess, and the specification is small: mentions, in order.

## 5. What would have refuted it

`persistent+ctx` failing to match `re-read`. Whatever was left over would have
been the real specification of cross-document state, and it would have been
larger than a list of names. It matched exactly, in every domain and at both
granularities.
