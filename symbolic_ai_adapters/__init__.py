"""Surface adapters: bytes as they arrive -> typed world IR.

An adapter is the boundary where an external representation stops being
authoritative. Everything upstream of it is somebody else's schema decision;
everything downstream is the world IR's. Three rules make that boundary honest
rather than a place where information quietly appears:

* **An adapter records what it discarded.** Same contract as a kernel
  projection. Openflights' airport rows carry ``icao``, ``callsign``, ``active``
  and a timezone; no profile consumes them, so they are dropped *by name*.
* **An assumption is provenance, not a default.** Openflights states no
  coordinate reference system anywhere in its bytes, and the geo kernel refuses
  a place without one. The adapter therefore asserts ``EPSG:4326`` **with a
  citation to the source documentation**, recorded on the facet, rather than
  defaulting to it silently. A reader can then disagree with the assumption
  instead of being unable to see it.
* **A missing value is missing.** ``pop=0`` in a body is not a population of
  zero unless something says it is.
"""

from __future__ import annotations

from .openflights import (MERGED_IATA_NODES, OPENFLIGHTS_CRS, AdapterResult,
                          OpenflightsIntegrityError, check_iata_merges,
                          detect_merged_iata_nodes, load_airports, load_routes,
                          parse_body)

__all__ = ["AdapterResult", "load_airports", "load_routes", "parse_body",
           "OPENFLIGHTS_CRS", "OpenflightsIntegrityError", "MERGED_IATA_NODES",
           "detect_merged_iata_nodes", "check_iata_merges"]
