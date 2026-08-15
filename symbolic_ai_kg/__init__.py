"""A vendored knowledge graph, and the machinery for binding variables under it.

The curriculum in ``symbolic_ai_data`` draws a colour and a shape *independently*
from two six-word lists, so a red cube and a purple rod are equiprobable and
nothing in a generated term ever distinguishes one entity from another. That is
why every entity symbol in an episode collapses into a single metavariable
component, and why the type head is a tree-shape lookup nothing has beaten. See
``notes/decisions/2026-08-14-semantic-constraint-from-a-knowledge-graph.md``.

This package is the seam for fixing that at the data level. It holds

* :mod:`symbolic_ai_kg.graph` — a small typed graph and the queries a binder
  needs (hypernym chain, parts, substances, co-hyponyms, attribute values,
  which verbs take an animate subject);
* :mod:`symbolic_ai_kg.registry` — **the graph is a parameter**, and that claim
  has now been cashed. ``load("wordnet")``, ``load("wordnet-shuffled")``,
  ``load("cskg")`` and ``load("cskg-shuffled")`` are four names in one table;
  adding the commonsense graph was two rows here, one builder script and one
  vendored file, with no change above this package and no movement in any
  WordNet fingerprint;
* :mod:`symbolic_ai_kg.scramble` — the degree-preserving edge permutation that
  makes "semantics helped" separable from "more structure helped";
* :mod:`symbolic_ai_kg.bind` — the dependency DAG: a lesson anchors some
  variables outright and binds the rest under constraint from the ones already
  bound;
* :mod:`symbolic_ai_kg.derive` — the slot that is **not drawn at all**. ``bind``
  re-labels the curriculum and its scramble is therefore an isomorphism, which
  is why that control tied at −0.0013 and could not have done anything else.
  ``derive`` makes an object's attribute *follow* from its kind through a fixed
  corpus-wide map, and its control — the same map permuted per episode — removes
  the one channel the treatment has. See
  ``notes/decisions/2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control.md``.

Nothing here changes the existing curriculum. The KG curricula are registered
beside it under their own names and the 179-lesson fingerprint stays green;
that test firing would mean this package had broken rule 1 of the decision note.
"""

from __future__ import annotations

from .derive import DeriveBinder, anchor_map
from .graph import KnowledgeGraph
from .registry import KG_NAMES, load
from .scramble import degree_preserving_shuffle

__all__ = ["KnowledgeGraph", "KG_NAMES", "load", "degree_preserving_shuffle",
           "DeriveBinder", "anchor_map"]
