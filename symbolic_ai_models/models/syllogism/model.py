"""symbolic-ai-001, as a predictive model: parse to logical form, then derive.

The agent this is built from answers questions. Making it a *text model* means
it has to do something much harder — say how likely every next token is, and how
likely every hidden node label is — out of the same machinery, with no separate
multiple-choice path to fall back on.

Two mechanisms carry it, and they are the parser's and the engine's:

**Entailment.** The prefix is parsed into categorical statements, the engine
saturates them under conversion, subalternation and the four valid syllogistic
figures, and what comes out is a set of things that *follow*. Where the text is
about to state a conclusion, the derived statement says which tokens come next.

**Structural alignment.** On the graph side the engine's logic is replaced by
the operation underneath unification: two subtrees with the same shape and the
same head are aligned position by position, and a hidden node is predicted from
whatever stands in its place in the other. ``(parent alice frank)`` beside
``(parent alice A)`` says what ``A`` is, and it says so by matching structure
rather than by having seen the word before — which is the whole reason a
symbolic method is worth running on a curriculum that invents its vocabulary
every episode.

This model is **narrow on purpose**. Its fragment is four categorical forms and
two individual forms, and outside that it abstains rather than guessing. Under
the mixture in :mod:`symbolic_ai_models.models.symbolic` an abstention costs it exactly
the back-off, so what its score measures is the value of being right where it
speaks — not a penalty for being quiet everywhere else. Reading which lessons it
declines is as informative as reading where it wins.
"""

from __future__ import annotations

import collections
from typing import Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer, split_words
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes
from ...parsers.primitives import lexicon
from .engine import NO, UNKNOWN, YES, Engine
from ...parsers.primitives.syllogistic import parse_prompt

__all__ = ["SyllogismModel"]


@register("syllogism", doc="Categorical parser plus forward-chaining entailment; aligns subtrees.")
class SyllogismModel(RuleBasedModel):
    """Parse, saturate, answer — and abstain outside the fragment."""

    LEARNED = ("verdict_tokens", "answer_tokens", "n_rules")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.engine = Engine(max_rounds=int(cfg.get("max_rounds", 6)))
        #: how the training text realises each verdict, e.g. yes -> {"yes", "true"}
        self.verdict_tokens: dict[str, collections.Counter] = {}
        #: tokens that follow a line-final position, for the answer slot
        self.answer_tokens: collections.Counter = collections.Counter()
        self.n_rules = 0

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Learn only the *surface* of the verdicts; the logic is not learned.

        The engine's rules are Aristotle's and are written down in
        :mod:`.engine`, not induced. What the training episodes are needed for
        is the vocabulary the answer is spelled with — whether this rendering
        says ``yes``, ``true`` or ``evet`` — which is a fact about the surface
        and has to come from somewhere.
        """
        self.verdict_tokens = {v: collections.Counter() for v in (YES, NO, UNKNOWN)}
        self.answer_tokens = collections.Counter()
        for ep in episodes:
            answer = ep.answer.strip()
            for piece in tok.encode(answer):
                self.answer_tokens[piece] += 1
            verdict = self._verdict_of(answer)
            if verdict is not None:
                for piece in tok.encode(answer):
                    self.verdict_tokens[verdict][piece] += 1
                for piece in tok.encode(" " + answer):
                    self.verdict_tokens[verdict][piece] += 1
        self.n_rules = sum(len(c) for c in self.verdict_tokens.values())

    @staticmethod
    def _verdict_of(answer: str) -> str | None:
        low = answer.strip().lower()
        if low in ("yes", "true", "valid"):
            return YES
        if low in ("no", "false", "invalid"):
            return NO
        if low in ("unknown", "maybe", "undetermined"):
            return UNKNOWN
        return None

    # ---- text ---------------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        """Vote only where the text is about to state the answer.

        The answer sits on the last line, so the position that predicts its
        first token is the one holding the final newline. Everything before that
        is prose the fragment has no opinion about, and voting there would be
        guessing dressed as reasoning.
        """
        assert self.tok is not None
        out: list[Votes] = [ABSTAIN] * len(ids)
        newline = self._last_newline(ids)
        if newline is None:
            return out
        # Only the prefix is decoded, so nothing after the split is ever read.
        prompt = self.tok.decode(ids[:newline + 1])
        parse = parse_prompt(prompt)
        if parse.query is None:
            return out
        answer = self.engine.ask(parse.premises, parse.query)
        votes = self.verdict_tokens.get(answer.value)
        if not votes:
            return out
        # Confidence tracks how much of the prompt the fragment actually covered:
        # a parse that understood two sentences out of nine has not earned much.
        confidence = 0.25 + 0.6 * parse.coverage
        out[newline] = (dict(votes), min(confidence, 0.9))
        return out

    def _last_newline(self, ids: Sequence[int]) -> int | None:
        assert self.tok is not None
        for t in range(len(ids) - 1, -1, -1):
            if "\n" in self.tok.itos[ids[t]]:
                return t
        return None

    # ---- graph --------------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            out[i] = (self._align(view, i), self._type_of(view, i))
        return out

    def _align(self, view: GraphView, i: int) -> Votes:
        """Predict a hidden node from its counterpart in a matching subtree.

        Anti-unification, in effect: find the subtrees that agree with this
        node's parent in head and arity, and read off whatever occupies the same
        slot. Several matches vote together, so a term appearing in that
        position twice outvotes one appearing once.
        """
        parent = view.parent[i]
        if parent < 0:
            return ABSTAIN
        head, arity = view.word(parent), len(view.children(parent))
        if head is None:
            return ABSTAIN
        slot = view.slot[i]

        votes: collections.Counter = collections.Counter()
        for other in range(len(view)):
            if other == parent or view.word(other) != head:
                continue
            kids = view.children(other)
            if len(kids) != arity or slot >= len(kids):
                continue
            candidate = view.labels[kids[slot]]
            if candidate is not None:
                votes[candidate] += 1
        if not votes:
            return ABSTAIN
        # One aligned subtree is already strong evidence on a term tree; two
        # agreeing is close to decisive.
        mass = sum(votes.values())
        return dict(votes), min(0.55 + 0.2 * (mass - 1), 0.92)

    def _type_of(self, view: GraphView, i: int) -> Votes:
        """A node's type from its parent's, which the tree fixes almost entirely."""
        parent = view.parent[i]
        if parent < 0:
            return ABSTAIN
        ptype = view.types[parent]
        if ptype is None:
            return ABSTAIN
        expected = {"str": "char", "record": "field", "app": "field"}.get(ptype)
        if expected:
            return {TYPE_TO_ID[expected]: 1.0}, 0.9
        siblings = [view.types[j] for j in view.siblings(i) if view.types[j]]
        if siblings:
            counts = collections.Counter(TYPE_TO_ID[t] for t in siblings)
            return dict(counts), 0.5
        return ABSTAIN

    def n_symbolic_parameters(self) -> int:
        # The rules are Aristotle's, not fitted, so they are not parameters —
        # but they are the model, and counting only the surface vocabulary would
        # understate it. Both are reported.
        return self.n_rules + len(lexicon.QUANTIFIERS) + 8
