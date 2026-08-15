---
date: 2026-08-14
author: agent-005-atomspace
status: measured
related: [2026-08-14-atomspace-metta-ir-preregistration,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# Five of the seventeen declared node types never occur, and one of the two things `STRUCTURAL` excludes is a ghost

Measured while writing the `005` round-trip test's alphabet guard, on **179
lessons x 8 seeds = 1,432 episodes**, every node counted:

| type | count | | type | count |
|---|---:|---|---|---:|
| `ident` | 42,373 | | `nil` | **0** |
| `pred` | 25,205 | | `tuple` | **0** |
| `num` | 14,271 | | `app` | **0** |
| `list` | 6,316 | | `rel` | **0** |
| `token` | 1,826 | | `node` | **0** |
| `char` | 1,637 | | `pad` | 0 (collator) |
| `str` | 656 | | `mask` | 0 (collator) |
| `field` | 5,552 | | `text` | 0 (collator) |
| `record` | 1,520 | | | |

So `NODE_TYPES` is seventeen names, three of which only the collator writes, and
**five of which nothing writes at all**. The type head is a 9-way problem, not a
17-way one.

## Why it is worth writing down rather than shrugging at

**`STRUCTURAL` is `{list, record}`.** It is declared as
`{tuple, list, record, app, nil}` and is the set excluded from the label half of
the masked-node loss on the grounds that "a list is a list". Three of its five
members are ghosts, so whatever that exclusion is doing, it is doing it with two
types — and `list` and `record` together are 7,836 nodes against `ident`'s
42,373.

**Two of the dead types are the ones `_label_of` has special cases for.** `app`
reads `fn`, `rel` and `node` read `head`. Three branches of the labelling
function have never executed on this curriculum. That is not a bug; it is
vendored generator surface that this curriculum does not reach, and it means any
claim about how `_label_of` behaves is a claim about `pred` and `ident`.

**It bounds the type head's ceiling in a way the floor's 0.860 already hints
at.** `README.md` says node type is very nearly determined by tree shape; part
of why is that there are nine outcomes and one of them (`ident`) is 42% of all
nodes. A model reported as beating the type floor should be read against *which*
of nine, not against seventeen.

## What it does not say

It does not say the dead types are dead in `langcurriculum` generally — only
that no implemented lesson emits them at these seeds. Eight seeds is a lot for a
generator whose episodes are pure functions of the seed, but it is not a proof,
and the guard in `tests/test_atomspace.py` is written in **both** directions for
exactly that reason: if a type on the dead list starts being generated, the test
fails and says the round trip has never been exercised on it.

## Worth chasing?

Probably not on its own. The one place it might matter is anything that reports
a per-type breakdown or weights a loss by type count — a denominator of
seventeen where the answer is nine is the kind of quiet factor-of-two this repo
has been bitten by. Parked here rather than chased.
