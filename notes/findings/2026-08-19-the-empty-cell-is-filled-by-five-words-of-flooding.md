---
title: The empty cell is filled, and the content that fills it is one vocabulary
date: 2026-08-19
status: measured
arm: minimal-content-for-the-residual
---

## What this closes

[[2026-08-19-two-readers-two-axes-and-an-empty-intersection]] found the two
reader mechanisms failing on orthogonal axes with an empty intersection, and
[[2026-08-19-the-empty-cell-is-closed-and-distinguishable-is-not-identifiable]]
proved that the residual blocking it — depot vs flooded — cannot be settled by
any content-free observable (21/21 role-slots ambiguous). So content is required,
and the open question was **how little**.

`state.yml` said "WordNet is on disk". **It is not** — `~/nltk_data/corpora`
holds only `words`, and `nltk` is not installed. That turned out to be lucky,
because it forced the cheap arm first.

## The arm

`read_content_roles` reads everything the signature determines exactly as
`read_signature_roles` does, consulting no content word, and reads **only** the
one group the signature leaves open. Its knowledge is a declared anchor
vocabulary per role, matched by token prefix (`base` reaches *based*, `start`
reaches *starts*, `supply` does not reach *resupply*).

**The anchors were fixed and written into `predictions.jsonl` before the phrasing
variants were read.** Choosing them afterwards would be memorising the generator,
which is why the rules arm's 1.000 at V=1 means nothing.

| reader | V1 grouped | V1 interleaved | V4 grouped | V4 interleaved |
|---|---:|---:|---:|---:|
| signature/roles | 1.000 | 0.000 | 1.000 | 0.000 |
| rules | 1.000 | 1.000 | 0.000 | 0.000 |
| **signature+content** | **1.000** | **1.000** | **1.000** | **1.000** |

The first reader in this repo invariant to **both** phrasing and arrangement.

I predicted 0.4–0.8 in the hardest cell, reasoning that a variant set written to
vary wording would dodge the obvious lemma. It does — "Vehicles are *dispatched*
from {w}" and "{w} is *asking for resupply*" are reached by no declared anchor.
The arm reaches 1.000 anyway because **elimination and adjacency cascade over the
misses**, which is the same partial-cascade mechanism the renaming manipulation
measured.

## The control, which fails as it must — and corrects an earlier claim

| anchors | V4 grouped | V4 interleaved |
|---|---:|---:|
| full | 1.000 | **1.000** |
| **ALL emptied** | 0.765 | **0.618** |
| without flooded | 0.882 | 0.853 |
| without depot | 0.941 | 0.941 |
| without needs | 1.000 | **1.000** |

Content is worth **+0.382**, so it is genuinely load-bearing. But the
content-free floor is **0.618**, not the 0.000 the earlier finding quoted, and
that difference is a **correction I owe to my own write-up**.

At claim level, with the anchors emptied:

| | needs | depot | flooded |
|---|---:|---:|---:|
| recall | **1.000** | 0.471 | 0.632 |

Three things follow:

- **Adjacency fully solves `needs`** — 1.000 recall with no content at all. That
  is why the needs vocabulary is redundant: removing it costs exactly nothing.
- **Depot and flooded sit where the closure finding says they must**, far from
  1.000 and unfixable by any rule. The closure result **stands at the claim
  level**.
- **Answer accuracy (0.618) exceeds depot recall (0.471)** because a region
  wrongly marked flooded is often not on the route the answer needs. Answers
  survive some wrong claims.

So what is corrected is the *answer-level* statement that the cell was empty. It
was empty **for the arms that existed** — `read_signature_roles` scored 0.000
there — and a properly built content-free arm floors at 0.618. Two of that arm's
improvements are content-free and were simply missing before: binding `needs` by
adjacency rather than paragraph membership, and never defaulting an unresolved
region to *flooded*.

That second one is not a detail. Marking a region impassable **cuts the network**
and destroys the answer; leaving it unassigned merely fails to help. The first
version of this reader defaulted to flooded and scored 0.000 for that reason
alone — a reader that looked like a failed hypothesis and was a bad default.

## What the content actually has to know

**One vocabulary, and it is flooding.** Removing the flooded anchors costs the
most (0.853); removing needs costs nothing; depot sits between (0.941).

The reason is structural rather than lexical. `needs` is pinned by adjacency and
`depot` is single-valued, so elimination can reach it — but **flooding is the
many-valued role**, and elimination cannot pin a set whose size it does not know.
That is what has to be read.

**WordNet is not needed here, and installing it would have been reaching for a
resource before measuring the gap.** Five concept words for flooding, declared in
advance, close a cell that no amount of content-free machinery can.

## What would refute this

- The anchors reaching 1.000 by accident of the four variants. The honest test is
  a fifth phrasing that avoids water, flood, submerge, inundate, impassable and
  underwater — *"{w} went under overnight"* already does, and the arm survives it
  only through elimination. A variant set built adversarially against the
  declared anchors would find the true floor, and that is the next test.
- `tests/test_content_roles.py` (9 tests) pins the grid, requires the ablation to
  damage, requires `needs` to be redundant, requires unresolved regions never to
  be marked flooded blindly, and requires the non-residual claim kinds to be
  **identical** with anchors emptied — so the arm cannot quietly start reading
  content for anything the signature already fixes.
