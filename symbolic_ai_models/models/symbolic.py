"""The other half of the repo: models that are *fitted*, not trained.

A symbolic model here is held to exactly the same standard as a network. It does
not get to answer multiple-choice questions while the transformers do
next-token prediction; it produces a probability distribution over the same
vocabulary at every position, and it is scored by the same cross-entropy,
against the same floors, out of the same :class:`~symbolic_ai_models.models.base.Model`
interface. If a decision list cannot say how likely the next word is, it does
not appear in the table.

That bar is what this module exists to enforce, and it enforces it three ways.

**A distribution, not an answer.** A rule-based model emits *votes* — a handful
of symbols it has a reason to expect — plus a **confidence** in ``[0, 1]``. The
base class turns that into a proper distribution by mixing against a smoothed
unigram back-off fitted on the training episodes::

    p(v) = (1 - confidence) · backoff(v) + confidence · votes(v)

Confidence zero is abstention, and it lands the model exactly on the back-off.
Nothing can assign zero probability, so cross-entropy is always finite and a
confidently wrong model is punished for it. The back-off is identical across
every rule-based model, so differences between them come from their machinery,
in the same way that shared embeddings and heads localise the differences
between the networks.

**It cannot see the answer.** Rather than asking models not to peek, the base
hands them a :class:`GraphView` in which hidden labels and types are literally
``None`` — there is no field holding the value being predicted. The text side
is checked empirically instead of structurally, because a per-position loop
would be far too slow for a program synthesiser: every model in the registry,
neural and symbolic alike, must pass a test that perturbing later tokens leaves
earlier predictions bit-identical.

**It is fitted on training seeds only.** ``fit`` sees the training episodes and
nothing else, and the evaluation episodes come from seeds a million apart.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch

from ..data.batch import SymbolicBatch
from ..data.curriculum import Episode
from ..data.graph import NODE_TYPES, TYPE_TO_ID
from ..data.tokenizer import SymbolTokenizer
from .base import FitContext, Model, ModelConfig, ModelOutput, N_TYPES

__all__ = ["RuleBasedModel", "GraphView", "Votes", "ABSTAIN"]

#: What a model returns when it has nothing to say: no votes, no confidence.
#: The mixture then reduces exactly to the back-off, which is the honest reading
#: of "I don't know" and is why abstention costs a model nothing beyond the
#: prior it declined to improve on.
ABSTAIN: "Votes" = ({}, 0.0)

#: ``({symbol id: weight}, confidence in [0, 1])``
Votes = tuple[Mapping[int, float], float]


@dataclass
class GraphView:
    """A masked graph, as a rule-based model is allowed to see it.

    ``labels[i]`` and ``types[i]`` are ``None`` exactly where the model is being
    asked to predict. There is no second field holding the true value: a model
    that wanted to cheat would have nothing to read. The relations in ``rel``
    have already had the coreference edges of hidden nodes withheld by
    :func:`~symbolic_ai_models.data.batch.relation_matrix`, so the shape of the tree is
    visible and the identity of the hidden symbol is not.
    """

    labels: list[int | None]
    types: list[str | None]
    parent: list[int]
    slot: list[int]
    depth: list[int]
    rel: np.ndarray
    hidden: list[int]
    tok: SymbolTokenizer

    def __len__(self) -> int:
        return len(self.labels)

    def word(self, i: int) -> str | None:
        """The label of node ``i`` as text, or ``None`` if it is hidden."""
        v = self.labels[i]
        return None if v is None else self.tok.itos[v]

    def children(self, i: int) -> list[int]:
        return [j for j, p in enumerate(self.parent) if p == i]

    def siblings(self, i: int) -> list[int]:
        p = self.parent[i]
        return [] if p < 0 else [j for j in self.children(p) if j != i]

    def parent_type(self, i: int) -> str:
        p = self.parent[i]
        return self.types[p] or "mask" if 0 <= p < len(self.types) else "ROOT"

    def path(self, i: int, depth: int = 3) -> tuple:
        """The chain of ancestor types above ``i``, nearest first."""
        out: list[str] = []
        p = self.parent[i]
        while 0 <= p < len(self.types) and len(out) < depth:
            out.append(self.types[p] or "mask")
            p = self.parent[p]
        return tuple(out)


class RuleBasedModel(Model):
    """Base for everything that computes an answer instead of learning one.

    Subclasses implement :meth:`learn` and at least one of :meth:`text_votes`
    and :meth:`node_votes`; whichever they do not implement abstains, and
    abstaining lands them on the back-off rather than excusing them from the
    task.
    """

    family = "rule-based"

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.tok: SymbolTokenizer | None = None
        # Every rule-based model gets a parser, named in `extra.parser` and
        # defaulting to the one that does nothing. Reading the text and
        # reasoning over what was read are separate choices, and welding them
        # together — as each of these models originally did — means a better
        # parser cannot be dropped under an existing reasoner. A reasoner that
        # ignores `self.parser` is unaffected; one that uses it must still work
        # when handed `none`.
        self.parser = _build_parser(str(cfg.get("parser", "none")))
        # Registered as buffers so a fitted model saves and reloads like any
        # other, through the same `torch.save(state_dict())` path.
        self.register_buffer("symbol_backoff", torch.zeros(cfg.vocab_size))
        self.register_buffer("type_backoff", torch.zeros(N_TYPES))
        self._fitted = False

    # ---- fitting -----------------------------------------------------
    def fit(self, ctx: FitContext) -> None:
        """Fit the shared back-off, then whatever the subclass learns.

        ``ctx.steps`` is ignored, and deliberately not reinterpreted as
        something else: a decision list induced from these episodes is the same
        list however long you leave it running. What the trainer records is
        ``steps: 0``, so a row in a comparison table cannot be misread as a
        model that trained as long as its neighbours.
        """
        self.tok = ctx.tok
        # The parser is fitted first and on the same episodes, so a reasoner
        # that consults it during `learn` sees the parser it will see at
        # evaluation rather than an unfitted one.
        self.parser.fit(ctx.episodes, ctx.tok)
        self._fit_backoff(ctx.episodes, ctx.tok)
        self.learn(ctx.episodes, ctx.tok)
        self._fitted = True

    def fit_on(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Fit straight from episodes, for callers with nothing else to say."""
        self.fit(FitContext(episodes=episodes, tok=tok))

    # ---- persistence -------------------------------------------------
    #: Attribute names holding what this model learned. A network's parameters
    #: are tensors and ``state_dict`` finds them by itself; a decision list, a
    #: counter and a codebook of templates are ordinary Python objects that it
    #: cannot see, so each model names them here and they are saved alongside.
    #: Leaving this empty means a model reloads unfitted and cannot predict.
    LEARNED: tuple[str, ...] = ()

    def symbolic_state(self) -> dict[str, Any]:
        """Everything ``state_dict`` would miss — the parser included."""
        return {"_fitted": self._fitted, "_parser": self.parser,
                **{name: getattr(self, name, None) for name in self.LEARNED}}

    def load_symbolic_state(self, state: Mapping[str, Any],
                            tok: SymbolTokenizer) -> None:
        self.tok = tok
        for name, value in state.items():
            if name == "_fitted":
                self._fitted = bool(value)
            elif name == "_parser":
                if value is not None:
                    self.parser = value
            else:
                setattr(self, name, value)

    def _fit_backoff(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """A smoothed unigram over everything the training episodes contain.

        Both surfaces feed it — text pieces and node labels — because it backs
        both tasks and a symbol common in one is worth expecting in the other.
        """
        counts = collections.Counter()
        types = collections.Counter()
        for ep in episodes:
            counts.update(tok.encode(ep.text, bos=True, eos=True))
            for label, type_ in zip(ep.graph.labels, ep.graph.types):
                types[TYPE_TO_ID[type_]] += 1
                if label:
                    counts[tok.label_id(label)] += 1
        self.symbol_backoff.copy_(_log_dirichlet(counts, len(tok)))
        self.type_backoff.copy_(_log_dirichlet(types, N_TYPES))

    def training_views(self, episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                       mask_rate: float = 0.15, max_nodes: int = 256,
                       repeats: int = 4, seed: int = 0
                       ) -> Iterable[tuple[GraphView, dict[int, tuple[int, int]]]]:
        """Masked views of the training graphs, with the answers alongside.

        A model that fits its context statistics on *whole* graphs and is then
        asked about *masked* ones has a train/test mismatch the networks do not
        have — ``collate_graph`` masks during their training too. It shows up as
        a rule keyed on the parent's label firing happily in training and
        finding ``None`` there at evaluation.

        So fitting goes through the very same collator, and the view is built by
        the very same ``_view``. Whatever a model can read here it can read at
        evaluation, and the mask rate is the one it will actually face.
        ``repeats`` passes re-mask the same episodes so that most nodes get to
        be a target at some point without any of them ever being visible while
        it is.
        """
        from ..data.batch import collate_graph
        rng = np.random.default_rng(seed)
        for _ in range(max(repeats, 1)):
            for start in range(0, len(episodes), 32):
                chunk = list(episodes[start:start + 32])
                if not chunk:
                    continue
                batch = collate_graph(chunk, tok, max_nodes=max_nodes,
                                      mask_rate=mask_rate, rng=rng)
                for b in range(len(chunk)):
                    view = self._view(batch, b)
                    targets = {
                        i: (int(batch.target_tokens[b, i]),
                            int(batch.target_types[b, i]))
                        for i in view.hidden
                    }
                    yield view, targets

    # ---- subclass hooks ----------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Read the training episodes and build whatever this model reasons with."""

    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        """Votes for each next token: entry ``t`` predicts ``ids[t + 1]``.

        Implementations must be **causal** — entry ``t`` may depend on
        ``ids[:t + 1]`` and nothing later. This is checked empirically for every
        registered model rather than taken on trust; see the causality test.
        """
        return [ABSTAIN] * len(ids)

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        """``{hidden node: (label votes, type votes)}``.

        Type votes are keyed by type id, over :data:`NODE_TYPES`.
        """
        return {}

    def n_symbolic_parameters(self) -> int:
        """How many discrete things this model learned.

        Reported instead of a tensor count, because "a decision list with 34
        rules" and "a transformer with 1.5 million weights" are both model sizes
        and printing zero for the first one would be worse than either.
        """
        return 0

    def n_parameters(self, trainable_only: bool = True) -> int:
        return self.n_symbolic_parameters()

    # ---- the shared forward -------------------------------------------
    def forward(self, batch: SymbolicBatch) -> ModelOutput:
        if not self._fitted:
            raise RuntimeError(f"{self.name}: fit() must be called before forward()")
        return (self._forward_text(batch) if batch.rel is None
                else self._forward_graph(batch))

    def _forward_text(self, batch: SymbolicBatch) -> ModelOutput:
        B, L = batch.tokens.shape
        rows, cols, syms, weights, conf = [], [], [], [], np.zeros((B, L), dtype=np.float64)
        tokens = batch.tokens.tolist()
        lengths = batch.pad_mask.sum(1).tolist()

        for b in range(B):
            ids = tokens[b][:lengths[b]]
            if not ids:
                continue
            for t, (votes, c) in enumerate(self.text_votes(ids)):
                if t >= L or not votes or c <= 0.0:
                    continue
                total = float(sum(votes.values()))
                if total <= 0.0:
                    continue
                conf[b, t] = min(max(c, 0.0), 1.0)
                for symbol, weight in votes.items():
                    rows.append(b)
                    cols.append(t)
                    syms.append(int(symbol))
                    weights.append(float(weight) / total)

        logits = self._mix(self.symbol_backoff, (B, L), conf, rows, cols, syms, weights)
        types = self.type_backoff.expand(B, L, N_TYPES).clone()
        return ModelOutput(symbol_logits=logits, type_logits=types,
                           hidden=torch.zeros((B, L, 1)))

    def _forward_graph(self, batch: SymbolicBatch) -> ModelOutput:
        B, L = batch.tokens.shape
        s_rows, s_cols, s_syms, s_w = [], [], [], []
        t_rows, t_cols, t_syms, t_w = [], [], [], []
        s_conf = np.zeros((B, L), dtype=np.float64)
        t_conf = np.zeros((B, L), dtype=np.float64)

        for b in range(B):
            view = self._view(batch, b)
            if not len(view):
                continue
            for node, (label_votes, type_votes) in self.node_votes(view).items():
                if not (0 <= node < L):
                    continue
                _collect(label_votes, b, node, s_rows, s_cols, s_syms, s_w, s_conf)
                _collect(type_votes, b, node, t_rows, t_cols, t_syms, t_w, t_conf)

        return ModelOutput(
            symbol_logits=self._mix(self.symbol_backoff, (B, L), s_conf,
                                    s_rows, s_cols, s_syms, s_w),
            type_logits=self._mix(self.type_backoff, (B, L), t_conf,
                                  t_rows, t_cols, t_syms, t_w),
            hidden=torch.zeros((B, L, 1)))

    def _view(self, batch: SymbolicBatch, b: int) -> GraphView:
        """Build the redacted view of sample ``b``. Hidden values are dropped."""
        n = int(batch.pad_mask[b].sum())
        types = batch.types[b, :n].tolist()
        labels = batch.tokens[b, :n].tolist()
        mask_id = TYPE_TO_ID["mask"]
        hidden = [i for i, t in enumerate(types) if t == mask_id]
        rel = batch.rel[b, :n, :n].cpu().numpy()
        parent, slot, depth = _tree_from_relations(rel, n)
        return GraphView(
            labels=[None if types[i] == mask_id else labels[i] for i in range(n)],
            types=[None if types[i] == mask_id else NODE_TYPES[types[i]]
                   for i in range(n)],
            parent=parent, slot=slot, depth=batch.depth[b, :n].tolist(),
            rel=rel, hidden=hidden, tok=self.tok)

    @staticmethod
    def _mix(backoff: torch.Tensor, shape: tuple[int, int], conf: np.ndarray,
             rows: list[int], cols: list[int], syms: list[int],
             weights: list[float]) -> torch.Tensor:
        """``log[(1 - c)·backoff + c·votes]``, built without a Python loop over
        the vocabulary.

        Everything not voted for gets ``(1 - c)`` of its back-off mass, which is
        a single scaled copy of one row; only the voted entries need touching,
        and they are written in one scatter. The result is the log of a proper
        distribution, so feeding it to ``cross_entropy`` is exact rather than
        approximately normalised.
        """
        B, L = shape
        V = backoff.shape[0]
        c = torch.from_numpy(conf).to(backoff.dtype)
        probs = backoff.exp()[None, None, :] * (1.0 - c)[:, :, None]
        probs = probs.contiguous()
        if rows:
            idx = (torch.tensor(rows), torch.tensor(cols), torch.tensor(syms))
            add = c[idx[0], idx[1]] * torch.tensor(weights, dtype=backoff.dtype)
            probs.index_put_(idx, add, accumulate=True)
        return probs.clamp_min(1e-12).log()


def _collect(votes: Votes, b: int, node: int, rows: list, cols: list,
             syms: list, weights: list, conf: np.ndarray) -> None:
    """Flatten one node's votes into the scatter arrays."""
    table, confidence = votes
    if not table or confidence <= 0.0:
        return
    total = float(sum(table.values()))
    if total <= 0.0:
        return
    conf[b, node] = min(max(float(confidence), 0.0), 1.0)
    for symbol, weight in table.items():
        rows.append(b)
        cols.append(node)
        syms.append(int(symbol))
        weights.append(float(weight) / total)


def _build_parser(name: str):
    """Resolve a parser by name. Imported lazily to keep the import graph a DAG:
    parsers depend on the data layer, models depend on parsers, and nothing
    depends on models."""
    from ..parsers import build
    return build(name)


def _log_dirichlet(counts: Mapping[int, float], size: int,
                   alpha: float = 0.5) -> torch.Tensor:
    """Log of an add-``alpha`` smoothed distribution over ``size`` symbols.

    Smoothed rather than raw so that a symbol the training episodes never used
    is merely unlikely. The curriculum invents vocabulary per episode, so the
    evaluation set is *guaranteed* to contain symbols training never saw, and an
    unsmoothed back-off would score infinite loss on every one of them.
    """
    total = sum(counts.values()) + alpha * size
    out = torch.full((size,), math.log(alpha / total))
    for k, v in counts.items():
        if 0 <= int(k) < size:
            out[int(k)] = math.log((v + alpha) / total)
    return out


def _tree_from_relations(rel: np.ndarray, n: int) -> tuple[list[int], list[int], list[int]]:
    """Recover ``(parent, slot, depth)`` from the relation matrix.

    The batch carries the tree as relations rather than as pointers, and a
    rule-based model wants the pointers back. Reading them out of ``rel``
    instead of off the episode is deliberate: it guarantees these models see
    precisely what the networks see and not one field more.
    """
    from ..data.batch import MAX_SLOT, REL
    parent = [-1] * n
    slot = [0] * n
    first = REL["parent_0"]
    for i in range(n):
        row = rel[i]
        hits = np.flatnonzero((row >= first) & (row < first + MAX_SLOT))
        if hits.size:
            parent[i] = int(hits[0])
            slot[i] = int(row[hits[0]]) - first
    depth = [0] * n
    for i in range(n):
        d, p, guard = 0, parent[i], 0
        while p >= 0 and guard < n:
            d += 1
            p = parent[p]
            guard += 1
        depth[i] = d
    return parent, slot, depth
