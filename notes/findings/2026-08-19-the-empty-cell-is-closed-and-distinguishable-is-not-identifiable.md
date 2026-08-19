---
title: The empty cell is closed, and distinguishable is not identifiable
date: 2026-08-19
status: measured
arm: is-the-empty-cell-reachable
---

## The question

[[2026-08-19-two-readers-two-axes-and-an-empty-intersection]] left the front at
one cell: V=4 phrasings, sentences interleaved, where every collapsing reader
scores 0.000 and the sound enumerating arm carries 2.5 worlds and decides 32.4%.
The residual blocking it is **depot vs flooded** — both realised as one-region,
no-number, no-vehicle sentences.

Before building a reader for that cell, is one possible? A reader consulting no
content word observes only entity types, numbers, value-registry membership, and
which sentences mention which entity.

## The wrong answer I nearly published

Compute each lone region's **fingerprint** — the multiset of sentence signatures
over every sentence mentioning it — and compare the depot's with the flooded
regions':

| | |
|---|---:|
| depot fingerprint identical to some flooded region | 4/60 (6.7%) |
| depot fingerprint **distinguishable** | **56/60 (93.3%)** |

I predicted "closed" at 0.75 confidence, and this said the opposite. The script
printed *REACHABLE — the empty cell is unsolved rather than closed*.

It is wrong, and the reason is worth more than the number. Look at what the
fingerprints actually differ on:

```
seed 0  depot 5 link-sentences, flooded 3 and 4
seed 1  depot 5,                flooded 5      <- tie
seed 2  depot 6,                flooded 4
```

The distinguishing feature is **node degree in the road network**. Two regions
having different degrees makes them *asymmetric*; it does not make either one
identifiable as the depot. **A reader needs a rule mapping observation → role,
and degree has no reason to encode depot-ness.**

## The right answer

**One rule, tested.** "The depot is the highest-degree lone region":

| | |
|---|---:|
| rule correct | 20/60 = **33.3%** |
| chance | **28.5%** |
| depot ties with another lone region | 14/60 = 23.3% |

Four points above chance, on 60 cases. No signal.

**Every rule at once.** A rule is only possible if observation → role is a
*function*. If the same content-free observation carries "depot" in one case and
"flooded" in another, no deterministic reader consuming that observation can be
right about both — whatever its architecture. Over 120 cases:

| observation | distinct | carrying >1 role | ambiguous role-slots |
|---|---:|---:|---:|
| exact fingerprint | 49 | 34 | 78/93 |
| rank-normalised | 7 | **7 (all)** | **21/21** |

It is not a function. Every rank-normalised observation carries all three roles.

## Conclusion

**The empty cell is closed to content-free reading.** Not because the surface is
symmetric — it mostly is not — but because its asymmetry is incidental rather
than informative. Settling depot vs flooded **requires reading content**.

That converts a lexical resource from a shortcut into a **necessity**, and it is
the first place in this programme where that is true rather than assumed.
`state.yml` had already guessed it — *"the first place a lexical resource
(WordNet is on disk) or a learned component is the only mechanism available, not
a shortcut"* — for the superlative case. It is now measured, for the harder one.

It also bounds the enumerating arm honestly: **32.4% decided is a ceiling for
content-free reading on this surface**, not a limitation of one implementation.
Effort spent on a better content-free reader for this cell is spent against a
proof.

## What would refute this

A content-free observable I did not include. The fingerprint covers entity types,
numbers, registry membership and sentence co-occurrence; it does **not** cover
the *identity* of co-occurring entities (which specific regions a region links
to). A reader using graph structure — "the depot is the region every route
starts from" — is using the kernel's semantics, not the text's, and would need
the world it is trying to build. But the collision test only bounds readers
consuming *this* observable, and a richer content-free observable would need its
own collision test before it could be ruled out.

## Correction

This finding's own first pass concluded the opposite, and the script printed it.
The script now runs all three tests and prints the corrected verdict, so it
cannot mislead a later session the way it briefly misled me.
