"""The readout that reads a graph emission as an action.

The registry, the protocol and the argument live in
:mod:`symbolic_ai_core.readout`; :mod:`symbolic_ai_models.readouts` holds the
ones that consume a :class:`~symbolic_ai_models.models.base.ModelOutput`, and
this package holds the one that consumes an
:class:`~symbolic_ai_agents.envs.base.Observation`. Three packages, one
registry — which is the point. A readout registered here is asked for by name
exactly as ``symbol`` and ``site`` are, so "which readout produced this number"
is answerable without knowing which package the number came out of.

Importing this module registers ``action-001``.
"""

from __future__ import annotations

from symbolic_ai_core.readout import (NODE, REGISTRY, SYMBOL, Readout, build,
                                      readout_names, register)

from .action import (BOTH, CHANNEL_CHOICES, ActionReadout, Asked, Emission,
                     emit)

__all__ = ["ActionReadout", "Asked", "Emission", "emit", "BOTH",
           "CHANNEL_CHOICES", "Readout", "REGISTRY", "build", "readout_names",
           "register", "SYMBOL", "NODE"]
