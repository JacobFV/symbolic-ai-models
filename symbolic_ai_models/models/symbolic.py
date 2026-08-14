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
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch

from symbolic_ai_core.data.batch import SymbolicBatch
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import NODE_TYPES, TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from symbolic_ai_core.graphview import (ABSTAIN, GraphView, Votes,
                                        node_context as _node_context)
from ..parsers import build as build_parser
from ..prefix import TextView, build_prefix_parser
from .base import FitContext, Model, ModelConfig, ModelOutput, N_TYPES

__all__ = ["RuleBasedModel", "GraphView", "TextView", "Votes", "ABSTAIN"]

# `GraphView`, `Votes`, `ABSTAIN` and `_node_context` moved into
# `symbolic_ai_core.graphview` and are re-exported here. Not decoration:
# `symbolic_ai_agents.envs.base`, `envs.repair` and three agents import
# `GraphView` from *this* module, and a merge that silently lost the name would
# look green — a modify/delete conflict resolves toward the delete without a
# word. `tests/test_layering.py` pins the re-export by identity, because a shim
# rebinding a *copy* of `GraphView` would pass an equality check and then fail
# every `isinstance` in the agents package.
#
# The move itself is the layering rule, not tidiness: a `GraphView` is what a
# reader of a masked term may see, whether that reader is scored by a task or by
# an environment, so the agents package was reaching into its sibling for a pure
# data type.


