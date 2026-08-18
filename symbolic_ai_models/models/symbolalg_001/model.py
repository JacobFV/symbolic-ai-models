"""base-symbolic-002, as a predictive model: read facts, then expect them again.

The parser this is built on is weak on purpose, and it emits *both* readings of
a clause because it genuinely does not know which token is the predicate —
``Agent at (0, 3)`` yields ``(at agent 0 3)`` and ``(agent at 0 3)``. Its author's
point was that the ambiguity belongs to the learner rather than to the
interface. Here that lands as a prediction rule: keep both readings, let the
evidence decide, and vote for whichever a template completion supports.

The mechanism is **template analogy within one episode**. Curriculum prose is
extremely repetitive inside a single episode — a scene states object after
object in the same shape, a proof states step after step in the same shape — so
the fact patterns already parsed out of the prefix say what the rest of the
sentence must look like. The model abstracts each parsed fact into a template by
replacing its arguments with holes, and predicts the next token by finding the
template the current partial clause is matching and reading off what filled that
slot before.

Nothing about this is fitted across episodes: the analogy is drawn *inside* the
episode being read, from text the model has already seen. What training does
supply is which templates are worth trusting, so an episode shaped unlike
anything in training is treated with less confidence rather than the same.
"""

from __future__ import annotations

import collections
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes
from ...parsers.primitives.clauses import clauses, facts_from_text, tokens

__all__ = ["SymbolAlgebraModel"]

HOLE = "\x00"


@register("symbolalg-001", doc="Ambiguity-preserving fact parser; predicts by template analogy.")
class SymbolAlgebraModel(RuleBasedModel):
    """Parse the prefix into facts; expect the next fact to rhyme with them."""

    LEARNED = ("templates", "slots", "max_context")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_context = int(cfg.get("max_context", 6))
        #: template -> how often the training text continued it that way
        self.templates: dict[tuple, collections.Counter] = {}
        #: (parent label, slot) -> labels, over training graphs
        self.slots: dict[tuple, collections.Counter] = {}

    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.templates = collections.defaultdict(collections.Counter)
        self.slots = collections.defaultdict(collections.Counter)
        for ep in episodes:
            for clause in clauses(ep.text):
                ts = tokens(clause)
                for k in range(1, min(self.max_context, len(ts))):
                    for i in range(len(ts) - k):
                        key = self._template(ts[i:i + k])
                        self.templates[key][self._word(ts[i + k], tok)] += 1
            g = ep.graph
            for i, label in enumerate(g.labels):
                p = g.parent[i]
                if label and p >= 0:
                    self.slots[(g.labels[p], g.slot[i])][tok.label_id(label)] += 1

    @staticmethod
    def _template(ts: Sequence) -> tuple:
        """Abstract a token run: numbers become holes, words stay themselves.

        Numbers are what vary between the repetitions of a pattern — the
        coordinates change, the object names change, the shape of the sentence
        does not — so holing them out is what makes two clauses the same
        template.
        """
        return tuple(HOLE if not isinstance(t, str) else t.lower() for t in ts)

    @staticmethod
    def _word(t, tok: SymbolTokenizer) -> int:
        return tok.label_id(str(t))

    # ---- text ---------------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        """Match the running clause against templates seen earlier and in training.

        The within-episode index is rebuilt as the prefix grows, so a template
        first seen at token 40 is available from token 40 onward and not before.
        """
        assert self.tok is not None
        out: list[Votes] = [ABSTAIN] * len(ids)
        words = [self.tok.itos[i].strip() for i in ids]
        local: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        run: list[str] = []

        for t, word in enumerate(words):
            if word:
                run.append(word.lower())
                run = run[-self.max_context:]
            # Everything below reads `run`, which holds only tokens <= t.
            votes, seen = collections.Counter(), 0
            for k in range(min(len(run), self.max_context), 0, -1):
                key = tuple(HOLE if _is_number(w) else w for w in run[-k:])
                for table, weight in ((local.get(key), 2.0),
                                      (self.templates.get(key), 1.0)):
                    if table:
                        for symbol, count in table.items():
                            votes[symbol] += count * weight * k
                        seen += sum(table.values())
                if votes:
                    break
            if votes:
                out[t] = (dict(votes), min(seen / (seen + 6.0), 0.85))
            # Only after voting is the observed continuation indexed, so a
            # position never learns from the token it was asked to predict.
            if t + 1 < len(words) and run:
                nxt = words[t + 1].strip()
                if nxt:
                    for k in range(1, min(len(run), self.max_context) + 1):
                        key = tuple(HOLE if _is_number(w) else w for w in run[-k:])
                        local[key][ids[t + 1]] += 1
        return out

    # ---- graph --------------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            out[i] = (self._label(view, i), self._type(view, i))
        return out

    def _label(self, view: GraphView, i: int) -> Votes:
        """The slot this node fills, read from the episode first, training second."""
        p = view.parent[i]
        head = view.word(p) if p >= 0 else None
        votes: collections.Counter = collections.Counter()

        if head is not None:
            for other in range(len(view)):
                if other == p or view.word(other) != head:
                    continue
                kids = view.children(other)
                if view.slot[i] < len(kids):
                    peer = view.labels[kids[view.slot[i]]]
                    if peer is not None:
                        votes[peer] += 3
            for symbol, count in (self.slots.get((head, view.slot[i])) or {}).items():
                votes[symbol] += count
        if not votes:
            return ABSTAIN
        mass = sum(votes.values())
        return dict(votes), min(mass / (mass + 4.0), 0.85)

    def _type(self, view: GraphView, i: int) -> Votes:
        peers = [view.types[j] for j in view.siblings(i) if view.types[j]]
        if not peers:
            return ABSTAIN
        counts = collections.Counter(TYPE_TO_ID[t] for t in peers)
        return dict(counts), min(len(peers) / (len(peers) + 2.0), 0.8)

    def n_symbolic_parameters(self) -> int:
        return (sum(len(v) for v in self.templates.values())
                + sum(len(v) for v in self.slots.values()))


def _is_number(word: str) -> bool:
    try:
        float(word)
    except ValueError:
        return False
    return True
