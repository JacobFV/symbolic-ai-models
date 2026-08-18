"""Licence closure: computed from the parents, never authored on the child.

The rule is **the most restrictive term on each axis**, and the ordering below
is the whole of it. Two properties matter more than the details:

* ``unresolved`` sorts as *more* restrictive than anything known. A derived
  artifact with one parent whose licence nobody established is unresolved, not
  permitted. That is deliberately inconvenient: the alternative is a closure
  that is wrong in the permissive direction, which is the direction that gets
  something published it should not have been.
* A closure is never edited on the child. If a derived artifact needs a
  different licence, the fix is upstream — a differently-licensed parent, or an
  established licence for the parent that had none.
"""

from __future__ import annotations

from typing import Iterable, Mapping

__all__ = ["LICENSE_ORDER", "license_closure", "COMMERCIAL_ORDER"]

#: Least restrictive first. ``unresolved`` is last on purpose.
LICENSE_ORDER = ("permitted", "attribution_only", "share_alike",
                 "non_commercial", "prohibited", "unresolved")

COMMERCIAL_ORDER = ("permitted", "restricted", "prohibited", "unresolved")


def _most_restrictive(values: Iterable[str], order: tuple[str, ...]) -> str:
    rank = {v: i for i, v in enumerate(order)}
    worst = "permitted"
    for v in values:
        if v not in rank:
            return "unresolved"
        if rank[v] > rank[worst]:
            worst = v
    return worst


def license_closure(parents: Iterable[Mapping[str, str]]) -> dict[str, str]:
    """The licence a thing derived from ``parents`` inherits.

    ``parents`` are the ``license`` blocks of the sources and artifacts it was
    computed from. An empty parent list is ``unresolved`` rather than
    ``permitted``: a thing with no recorded provenance has not been established
    to be redistributable, it has merely not been asked.
    """
    parents = list(parents)
    if not parents:
        return {"redistribution": "unresolved", "commercial_use": "unresolved",
                "spdx": "", "sources": []}
    redist = _most_restrictive(
        (p.get("redistribution", "unresolved") for p in parents), LICENSE_ORDER)
    commercial = _most_restrictive(
        (p.get("commercial_use", "unresolved") for p in parents),
        COMMERCIAL_ORDER)
    spdx = sorted({p.get("spdx", "") for p in parents if p.get("spdx")})
    return {"redistribution": redist, "commercial_use": commercial,
            "spdx": " AND ".join(spdx), "sources": spdx}
