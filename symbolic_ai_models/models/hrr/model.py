"""Holographic Reduced Representations: binding by circular convolution.

The other classical answer to "how does a vector carry a structure". Where a
tensor product grows the representation (``R`` roles times ``F`` features), an
HRR keeps it the same size: binding is circular convolution, which maps
``D x D -> D``, and structures superpose by addition. The price is that
unbinding is approximate — correlation returns the filler plus noise from
everything else in the superposition — which is why a real VSA has a **cleanup
memory** that snaps a noisy vector back to the nearest thing it knows.

Both halves are here:

* ``bind`` is ``ifft(fft(role) * fft(filler))``, and ``unbind`` is the same with
  the role's conjugate — genuine circular convolution and correlation, not a
  learned stand-in;
* ``cleanup`` is attention over a learned codebook of exemplar vectors, which is
  the differentiable form of "snap to the nearest known symbol".

Roles come from the edge type, so a child's contribution to its parent is bound
with the vector for ``child_2`` and arrives distinguishable from the one bound
with ``child_0``. On running text, where no explicit relations exist, roles come
from bucketed relative position instead, which is the same idea applied to the
one relation a string has.

This is the most constrained architecture in the repo: superposition is a sum,
so capacity is genuinely limited, and it will lose on tasks that need to hold
many bindings at once. That is a finding, not a bug — it is the property the
comparison exists to measure.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from ...data.batch import N_RELATIONS, SymbolicBatch
from ..base import FeedForward, ModelConfig, SymbolicModel, attention_bias
from ..registry import register

__all__ = ["HRRModel", "bind", "unbind"]


def bind(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Circular convolution ``a ⊛ b`` along the last dimension."""
    return torch.fft.irfft(torch.fft.rfft(a.float(), dim=-1)
                           * torch.fft.rfft(b.float(), dim=-1),
                           n=a.shape[-1], dim=-1).to(a.dtype)


def unbind(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Circular correlation: the approximate inverse of :func:`bind` by ``a``."""
    return torch.fft.irfft(torch.fft.rfft(a.float(), dim=-1).conj()
                           * torch.fft.rfft(b.float(), dim=-1),
                           n=a.shape[-1], dim=-1).to(a.dtype)


class CleanupMemory(nn.Module):
    """Snap a noisy vector to a mixture of learned exemplars.

    Attention over a codebook, which is what a cleanup memory is once it has to
    be differentiable: the query is the noisy unbound vector, the keys and
    values are the exemplars, and a confident match returns the exemplar nearly
    unchanged while an unrecognisable query returns a blend. The residual keeps
    the original signal available, so cleanup can never destroy information the
    codebook has no entry for.
    """

    def __init__(self, d_model: int, n_slots: int, temperature: float = 1.0) -> None:
        super().__init__()
        self.codebook = nn.Parameter(torch.randn(n_slots, d_model) / d_model ** 0.5)
        self.temperature = temperature
        self.gate = nn.Linear(d_model, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        code = torch.nn.functional.normalize(self.codebook, dim=-1).to(x.dtype)
        sim = torch.nn.functional.normalize(x, dim=-1) @ code.T / self.temperature
        cleaned = torch.softmax(sim, dim=-1) @ code
        g = torch.sigmoid(self.gate(x))
        return g * cleaned + (1 - g) * x


class HRRLayer(nn.Module):
    """Bind by edge type, superpose, clean up, unbind."""

    def __init__(self, cfg: ModelConfig, n_slots: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(cfg.d_model)
        self.value = nn.Linear(cfg.d_model, cfg.d_model)
        self.score = nn.Linear(cfg.d_model, cfg.d_model)

        # One role vector per edge type. Unit-ish Gaussian entries are what make
        # circular convolution approximately invertible, so these are
        # initialised at the scale HRR theory asks for rather than at 0.02.
        self.roles = nn.Parameter(torch.randn(N_RELATIONS, cfg.d_model)
                                  / cfg.d_model ** 0.5)
        self.seq_roles = nn.Parameter(torch.randn(3, cfg.d_model) / cfg.d_model ** 0.5)

        self.cleanup = CleanupMemory(cfg.d_model, n_slots)
        self.query_role = nn.Linear(cfg.d_model, cfg.d_model)
        self.out = nn.Linear(cfg.d_model, cfg.d_model)
        self.norm2 = nn.LayerNorm(cfg.d_model)
        self.ff = FeedForward(cfg)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        h = self.norm(x)
        w = self._weights(h, batch)                              # [B, L, L]
        v = self.value(h)

        trace = self._superpose(v, w, batch)                     # [B, L, D]
        trace = self.cleanup(trace)
        recovered = unbind(self.query_role(h), trace)            # ask a role back
        y = self.out(recovered + trace)

        x = x + self.drop(y)
        return x + self.drop(self.ff(self.norm2(x)))

    def _weights(self, h: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        s = self.score(h)
        scores = torch.einsum("bld,bmd->blm", s, h) / (h.shape[-1] ** 0.5)
        scores = scores + attention_bias(batch, h.shape[1], h.device, h.dtype).squeeze(1)
        return torch.softmax(scores, dim=-1)

    def _superpose(self, v: torch.Tensor, w: torch.Tensor,
                   batch: SymbolicBatch) -> torch.Tensor:
        """``Σ_j w_ij · (role(rel_ij) ⊛ v_j)``, grouped by edge type.

        Binding distributes over the sum, so the whole superposition is a
        per-edge-type weighted sum followed by one convolution each, rather than
        a convolution per pair.
        """
        if batch.rel is None:
            # A string has three relations: before, self, after.
            idx = torch.arange(v.shape[1], device=v.device)
            group_id = (torch.sign(idx[None, :] - idx[:, None]).long() + 1)[None]
            roles, n_groups = self.seq_roles, 3
        else:
            group_id, roles, n_groups = batch.rel.long(), self.roles, N_RELATIONS

        total = torch.zeros_like(v)
        for t in range(n_groups):
            part = torch.bmm(w * (group_id == t).to(w.dtype), v)
            total = total + bind(roles[t].to(v.dtype).expand_as(part), part)
        return total


class _HRRStack(nn.Module):
    def __init__(self, cfg: ModelConfig, n_slots: int) -> None:
        super().__init__()
        self.layers = nn.ModuleList(HRRLayer(cfg, n_slots) for _ in range(cfg.n_layers))

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x, batch)
        return x


@register("hrr", doc="Vector-symbolic architecture: circular-convolution binding with a cleanup memory.")
class HRRModel(SymbolicModel):
    """HRR/VSA. ``extra.cleanup_slots`` sizes the cleanup codebook."""

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return _HRRStack(cfg, int(cfg.get("cleanup_slots", 512)))
