"""What every architecture in this repo shares, so that only the interesting
part differs.

A model here is an **encoder** and nothing else. The embedding tables, the
output heads, the parameter budget and the two losses are defined once, in this
file, and every architecture inherits them. That is deliberate and it is the
whole methodology: if the relational transformer beats the plain one, the
difference has to be attributable to how it moves information between
positions, not to it having a bigger vocabulary projection or an extra
normalisation nobody noticed.

Subclasses implement exactly one method::

    def build_encoder(self, cfg: ModelConfig) -> nn.Module

returning a module whose ``forward(h, batch)`` maps ``[B, L, D]`` to
``[B, L, D]``. Everything else — how a batch becomes ``h``, how ``h`` becomes
logits — is settled here.

The output side is shared in a stronger sense than "same code": the symbol head
is *the same head* for both tasks, tied to the input embedding. Predicting the
next word of the prose and naming a masked predicate in the term graph are one
classification over one vocabulary, which is what makes it meaningful to ask
whether training on one helps the other.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

from ..data.batch import N_RELATIONS, SymbolicBatch
from ..data.graph import NODE_TYPES

__all__ = ["ModelConfig", "SymbolicModel", "ModelOutput", "Attention",
           "RelationBias", "attention_bias", "N_TYPES"]

N_TYPES = len(NODE_TYPES)

#: Relative-position buckets used when a batch has no explicit relations, i.e.
#: for running text. Distances are bucketed logarithmically outward from zero so
#: that "the previous token" and "eighty tokens ago" are not the same feature.
N_BUCKETS = 32


@dataclass
class ModelConfig:
    """Everything an architecture is allowed to vary, plus a free-form ``extra``
    for the knobs that only one of them has."""

    vocab_size: int
    d_model: int = 256
    n_layers: int = 6
    n_heads: int = 8
    d_ff: int = 1024
    dropout: float = 0.1
    max_len: int = 1024
    max_depth: int = 64
    tie_embeddings: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any) -> Any:
        return self.extra.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {"vocab_size": self.vocab_size, "d_model": self.d_model,
                "n_layers": self.n_layers, "n_heads": self.n_heads,
                "d_ff": self.d_ff, "dropout": self.dropout,
                "max_len": self.max_len, "max_depth": self.max_depth,
                "tie_embeddings": self.tie_embeddings, "extra": dict(self.extra)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ModelConfig":
        return cls(**d)


@dataclass
class ModelOutput:
    """Logits for both questions. ``hidden`` is kept for probing."""

    symbol_logits: torch.Tensor          # [B, L, V]
    type_logits: torch.Tensor            # [B, L, N_TYPES]
    hidden: torch.Tensor                 # [B, L, D]


# ---------------------------------------------------------------------------
# shared attention machinery
# ---------------------------------------------------------------------------
def _relative_buckets(length: int, device: torch.device) -> torch.Tensor:
    """``[L, L]`` bucket ids for ``j - i``, log-spaced away from the diagonal."""
    pos = torch.arange(length, device=device)
    rel = pos[None, :] - pos[:, None]
    sign = torch.sign(rel)
    mag = rel.abs().float()
    half = N_BUCKETS // 2
    small = mag < half
    large = half + (torch.log(mag.clamp(min=half) / half)
                    / math.log(max(length, half + 1) / half) * (N_BUCKETS - half))
    bucket = torch.where(small, mag, large.clamp(max=N_BUCKETS - 1)).long()
    return (bucket * sign.long() + N_BUCKETS)     # 0 .. 2*N_BUCKETS


class RelationBias(nn.Module):
    """A per-head additive bias saying how two positions are related.

    Two tables, because a batch carries one of two very different notions of
    "related": an explicit term-graph relation, or a relative position in a
    string. Both land on the same interface, which is what lets one attention
    implementation serve the graph task and the text task.
    """

    def __init__(self, n_heads: int, *, use_graph: bool = True) -> None:
        super().__init__()
        self.n_heads = n_heads
        self.use_graph = use_graph
        self.graph = nn.Embedding(N_RELATIONS, n_heads) if use_graph else None
        self.sequence = nn.Embedding(2 * N_BUCKETS + 1, n_heads)
        nn.init.zeros_(self.sequence.weight)
        if self.graph is not None:
            nn.init.zeros_(self.graph.weight)

    def forward(self, batch: SymbolicBatch, length: int,
                device: torch.device) -> torch.Tensor:
        if batch.rel is not None and self.graph is not None:
            # [B, L, L, H] -> [B, H, L, L]
            return self.graph(batch.rel.long()).permute(0, 3, 1, 2)
        buckets = _relative_buckets(length, device)
        return self.sequence(buckets).permute(2, 0, 1).unsqueeze(0)


def attention_bias(batch: SymbolicBatch, length: int,
                   device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    """The additive ``-inf`` mask: padding always, plus the future if causal."""
    neg = torch.finfo(dtype).min
    mask = torch.zeros((batch.batch_size, 1, 1, length), device=device, dtype=dtype)
    mask = mask.masked_fill(~batch.pad_mask[:, None, None, :], neg)
    if batch.causal:
        future = torch.ones((length, length), device=device, dtype=torch.bool).triu(1)
        mask = mask + torch.zeros((length, length), device=device, dtype=dtype
                                  ).masked_fill(future, neg)
    return mask


class Attention(nn.Module):
    """Multi-head attention with an additive relational bias.

    ``use_relations`` is the switch the whole comparison turns on. With it off,
    a graph is just its pre-order linearisation and the module can only tell
    that one node came before another — the honest sequence-model baseline. With
    it on, the module is told which positions are parent, child, sibling or
    coreferent. Both settings see the same relative-position information on
    running text, so the switch changes the graph task and leaves text alone.
    """

    def __init__(self, cfg: ModelConfig, *, use_relations: bool = True) -> None:
        super().__init__()
        if cfg.d_model % cfg.n_heads:
            raise ValueError(f"d_model {cfg.d_model} not divisible by n_heads {cfg.n_heads}")
        self.h = cfg.n_heads
        self.dk = cfg.d_model // cfg.n_heads
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model)
        self.out = nn.Linear(cfg.d_model, cfg.d_model)
        self.drop = cfg.dropout
        self.bias = RelationBias(cfg.n_heads, use_graph=use_relations)

    def forward(self, x: torch.Tensor, batch: SymbolicBatch,
                extra_bias: torch.Tensor | None = None) -> torch.Tensor:
        B, L, _ = x.shape
        q, k, v = self.qkv(x).view(B, L, 3, self.h, self.dk).permute(2, 0, 3, 1, 4)
        bias = attention_bias(batch, L, x.device, x.dtype)
        bias = bias + self.bias(batch, L, x.device).to(x.dtype)
        if extra_bias is not None:
            bias = bias + extra_bias
        y = F.scaled_dot_product_attention(
            q, k, v, attn_mask=bias, dropout_p=self.drop if self.training else 0.0)
        return self.out(y.transpose(1, 2).reshape(B, L, -1))


class FeedForward(nn.Sequential):
    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(nn.Linear(cfg.d_model, cfg.d_ff), nn.GELU(),
                         nn.Dropout(cfg.dropout), nn.Linear(cfg.d_ff, cfg.d_model))


# ---------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------
class SymbolicModel(nn.Module):
    """Base class: embeddings in, two heads out, one encoder in between."""

    #: registry name, set by ``@register``
    name: str = ""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.symbol_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.type_emb = nn.Embedding(N_TYPES, cfg.d_model)
        self.depth_emb = nn.Embedding(cfg.max_depth, cfg.d_model)
        self.pos_emb = nn.Embedding(cfg.max_len, cfg.d_model)
        self.emb_norm = nn.LayerNorm(cfg.d_model)
        self.emb_drop = nn.Dropout(cfg.dropout)

        self.encoder = self.build_encoder(cfg)

        self.out_norm = nn.LayerNorm(cfg.d_model)
        self.symbol_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        self.type_head = nn.Linear(cfg.d_model, N_TYPES)
        if cfg.tie_embeddings:
            self.symbol_head.weight = self.symbol_emb.weight
        self.apply(self._init)

    # ---- to be provided by an architecture ---------------------------
    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        raise NotImplementedError

    @staticmethod
    def _init(m: nn.Module) -> None:
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    # ---- shared forward ----------------------------------------------
    def embed(self, batch: SymbolicBatch) -> torch.Tensor:
        """Symbol, type, depth and position, summed.

        Every position of every task gets the same four features. Text carries a
        constant type and zero depth, which costs a model nothing and means the
        two tasks cannot be told apart by the *shape* of their input.
        """
        L = batch.length
        pos = torch.arange(L, device=batch.tokens.device).clamp(max=self.cfg.max_len - 1)
        h = (self.symbol_emb(batch.tokens)
             + self.type_emb(batch.types)
             + self.depth_emb(batch.depth.clamp(max=self.cfg.max_depth - 1))
             + self.pos_emb(pos)[None])
        return self.emb_drop(self.emb_norm(h))

    def forward(self, batch: SymbolicBatch) -> ModelOutput:
        h = self.encoder(self.embed(batch), batch)
        h = self.out_norm(h)
        return ModelOutput(symbol_logits=self.symbol_head(h),
                           type_logits=self.type_head(h), hidden=h)

    # ---- bookkeeping --------------------------------------------------
    def n_parameters(self, trainable_only: bool = True) -> int:
        ps = self.parameters()
        return sum(p.numel() for p in ps if p.requires_grad or not trainable_only)
