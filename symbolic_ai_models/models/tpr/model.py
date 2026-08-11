"""Tensor Product Representations: a state that is explicitly role ⊗ filler.

Smolensky's proposal is that a connectionist system can carry symbolic structure
if it represents a bound pair as an outer product, so that a structure is a sum
of such products and a constituent is recovered by unbinding with its role. The
appeal for this repo is that the claim is *checkable*: unbinding is a real
operation with a real readout, not a metaphor about what attention might be
doing.

Every position carries ``R`` roles, each holding an ``F``-dimensional filler, so
the hidden state ``[B, L, D]`` with ``D = R * F`` is read as ``[B, L, R, F]`` —
the tensor product, laid out. Three operations act on it:

* **bind** — a position writes a filler into each role, gated by how strongly it
  occupies that role;
* **transport** — a message crossing an edge has its roles remapped by a learned
  ``R x R`` matrix *belonging to that edge type*, so the thing that was a
  predicate's first argument arrives at the predicate as something else. This is
  the operation a plain transformer has no vocabulary for, and it is why
  ``f(a, b)`` and ``f(b, a)`` are not the same state here even though the two
  have identical neighbour sets;
* **unbind** — the readout queries a role and gets its filler back.

Transport is applied by summing over edge types rather than by looking a matrix
up per pair: ``Σ_j w_ij · T[rel_ij] · s_j`` equals ``Σ_t T[t] · (Σ_j w_ij ·
1[rel_ij = t] · s_j)``, and the right-hand form is a fixed number of matrix
products instead of one per pair. It costs roughly ``N_RELATIONS`` times a
transformer's aggregation, which is the price of the role algebra and is stated
here so nobody has to discover it from a training curve.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from ...data.batch import N_RELATIONS, SymbolicBatch
from ..base import (Attention, FeedForward, ModelConfig, SymbolicModel,
                   attention_bias)
from ..registry import register

__all__ = ["TPRModel"]


class TPRLayer(nn.Module):
    """One round of bind, transport, unbind."""

    def __init__(self, cfg: ModelConfig, n_roles: int) -> None:
        super().__init__()
        if cfg.d_model % n_roles:
            raise ValueError(f"d_model {cfg.d_model} not divisible by n_roles {n_roles}")
        self.R = n_roles
        self.Fd = cfg.d_model // n_roles

        self.norm = nn.LayerNorm(cfg.d_model)
        self.attn = Attention(cfg, use_relations=True)

        self.role_logits = nn.Linear(cfg.d_model, n_roles)   # role occupancy
        self.filler = nn.Linear(cfg.d_model, cfg.d_model)    # what to bind
        self.query = nn.Linear(cfg.d_model, n_roles)         # which role to unbind
        self.unbound_up = nn.Linear(self.Fd, cfg.d_model)
        self.out = nn.Linear(cfg.d_model, cfg.d_model)

        # One role-remapping matrix per edge type, plus a shared one at index 0
        # used when there are no explicit edges (running text). Identity at
        # initialisation, so an untrained layer transports roles unchanged.
        self.transport = nn.Parameter(
            torch.eye(n_roles).expand(N_RELATIONS, n_roles, n_roles).clone())

        self.norm2 = nn.LayerNorm(cfg.d_model)
        self.ff = FeedForward(cfg)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        B, L, D = x.shape
        h = self.norm(x)

        # ---- bind ------------------------------------------------------
        occupancy = torch.softmax(self.role_logits(h), dim=-1)          # [B, L, R]
        filler = self.filler(h).view(B, L, self.R, self.Fd)
        bound = occupancy.unsqueeze(-1) * filler                        # [B, L, R, F]

        # ---- transport -------------------------------------------------
        w = self._weights(h, batch)                                     # [B, L, L]
        moved = self._transport(bound, w, batch)                        # [B, L, R, F]

        # ---- unbind ----------------------------------------------------
        q = torch.softmax(self.query(h), dim=-1)                        # [B, L, R]
        unbound = torch.einsum("blr,blrf->blf", q, moved)               # [B, L, F]
        y = self.out(moved.reshape(B, L, D)) + self.unbound_up(unbound)

        x = x + self.drop(y) + self.drop(self.attn(h, batch))
        return x + self.drop(self.ff(self.norm2(x)))

    def _weights(self, h: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        """Which constituents this position gathers.

        One shared map over the whole ``[R, F]`` state rather than one per role,
        because a role is a slot in a structure, not a head: relevance is a
        property of the position, and which role each gathered thing lands in is
        what ``transport`` decides.
        """
        scores = torch.einsum("bld,bmd->blm", h, h) / (h.shape[-1] ** 0.5)
        scores = scores + attention_bias(batch, h.shape[1], h.device, h.dtype).squeeze(1)
        return torch.softmax(scores, dim=-1)

    def _transport(self, bound: torch.Tensor, w: torch.Tensor,
                   batch: SymbolicBatch) -> torch.Tensor:
        B, L, R, Fd = bound.shape
        flat = bound.reshape(B, L, R * Fd)
        T = self.transport.to(bound.dtype)
        if batch.rel is None:
            gathered = torch.bmm(w, flat).view(B, L, R, Fd)
            return torch.einsum("rs,blsf->blrf", T[0], gathered)
        rel = batch.rel.long()
        out = bound.new_zeros(B, L, R, Fd)
        for t in range(1, N_RELATIONS):                  # 0 is "no relation"
            masked = w * (rel == t).to(w.dtype)
            gathered = torch.bmm(masked, flat).view(B, L, R, Fd)
            out = out + torch.einsum("rs,blsf->blrf", T[t], gathered)
        return out


class _TPRStack(nn.Module):
    def __init__(self, cfg: ModelConfig, n_roles: int) -> None:
        super().__init__()
        self.layers = nn.ModuleList(TPRLayer(cfg, n_roles) for _ in range(cfg.n_layers))

    def forward(self, x: torch.Tensor, batch: SymbolicBatch) -> torch.Tensor:
        for layer in self.layers:
            x = layer(x, batch)
        return x


@register("tpr-001", doc="Tensor Product Representations: role-filler binding with a per-edge role algebra.")
class TPRModel(SymbolicModel):
    """Role-filler binding, with a learned role algebra on the edges.

    ``extra.n_roles`` sets how many roles a position carries; it must divide
    ``d_model``, since the hidden state *is* the ``role x filler`` matrix.
    """

    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return _TPRStack(cfg, int(cfg.get("n_roles", 8)))
