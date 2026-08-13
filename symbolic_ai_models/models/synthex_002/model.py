"""synthEX's class layer, imported with the control it shipped and did not publish.

The leapfrog thesis (``synthEX/docs/leapfrog-seeding.md``) is that a curated
concept layer makes structure *estimable*: a 50K vocabulary is data-starved even
for a bigram, but clustering it into a few hundred bounded classes makes the
transition table dense, and a word never seen in training still has a known
class. Its headline result is +1.21 bits/word on the unseen tail from a WordNet
supersense seed.

**That headline does not survive its own control, and the control is in the same
repository.** ``wordnet_seed.measure_seed_control`` is labelled "the HONESTY
CONTROL", its comments read ``INFLATED`` and ``the HONEST win (≈0)``, and it was
run — the numbers sit in ``examples/seed_leapfrog_report.json``:

=============  =============  ===============  ================  ==============
train chars    seed_vs_mem    random_vs_mem    seed_vs_random    seed_vs_fair
=============  =============  ===============  ================  ==============
3,000,000            1.3059           1.1999            0.1060         -0.0160
10,000,000           1.2889           1.2642            0.0247         -0.0331
20,000,000           1.2480           1.2743           -0.0263         -0.0740
=============  =============  ===============  ================  ==============

The memorizer it is compared against backs off to ``0.4 * unigram``, and
``-log2(0.4) = 1.3219`` bits — the entire reported win, to three digits. A
**meaningless sha256 partition** of the same cardinality collects 1.27 of it. The
seed's actual semantic content is ``seed_vs_random``, which shrinks with data and
turns negative by 15M characters; against a fairly-backed-off memorizer it is
negative at every scale.

So the honest reading of the leapfrog is: **bounded-class backoff works, curated
semantics contributed approximately nothing, and the advantage decays with
data.** Bounded-class backoff is a good idea — it is also Brown clustering, and
it is what ``grammar`` already does here by union-find.

What this pair tests
--------------------
Whether curated classes *ever* beat a random partition — asked where the
curriculum makes the question maximally favourable to the seed. WordNet's
supersense for an English word is a noisy guess about a word with many senses;
this curriculum's node **type** is the generator's own ground truth, exact and
free. If a curated class layer cannot beat a same-cardinality random partition
*here*, the deflation above is not an artefact of WordNet's quality.

Two models, one line apart:

``synthex_class-002``
    Classes are the curriculum's real node types — a curated, correct,
    17-category ontology.

``synthex_random-002``
    Classes are ``sha256(symbol) % 17`` — the same cardinality, no meaning.
    synthEX's ``_random_class`` control, moved to where the ontology is exact.

Both back off identically and are scored on the same floors, so the gap between
the two rows is the value of the semantics and can be nothing else. A gap near
zero reproduces R59 on ground-truth classes and is the stronger result.
"""

from __future__ import annotations

import collections
import hashlib
from typing import Sequence

from ...calibration import MassCalibrator
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["SynthexClassModel", "SynthexCurated", "SynthexRandom"]


