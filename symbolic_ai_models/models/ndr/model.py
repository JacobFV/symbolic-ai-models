"""Neural Data Router: one shared layer, applied until the structure resolves.

The systematic-generalisation line of work argues that the reason a transformer
fails to extrapolate to deeper structure than it was trained on is that depth of
*computation* is tied to depth of *network*: a six-layer model has six steps,
whatever the input needed. A universal transformer unties them by sharing one
layer across ``T`` steps, and the Neural Data Router adds the two pieces that
make those steps behave like evaluating a tree:

* a **copy gate**, so a position that has nothing to do this step passes its
  state through unchanged rather than being rewritten by an unwanted update —
  which is what lets a subtree sit still while a sibling is still being reduced;
* **geometric attention**, where a position attends to the *nearest* qualifying
  source rather than to a softmax mixture of all of them. The score for source
  ``j`` is its own match probability times the probability that nothing between
  ``i`` and ``j`` matched, which makes "my argument" resolve to one constituent
  instead of an average over several.

For the graph task, "between" is read along the term tree's linearisation, and
the relational bias supplies the edges. This is the architecture most likely to
beat the others on the recursion lessons and least likely to matter on the flat
ones, and separating those two outcomes is the point of running it.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from ...data.batch import SymbolicBatch
from ..base import (FeedForward, ModelConfig, RelationBias, SymbolicModel,
                   attention_bias)
from ..registry import register

__all__ = ["NDRModel"]


class GeometricAttention(nn.Module):
    """Attend to the closest matching source, not to a mixture of all of them."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.h = cfg.n_heads
        self.dk = cfg.d_model // cfg.n_heads
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model)
        self.out = nn.Linear(cfg.d_model, cfg.d_model)
        self.bias = RelationBias(cfg.n_heads)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        B, L, _ = x.shape
        q, k, v = self.qkv(x).view(B, L, 3, self.h, self.dk).permute(2, 0, 3, 1, 4)
        logits = q @ k.transpose(-1, -2) / self.dk ** 0.5
        logits = logits + attention_bias(batch, L, x.device, x.dtype)
        logits = logits + self.bias(batch, L, x.device).to(x.dtype)

        # p_ij: does j match i at all. Independent per pair, not a softmax.
        p = torch.sigmoid(logits)                                   # [B, H, L, L]
        w = self._nearest_first(p)
        return self.out((w @ v).transpose(1, 2).reshape(B, L, -1))

    @staticmethod
    def _nearest_first(p: torch.Tensor) -> torch.Tensor:
        """``w_ij = p_ij · Π_{k strictly between i and j} (1 - p_ik)``.

        Computed in log space and split into the two directions, because the
        product runs outward from the diagonal and a single cumulative pass
        would run it from the left edge instead. The result is not normalised —
        a position that matches nothing attends to nothing, which is the
        behaviour the copy gate is there to exploit.
        """
        eps = 1e-6
        log_miss = torch.log1p(-p.clamp(max=1 - eps))               # [B, H, L, L]
        L = p.shape[-1]
        idx = torch.arange(L, device=p.device)
        after = idx[None, :] > idx[:, None]

        # Rightward: cumulative miss from i+1 up to j-1.
        right = torch.cumsum(log_miss.masked_fill(~after, 0.0), dim=-1) - \
            log_miss.masked_fill(~after, 0.0)
        # Leftward: cumulative miss from i-1 back down to j+1.
        before = ~after & (idx[None, :] != idx[:, None])
        flipped = log_miss.masked_fill(~before, 0.0).flip(-1)
        left = (torch.cumsum(flipped, dim=-1) - flipped).flip(-1)
        return p * torch.exp(torch.where(after, right, left))


class NDRLayer(nn.Module):
    """One shared step: attend geometrically, then gate the update."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.n1 = nn.LayerNorm(cfg.d_model)
        self.attn = GeometricAttention(cfg)
        self.n2 = nn.LayerNorm(cfg.d_model)
        self.ff = FeedForward(cfg)
        # The copy gate is biased shut at initialisation, so an untrained model
        # passes state through and learns to write rather than learning to stop.
        self.gate = nn.Linear(2 * cfg.d_model, cfg.d_model)
        nn.init.constant_(self.gate.bias, -1.0)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch,
                step: torch.Tensor) -> torch.Tensor:
        h = self.n1(x + step)
        update = self.ff(self.n2(self.drop(self.attn(h, batch)) + x))
        g = torch.sigmoid(self.gate(torch.cat([x, update], dim=-1)))
        return g * update + (1 - g) * x


class _NDRStack(nn.Module):
    """``n_layers`` applications of one layer, with a step embedding.

    The step embedding is what keeps the shared layer from having to be
    step-invariant: it can behave differently on the first pass than on the
    fifth while still being one set of weights, which is the property that lets
    the number of steps be raised at evaluation time beyond what was trained.
    """

    def __init__(self, cfg: ModelConfig, n_steps: int) -> None:
        super().__init__()
        self.layer = NDRLayer(cfg)
        self.n_steps = n_steps
        self.step_emb = nn.Embedding(max(n_steps, 64), cfg.d_model)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        for t in range(self.n_steps):
            step = self.step_emb(torch.tensor(t, device=x.device))[None, None]
            x = self.layer(x, batch, step)
        return x


@register("ndr", doc="Neural Data Router: shared layer, copy gate, geometric attention.")
class NDRModel(SymbolicModel):
    """Depth of computation untied from depth of network.

    ``extra.n_steps`` sets how many times the shared layer runs; it defaults to
    ``n_layers`` so that the parameter budget is smaller than every other model
    here while the compute is the same.
    """

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return _NDRStack(cfg, int(cfg.get("n_steps", cfg.n_layers)))

    def set_steps(self, n_steps: int) -> None:
        """Change the number of steps after training — the extrapolation probe."""
        self.encoder.n_steps = n_steps