class RuleBasedModel(Model):
    """Base for everything that computes an answer instead of learning one.

    Subclasses implement :meth:`learn` and at least one of :meth:`text_votes`
    and :meth:`node_votes`; whichever they do not implement abstains, and
    abstaining lands them on the back-off rather than excusing them from the
    task.
    """

    family = "rule-based"

    #: Which prefix parser this model reads the text surface through, unless
    #: ``extra.text_parser`` overrides it. A *class* attribute so that two
    #: registrations of one reasoner can differ in exactly this and nothing
    #: else, which is what makes the difference between their rows a
    #: measurement of the parser rather than of two models.
    default_text_parser = "none"

    #: Whether this model reads the text surface through ``self.text_parser``.
    #: Off by default: building the prefix reading costs a decode per sequence,
    #: and a model that never asks should not pay for it.
    reads_text_parser = False

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
        self.parser = build_parser(str(cfg.get("parser", "none")))
        # The same idea one surface over. `self.parser` reads text into a
        # `ParseResult` -- word classes and brackets -- which is a claim about
        # categories. `self.text_parser` reads *prefixes* of the text into
        # `Graph`s, which is the codomain the masked-node task already uses, so
        # a reasoner written against the term graph can be pointed at the text
        # without being rewritten. See :mod:`symbolic_ai_models.prefix`, which
        # also carries the leak argument for the oracle that can sit here.
        self.text_parser = build_prefix_parser(
            str(cfg.get("text_parser", self.default_text_parser)))
        #: structural context -> (commonest label, how pure that context is)
        self.context_prior: dict[tuple, tuple[int, float]] = {}
        #: Post-hoc temperature on the graph output. 1.0 is no change.
        self.temperature = 1.0
        self._fitting_temperature = False
        # Registered as buffers so a fitted model saves and reloads like any
        # other, through the same `torch.save(state_dict())` path.
        self.register_buffer("symbol_backoff", torch.zeros(cfg.vocab_size))
        self.register_buffer("type_backoff", torch.zeros(N_TYPES))
        self._fitted = False

    # ---- fitting -----------------------------------------------------
    #: Whether an abstention falls back on the structural lookup rather than on
    #: the unigram prior. On by default: the unigram ignores structure that is
    #: free to read, and a model that declines to answer should not be dropped
    #: to a worse baseline than the one it is scored against.
    structural_fallback = True

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
        self.text_parser.fit(ctx.episodes, ctx.tok)
        self._fit_backoff(ctx.episodes, ctx.tok)
        self._fit_context_prior(ctx.episodes, ctx.tok)
        self.learn(ctx.episodes, ctx.tok)
        self._fitted = True
        self._fit_temperature(ctx.episodes, ctx.tok)

    def _fit_temperature(self, episodes: Sequence[Episode],
                         tok: SymbolTokenizer) -> None:
        """Scale the graph output so its stated probabilities mean what they say.

        Each model already calibrates its *vote* confidence, but the number a
        reader sees is the probability of the mixture, and the two came apart
        when the back-off became structure-aware: accuracy rose sharply while
        the vote confidences were still fitted against a weaker back-off,
        leaving the models under-confident by about 0.05 and their ECE up from
        ~0.09 to ~0.22.

        Temperature scaling is the minimal repair and the reason it is the right
        one here is that dividing log-probabilities by a positive constant
        cannot reorder them. Every prediction, and therefore every accuracy in
        the repo, is left exactly as it was; only the confidence attached to it
        moves. Fitted on held-out episodes by minimising negative log-likelihood
        over a coarse grid — one parameter, so a grid is honest and a search
        would be false precision.
        """
        import math

        cut = max(int(len(episodes) * 0.8), 1)
        held_out = episodes[cut:] or episodes
        self._fitting_temperature = True
        try:
            rows: list[tuple[float, ...]] = []
            targets: list[int] = []
            for chunk in range(0, len(held_out), 16):
                batch = self._masked_batch(held_out[chunk:chunk + 16], tok)
                if batch is None:
                    continue
                with torch.no_grad():
                    logits = self(batch).symbol_logits
                scored = batch.target_tokens >= 0
                if not bool(scored.any()):
                    continue
                rows.append(logits[scored].double())
                targets.extend(batch.target_tokens[scored].tolist())
        finally:
            self._fitting_temperature = False
        if not rows or len(targets) < 20:
            return

        stacked = torch.cat(rows, dim=0)
        gold = torch.tensor(targets, dtype=torch.long)
        best_t, best_nll = 1.0, math.inf
        for step in range(1, 41):
            t = step * 0.1
            nll = float(torch.nn.functional.cross_entropy(stacked / t, gold))
            if nll < best_nll:
                best_t, best_nll = t, nll
        self.temperature = best_t

    def _masked_batch(self, episodes: Sequence[Episode], tok: SymbolTokenizer):
        from symbolic_ai_core.data.batch import collate_graph
        if not episodes:
            return None
        return collate_graph(episodes, tok, max_nodes=self.cfg.max_nodes,
                             mask_rate=0.15, rng=np.random.default_rng(41))

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
                "_text_parser": self.text_parser,
                "_context_prior": self.context_prior,
                "_temperature": self.temperature,
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
            elif name == "_text_parser":
                if value is not None:
                    self.text_parser = value
            elif name == "_context_prior":
                self.context_prior = value or {}
            elif name == "_temperature":
                self.temperature = float(value or 1.0)
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

    def _fit_context_prior(self, episodes: Sequence[Episode],
                           tok: SymbolTokenizer) -> None:
        """The commonest label per structural context — the floor's own strategy.

        This is what an abstention now falls back on, and it matters more than
        it sounds. The unigram back-off ignores the shape of the tree, which is
        free to read and is exactly what the floor uses, so a model that
        declined to answer was being dropped below the baseline it is compared
        against — and the diagnostic showed several models whose *mechanism*
        beats the floor comfortably while their score does not, purely because
        they abstain. ``ilp`` answers 35% of nodes at 0.525 against a floor of
        0.332; ``synth`` answers 1% at 1.000.

        Shared here rather than bolted onto each model so every one of them
        falls back on the same thing, which is what keeps the comparison between
        them about their mechanisms.

        Worth stating plainly: only rule-based models have a back-off, so
        strengthening it moves them relative to the networks. The justification
        is that the old one was needlessly weak, not that the families should be
        levelled.
        """
        cut = max(int(len(episodes) * 0.8), 1)
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes[:cut], tok, repeats=2,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, type_id) in targets.items():
                if label_id >= 0:
                    counts[_node_context(view, node)][label_id] += 1
        # How much mass the prior takes is the context's own **purity** — how
        # often its commonest label was the right one in training — not a fixed
        # constant. A flat weight was tried first and it cost the two best
        # models (`ilp` 0.349 -> 0.308) while helping the weak ones, because a
        # confident-but-ambiguous context outranked a good vote. Purity settles
        # it with data: a near-deterministic context speaks loudly, an
        # ambiguous one steps aside and lets the model's reasoning decide.
        chosen = {key: table.most_common(1)[0][0]
                  for key, table in counts.items() if sum(table.values()) >= 3}

        # Purity measured on episodes the counts were *not* taken from. The
        # in-sample version is a maximum over labels fitted on the same data, so
        # it overstates — and since this mass is the back-off's own confidence,
        # overstating it made a well-calibrated model overconfident (`workspace`
        # ECE 0.094 -> 0.258) without changing a single prediction.
        hit: collections.Counter = collections.Counter()
        seen: collections.Counter = collections.Counter()
        for view, targets in self.training_views(episodes[cut:] or episodes, tok,
                                                 repeats=2, seed=31,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                key = _node_context(view, node)
                if key in chosen:
                    seen[key] += 1
                    hit[key] += chosen[key] == label_id
        overall = sum(hit.values()) / max(sum(seen.values()), 1)

        self.context_prior = {}
        for key, symbol in chosen.items():
            n = seen.get(key, 0)
            # Shrunk towards the global rate, so a context seen twice in the
            # held-out slice does not get to claim certainty.
            purity = (hit.get(key, 0) + 3.0 * overall) / (n + 3.0)
            self.context_prior[key] = (symbol, min(max(purity, 0.0), 0.9))

    def training_views(self, episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                       mask_rate: float = 0.15, max_nodes: int = 256,
                       repeats: int = 4, seed: int = 0, with_index: bool = False
                       ) -> Iterable[tuple]:
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
        from symbolic_ai_core.data.batch import collate_graph
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
                    # `with_index` names the episode a view came from, which a
                    # model needs to calibrate itself honestly: scoring a
                    # retrieval against a case base containing that very episode
                    # measures memory, not method.
                    yield ((view, targets, start + b) if with_index
                           else (view, targets))

    # ---- what the back-off already knows -------------------------------
    def backoff_prob(self, view: GraphView, node: int, symbol: int) -> float:
        """The probability the shared back-off puts on ``symbol`` at ``node``.

        Exactly the quantity :meth:`_mix` spends ``(1 - c)`` of the mass on, and
        computed here from the same two tables so the two cannot drift apart. A
        model fitting its own mixture weight against
        :class:`~symbolic_ai_models.calibration.MassCalibrator` needs this: the
        weight between two components is meaningless unless both are the
        probability of the same event.

        Not used by anything on the prediction path — it is a fitting-time
        helper — so a model that ignores it is unaffected.
        """
        base = float(self.symbol_backoff[symbol].exp())
        entry = self.context_prior.get(_node_context(view, node))
        if entry is None:
            return base
        prior_symbol, share = entry
        return base * (1.0 - share) + (share if int(prior_symbol) == int(symbol)
                                       else 0.0)

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

    def text_votes_view(self, view: TextView) -> list[Votes]:
        """The same question, with the prefix parses alongside the tokens.

        A model that sets ``reads_text_parser`` overrides this instead of
        :meth:`text_votes` and gets ``view.graph(t)`` — the structure its parser
        recovered from ``ids[:t + 1]``. The causality requirement is unchanged
        and the view is what enforces it: there is no field on it holding the
        episode, the answer, or any position after ``t``.
        """
        return self.text_votes(view.ids)

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        """``{hidden node: (label votes, type votes)}``.

        Type votes are keyed by type id, over :data:`NODE_TYPES`.
        """
        return {}

    #: Whether this model points at *sites* on the text surface. Off by
    #: default for the same reason ``reads_text_parser`` is: assembling a
    #: ``[B, L, L]`` pointer costs a pass per sequence, and a model that never
    #: points should not pay for one.
    emits_site = False

    def site_votes_view(self, view: TextView) -> dict[int, Votes]:
        """``{position: votes over *earlier positions* of the same sequence}``.

        The text-surface twin of :meth:`source_votes`, and the same seam: a
        pointer over the sites of whichever surface the batch carries. Here the
        question is **attachment** — "the head this token hangs under is that
        one" — which is the one thing the corpus is uniquely privileged for and
        which nothing in the repo has ever asked. The curriculum ships the true
        term *and* its rendering, so the correct site has ground truth at every
        position, for free, and
        :class:`symbolic_ai_models.readouts.site.SiteReadout` derives it.

        Causal on the same terms as :meth:`text_votes_view`: entry ``t`` may
        depend on ``view.graph(t)`` and ``view.text(t)``, both of which are
        functions of ``ids[:t + 1]``, and on nothing later. Votes naming a
        position after ``t`` are dropped rather than trusted — a leak here would
        make attachment look solved, so it is closed structurally rather than by
        asking implementations to behave.
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
        # The answer key, and only the oracle parser is ever shown it. See the
        # comment on `meta["graphs"]` in `collate_text` and the leak argument in
        # `symbolic_ai_models.prefix`: a batch that was not built from episodes
        # simply has none, and an oracle handed none returns nothing.
        truths = (batch.meta or {}).get("graphs") if self.text_parser.needs_truth \
            else None

        sites: list[tuple[int, int, Mapping[int, float], float]] = []
        for b in range(B):
            ids = tokens[b][:lengths[b]]
            if not ids:
                continue
            if self.reads_text_parser:
                truth = truths[b] if truths and b < len(truths) else None
                view = self.text_parser.begin(ids, self.tok, truth)
                row = self.text_votes_view(view)
                if self.emits_site:
                    for t, v in self.site_votes_view(view).items():
                        if 0 <= t < L and v is not ABSTAIN:
                            sites.append((b, int(t), v[0], float(v[1])))
            else:
                row = self.text_votes(ids)
            for t, (votes, c) in enumerate(row):
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
        channels: dict[str, torch.Tensor] = {}
        site = self._pointer_logits(sites, (B, L), batch.pad_mask, causal=True)
        if site is not None:
            channels["site"] = site
        return ModelOutput(symbol_logits=logits, type_logits=types,
                           hidden=torch.zeros((B, L, 1)), channels=channels)

    def _forward_graph(self, batch: SymbolicBatch) -> ModelOutput:
        B, L = batch.tokens.shape
        s_rows, s_cols, s_syms, s_w = [], [], [], []
        t_rows, t_cols, t_syms, t_w = [], [], [], []
        p_rows, p_cols, p_syms, p_mass = [], [], [], []
        s_conf = np.zeros((B, L), dtype=np.float64)
        t_conf = np.zeros((B, L), dtype=np.float64)

        for b in range(B):
            view = self._view(batch, b)
            if not len(view):
                continue
            votes = self.node_votes(view)
            if self.structural_fallback:
                # What a model degrades *to* has to be one thing. Treating only
                # abstentions left a second path untreated: a model that votes
                # with low confidence keeps most of its mass on the back-off,
                # and that back-off was the global unigram — so declining to
                # answer degraded to the structural prior while merely being
                # unsure degraded to something strictly worse. `ruleinduce`
                # votes on every node at 0.192 and scored 0.076 for exactly
                # that reason. The context prior is part of the back-off now, so
                # both paths land in the same place.
                for node in view.hidden:
                    entry = self.context_prior.get(_node_context(view, node))
                    if entry is not None:
                        p_rows.append(b)
                        p_cols.append(node)
                        p_syms.append(int(entry[0]))
                        p_mass.append(float(entry[1]))
            for node, (label_votes, type_votes) in votes.items():
                if not (0 <= node < L):
                    continue
                _collect(label_votes, b, node, s_rows, s_cols, s_syms, s_w, s_conf)
                _collect(type_votes, b, node, t_rows, t_cols, t_syms, t_w, t_conf)

        source_logits = self._source_logits(batch, (B, L))

        symbol_logits = self._mix(self.symbol_backoff, (B, L), s_conf,
                                  s_rows, s_cols, s_syms, s_w,
                                  prior=(p_rows, p_cols, p_syms, p_mass))
        if self.temperature != 1.0 and not self._fitting_temperature:
            symbol_logits = torch.log_softmax(symbol_logits / self.temperature,
                                              dim=-1)
        return ModelOutput(
            symbol_logits=symbol_logits,
            type_logits=self._mix(self.type_backoff, (B, L), t_conf,
                                  t_rows, t_cols, t_syms, t_w),
            source_logits=source_logits,
            hidden=torch.zeros((B, L, 1)))

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        """``{hidden node: votes over *node indices* of this episode}``.

        The optional third head. A model that answers "the label here is
        whatever node 7 says" states a binding; a model that answers with a
        symbol states a guess about vocabulary. On this curriculum 71.9% of
        scored answers already sit on a visible node, so the binding is usually
        available and the vocabulary usually is not — 88.5% of the labels the
        symbol head cannot even score are invented `ident` names.

        Default is no pointer, which leaves ``source_logits`` unset and the
        model simply unscored on copying rather than scored as zero.
        """
        return {}

    def _source_logits(self, batch: SymbolicBatch,
                       shape: tuple[int, int]) -> torch.Tensor | None:
        """Assemble the pointer head, or ``None`` if this model has no pointer."""
        B, L = shape
        votes: list[tuple[int, int, Mapping[int, float], float]] = []
        for b in range(B):
            for node, v in self.source_votes(self._view(batch, b)).items():
                if v is ABSTAIN or not 0 <= node < L:
                    continue
                weights, confidence = v
                if weights and confidence > 0.0:
                    votes.append((b, node, weights, float(confidence)))
        return self._pointer_logits(votes, shape, batch.pad_mask)

    @staticmethod
    def _pointer_logits(votes: Sequence[tuple[int, int, Mapping[int, float], float]],
                        shape: tuple[int, int], visible: torch.Tensor, *,
                        causal: bool = False) -> torch.Tensor | None:
        """``[B, L, L]`` for any pointer channel, or ``None`` if nothing pointed.

        One assembler for both pointer channels rather than two, which is the
        whole claim that ``site`` **generalises** ``source_logits`` instead of
        sitting beside it as a second mechanism. The two differ in what a
        position means — a node of a term, a token of a rendering — and in
        nothing about how a vote becomes a score.

        The back-off is flat over the legal targets rather than learned. A
        pointer's floor is already a structure-only rule scoring 0.266, so
        giving the back-off structural knowledge here would quietly move the
        thing every pointer is measured against.

        ``causal`` closes the text-surface leak structurally: on a running-text
        batch a site at ``t`` may only name a position ``<= t``, so a vote
        pointing forward is dropped rather than trusted. Attachment would look
        solved if it were allowed to read ahead, and asking implementations not
        to is not a guard.
        """
        B, L = shape
        if not votes:
            return None
        logits = torch.full((B, L, L), -1e9)
        logits[visible[:, None, :].expand(B, L, L)] = 0.0
        if causal:
            future = torch.ones((L, L), dtype=torch.bool).triu(1)
            logits[future[None].expand(B, L, L)] = -1e9
        for b, site, weights, confidence in votes:
            total = sum(weights.values()) or 1.0
            for j, w in weights.items():
                if not 0 <= j < L or not bool(visible[b, j]):
                    continue
                if causal and j > site:
                    continue
                logits[b, site, j] += 1.0 + 9.0 * confidence * (w / total)
        return logits

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
            rel=rel, hidden=hidden, tok=self.tok,
            text=((batch.meta or {}).get("prompts") or [""] * (b + 1))[b],
            language=((batch.meta or {}).get("languages") or [""] * (b + 1))[b])

    @staticmethod
    def _mix(backoff: torch.Tensor, shape: tuple[int, int], conf: np.ndarray,
             rows: list[int], cols: list[int], syms: list[int],
             weights: list[float],
             prior: tuple[list[int], list[int], list[int], list[float]] | None = None
             ) -> torch.Tensor:
        """``log[(1 - c)·backoff + c·votes]``, built without a Python loop over
        the vocabulary.

        Everything not voted for gets ``(1 - c)`` of its back-off mass, which is
        a single scaled copy of one row; only the voted entries need touching,
        and they are written in one scatter. The result is the log of a proper
        distribution, so feeding it to ``cross_entropy`` is exact rather than
        approximately normalised.

        ``prior`` names one symbol per position that the structural context
        expects, together with how much of the back-off mass it should take —
        the context's purity, measured in training. That makes the back-off
        itself structure-aware: a model with no opinion, or an unsure one, falls
        to what usually stands in that slot rather than to the corpus-wide
        unigram, and by an amount the data justifies.
        """
        B, L = shape
        device = backoff.device
        c = torch.from_numpy(conf).to(device=device, dtype=backoff.dtype)

        share = torch.zeros((B, L), device=device, dtype=backoff.dtype)
        if prior and prior[0]:
            idx = (torch.tensor(prior[0], device=device),
                   torch.tensor(prior[1], device=device))
            share.index_put_(idx, torch.tensor(prior[3], device=device,
                                               dtype=backoff.dtype))

        # (1 - c) of the mass is the back-off; of that, `share` goes to the
        # structural prior and the rest keeps the unigram shape.
        probs = (backoff.exp()[None, None, :]
                 * ((1.0 - c) * (1.0 - share))[:, :, None]).contiguous()
        if prior and prior[0]:
            idx = (torch.tensor(prior[0], device=device),
                   torch.tensor(prior[1], device=device),
                   torch.tensor(prior[2], device=device))
            mass = torch.tensor(prior[3], device=device, dtype=backoff.dtype)
            probs.index_put_(idx, (1.0 - c[idx[0], idx[1]]) * mass,
                             accumulate=True)
        if rows:
            idx = (torch.tensor(rows, device=device),
                   torch.tensor(cols, device=device),
                   torch.tensor(syms, device=device))
            add = c[idx[0], idx[1]] * torch.tensor(weights, dtype=backoff.dtype,
                                                   device=device)
            probs.index_put_(idx, add, accumulate=True)
        return probs.clamp_min(1e-12).log()


def prune_tables(tables: Mapping[Any, "collections.Counter"], *,
                 max_entries: int, min_count: int = 1) -> dict:
    """Bound a context table's size, dropping the least-evidenced contexts.

    Count tables grow with distinct contexts, which on this data is close to
    linear in tokens — about 0.9 entries per token for `ngram` and 1.4 for
    `ctw`, so a 40M-token corpus would want tens of millions of entries and
    several gigabytes of Python dict. The source work these models come from
    reports exactly that failure, and nothing here bounded it.

    The remedy is the standard one for count-based language models: a count
    cutoff first, dropping contexts seen fewer than ``min_count`` times, then a
    hard cap keeping the most-observed. Both prune the *long tail*, which is
    where the entries are and where the evidence is not — a context seen once
    supports a prediction worth almost nothing, and dropping it costs a back-off
    rather than an answer.
    """
    kept = {k: c for k, c in tables.items() if sum(c.values()) >= min_count}
    if len(kept) <= max_entries:
        return kept
    ranked = sorted(kept.items(), key=lambda kv: (-sum(kv[1].values()), str(kv[0])))
    return dict(ranked[:max_entries])


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
    from symbolic_ai_core.data.batch import MAX_SLOT, REL
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
