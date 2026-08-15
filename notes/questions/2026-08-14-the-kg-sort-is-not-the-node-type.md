---
date: 2026-08-14
author: agent-kg-seam
status: idea
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach,
          2026-08-14-five-of-seventeen-node-types-are-dead,
          2026-08-14-the-curriculum-has-one-object-sort]
---

# The KG seam binds symbols but cannot touch the type head, and the decision note assumed it would

The decision note lists "the type head becomes a real question" as one of four
things a knowledge-graph curriculum buys. As built, **it does not**, and the
reason is worth writing down before someone measures `type_acc` across the arms
and reports a null as evidence about semantics.

`graph.types` in this harness is a **syntactic** category — `ident`, `pred`,
`num`, `list`, `record`, `field`, `str`, `char`, `token` — read off the term's
shape by `symbolic_ai_core/data/graph.py`. The KG binder changes *labels* and
leaves the term shape alone, on purpose: that is what makes a score difference
attributable. So `type_acc` measures exactly what it measured before, and the
0.860 tree-shape floor is untouched by construction.

The binder knows the sort. `KGBinder._trace["kinds"]` carries graph node ids
whose hypernym chains are right there, and `describe()` already reports the
family. What is missing is a way for it to reach the graph: `Lesson.structured`
returns `observation` / `choices` / `answer` / `hidden`, and the sort would have
to travel into a *node attribute*, which means either

* emitting it into `hidden` and having `graph_from_json` carry a parallel
  `sorts` array beside `types` — a new channel, a new head, and a new floor; or
* making the term itself typed, e.g. `obj(id, attr, kind:bird, x, y)`, which
  changes the tree and therefore breaks the one property the arms rest on.

The first is the right shape and it is a real piece of work: a new readout, its
own floor, its own calibrator (and the type head not getting its own calibrator
already cost **-1.96 type lift** on three models at once), and a coverage
number, since only the 5.3% of nodes the graph reaches would have a sort at all.

Until then: **`type_acc` differences between the arms are noise about tokenizers
and label coverage, not evidence about semantics.** Do not read them as the
decision note's second bullet coming true or failing to.
