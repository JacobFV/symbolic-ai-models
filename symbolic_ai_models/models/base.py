"""What every architecture shares, so that only the interesting part differs.

Two families live in this repo and both answer to :class:`Model`: networks that
are trained by gradient descent, and rule-based systems that are *fitted* by
counting, parsing and searching. They meet at one interface — a
:class:`~symbolic_ai_core.data.batch.SymbolicBatch` in, a :class:`ModelOutput` of logits
out — which is what lets a decision list and a transformer appear in the same
table under the same floors. See :mod:`symbolic_ai_models.models.symbolic` for the other
half.

A **neural** model here is an encoder and nothing else. The embedding tables, the
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
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Mapping, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from symbolic_ai_core.data.batch import N_RELATIONS, SymbolicBatch
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import NODE_TYPES

if TYPE_CHECKING:                     # avoids a cycle: tasks imports ModelOutput
    from symbolic_ai_core.data.tokenizer import SymbolTokenizer

__all__ = ["ModelConfig", "Model", "NeuralModel", "SymbolicModel", "ModelOutput",
           "FitContext", "Attention", "FeedForward", "RelationBias",
           "attention_bias", "autocast", "N_TYPES"]


def autocast(device: torch.device, enabled: bool):
    """bfloat16 on CUDA, nothing on CPU. Shared so the loop and the evaluator
    cannot disagree about the precision a number was computed in."""
    if device.type == "cuda" and enabled:
        return torch.autocast("cuda", dtype=torch.bfloat16)
    return torch.autocast("cpu", enabled=False)


def _lr_at(step: int, ctx: "FitContext") -> float:
    """Linear warmup into a cosine decay, floored at ``min_lr_ratio``."""
    if step < ctx.warmup:
        return ctx.lr * (step + 1) / max(ctx.warmup, 1)
    progress = (step - ctx.warmup) / max(ctx.steps - ctx.warmup, 1)
    cosine = 0.5 * (1 + math.cos(math.pi * min(progress, 1.0)))
    return ctx.lr * (ctx.min_lr_ratio + (1 - ctx.min_lr_ratio) * cosine)

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
    #: TermGraph truncation, which is *not* `max_len`. Models were passing the text
    #: length as the node cap, so they fitted on graphs cut at 520 nodes and
    #: were evaluated on graphs cut at 128 — different data, and four times the
    #: work for the half of it that was thrown away.
    max_nodes: int = 256
    max_depth: int = 64
    tie_embeddings: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any) -> Any:
        return self.extra.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return {"vocab_size": self.vocab_size, "d_model": self.d_model,
                "n_layers": self.n_layers, "n_heads": self.n_heads,
                "d_ff": self.d_ff, "dropout": self.dropout,
                "max_len": self.max_len, "max_nodes": self.max_nodes,
                "max_depth": self.max_depth,
                "tie_embeddings": self.tie_embeddings, "extra": dict(self.extra)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ModelConfig":
        return cls(**d)


@dataclass
class ModelOutput:
    """Logits for every question a readout might ask. ``hidden`` is for probing.

    The three named fields are the ones every model has always had. Anything
    else a model wants to say goes in :attr:`channels`, which is what makes the
    readout a knob rather than a hard-coded set of heads — see
    :mod:`symbolic_ai_core.readout` for what a channel is and why
    ``source_logits`` became one instead of staying a special case.
    """

    symbol_logits: torch.Tensor          # [B, L, V]
    type_logits: torch.Tensor            # [B, L, N_TYPES]
    hidden: torch.Tensor                 # [B, L, D]
    #: [B, L, L] — optional. For each masked node, a score over the *nodes* of
    #: its own episode: "the answer is whatever that one says". A model without
    #: one leaves it None and is simply not scored on the copy head. Kept
    #: separate from `symbol_logits` rather than folded into it, because a
    #: pointer can name a symbol the vocabulary cannot, which is the whole
    #: reason for having one.
    #:
    #: Kept as a named field, and not quietly turned into ``channels["node"]``
    #: only: eight files construct and read it, and a published copy number is
    #: attached to it. It is *mirrored* into the channels below, so the two can
    #: never disagree.
    source_logits: torch.Tensor | None = None
    #: Every readout-visible output, by channel name. The generalisation of
    #: ``source_logits``: a pointer over nodes was always one channel among
    #: several, and writing the second one (``site``, a pointer over text
    #: positions) as another field would have been the moment this became a pile
    #: of heads instead of a seam.
    channels: dict[str, torch.Tensor] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # `setdefault`, so a model that filled a channel explicitly keeps what
        # it put there and the mirroring never silently overwrites it.
        self.channels.setdefault("symbol", self.symbol_logits)
        self.channels.setdefault("type", self.type_logits)
        if self.source_logits is not None:
            self.channels.setdefault("node", self.source_logits)
        elif "node" in self.channels:
            self.source_logits = self.channels["node"]

    def channel(self, name: str) -> torch.Tensor | None:
        """What this model said on ``name``, or ``None`` if it said nothing.

        ``None`` rather than zeros, and the distinction is the whole point: a
        readout must be able to tell "has no pointer" from "has a bad pointer",
        and a zero tensor says the second while meaning the first.
        """
        return self.channels.get(name)


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
@dataclass
class FitContext:
    """Everything a model might need in order to learn, and nothing about *how*.

    The trainer fills this in and hands it over. What happens next belongs to
    the model: :class:`NeuralModel` runs the gradient loop below, a rule-based
    model counts and induces, and anything else — evolutionary search, EM, a
    solver — implements ``fit`` its own way without the trainer needing to know.
    That is the point of the split, and it is why the optimiser lives here in
    ``models/`` rather than in ``train.py``.

    ``on_step`` and ``on_eval`` are the two hooks a learner may call if it has
    something to report. Neither is required: a model that fits in one pass
    calls neither and still produces the same artefacts.
    """

    episodes: Sequence[Episode]
    tok: "SymbolTokenizer"
    tasks: Mapping[str, Any] = field(default_factory=dict)
    task_weights: Mapping[str, float] = field(default_factory=dict)

    steps: int = 0
    batch_size: int = 16
    lr: float = 3e-4
    min_lr_ratio: float = 0.1
    warmup: int = 100
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    eval_every: int = 250
    log_every: int = 50
    seed: int = 0
    amp: bool = True
    device: torch.device = field(default_factory=lambda: torch.device("cpu"))

    #: Where to write periodic training state, so a long run can be assembled
    #: from pieces rather than lost when the process is interrupted.
    checkpoint: str | None = None
    #: Continue from that checkpoint if it exists.
    resume: bool = False

    #: ``(step, total, losses, grad_norm) -> None``
    on_step: Callable[..., None] | None = None
    #: ``(step) -> None`` — the trainer evaluates and records history
    on_eval: Callable[[int], None] | None = None


class Model(nn.Module):
    """The interface every architecture answers to, neural or not.

    Two methods matter. ``forward(batch) -> ModelOutput`` says what the model
    predicts; ``fit(ctx)`` says how it came to predict that. Whether the logits
    behind it came from attention or from a decision list, and whether the
    fitting was ten thousand gradient steps or one pass of counting, is exactly
    the question the repo is asking — so the trainer does neither and only
    supplies the data, the tasks and the budget.
    """

    #: registry name, set by ``@register``
    name: str = ""
    #: ``"neural"`` or ``"rule-based"`` — printed in comparison tables, because
    #: a parameter count means very different things across the two.
    family: str = "neural"

    def forward(self, batch: SymbolicBatch) -> "ModelOutput":
        raise NotImplementedError

    def fit(self, ctx: FitContext) -> None:
        """Learn from ``ctx.episodes``. Subclasses decide what that means."""
        raise NotImplementedError

    def n_parameters(self, trainable_only: bool = True) -> int:
        ps = self.parameters()
        return sum(p.numel() for p in ps if p.requires_grad or not trainable_only)


class NeuralModel(Model):
    """Embeddings in, two heads out, one encoder in between."""

    family = "neural"

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

    # ---- how a network learns ----------------------------------------
    def fit(self, ctx: FitContext) -> None:
        """AdamW, cosine decay, gradient clipping — the plain recipe.

        It is deliberately unremarkable, because it is a control rather than a
        contribution: every network in the repo inherits *this* method, so two
        architectures differ in what they compute and not in how they were
        tuned. A model that wants a different recipe overrides this and says so.

        Both objectives are stepped together rather than alternated. Alternating
        makes the last task's gradient the one the model most recently moved on,
        which shows up as a sawtooth in whichever metric was not updated last
        and makes two runs with different task orders incomparable.
        """
        import os

        from symbolic_ai_core.data.sampler import cycle

        self.to(ctx.device).train()
        opt = torch.optim.AdamW(self.parameters(), lr=ctx.lr,
                                weight_decay=ctx.weight_decay, betas=(0.9, 0.95))
        rng = random.Random(ctx.seed)
        streams = {n: cycle(ctx.episodes, t, ctx.tok,
                            batch_size=ctx.batch_size, rng=rng)
                   for n, t in ctx.tasks.items()}

        # A full-curriculum neural run is hours on a CPU, and a run that loses
        # everything when it is interrupted is a run that never finishes. The
        # optimiser state travels with the weights: resuming with a fresh AdamW
        # would restart its moment estimates and put a visible dent in the loss
        # exactly at the join.
        start = 0
        if ctx.resume and ctx.checkpoint and os.path.exists(ctx.checkpoint):
            state = torch.load(ctx.checkpoint, map_location=ctx.device,
                               weights_only=False)
            self.load_state_dict(state["model"])
            opt.load_state_dict(state["optimizer"])
            start = int(state["step"])
            if ctx.on_step:
                ctx.on_step(start - 1, ctx.steps, {"resumed": float(start)}, 0.0)
            if start >= ctx.steps:
                return

        for step in range(start, ctx.steps):
            for group in opt.param_groups:
                group["lr"] = _lr_at(step, ctx)

            opt.zero_grad(set_to_none=True)
            losses: dict[str, float] = {}
            for name, task in ctx.tasks.items():
                batch = next(streams[name]).to(ctx.device)
                with autocast(ctx.device, ctx.amp):
                    result = task.compute(self(batch), batch)
                (result.loss * ctx.task_weights.get(name, 1.0)).backward()
                losses[name] = float(result.loss.detach())

            grad = torch.nn.utils.clip_grad_norm_(self.parameters(), ctx.grad_clip)
            opt.step()

            last = step == ctx.steps - 1
            if ctx.on_step and (step % ctx.log_every == 0 or last):
                ctx.on_step(step, ctx.steps, losses, float(grad))
            if ctx.on_eval and ((step + 1) % ctx.eval_every == 0 or last):
                ctx.on_eval(step + 1)
                self.train()
            if ctx.checkpoint and ((step + 1) % ctx.eval_every == 0 or last):
                # Written next to the run's other artefacts, and only on the
                # same cadence as evaluation: checkpointing every step would
                # cost more than the training on a small model.
                torch.save({"model": self.state_dict(),
                            "optimizer": opt.state_dict(), "step": step + 1},
                           ctx.checkpoint)


#: The old name for :class:`NeuralModel`, kept because "symbolic model" now
#: means something specific in this repo and the ambiguity is worth retiring.
SymbolicModel = NeuralModel
