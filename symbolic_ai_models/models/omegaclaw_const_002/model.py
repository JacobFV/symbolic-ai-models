"""The control for ``omegaclaw_lang-002``: the extra dimension, carrying nothing.

``omegaclaw_lang-002`` widens the context key by one field. If it then scores
differently from ``omegaclaw_ctx-001``, two explanations are available and they
are not the same claim:

1. the language is informative, or
2. widening the key at all changed something — the finer partition, the
   iteration order, the shrinkage, the plumbing that carries the field.

This model rules out (2) by construction. It appends a **constant** where
``lang`` appends the language, so the extra dimension is present and carries no
information at all.

What it must do, and why that is worth a row
--------------------------------------------
Appending a constant to a tuple is a bijection on context keys: every cell maps
to exactly one new cell with the same counts, ``reliability`` returns the same
number, and every prediction is identical. So this row must land on
``omegaclaw_ctx-001``'s numbers **exactly**, and any difference at all is a bug
in the harness rather than a finding about language.

It is registered rather than left as a unit test because that check is cheapest
where the numbers are: two identical rows in one sweep table are self-evidently
a null, and a passing test in another file is not.
"""

from __future__ import annotations

from typing import Hashable

from ..omegaclaw import Claim, OmegaClaw
from ..registry import register
from ..symbolic import GraphView

__all__ = ["OmegaClawConstant"]


@register("omegaclaw_const-002",
          doc="Control for omegaclaw_lang: a constant where the language goes.")
class OmegaClawConstant(OmegaClaw):
    """The language-shaped hole in the context key, with nothing in it."""

    #: Deliberately not the empty string. An empty field is what an *unlabelled*
    #: episode would carry, and a control that is indistinguishable from a
    #: missing value is a control nobody can read.
    TOKEN = "<constant>"

    def perceive(self, view: GraphView, node: int) -> Hashable:
        return (self.TOKEN, *OmegaClaw.perceive(self, view, node))

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength * self.reliability(name, ctx)
