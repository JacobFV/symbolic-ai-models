"""Insensitivity where detection is impossible.

Solvency's `owns` channel is **multi-valued** -- a group holds any number of
subsidiaries -- so no arity constraint checks it and no companion sentence pins
it. Detection fires 0.000 there, measured. The other response to a corrupt
channel is not to decide whether the claim is true but to prove the **answer does
not depend on it**, which is what
`symbolic_ai_generators/flood/certificate.py` does for a spurious road.

It is available here for a reason that does not extend to the *revenue* channel:
the verdict is a sum against a threshold, so dropping a **member** moves the sum
by that member's filing, and whether that changes the verdict depends on the
**margin**. Dropping a *filing* always moves the sum, which is why the same idea
is vacuous there -- the decidedness law already measures solvency revenue at
0.000 decided against `owns` at 1.000.

The hypothesis carried is **at most one membership is spurious**, the same bound
the flood certificate carries for links.
"""

from __future__ import annotations

from dataclasses import replace

from .read_surface import Reading, decide_reading

__all__ = ["certifies_membership_insensitive"]


def certifies_membership_insensitive(reading: Reading) -> bool:
    """True if the verdict survives removing **any single member**.

    Sound for the one-spurious-membership hypothesis and **conditional on the
    rest of the reading**: it says nothing about a wrong threshold, a wrong
    determination date, or a spurious *filing*. That is the same conditional
    structure as the flood certificate, and the same thing to state rather than
    let the name imply.

    Costs one sum per member, no kernel call.
    """
    base = decide_reading(reading)
    if base is None:
        return False
    for m in reading.members:
        without = replace(reading, members=reading.members - {m})
        if decide_reading(without) != base:
            return False
    return True
