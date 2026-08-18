"""The world IR: what is represented, as opposed to what is executed.

The executable half of this substrate is a DAG. **This half is not.** A road
network is cyclic, an economy is cyclic, a social graph is cyclic, and mutual
constraints in a scene are cyclic. Anything here that assumed acyclicity would
be assuming the world is a tree, and the whole reason the flow layer is a
separate module is so that it can be strict without this one having to be.

The primitives are deliberately few — entity, facet, quantity, claim, event,
delta, snapshot — and the domain complexity lives in **profiles** and in kernels
rather than in a single ontology. One entity carries several facets at once
(``san_francisco`` is a ``geo.place``, a ``politics.jurisdiction`` and an
``economy.market_area``); a kernel asks for the capabilities it needs and is
indifferent to the rest.
"""

from __future__ import annotations

from .profile import CORE_PROFILES, PROFILES, check_profiles, known_profile
from .entity import Entity, EntityRef, Facet, Quantity
from .claim import ALIGNMENT_RELATIONS, Alignment, Claim, MODALITIES, POLARITIES
from .delta import WorldDelta
from .snapshot import WorldSnapshot

__all__ = ["CORE_PROFILES", "PROFILES", "check_profiles", "known_profile",
           "Entity", "EntityRef", "Facet", "Quantity",
           "ALIGNMENT_RELATIONS", "Alignment", "Claim", "MODALITIES",
           "POLARITIES", "WorldDelta", "WorldSnapshot"]
