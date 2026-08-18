"""symcontrol-001, as a predictive model: retrieve the evidence, or abstain.

The agent this comes from answers a question by finding the one sentence in the
body that shares enough concepts with it, and refusing to answer when no
sentence clears the evidence threshold. Refusing is the part that matters — it
is a system that would rather say nothing than say something unsupported.

As a text model the same pipeline becomes **predict by retrieval**. The prefix
is split into sentences; the sentence currently being written is scored against
each earlier one by shared concept lemmas, weighted by how discriminative each
concept is inside this episode; the best-matching earlier sentence is aligned
with the current one, and the token that continued it there is what the model
expects to come next. Curriculum episodes state many parallel sentences — object
after object, step after step — so an earlier sentence is very often a genuine
template for the one being written.

The threshold survives the port intact, and so does what it is for. When no
earlier sentence clears it the model returns :data:`~symbolic_ai_models.models.symbolic.ABSTAIN`,
which under the mixture means falling back to the shared prior rather than
committing to an unsupported guess. That makes abstention *measurable* here in a
way it is not for a network: ``abstention_rate`` reports how often this model
declined, and its accuracy is what it achieved on the rest.
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes
from .answering import EVIDENCE_THRESHOLD, concepts

__all__ = ["EvidenceModel"]


@register("evidence-001", doc="Retrieval by concept overlap, with a real abstention threshold.")
class EvidenceModel(RuleBasedModel):
    """Find the earlier sentence this one is echoing; continue it the same way."""

    LEARNED = ("document_frequency", "n_documents", "threshold")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.threshold = float(cfg.get("threshold", EVIDENCE_THRESHOLD))
        self.document_frequency: collections.Counter = collections.Counter()
        self.n_documents = 0
        self.asked = 0
        self.abstained = 0

    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Learn only how discriminative each concept is.

        The source weighted a shared concept by how rare it was *within the
        body*. Across a whole curriculum a corpus-level document frequency is
        the better estimate of the same quantity, and it is the only thing
        carried between episodes — the retrieval itself is always within the
        episode being read.
        """
        self.document_frequency = collections.Counter()
        self.n_documents = len(episodes)
        for ep in episodes:
            self.document_frequency.update(set(concepts(ep.text)))
        self.asked = self.abstained = 0

    def _weight(self, concept: str) -> float:
        """Inverse document frequency, floored at one so nothing is worthless."""
        df = self.document_frequency.get(concept, 0)
        return 1.0 + math.log((self.n_documents + 1) / (df + 1))

    # ---- text ---------------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        """Align the running line against the best-matching earlier line.

        Lines are accumulated as the prefix advances, so the candidate set at
        position ``t`` contains only lines that finished before ``t``.
        """
        assert self.tok is not None
        out: list[Votes] = [ABSTAIN] * len(ids)
        pieces = [self.tok.itos[i] for i in ids]

        # (tokens of the line, its concept set), for lines already complete
        done: list[tuple[list[int], set[str], str]] = []
        current: list[int] = []
        current_text: list[str] = []

        for t in range(len(ids)):
            piece = pieces[t]
            current.append(ids[t])
            current_text.append(piece)
            if "\n" in piece:
                text = "".join(current_text)
                done.append((list(current), set(concepts(text)), text))
                current, current_text = [], []
                continue

            self.asked += 1
            vote = self._align(current, current_text, done)
            if vote is ABSTAIN:
                self.abstained += 1
            else:
                out[t] = vote
        return out

    def _align(self, current: list[int], current_text: list[str],
               done: list[tuple[list[int], set[str], str]]) -> Votes:
        """Score earlier lines, take the best, and read off its next token."""
        if not done or not current:
            return ABSTAIN
        query = set(concepts("".join(current_text)))
        if not query:
            return ABSTAIN

        best_score, best = 0.0, None
        for tokens_, sentence_concepts, _ in done:
            if len(tokens_) <= len(current):
                continue
            overlap = query & sentence_concepts
            score = 2.0 * sum(self._weight(c) for c in overlap)
            # A line that also matches token for token is a far better template
            # than one that merely shares vocabulary.
            prefix_match = sum(1 for a, b in zip(current, tokens_) if a == b)
            score += 0.35 * prefix_match
            if score > best_score:
                best_score, best = score, tokens_

        # The threshold is tested against the evidence alone, exactly as in the
        # source: it decides whether any line is relevant, not which is best.
        if best is None or best_score < self.threshold:
            return ABSTAIN
        nxt = best[len(current)]
        return {nxt: 1.0}, min(0.2 + 0.12 * best_score, 0.85)

    # ---- graph --------------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        """Retrieve the most similar node elsewhere in the graph and copy it.

        Similarity is over structural context rather than over words, since a
        node has no prose around it: same parent head, same slot, same depth,
        same arity. It is the same "find the best-supported evidence, or
        abstain" rule, applied to a tree.
        """
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            self.asked += 1
            votes = self._retrieve(view, i)
            if votes is ABSTAIN:
                self.abstained += 1
            out[i] = (votes, self._type_vote(view, i))
        return out

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        """The same retrieval, kept as *which node* rather than which symbol.

        `_retrieve` already finds the best-supported node and then throws the
        node away, summing its overlap into a vote for that node's label. The
        binding is what was computed; the symbol was a lossy projection of it,
        and one that cannot express an answer the vocabulary has no id for.
        """
        out: dict[int, Votes] = {}
        for i in view.hidden:
            signature = self._signature(view, i)
            scored: dict[int, float] = {}
            best = 0.0
            for j in range(len(view)):
                if j == i or view.labels[j] is None:
                    continue
                overlap = len(signature & self._signature(view, j))
                if overlap >= 2:
                    scored[j] = float(overlap)
                    best = max(best, float(overlap))
            if scored and best >= 2.0:
                out[i] = (scored, min(0.2 + 0.15 * best, 0.8))
        return out

    def _retrieve(self, view: GraphView, i: int) -> Votes:
        signature = self._signature(view, i)
        scored: collections.Counter = collections.Counter()
        best = 0.0
        for j in range(len(view)):
            if j == i or view.labels[j] is None:
                continue
            overlap = len(signature & self._signature(view, j))
            if overlap >= 2:
                scored[view.labels[j]] += overlap
                best = max(best, float(overlap))
        if not scored or best < 2.0:
            return ABSTAIN
        return dict(scored), min(0.2 + 0.15 * best, 0.8)

    @staticmethod
    def _signature(view: GraphView, i: int) -> set:
        p = view.parent[i]
        return {
            ("slot", view.slot[i]),
            ("depth", min(view.depth[i], 6)),
            ("arity", len(view.children(i))),
            ("ptype", view.types[p] if p >= 0 and view.types[p] else "ROOT"),
            ("phead", view.labels[p] if p >= 0 else None),
        }

    def _type_vote(self, view: GraphView, i: int) -> Votes:
        peers = [view.types[j] for j in view.siblings(i) if view.types[j]]
        if not peers:
            return ABSTAIN
        counts = collections.Counter(TYPE_TO_ID[t] for t in peers)
        return dict(counts), min(len(peers) / (len(peers) + 2.0), 0.8)

    @property
    def abstention_rate(self) -> float:
        """How often this model declined. Reported because it is a result."""
        return self.abstained / self.asked if self.asked else 0.0

    def n_symbolic_parameters(self) -> int:
        return len(self.document_frequency) + 1
