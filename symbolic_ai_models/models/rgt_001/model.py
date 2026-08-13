"""The same transformer, told which positions are parent, child and sibling.

The contrast with :mod:`symbolic_ai_models.models.transformer_001` is the cleanest one in the
repo: same depth, same width, same heads, same initialisation, same data in the
same order. The only difference is that the edges of the term graph are visible
here and invisible there, so whatever separates the two numbers is the value of
knowing the structure rather than inferring it from a linearisation.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from symbolic_ai_core.data.batch import N_RELATIONS, SymbolicBatch
from ..base import ModelConfig, NeuralModel
from ..registry import register
from ..transformer_001.model import Block

__all__ = ["RelationalTransformer"]


class RelationalBlock(Block):
    """Attention biased by relation, and values shifted by relation.

    The additive bias alone lets a node decide *whether* to look at its parent.
    It does not let the parent's contribution arrive marked as coming from a
    parent, which is the part that matters for a term tree: ``f(a, b)`` and
    ``f(b, a)`` have identical neighbour sets and differ only in which edge each
    argument arrived on. The value shift below adds a learned per-relation
    vector to what each position contributes, so slot identity survives the
    aggregation.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg, use_relations=True)
        self.rel_value = nn.Embedding(N_RELATIONS, cfg.d_model)
        nn.init.zeros_(self.rel_value.weight)
        self.gate = nn.Linear(cfg.d_model, cfg.d_model)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        h = self.n1(x)
        x = x + self.drop(self.attn(h, batch) + self._relational(h, batch))
        return x + self.drop(self.ff(self.n2(x)))

    def _relational(self, h: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        """Mean of ``value(j) + rel_vector(i, j)`` over the edges into ``i``.

        Restricted to the explicit relations, and skipped entirely on text,
        where ``batch.rel`` is ``None`` and the chain is already what
        relative-position attention encodes.

        The edge term is accumulated by counting relations per node and
        multiplying once by the embedding table, rather than by looking the
        table up at every pair. The two are equal — a sum of embeddings is the
        embedding matrix applied to the counts — but the lookup would build a
        ``[B, L, L, d_model]`` tensor, which at any useful batch size is several
        hundred megabytes for one term in one layer.
        """
        if batch.rel is None:
            return torch.zeros_like(h)
        rel = batch.rel.long()                              # [B, L, L]
        counts = torch.zeros(rel.shape[0], rel.shape[1], N_RELATIONS,
                             device=h.device, dtype=h.dtype)
        counts.scatter_add_(2, rel, torch.ones_like(rel, dtype=h.dtype))
        counts[:, :, 0] = 0                                 # "none" is not an edge
        deg = counts.sum(-1, keepdim=True).clamp(min=1.0)
        msg = torch.bmm((rel > 0).to(h.dtype), h) / deg      # neighbour mean
        edge = (counts @ self.rel_value.weight.to(h.dtype)) / deg
        return torch.tanh(self.gate(msg + edge))


class RelationalStack(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.blocks = nn.ModuleList(RelationalBlock(cfg) for _ in range(cfg.n_layers))

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        for b in self.blocks:
            x = b(x, batch)
        return x


@register("rgt-001", doc="Relational graph transformer: attention biased and values marked by edge type.")
class RelationalTransformer(NeuralModel):
    """The same transformer, told which positions are parent, child and sibling."""

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return RelationalStack(cfg)
