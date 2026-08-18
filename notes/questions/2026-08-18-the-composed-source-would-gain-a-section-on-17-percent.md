---
date: 2026-08-18
author: lead
status: idea
tags: [knowledge-source, federation, alignment]
---

# A WordNet+CSKG composed source gains a section on 17% of topics, and the join is an alignment we are not entitled to assert

Measured before building it, which is why it is a question note and not a
finding:

| | |
|---|---|
| WordNet lemmas also in CSKG | 5,237 / 10,094 = **0.519** |
| WordNet rich topics joinable | 677 / 1,074 = **0.630** |
| of those, gain a `qualities` section | 164 / 677 = 0.242 |
| of those, gain a `behaviour` section | 130 / 677 = 0.192 |
| of those, gain **at least one** | 0.267 |
| **overall share of rich topics gaining a section** | **0.630 × 0.267 ≈ 0.168** |

So a composed source fills the two dead sections on roughly **one topic in six**,
not on the 0.405 / 0.230 CSKG reaches over its *own* topic set. Worth building,
much less worth it than the per-source numbers suggest, and knowing that cost one
measurement rather than one implementation.

## The part that is not a mechanical join

Joining on exact lemma is precisely the **silent identity collapse** the
federation decision note forbids. WordNet's `dog.n.01` is a *synset*; CSKG's
`/c/en/dog` is a lemma-collapsed concept that already merges senses. They are not
established to be the same thing, and for a polysemous lemma they demonstrably
are not — `bank` is one CSKG node and several WordNet ones.

So the composed source must express the join as an `Alignment` with relation
`possibly_same` and a stated confidence, **not** as a merge, and the resulting
essays carry claims of mixed provenance. That is what per-claim provenance in the
world IR is for, and this would be its first real use.

## And the double-count is live here

CSKG is a consolidation of seven upstreams **including WordNet 3.0**. A composed
WordNet+CSKG source therefore ingests some WordNet assertions twice — once
directly, once through CSKG — which is exactly the composite-source double-count
`catalog/sources/cskg.yaml` warns about and
`tests/test_source_federation.py::test_composite_sources_do_not_double_count`
exists to keep visible. The composed source is the first thing that would
actually trip it, so it should be built *with* the assertion-level origin
tracking rather than before it.

## The one thing that could have made it worth more, checked

If the 17% concentrated on the topics a task actually draws, the average would
understate it. It does not — `generate` samples the rich-topic pool uniformly,
so the drawn rate matches the pool rate almost exactly:

| | |
|---|---|
| share of the pool that gains a section | 0.169 |
| share of 400 *drawn* topics that gain one | 0.175 |
| distinct topics in those 400 draws | 249 of 1,074 |

So 17% is the number, not a lower bound on it. That closes the only cheap way
this could have been more valuable than it looks, which is why this stays a
question note: worth doing, not worth doing next.
