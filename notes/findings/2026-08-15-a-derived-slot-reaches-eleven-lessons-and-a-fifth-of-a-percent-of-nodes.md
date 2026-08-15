---
date: 2026-08-15
author: agent-derived-slot
status: provisional
related: [2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control,
          2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach,
          2026-08-15-coverage-is-bounded-by-the-curriculum-not-by-the-graph,
          2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]
---

# A derived slot reaches 11 of 179 lessons and 0.20% of graph positions, and the arms are matched everywhere else

Coverage before models, as rule 4 of the semantic-constraint decision note
requires and as the derivability pre-registration repeats. **Full 179 lessons,
training seeds 0-7, 1,432 episodes per arm, `max_nodes=128`.** No slice.
Reproduced by the scratch pass recorded in this note's companion decision file;
the per-arm matching claims are asserted in `tests/test_kg_derive.py`.

## The headline, and it is small

| | |
|---|---:|
| scene objects the binder is offered | 728 |
| … it derives a value for | **728 (100.0%)** |
| graph positions carrying a derived value | **175** |
| … as a share of all graph nodes | **0.205%** |
| lessons with at least one | **11 of 179** |
| of the derived positions, **not** copyable | 58 (33.1%) |

Read the last three rows before any score. **The pooled 179-lesson `label_acc`
cannot move by more than about 0.003 even if the derived bucket goes from 1/6 to
1.00**, so a flat pooled table is not a result about derivability and must not be
reported as one. That is the same dilution the `kg:` arms had — they reached
5.2% of node labels — a further factor of twenty-five down, because a *derived*
fill needs a per-object hook and the curriculum has one in two places.

The 100% binding rate is the one number that improved. The `kg:` binder fired on
**53%** of scene objects because WordNet had nothing to say about the other
half; here the anchor slot *is* the map's domain, so it never falls back, and
`slots_fallback` is empty on every episode tested. A treatment that backs off on
half its opportunities is a treatment wearing its baseline's behaviour, which is
the failure `notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md`
records; this one does not.

## Where the ceiling is, and it is the curriculum's, not the graph's

The same measurement pass counted, for every closed word list the curriculum
exposes, how many graph positions carry one of its words:

| slot | words | positions | share of nodes | lessons |
|---|---:|---:|---:|---:|
| `name` | 6 | 1,868 | 2.19% | 28 |
| `color` | 6 | 1,679 | 1.97% | 37 |
| `shape` | 6 | 1,156 | 1.35% | 28 |
| `act` | 9 | 593 | 0.69% | 12 |
| `property` | 13 | 508 | 0.59% | 6 |
| all seventeen slots | | 7,515 | **8.79%** | |

A per-fill dependency can only be stated where two bound words sit **under one
parent node**, and there are exactly 965 such colour/kind pairs in the corpus —
the largest such pairing by a factor of four (`shape`/`size` is next at 230).
The existing `bind_scene` seam reaches **175 of those 965 (18%)**, because it
lives in `generators/base.py::_scene` and `generators/extra.py::_objects` and
seven other lesson modules build an `obj` predicate themselves. Hooking those
would roughly quintuple the reach and is a data change, not a design change; it
is recorded as a question rather than done, because the question this arm asks is
whether the mechanism works at all.

**Raising the reach past ~1% would be a curriculum change and not a graph
change**, which is the same conclusion
[[2026-08-15-coverage-is-bounded-by-the-curriculum-not-by-the-graph]] reached
from the other direction.

## The arms are matched, which is what makes a difference readable

The `kg:` arms moved a tree shape on 3 of 2,148 episodes — small, named, and
caused by a rejection loop whose acceptance test reads the symbols. The
`derive:` arms move **none**:

| compared against `derive:wordnet`, 1,432 episodes | episodes whose tree shape differs |
|---|---:|
| `derive:wordnet-perm` | **0** |
| `derive:wordnet-shuffled` | **0** |
| `base` | 1 |

Zero rather than three because the value slot's collision structure *is* the kind
slot's in every arm: a bijection composed with a permutation is a bijection, so
two objects share a value exactly when they share a kind, and a rejection loop
that filters on symbol equality accepts or rejects identically in all three arms.
The same property fixes the copyable share, which is the denominator every
`acc | not copyable` number is conditioned on.

## The one place the arms were *not* matched, found the loud way

`compositional_reference` redraws colours **after** `bind_scene` has run:

```python
while sum(1 for o in lefts if o["color"] == tgt_color) > 1:
    tgt_color = rng.choice(COLORS)
    for o in lefts:
        o["color"] = rng.choice(COLORS)
```

so on some episodes an object's value is a fresh uniform draw rather than the
derived one — and *which* objects survive depends on the arm. Measured on five
scene lessons at six seeds: **114 surviving derived positions in the treatment
against 112 in the control**, 1.8% apart.

1.8% is small and is the wrong thing to shrug at, because `acc | derived, not
copyable` is read per arm and *subtracted*: a difference between two slightly
different populations is not a difference between two models — the failure
[[2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model]]
records. `scripts/derived_split.py::matched_episodes` therefore intersects the
derived positions over all three arms, and `tests/test_kg_derive.py` asserts the
scored position list is identical episode by episode rather than merely equal in
size.

It is also worth stating what this says about the corpus: **a hook into a
generator does not guarantee the value it wrote survives to the term.** Nothing
about the binder could have caught it, and a detector that identified derived
positions by matching labels against the value list would have counted the
redrawn ones as derived once in six by chance, in both arms.

## What would have refuted this note

* **Coverage near zero.** Under about 30 derived positions in the whole corpus
  and no evaluation draw could separate the arms; the honest report would have
  been that the seam cannot carry the experiment. 175 in training and ~2,200 in
  the derived evaluation draw is enough.
* **The binder falling back.** A treatment that derived a value on half its
  objects would be half a control. 728 of 728.
* **A tree shape moving between the arms.** Then a score difference is a shape
  difference. Zero of 1,432, against the `kg:` arms' three.
* **The arms scoring different positions.** They did, by 1.8%, until intersected;
  reported here rather than repaired quietly.

## What this note does not say

Nothing here is a score. It says how much of the curriculum the manipulation
touches and that the arms differ in one thing only. Whether any model uses the
channel is `scripts/derived_split.py` and the companion finding.
