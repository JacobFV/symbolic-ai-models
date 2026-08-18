"""Typed ports, and the binding that connects two of them.

A port declares what travels through it: an artifact ``type``, and optionally
the ``unit`` and coordinate ``frame`` that artifact must be in. Those last two
are checked at evaluation and are not decoration — an implicit unit conversion
is how a metre meets a foot, and this repo's own history says the shared plumbing
moves results further than the models do.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["Port", "Binding", "ANY", "compatible"]

#: The wildcard port type. ``flow.const@1``, ``flow.identity@1`` and the
#: container ops are genuinely polymorphic -- a constant carries whatever it was
#: given -- so they declare ``any`` and the checker lets anything through them.
#:
#: It is a **wildcard, not a default**. A domain op that declares ``any`` has
#: opted out of the one check that would have caught a term_graph plugged into a
#: world_snapshot, so ``any`` on anything outside the flow layer itself is a
#: smell, and the ops registry prints the type it was actually handed in the
#: trace either way.
ANY = "any"


def compatible(want: str, give: str) -> bool:
    return want == give or ANY in (want, give)


@dataclass(frozen=True)
class Port:
    """One named input or output of an operation."""

    name: str
    type: str
    required: bool = True
    unit: str = ""       #: "" means "this port does not constrain the unit"
    frame: str = ""      #: "" means "this port does not constrain the frame"
    profiles: tuple[str, ...] = ()   #: world profiles the payload must carry

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "type": self.type, "required": self.required,
                "unit": self.unit, "frame": self.frame,
                "profiles": list(self.profiles)}


@dataclass(frozen=True)
class Binding:
    """An input is bound to some upstream node's output port.

    Downstream-declared, exactly as in the commandagi operation graph: a node
    lists where its inputs come from, and no node has to know who consumes it.
    That is what makes deleting a leaf a local edit.
    """

    node: str
    port: str = "out"

    def to_dict(self) -> dict[str, Any]:
        return {"node": self.node, "port": self.port}
