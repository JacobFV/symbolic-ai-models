"""How far a decision sits from its boundary, and what that predicts.

Three tasks measured across two wake-ups say the same thing: the distance from
the decision boundary governs **both** whether a cheap gate can fire and whether
recall or precision errors dominate — because both are asking how large an error
it takes to change the answer.

If that is true, it is actionable rather than merely interesting: the margin can
be measured on **uncorrupted** worlds, before a reader exists, before a router is
built, and before anyone spends a week on the wrong one.

The measurement is deliberately crude and assumption-light. Given a decision
function and a way to scale the quantity the decision turns on, binary-search the
scale factor at which the answer flips. ``|factor − 1|`` is the relative margin,
and its distribution over a corpus is the profile.

What it is **not**: a substitute for measuring the corruption channels. It is a
*prediction* of their ordering, and the point of writing it as code is that the
prediction can then be wrong out loud.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any, Callable, Iterable, Sequence

__all__ = ["MarginProfile", "relative_margin", "margin_profile",
           "RECALL_DOMINATES_BELOW", "PRECISION_DOMINATES_ABOVE"]

#: Where the recall/precision ordering crosses. **Read off two tasks and then
#: confirmed on a third that was measured before this module existed** -- flood's
#: drop/misread ratio of 1.76 was recorded days earlier, and its median margin
#: came out 0.280, on the curve between solvency at 0.250/1.74 and scheduling at
#: 0.335/1.61.
#:
#: Stated as constants rather than buried, because they are the falsifiable part:
#: a task whose margin is 0.15 and whose precision errors dominate refutes this
#: directly.
RECALL_DOMINATES_BELOW = 0.35
PRECISION_DOMINATES_ABOVE = 0.45


@dataclass(frozen=True)
class MarginProfile:
    """The distribution of how far decisions sit from their boundary."""

    margins: tuple[float, ...]
    n: int
    unbounded: int = 0        #: cases no scaling in range could flip

    @property
    def median_margin(self) -> float:
        """``inf`` when most cases cannot be flipped at all -- a real answer.

        A corpus where scaling the deciding quantity by 10x changes nothing is
        not a corpus with a large margin, it is one where this quantity is not
        what the decision turns on, and the caller needs to know which.
        """
        finite = [m for m in self.margins if m != float("inf")]
        if not finite or len(finite) < self.n / 2:
            return float("inf")
        return median(finite)

    @property
    def dominant_channel(self) -> str:
        m = self.median_margin
        if m == float("inf"):
            return "neither -- the scaled quantity does not decide this task"
        if m < RECALL_DOMINATES_BELOW:
            return "recall"
        if m > PRECISION_DOMINATES_ABOVE:
            return "precision"
        return "both"

    @property
    def routable(self) -> bool:
        """Whether a cheap sufficient condition can be expected to fire.

        A gate is a bound, and a bound only decides cases that sit near or past
        the boundary. A corpus whose decisions all sit far from it has nothing
        for a bound to catch, which is what the scheduling sweep showed: the
        capacity gate fired on 100% of over-subscribed instances and 0% of
        everything else.
        """
        return self.median_margin < PRECISION_DOMINATES_ABOVE

    def advice(self) -> str:
        m = self.median_margin
        if m == float("inf"):
            return ("the quantity scaled here does not decide this task; "
                    "measure the margin on whatever does before trusting any "
                    "of this")
        parts = [f"median relative margin {m:.2f}"]
        parts.append({"recall": "spend on RECALL -- a missing fact flips this "
                                "task and a mis-scaled one usually does too",
                      "precision": "spend on PRECISION -- only a multiplicative "
                                   "error moves this answer; missing a term "
                                   "will not",
                      "both": "recall and precision are comparable here; "
                              "neither dominates"}[self.dominant_channel])
        parts.append("a cheap sufficient gate should fire" if self.routable
                     else "a cheap gate will not fire; do not build a router")
        return "; ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {"n": self.n, "unbounded": self.unbounded,
                "median_margin": self.median_margin,
                "dominant_channel": self.dominant_channel,
                "routable": self.routable}


def relative_margin(world: Any, decide: Callable[[Any], bool],
                    scale: Callable[[Any, float], Any], *,
                    lo: float = 0.05, hi: float = 20.0,
                    steps: int = 24) -> float:
    """The smallest ``|factor − 1|`` that flips ``decide``, or ``inf``.

    Searches both directions, because a decision can be near its boundary from
    below, from above, or from neither, and taking the nearer of the two is the
    only reading that corresponds to "how much error can this tolerate".
    """
    base = decide(world)
    best = float("inf")
    for direction in (1.0, -1.0):
        far = hi if direction > 0 else lo
        if decide(scale(world, far)) == base:
            continue                    # this direction never flips
        near, far_f = 1.0, far
        for _ in range(steps):
            mid = (near + far_f) / 2
            if decide(scale(world, mid)) == base:
                near = mid
            else:
                far_f = mid
        best = min(best, abs(far_f - 1.0))
    return best


def margin_profile(worlds: Iterable[Any], decide: Callable[[Any], bool],
                   scale: Callable[[Any, float], Any], **kw: Any
                   ) -> MarginProfile:
    """:func:`relative_margin` over a corpus."""
    margins: list[float] = []
    for w in worlds:
        margins.append(relative_margin(w, decide, scale, **kw))
    return MarginProfile(margins=tuple(margins), n=len(margins),
                         unbounded=sum(1 for m in margins
                                       if m == float("inf")))
