"""A recurrent control, so the comparison has a floor as well as a ceiling.

Every other architecture here can attend anywhere in constant depth. This one
cannot: it carries a fixed-width state along the linearisation, forwards when
the task is causal and in both directions when it is not. It is in the repo for
the same reason ``langcurriculum`` reports a floor next to every accuracy — a
number is not interpretable without knowing what the cheap thing gets. If a
structure-aware model does not beat a GRU reading the pre-order traversal, the
structure was not what did the work.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from ...data.batch import SymbolicBatch
from ..base import ModelConfig, SymbolicModel
from ..registry import register

__all__ = ["RecurrentModel"]


class _GRUStack(nn.Module):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.d = cfg.d_model
        # One cell, not one per task. A separate bidirectional module would mean
        # the text task and the graph task trained disjoint sets of recurrent
        # weights, and the premise of this repo is that both tasks drive *the
        # same* encoder. The backward pass therefore reuses these weights on a
        # reversed sequence rather than owning its own.
        self.gru = nn.GRU(cfg.d_model, cfg.d_model, num_layers=cfg.n_layers,
                          batch_first=True,
                          dropout=cfg.dropout if cfg.n_layers > 1 else 0.0)
        self.norm = nn.LayerNorm(cfg.d_model)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        keep = batch.pad_mask.unsqueeze(-1).to(x.dtype)
        x = x * keep
        lengths = batch.pad_mask.sum(1)
        out = self._run(x, lengths)
        if not batch.causal:
            # A non-causal task may look both ways; the same cell runs over the
            # reversed sequence. Reversal is per sequence rather than a whole
            # tensor flip, because a flipped batch starts the backward pass
            # inside the padding and a short episode would then be scored
            # differently depending on how long its batch-mates were.
            rev = self._reverse(x, lengths)
            out = out + self._reverse(self._run(rev, lengths), lengths)
        return self.norm(out + x) * keep

    def _run(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """Run the cell over real positions only."""
        packed = nn.utils.rnn.pack_padded_sequence(
            x, lengths.clamp(min=1).cpu(), batch_first=True, enforce_sorted=False)
        out, _ = self.gru(packed)
        out, _ = nn.utils.rnn.pad_packed_sequence(
            out, batch_first=True, total_length=x.shape[1])
        return out

    @staticmethod
    def _reverse(x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """Reverse each sequence within its own length, leaving padding put."""
        pos = torch.arange(x.shape[1], device=x.device)[None, :]
        real = pos < lengths[:, None]
        idx = torch.where(real, (lengths[:, None] - 1 - pos).clamp(min=0), pos)
        return x.gather(1, idx.unsqueeze(-1).expand_as(x))


@register("gru-001", doc="Recurrent control: a GRU over the linearisation, causal or bidirectional.")
class RecurrentModel(SymbolicModel):
    """The floor. No attention, no edges, fixed-width state."""

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        if cfg.d_model % 2:
            raise ValueError("d_model must be even for the bidirectional pass")
        return _GRUStack(cfg)
