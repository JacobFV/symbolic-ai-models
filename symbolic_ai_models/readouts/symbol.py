"""The two readouts that already existed, written down as readouts.

Neither is new and that is the point of them. ``symbol`` is the vocabulary head
every model in the repo has always been scored on; ``node`` is the pointer head
two of them emit. Both are re-expressed here against
:class:`symbolic_ai_core.readout.Readout` so that the third one — ``site`` — is
a *third* member of a family rather than a special case bolted onto a harness
that assumed there was one.

They are required to reproduce their predecessors **bit for bit**, and
``tests/test_readouts.py`` is what says so. That requirement is the whole
argument that this refactor is behaviour-preserving: every published number in
this repo carrying ``label_acc`` or ``copy_acc`` was produced by
:meth:`~symbolic_ai_models.tasks.masked_node.MaskedNode.compute`, and a readout
that computed something *nearly* the same would silently redefine all of them.
So the counts are added beside the task's own rather than replacing them —
register beside, never edit in place — and the test compares the two columns
rather than trusting that they agree.
"""

from __future__ import annotations

from typing import Any, Sequence

import torch

from symbolic_ai_core.data.batch import IGNORE
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from symbolic_ai_core.floors import Totals, ratio, score_block
from symbolic_ai_core.readout import (NODE, SYMBOL, HasChannels, Readout,
                                      register)

__all__ = ["SymbolReadout", "NodeReadout"]


@register("symbol-001", channel=SYMBOL, prefix="rsymbol",
          doc="The vocabulary head: name the hidden symbol out of 8,192.")
class SymbolReadout(Readout):
    """Argmax over the vocabulary — what every number in the repo has meant.

    Reported under ``rsymbol_*`` rather than ``label_*`` deliberately. Two
    columns computing the same quantity by two routes is worth the width while
    the seam is new: they must agree, and a table in which they visibly do is a
    stronger statement than a docstring claiming it.
    """

    def score(self, out: HasChannels, batch: Any) -> dict[str, float]:
        logits = out.channels.get(SYMBOL)
        if logits is None or batch.target_tokens is None:
            return {}
        with torch.no_grad():
            _, counts = score_block(logits.detach(), batch.target_tokens, "rsymbol")
        return counts if counts.get("rsymbol_n") else {}

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode], **kwargs: Any) -> dict[str, float]:
        """The masked-node task's own structural floor, not a second opinion.

        Reusing it rather than re-deriving it is not laziness: a floor is the
        one number in a table that nothing else is checked against, so two
        near-identical copies of it would drift and nothing would notice. This
        repo has already published a lift over a floor 0.065 too low.
        """
        from ..tasks.masked_node import MaskedNode
        task = MaskedNode(**{k: v for k, v in kwargs.items()
                             if k in ("mask_rate", "max_nodes", "seed")})
        got = task.floor(episodes, tok, train)
        return {"rsymbol_acc": got.get("label_acc", float("nan")),
                "rsymbol_bits": got.get("label_bits", float("nan")),
                "rsymbol_n": got.get("label_n", 0.0), "floor_by": "structural"}


@register("node-001", channel=NODE, prefix="rnode",
          doc="The pointer head: which visible node of this episode says it.")
class NodeReadout(Readout):
    """"The answer here is whatever that one says", scored by what was picked.

    Several nodes usually carry the same label, so index equality would mark a
    correct copy wrong whenever the reader chose a different valid source.
    Correctness is ``label_group[picked] == label_group[asked]`` — the rule
    ``_pointer_counts`` established and the reason
    :mod:`symbolic_ai_core.readout` states it once for both pointer channels.
    """

    def score(self, out: HasChannels, batch: Any) -> dict[str, float]:
        logits = out.channels.get(NODE)
        if logits is None or batch.label_group is None:
            return {}
        asked = batch.label_group != IGNORE
        masked = batch.target_types != IGNORE
        scored = asked & masked
        if not bool(scored.any()):
            return {}
        # A pointer may not choose a padded position, and must not choose
        # itself -- a node cannot be its own evidence when its label is what is
        # hidden.
        valid = batch.pad_mask.clone()
        eye = torch.eye(valid.shape[1], dtype=torch.bool, device=valid.device)
        allowed = valid[:, None, :] & ~eye[None]
        picked = logits.masked_fill(~allowed, float("-inf")).argmax(-1)
        picked_group = torch.gather(batch.label_group, 1, picked)
        correct = (picked_group == batch.label_group) & scored
        return {"rnode_n": float(scored.sum()),
                "rnode_correct": float(correct.sum())}

    def summarize(self, totals: Totals) -> dict[str, float]:
        if not totals.get("rnode_n"):
            return {}
        out = ratio(totals, "rnode")
        out.pop("rnode_bits", None)     # no distribution is charged here
        return out

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode], **kwargs: Any) -> dict[str, float]:
        from ..tasks.masked_node import MaskedNode
        task = MaskedNode(**{k: v for k, v in kwargs.items()
                             if k in ("mask_rate", "max_nodes", "seed")})
        return {"rnode_acc": task._copy_floor(episodes, train, tok),
                "floor_by": "offset"}
