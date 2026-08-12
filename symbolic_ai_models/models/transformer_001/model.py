"""A plain pre-LN transformer: the control the rest of the repo is read against.

On the text task it is exactly what you would expect. On the graph task it reads
the term tree as its pre-order linearisation and is left to infer from position
and depth what the edges were — no edge ever reaches it. Its sibling
:mod:`symbolic_ai_models.models.rgt_001` is the same network with the edges handed over, and
nothing else differs between them, so the gap is the value of being told the
structure rather than having to infer it.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from ...data.batch import SymbolicBatch
from ..base import Attention, FeedForward, ModelConfig, NeuralModel
from ..registry import register

__all__ = ["TransformerModel", "Block", "Stack"]


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


@register("transformer-001", doc="Plain pre-LN transformer; reads a graph as its linearisation.")
class TransformerModel(NeuralModel):
    """The control. No edge ever reaches it."""

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return Stack(cfg, use_relations=False)
