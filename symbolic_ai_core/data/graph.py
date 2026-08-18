"""Deprecated. Moved to :mod:`symbolic_ai_core.data.term_graph`.

A bare "graph" is ambiguous in this repo now: a ``flow_graph`` is executable and
acyclic, a ``world_ir`` is represented state with arbitrary topology, and the
thing this module used to hold is a **term graph** — one episode's syntax tree,
flattened into parallel arrays. See
``notes/decisions/2026-08-18-flow-is-a-dag-the-world-is-not.md``.

Kept so that anything written against the old path — including
``symbolic_ai_agents`` on its own branch — keeps importing. Import from
:mod:`symbolic_ai_core.data.term_graph` in anything new.
"""

from __future__ import annotations

from .term_graph import *                              # noqa: F401,F403
from .term_graph import Graph, __all__, graph_from_json  # noqa: F401
