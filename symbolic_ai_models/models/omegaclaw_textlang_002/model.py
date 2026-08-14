"""One rule set, selectively applied — conditioned on a language that can matter.

The model the whole exercise is for. Fourteen claws, eleven reading the graph
and three reading the prompt, and a context key that carries which language
rendered that prompt. Its control is ``omegaclaw_text-002``: identical reach,
identical everything, no language in the key.

Why this is the version that can win, when ``omegaclaw_lang-002`` cannot
------------------------------------------------------------------------
``Lesson.structured`` takes no language, so the term graph is byte-identical
across all seven packs and a graph-only rule has the same reliability in every
one of them *by construction*. ``omegaclaw_lang-002`` conditions on the language
anyway and can therefore only lose. The three surface claws are the exception:
they consult ``GraphView.text``, which is the one field the language moves.
Share of graph labels appearing verbatim in the prompt, 179 lessons x 2 seeds::

    symbols 0.978   english 0.808   english_synonym 0.808   swahili 0.693
    turkish 0.650   spanish 0.498   chinese 0.285

A rule that finds its answer by looking for a label in the prose is worth 0.98
of a rule in an s-expression notation and 0.29 of one in Chinese. That is a
genuine per-language reliability difference for ``weigh`` to learn, and it is the
only one this corpus contains.

What the per-language table is *also* for
-----------------------------------------
Beyond the score, this model's ``claw_evidence`` is the input to the falsifiable
prediction in ``notes/questions/2026-08-13-selective-rule-application-by-language.md``:
a rule reliable in every language is universal, one reliable in a subset is
family-specific, so clustering the languages by their per-rule reliability
vectors should recover real families. Read
``notes/findings/2026-08-13-language-conditioning-recovers-typology-not-genealogy.md``
before believing that framing — the order above is already not genealogical, and
Spanish, the one relative English has here, is second from the bottom.
"""

from __future__ import annotations

from typing import Hashable, Mapping

from ..omegaclaw import TEXT_CLAWS, Claim, Claw, OmegaClaw
from ..registry import register
from ..symbolic import GraphView

__all__ = ["OmegaClawTextLanguage"]


@register("omegaclaw_textlang-002",
          doc="OmegaClaw reaching into the prompt, with per-language reliability.")
class OmegaClawTextLanguage(OmegaClaw):
    """Fourteen claws, and reliability learned per language as well as per context."""

    def claws(self) -> Mapping[str, Claw]:
        return TEXT_CLAWS

    def perceive(self, view: GraphView, node: int) -> Hashable:
        return (view.language, *OmegaClaw.perceive(self, view, node))

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength * self.reliability(name, ctx)
