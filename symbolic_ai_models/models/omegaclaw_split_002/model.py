"""A seven-way split of the evidence that is not the language. The hard control.

Added *after* the first rows landed and because of what they said.
``omegaclaw_lang-002`` was registered expecting it to lose: the term graph is
byte-identical across all seven packs, the eleven claws read only the graph, so
splitting the evidence table by language is data-thinning with nothing bought.
It did not lose. It came in **above** ``omegaclaw_ctx-001``.

There are two explanations and they are not remotely the same claim:

1. the language is informative after all, or
2. **a seven-way split of the evidence is worth something whatever it splits
   on** — thinner cells shrink harder towards each claw's global rate, and on
   this table more shrinkage is better.

``omegaclaw_const-002`` cannot separate them. It puts a *constant* where the
language goes, which is a bijection on context keys and therefore changes
nothing at all; it proves the plumbing is free and says nothing about
partitioning. What (2) needs is a partition of the same *shape* — seven
episode-level buckets over the same corpus — carrying no information.

That is this model. The bucket is ``crc32`` of the prompt, modulo seven: stable
across processes and across runs, computed per episode, and uncorrelated with
anything the claws can see. It is also uncorrelated with the language, which is
the point — the corpus renders every seed in all seven packs, so both this
partition and the language partition put roughly one copy of every graph in
every bucket, and they differ only in whether the bucket *means* anything.

Read it as: ``lang - ctx`` is what a language-shaped split is worth, ``split -
ctx`` is what a same-shaped split with no language in it is worth, and the
difference between those two is the only part that can honestly be called the
value of knowing the language.

``crc32`` and not ``hash``: Python's string hash is salted per process, so a
model keyed on it would fit one partition and evaluate on another.
"""

from __future__ import annotations

import zlib
from typing import Hashable

from ..omegaclaw import Claim, OmegaClaw
from ..registry import register
from ..symbolic import GraphView

__all__ = ["OmegaClawSplit", "OmegaClawSplitPure"]


@register("omegaclaw_split-002",
          doc="Control: a seven-way split of the evidence that is not the language.")
class OmegaClawSplit(OmegaClaw):
    """``omegaclaw_lang-002``'s partition, with the meaning taken out."""

    #: Seven because the corpus has seven packs. The comparison is only fair if
    #: the two partitions are the same size, not merely both "arbitrary".
    BUCKETS = 7

    def perceive(self, view: GraphView, node: int) -> Hashable:
        bucket = zlib.crc32(view.text.encode("utf-8")) % self.BUCKETS
        return (f"bucket{bucket}", *OmegaClaw.perceive(self, view, node))

    def weigh(self, name: str, ctx: Hashable, claim: Claim) -> float:
        return claim.strength * self.reliability(name, ctx)


@register("omegaclaw_split_pure-002",
          doc="omegaclaw_split-002 without the shared memorising fallback.")
class OmegaClawSplitPure(OmegaClawSplit):
    """The same control, read without a shared floor underneath it."""

    structural_fallback = False
