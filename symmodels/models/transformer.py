"""The two transformers: the one that is told the structure and the one that is not.

These are the poles of the comparison. ``transformer`` is an ordinary pre-LN
transformer: on the text task it is exactly what you would expect, and on the
graph task it reads the term tree as its pre-order linearisation and is left to
infer from position and depth what the edges were. ``rgt`` is the same network
with the edges handed to it.

Nothing else differs — same depth, same width, same heads, same initialisation —
so the gap between them is the value of knowing the structure rather than
inferring it, measured directly.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from ..data.batch import N_RELATIONS, SymbolicBatch
from .base import Attention, FeedForward, ModelConfig, SymbolicModel
from .registry import register

__all__ = ["TransformerModel", "RelationalTransformer"]


class Block(nn.Module):
    """Pre-LN block. ``use_relations`` is passed straight through to attention."""

    def __init__(self, cfg: ModelConfig, *, use_relations: bool) -> None:
        super().__init__()
        self.n1 = nn.LayerNorm(cfg.d_model)
        self.attn = Attention(cfg, use_relations=use_relations)
        self.n2 = nn.LayerNorm(cfg.d_model)
        self.ff = FeedForward(cfg)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        x = x + self.drop(self.attn(self.n1(x), batch))
        return x + self.drop(self.ff(self.n2(x)))


class Stack(nn.Module):
    def __init__(self, cfg: ModelConfig, *, use_relations: bool) -> None:
        super().__init__()
        self.blocks = nn.ModuleList(
            Block(cfg, use_relations=use_relations) for _ in range(cfg.n_layers))

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        for b in self.blocks:
            x = b(x, batch)
        return x


@register("transformer", doc="Plain pre-LN transformer; reads a graph as its linearisation.")
class TransformerModel(SymbolicModel):
    """The control. No edge ever reaches it."""

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return Stack(cfg, use_relations=False)


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


@register("rgt", doc="Relational graph transformer: attention biased and values marked by edge type.")
class RelationalTransformer(SymbolicModel):
    """The same transformer, told which positions are parent, child and sibling."""

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return RelationalStack(cfg)
