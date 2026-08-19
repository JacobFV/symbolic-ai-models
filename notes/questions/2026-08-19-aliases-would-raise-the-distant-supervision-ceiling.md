---
title: Aliases would raise the distant-supervision ceiling, and the local mirror cannot supply them
date: 2026-08-19
status: idea
---

Distant supervision on the 168-article corpus caps at **0.577** for `parent`:
only 58% of intros contain a sentence with the gold parent's *canonical label*.
Many of the rest almost certainly state the relation with a different surface
form — *owned by Sony* where the gold is `Sony Music`, *a Ministry of
Communications body* where the label matched but the sentence did not.

Matching on **any Wikidata alias** of the gold entity (and on the labels of its
`P361`/`P749` chain) should raise that ceiling materially, and it is the kind of
external standard this repo already treats as a given. It would raise the ceiling
for every arm at once, including the hand-written reader's 0.393, so it changes
the denominator rather than favouring anything.

**Blocked on where the aliases come from.** The local mirror
`data/sources/wikidata/.../backbone_*.parquet` is 53M rows of
`(source_id, target_id, kind)` — an edge list with no labels and no aliases at
all. The `wbgetentities` API has them, and it is the same endpoint currently
being rate-limited to 429s while the scale corpus is fetched.

So: worth doing, after the scale fetch is finished and the rate limit has
recovered, in one batched pass over the gold qids already on disk. Until then the
0.577 stands as a ceiling *on canonical-label containment*, which is narrower
than "distant supervision cannot see the rest" and should be quoted that way.
