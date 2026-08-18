"""No exported public type may be called merely ``Graph``.

The repo now distinguishes a ``flow_graph`` (executable, acyclic), a ``world_ir``
(represented state, arbitrary topology) and a ``term_graph`` (one episode's
flattened syntax tree). The project this will share a wire schema with uses
"graph" for four more things again. An unqualified ``Graph`` collides with all
of them, and the collision is silent — two modules each importing "the" Graph
and getting different ones fails at runtime, far from the import.

One alias survives, in one module, because fifty registered models and every
published number here are defined over it. This test allows exactly that and
fails on anything else. See
``notes/decisions/2026-08-18-flow-is-a-dag-the-world-is-not.md``.
"""

from __future__ import annotations

import importlib
import pkgutil

#: The deprecated alias, and the two modules allowed to carry it.
ALLOWED = {
    "symbolic_ai_core.data.term_graph",   # where TermGraph is defined
    "symbolic_ai_core.data.graph",        # the shim at the old import path
    "symbolic_ai_models.data.graph",      # the older shim, for symbolic_ai_agents
}

PACKAGES = ("symbolic_ai_core", "symbolic_ai_kg", "symbolic_ai_parsers",
            "symbolic_ai_lean", "symbolic_ai_atomspace")


def _modules():
    for pkg_name in PACKAGES:
        pkg = importlib.import_module(pkg_name)
        yield pkg_name, pkg
        for info in pkgutil.walk_packages(pkg.__path__, pkg_name + "."):
            if ".models." in info.name:            # 50 model packages, slow
                continue
            try:
                yield info.name, importlib.import_module(info.name)
            except Exception:                      # optional deps, torch-gated
                continue


def test_no_public_unqualified_graph_type():
    offenders = []
    for name, mod in _modules():
        if name in ALLOWED:
            continue
        obj = getattr(mod, "Graph", None)
        if obj is None:
            continue
        # A re-export of the one allowed alias is the alias, not a new name.
        if getattr(obj, "__module__", "") == "symbolic_ai_core.data.term_graph":
            offenders.append(f"{name} re-exports the deprecated Graph alias")
        else:
            offenders.append(f"{name}.Graph is a distinct type")
    assert not offenders, (
        "a bare `Graph` is ambiguous between flow_graph, world_ir and "
        "term_graph:\n  " + "\n  ".join(offenders))


def test_the_deprecated_alias_is_the_same_object():
    from symbolic_ai_core.data.graph import Graph, graph_from_json
    from symbolic_ai_core.data.term_graph import TermGraph, term_graph_from_json

    assert Graph is TermGraph
    assert graph_from_json is term_graph_from_json


def test_the_term_graph_still_builds_an_episode():
    """The rename is a rename. It must not have changed what is built."""
    from symbolic_ai_core.data.term_graph import term_graph_from_json

    g = term_graph_from_json({"t": "pred", "head": "on",
                              "args": [{"t": "ident", "v": "cup"},
                                       {"t": "ident", "v": "table"}]})
    assert g.sexpr() == "(on cup table)"
    assert g.types[0] == "pred" and g.parent[0] == -1