class SynthexClassModel(RuleBasedModel):
    """Predict a label from the *classes* of its structural neighbourhood."""

    LEARNED = ("symbol_class", "tables", "gate_map", "type_rules", "n_classes")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.n_classes = int(cfg.get("n_classes", 17))
        #: symbol id -> class id. The seed.
        self.symbol_class: dict[int, int] = {}
        #: (class context) -> Counter over labels. The estimable table.
        self.tables: dict[tuple, collections.Counter] = {}
        self.gate_map = MassCalibrator()
        self.type_rules: dict[tuple, collections.Counter] = {}
        self.min_support = int(cfg.get("min_support", 3))

    # ---- the seed ------------------------------------------------------
    def _assign_classes(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> dict[int, int]:
        raise NotImplementedError

    def _class_of(self, symbol: int | None) -> int:
        """Unknown symbols get their own bucket rather than a wrong one.

        A separate ``unknown`` class is what makes the unseen tail *reachable* at
        all, and — per the control this module documents — it is most of what a
        class layer was ever buying.
        """
        if symbol is None:
            return self.n_classes
        return self.symbol_class.get(int(symbol), self.n_classes)

    # ---- fitting -------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.symbol_class = self._assign_classes(episodes, tok)
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        types: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        cut = max(int(len(episodes) * 0.8), 1)
        for view, targets in self.training_views(episodes[:cut], tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, type_id) in targets.items():
                if label_id >= 0:
                    for key in self._contexts(view, node):
                        counts[key][int(label_id)] += 1
                if type_id >= 0:
                    types[self._contexts(view, node)[-1]][int(type_id)] += 1
        self.tables = dict(counts)
        self.type_rules = dict(types)
        self._fit_gate(episodes[cut:] or episodes, tok)

    def _contexts(self, view: GraphView, node: int) -> list[tuple]:
        """Class-valued descriptions of the neighbourhood, most specific first.

        Every element is a *class* rather than a symbol, which is the whole
        point: the table stays dense because there are 18 classes and not 8,192
        symbols. Backing off along this ladder is what makes an unseen
        neighbourhood still land somewhere.
        """
        parent = view.parent[node]
        parent_class = self._class_of(view.labels[parent] if parent >= 0 else None)
        siblings = [self._class_of(view.labels[j]) for j in view.siblings(node)]
        sibling_class = siblings[0] if siblings else self.n_classes
        slot = min(view.slot[node], 6)
        depth = min(view.depth[node], 6)
        return [
            ("pcs", parent_class, sibling_class, slot, depth),
            ("pc", parent_class, sibling_class, slot),
            ("p", parent_class, slot),
            ("d", depth, slot),
        ]

    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(episodes, tok, repeats=1,
                                                 seed=7,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                table = self._label_table(view, node)
                if not table:
                    continue
                total = sum(table.values())
                scores.append(max(table.values()) / total)
                votes.append(table.get(int(label_id), 0.0) / total)
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        self.gate_map = MassCalibrator().fit(scores, votes, backoff)

    # ---- prediction ----------------------------------------------------
    def _label_table(self, view: GraphView, node: int) -> dict[int, float]:
        """The most specific class context with enough evidence wins."""
        for key in self._contexts(view, node):
            counts = self.tables.get(key)
            if counts and sum(counts.values()) >= self.min_support:
                return {int(s): float(c) for s, c in counts.items()}
        return {}

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            table = self._label_table(view, i)
            type_vote = self._type_vote(view, i)
            if not table or not self.gate_map.fitted:
                out[i] = (ABSTAIN, type_vote)
                continue
            total = sum(table.values())
            gate = float(self.gate_map(max(table.values()) / total))
            out[i] = ((table, gate) if gate > 0.0 else ABSTAIN, type_vote)
        return out

    def _type_vote(self, view: GraphView, node: int) -> Votes:
        counts = self.type_rules.get(self._contexts(view, node)[-1])
        if counts and sum(counts.values()) >= self.min_support:
            total = sum(counts.values())
            top, n = counts.most_common(1)[0]
            return {int(top): 1.0}, min(0.15 + 0.8 * n / total, 0.95)
        return ABSTAIN

    def n_symbolic_parameters(self) -> int:
        return len(self.symbol_class) + len(self.tables)

    def render(self) -> str:
        used = len(set(self.symbol_class.values())) if self.symbol_class else 0
        return "\n".join([
            f"=== {self.name}: {used} classes over "
            f"{len(self.symbol_class)} symbols ===",
            f"  context tables {len(self.tables)}",
            f"  gate: {'fitted' if self.gate_map.fitted else 'unfitted'}"])


@register("synthex_class-002",
          doc="synthEX class layer, classes = the curriculum's true node types.")
class SynthexCurated(SynthexClassModel):
    """A curated, *correct* ontology: the generator's own type for each symbol.

    This is the strongest form of the leapfrog's high-level seed available
    anywhere — not a guessed supersense for a polysemous word but the category
    the data-generating process actually used. If curated classes beat a random
    partition, they beat it here.
    """

    def _assign_classes(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> dict[int, int]:
        from symbolic_ai_core.data.graph import TYPE_TO_ID
        # A symbol's class is the type it most often carries in training. Ties
        # break by type id so the assignment does not depend on dict order.
        seen: dict[int, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for episode in episodes:
            for label, type_ in zip(episode.graph.labels, episode.graph.types):
                if label:
                    seen[tok.label_id(label)][TYPE_TO_ID[type_]] += 1
        return {symbol: min(counts.most_common(),
                            key=lambda kv: (-kv[1], kv[0]))[0]
                for symbol, counts in seen.items()}


@register("synthex_random-002",
          doc="The same model with meaningless classes: synthEX's R59 control.")
class SynthexRandom(SynthexClassModel):
    """Same cardinality, no semantics. ``sha256(symbol) % n_classes``.

    Lifted from ``synthEX/synthetic_worlds/perception/wordnet_seed._random_class``
    and moved to where the curated alternative is ground truth rather than a
    lexicographer's guess. Deterministic across processes, which matters here:
    ``hash()`` is salted per interpreter and would make the row unreproducible.
    """

    def _assign_classes(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> dict[int, int]:
        # Cardinality is taken from the curated assignment, not from the
        # nominal 17. Only 6 of the curriculum's types ever land on a labelled
        # node, and a first version hashed into all 17 — giving the control a
        # partition nearly three times finer than the thing it controls for.
        # It won, and the row would have read "random beats curated" when it
        # said "more classes beat fewer". synthEX's own control sets
        # `k = max(len(set(real_classes)), 2)` for exactly this reason.
        curated = SynthexCurated._assign_classes(self, episodes, tok)
        k = max(len(set(curated.values())), 2)
        self.n_classes = k
        return {symbol: int(hashlib.sha256(str(symbol).encode()).hexdigest(),
                            16) % k
                for symbol in curated}
