"""``retrieve-001``: hand back the graph of the most similar training prompt.

Memorisation, with no parsing in it at all, and it is registered because it is
the control that could embarrass every other row in the table. A templated
corpus rewards recall enormously: if a lesson's graph barely changes between
seeds, then finding the right lesson *is* most of the answer, and a parser that
scores well may have learned to look things up rather than to read.

So it is deliberately given the strongest lookup signal — word identity — and no
ability to use it for anything else. Whatever ``template-001`` scores above this
row is the part attributable to reading the episode rather than recognising the
lesson. Whatever it scores below is worse than not parsing.

It is also the sharpest cross-language prediction in the package: word identity
is the thing translation destroys, so this row should fall furthest. If it does
not, the languages share more surface than the README claims and every other
cross-language number here needs re-reading.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.graph import Graph

from ...base import Parser, register
from ...retrieval import WordIndex


@register("retrieve-001", learned=True,
          doc="Nearest training prompt by word overlap; emit its graph verbatim.")
class RetrieveParser(Parser):
    """No structure is built. The graph is copied from a remembered episode."""

    def __init__(self) -> None:
        self._index = WordIndex()
        self._graphs: list[Graph] = []
        self._lessons: list[str] = []
        self.last_lesson: str = ""

    def fit(self, episodes: Sequence[Episode]) -> None:
        eps = list(episodes)
        self._index.fit([ep.prompt for ep in eps])
        self._graphs = [ep.graph for ep in eps]
        self._lessons = [ep.lesson_id for ep in eps]

    def parse(self, text: str) -> Graph:
        i = self._index.query(text)
        if i < 0:
            self.last_lesson = ""
            return Graph()
        self.last_lesson = self._lessons[i]
        return self._graphs[i]

    def n_parameters(self) -> int:
        return self._index.n_parameters()
