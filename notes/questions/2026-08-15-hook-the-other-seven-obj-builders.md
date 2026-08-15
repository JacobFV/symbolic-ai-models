---
date: 2026-08-15
author: agent-derived-slot
status: idea
related: [2026-08-15-a-derived-slot-reaches-eleven-lessons-and-a-fifth-of-a-percent-of-nodes]
---

A per-fill dependency can only be stated where two bound words sit under one
parent, and the curriculum has **965 colour/kind pairs** like that over 179
lessons x 8 seeds. `bind_scene` reaches **175 of them (18%)**, because it lives
in `generators/base.py::_scene` and `generators/extra.py::_objects` and seven
other modules build an `obj` predicate themselves — `social.py::_obj_facts`,
`semantics.py::_world`, `spatial_language`, `underspecification_reasoning`,
`speaker_listener_game`, `interactive_reference`, `natural_language_bridge`,
`ambiguity_preservation`.

Hooking those would take the derived slot from 0.20% of graph positions to about
1%, five times the population, and it is a data change rather than a design one:
the hook is inert without an active binder, so the base fingerprint cannot move.

Two things to check before doing it, both learned in this arm:

* `compositional_reference` **overwrites** the bound colour in a rejection loop
  after `bind_scene` returns, so a hook does not guarantee the derived value
  survives to the term. Any new hook needs the same intersection check.
* `shape`/`size` is the next largest co-parented pairing at 230 positions and
  `name`/`thing` at 217. A second derived slot on a different pair would say
  whether the result is about the mechanism or about `color`.
