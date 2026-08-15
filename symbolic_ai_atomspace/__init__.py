"""`005`: AtomSpace / MeTTa as the intermediate representation.

The third seam of the repo, opened in
``notes/decisions/2026-08-14-the-ir-is-a-knob.md``. ``symbolic_ai_parsers`` made
*text -> Graph* a parameter and ``symbolic_ai_core.readout`` made *Graph ->
scored prediction* one; both hold the middle term fixed. This package varies it.

An IR earns the name by supplying three things: ``Graph -> IR`` so the
curriculum's exact unannotated ground truth transfers, **native operations** the
flat arrays cannot express, and ``IR -> Graph`` so every existing floor, readout
and published number still applies. Here the native operation is **pattern
matching and rewriting** over a hypergraph of atoms.

Pre-registration, including the prediction that this will *not* beat
``corefer-001`` on label accuracy and why:
``notes/decisions/2026-08-14-atomspace-metta-ir-preregistration.md``.

The real ``hyperon`` is an outside conformance oracle, never a dependency and
never in the hot path — it publishes no wheel for this project's Python, and a C
extension inside a 179-lesson sweep would break ``APPROACH.md``'s cost budget.
"""

from __future__ import annotations

__all__: list[str] = []
