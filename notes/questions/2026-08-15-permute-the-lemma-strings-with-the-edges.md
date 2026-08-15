---
date: 2026-08-15
author: agent-kg-semantics
status: idea
related: [2026-08-15-the-kg-arms-are-a-null-and-the-quarter-that-mattered-did-not-move,
          2026-08-14-a-kg-curriculum-may-need-a-model-that-knows-english,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]
---

# A fourth control: permute the lemmas too, and see whether the +0.004 survives

`kg:wordnet` beats `kg:wordnet-shuffled` by **+0.0041** mean pooled `label_acc`,
12 of 15 models positive (sign test p ≈ 0.035), all of it inside the copyable
bucket and none of it on the non-copyable quarter. Too small to be the headline,
too consistent to ignore.

The named candidate mechanism is the only channel the degree-preserving scramble
leaves open: **lemma strings**. In the real graph a family's members share
morphology (`stringed_instrument` / `wind_instrument`), so an episode's six
words share subword pieces; the scramble permutes edges and leaves the names
where they are.

The arm that would settle it is cheap and is a `registry.py` row: scramble the
edges **and** apply a permutation to the node→lemma map, so the graph keeps its
degrees *and* loses the string correlation. Three outcomes:

* `kg` > `lemma-scrambled` ≈ `shuffled` — the +0.004 is morphology, and it is a
  tokenizer effect wearing the semantics' name;
* `kg` ≈ `shuffled` > `lemma-scrambled` — the string channel was carrying
  something in *both* arms;
* all three equal — the +0.004 was noise at n=15, which the sign test cannot
  rule out on its own.

Worth doing before anyone quotes the +0.004 as evidence for anything.
