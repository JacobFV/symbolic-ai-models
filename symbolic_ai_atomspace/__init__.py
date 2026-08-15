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

from .atoms import (Atom, E, Expression, G, Grounded, S, Symbol, V, Variable,
                    is_ground, parse_atom, parse_atoms, print_atom,
                    variables_in)
from .encode import (CHILD, DERIVED_RULES, HIDDEN, LABEL, NODE, ROOT, TYPE,
                     UNKNOWN_TYPE, atomspace_to_graph, derived_space,
                     graph_to_atomspace, occurrence, term_atom,
                     view_to_atomspace)
from .metta import CONJ, EQ, Rule, chain, rule
from .roles import (ANCESTOR_RULES_SOURCE, ROLE_QUERIES, TUPLE_QUERIES,
                    RoleQuery, child_type_key, node_index, role_signatures)
from .space import AtomSpace
from .unify import Bindings, match_atom, substitute, unify

__all__ = [
    # atoms
    "Atom", "Symbol", "Variable", "Expression", "Grounded",
    "S", "V", "E", "G", "print_atom", "parse_atom", "parse_atoms",
    "is_ground", "variables_in",
    # unification
    "unify", "match_atom", "substitute", "Bindings",
    # the space
    "AtomSpace",
    # the language
    "Rule", "rule", "chain", "CONJ", "EQ",
    # the encoding
    "NODE", "TYPE", "LABEL", "CHILD", "ROOT", "HIDDEN", "UNKNOWN_TYPE",
    "occurrence", "graph_to_atomspace", "atomspace_to_graph",
    "view_to_atomspace", "term_atom", "derived_space", "DERIVED_RULES",
    # roles
    "RoleQuery", "ROLE_QUERIES", "TUPLE_QUERIES", "role_signatures",
    "child_type_key", "node_index", "ANCESTOR_RULES_SOURCE",
]
