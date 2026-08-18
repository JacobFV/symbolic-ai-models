---
title: I said retention was missing and it was not — it was real in memory and lost the moment a result left the process
date: 2026-08-18
status: provisional
tags: [fusion, serialisation, real-data, gleif, correction]
---

## A correction first

Last wake-up I named a gap: *"alternatives retained not collapsed" has a
mechanism that refuses to collapse and none that retains.* **That was wrong.**
`fuse()` already catches a `FusionError` from a rule, puts the whole group in
`unresolved`, and records a note. Retention was there.

I got it wrong because I had only ever called `prefer_measured` **directly**,
which bypasses `fuse()` entirely. A rule raising in isolation looks like a
refusal with nowhere to go; the same rule inside the function it was written for
is a mixture being preserved. Testing a component outside its harness and
concluding something about the system is its own small lesson.

## The gap that was actually there

Retention was real **in memory** and disappeared at serialisation.
`FusionResult.to_dict()` emitted, per unresolved group, a predicate, a subject,
a **count** and a producer list — and dropped the competing claims themselves.

Every flow node exchanges artifacts, so a downstream node reading a fused result
learned that two sources had disagreed and **could not recover what either one
said**. The ADR's principle held exactly as far as the edge of the process that
computed it.

Fixed: `to_dict` carries the claims, `from_dict` rebuilds them, and a document
whose `n` disagrees with its `claims` list is **refused** — a truncated mixture
with an intact count is indistinguishable from a smaller mixture, and the reader
has no way to tell.

## Measured on a real source-internal conflict

The case is GLEIF disagreeing with itself. Its filed `IS_ULTIMATELY_CONSOLIDATED_BY`
sometimes names an entity that is an **intermediate on its own filed
`IS_DIRECTLY_CONSOLIDATED_BY` chain** — two filings, both `measured`, naming
different ultimate parents.

**Prediction: 251 groups unresolved, none resolved, all surviving a round trip.**

| | |
|---|---|
| entities where GLEIF's two filings disagree, both measured | **251** |
| resolved by `prefer_measured` | **0** — correct; arrival order is not an argument |
| retained as mixtures | **251** |
| competing claims surviving a JSON round trip | **502** |
| serialised size | 378,314 bytes |

Every prediction held. `prefer_measured` refuses a tie at the top derivation
rank, `fuse` keeps the group, and both alternatives now cross the boundary with
their producers and derivations intact.

## And an asymmetry in my own change, caught by one test

Adding `Provenance.derivation` yesterday, I put it in `to_dict` and **not** in
`from_dict` — so it serialised and came back empty. Twice over, because
`claim.py` and `snapshot.py` each rebuild a `Provenance` field by field.

That is the same add-one-side asymmetry as every contract found this week
(`add_facts`, `cost_estimator`, `budget_ns`), except the author was me and it
survived less than a day. The guard is written over `dataclasses.fields` rather
than a hand-listed set, so the **next** field added is covered without anyone
remembering to cover it.

## What would refute it

- The 251 are one source contradicting itself, which is the easiest kind of
  conflict to construct and the least interesting kind to resolve. Two
  *different* sources disagreeing about one property is the case the federation
  layer is really for, and the corpus still offers none — SEC and GLEIF share
  no predicate.
- Nothing consumes an unresolved mixture yet. It is retained and serialised and
  no kernel or node reads one, so "the alternatives are available downstream" is
  true and untested by any downstream.
- `prefer_measured` is registered for no predicate by default. The tie refusal
  fires only where a caller passes it explicitly, so the protection is opt-in
  and a caller who forgets gets the old default — the mixture is kept, but
  unresolved rather than ranked, which is safe and less useful.
