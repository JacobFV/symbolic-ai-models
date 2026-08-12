"""A claw the search found, rather than one somebody thought of.

The OmegaClaw family's headline contrast is that **control beats reach**:
``flat`` and ``ctx`` run the same eleven claws and differ only in whether they
learn which to trust, and that is worth +0.107 lift, while every attempt to
argue about the claw set has been an argument. The claw set itself has never
been tested, because nobody had a principled way to propose a twelfth.

``ilp`` turns out to be that way, and this model is what its output asked for.

Where the proposal came from
----------------------------
``ilp`` is the one model here whose hypothesis space is not a list somebody
wrote down: it grows clauses one literal at a time under FOIL's information
gain, so it can express conjunctions the fixed claw vocabulary cannot. Whether
it ever *uses* that freedom had never been checked, and its docstring's claim --
that "a different chain, two steps up and one across, costs nothing extra to
discover" -- was doing real work in this repo's story about first-order
induction.

Measured over 9,592 masked nodes on twelve lessons (every fifteenth id), with
``ilp`` fitted and every claw run on the same nodes:

===============================================  ======
clause firings                                   11,167
firings landing where no claw reaches             4,293
...and correct there                              3,537
nodes where ``ilp`` was right and no claw was       213
===============================================  ======

Both halves matter and they say different things. The freedom is real and
heavily used — 38% of firings land somewhere the eleven claws cannot reach, and
they are right there 82% of the time. But the *uniquely attributable* gain is
2.2% of nodes, because the claw set already arrives at the same answer by some
other route almost everywhere. First-order induction earns its keep here, and
it earns much less than "38% novel reach" would suggest.

What it found
-------------
The clause carrying most of it, at 1,885 correct out of 2,152 firings::

    answer(X,L) :- sibling(X,V1), type(V1)=pred, slot(V1)=3, label(V1,L).

"My sibling that is a ``pred`` sitting at slot 3." ``CLAWS`` has ``sibling0``
(the first sibling, whatever it is) and ``prev_sibling`` (the nearest earlier
one) and no way to say *which* sibling by what it is or where it sits. That is a
conjunction, and the claw vocabulary has no conjunctions.

So this model adds the smallest generalisation of what was found: siblings
selected by slot, and siblings selected by the type they carry. Not the specific
clause — hard-coding ``type=pred, slot=3`` would be fitting the twelve-lesson
slice it was measured on, and this repo has been burned three times by
conclusions drawn from small slices. The claw is the *shape* of the discovery;
which slot and which type pay off is left to ``weigh`` and the evidence table,
which is what they are for.

**What would refute it.** If this lands on ``omegaclaw_ctx``'s number, the claw
set was already sufficient and 38% novel reach was 38% redundant reach — which
the 2.2% figure predicts, and which would make "control beats reach" a stronger
claim than it currently is rather than a weaker one. A null here is the more
likely outcome and it is worth as much as a win, because the family has never
had a reach experiment that was not a guess.

Everything else is ``omegaclaw_ctx-001``: same ``weigh``, same ``perceive``,
same ``commit``, same calibration. The one axis is what the model is allowed to
look at.
"""

from __future__ import annotations

from typing import Hashable, Mapping

from ..omegaclaw import CLAWS, Claim, Claw, OmegaClaw, Scan
from ..omegaclaw.base import _at
from ..registry import register

__all__ = ["OmegaClawReach", "REACHING_CLAWS"]

#: How far out the slot- and type-selected siblings look. Four covers the
#: arities the curriculum's terms actually use; beyond that the claws fire too
#: rarely for the evidence table to say anything about them.
MAX_SLOT = 4


def _sibling_at_slot(slot: int) -> Claw:
    """The sibling sitting at a named slot, whatever it is called."""
    def claw(scan: Scan, node: int) -> Claim | None:
        for j in scan.siblings(node):
            if scan.slot[j] == slot:
                # Weaker than `peer`, which requires a matching head, and
                # stronger than `sibling0`, which takes whatever comes first.
                return _at(scan, j, 0.5)
        return None
    return claw


def _sibling_of_type(type_name: str) -> Claw:
    """The first sibling carrying a named type.

    The half of the discovery that is genuinely new: every existing claw picks
    a neighbour by *position*, and this picks one by *kind*. ``ilp`` reached it
    by conjoining ``sibling(X,V1)`` with ``type(V1)=pred``, which no single claw
    can express.
    """
    def claw(scan: Scan, node: int) -> Claim | None:
        for j in scan.siblings(node):
            if scan.view.types[j] == type_name:
                return _at(scan, j, 0.5)
        return None
    return claw


#: The eleven, plus what the search proposed. Insertion order is the iteration
#: order and therefore part of the model; the originals come first so that a
#: winner-take-all tie still breaks exactly as it did before.
REACHING_CLAWS: Mapping[str, Claw] = {
    **CLAWS,
    **{f"sibling_slot{k}": _sibling_at_slot(k) for k in range(MAX_SLOT)},
    **{f"sibling_{t}": _sibling_of_type(t)
       for t in ("pred", "ident", "field", "token")},
}


@register("omegaclaw_reach-001",
          doc="omegaclaw_ctx with the claws ilp's search says are missing.")
class OmegaClawReach(OmegaClaw):
    """``omegaclaw_ctx-001`` with a wider reach and identical control."""

    def claws(self) -> Mapping[str, Claw]:
        return REACHING_CLAWS

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        # Identical to `omegaclaw_ctx`, so the only difference between the two
        # rows is what the model was allowed to look at.
        return claim.strength * self.reliability(name, ctx)
