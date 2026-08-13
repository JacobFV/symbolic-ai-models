"""Shared skeleton for the classical parsers. One grammar, three searches.

Nothing here is registered; ``cky_001``, ``lr_001`` and ``shiftreduce_001`` are
packages beside this one and each supplies exactly one method, :meth:`decode`.
Everything else — inducing the treebank, inducing the grammar, segmenting the
prompt, assembling the record — is identical between them **on purpose**, so
that the difference between a chart, a deterministic table and a learned oracle
is the only thing the table is measuring.

These are the first parsers in the package that *compose* an answer. Every other
one either emits a fixed structure or copies a training graph and substitutes
words, which is why `RESEARCH_LOG.md` recorded "nothing has tried to build a
graph rather than retrieve one" as the open question. They are also the ones
with an honest, visible ceiling: the treebank only ever recovers clause-level
spans, so record/field/list come from block layout and only the clause is
parsed. That cap is in the code, not in the interpretation of the scores.

What would refute the whole family, written before the numbers: if none of the
three beats ``bracket-001``, which builds the same scaffolding and guesses the
head of every clause to be its first word, then the induced grammar contributes
nothing and the scaffolding was the whole score. That is a live possibility —
``bracket-001`` already clears the type floor.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import Graph

from ...base import Parser
from ...features import words_of
from ...grammar import Derivation, Grammar, assemble
from ...treebank import Treebank, blocks, segments


class ClassicalParser(Parser):
    """Induce a grammar from aligned clauses; parse each clause; assemble."""

    #: what the row means, printed by ``describe``
    strategy: str = "?"

    def __init__(self) -> None:
        self.grammar = Grammar()
        self.treebank = Treebank()

    def fit(self, episodes: Sequence[Episode]) -> None:
        self.treebank = Treebank.build(episodes)
        self.grammar = Grammar.induce(self.treebank)
        self.train(episodes)

    def train(self, episodes: Sequence[Episode]) -> None:
        """Anything a variant needs beyond the grammar. Most need nothing."""

    # ---- the one method that differs -----------------------------------
    def decode(self, tokens: Sequence[str]) -> list[Derivation]:
        raise NotImplementedError

    # ---- shared pipeline ------------------------------------------------
    def parse(self, text: str) -> Graph:
        if not self.grammar.rules:
            return Graph()
        blks = blocks(text)
        by_block: dict[int, list[tuple[Sequence[str], list[Derivation]]]] = {}
        for seg in segments(text):
            ds = self.decode(seg.tokens)
            if ds:
                by_block.setdefault(seg.block, []).append((seg.tokens, ds))
        return assemble([(h, ()) for h, _ in blks], by_block, _field_label)

    def n_parameters(self) -> int:
        return self.grammar.n_parameters()

    def describe(self) -> str:
        return (f"{self.name}: {self.strategy}; {len(self.grammar.rules):,} rules "
                f"from {self.treebank.coverage:.0%} clause coverage")


def _field_label(header: str) -> str:
    return "_".join(words_of(header)[:6]).lower()
