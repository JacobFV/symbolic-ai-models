"""``prior-001``: emit one fixed training graph, whatever the text says.

The floor, registered as a parser so that it prints as a row rather than as a
column of a table nobody reads twice. It is text-blind by construction, so
whatever it scores is the part of a parser's score that is arithmetic about how
alike these graphs are.

It differs from :mod:`symbolic_ai_parsers.floors` in one way that matters: the
floor picks a *different* constant for each metric, which is the strongest
text-blind predictor and therefore the right thing to compare against. This
parser has to emit one graph, so it commits to the constant that maximises
``bracket_f1`` and reports its other five numbers honestly, whatever they are.
The row will therefore sit at or below the floor line everywhere except
``bracket_f1``, and that gap is a useful thing to see: it is the price of having
to answer with one object.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.graph import Graph

from ...base import Parser, register
from ...floors import fit_floor


@register("prior-001", learned=True,
          doc="One fixed training graph, chosen to maximise bracket F1. Ignores the text.")
class PriorParser(Parser):
    """The best text-blind constant, made visible as a table row."""

    SELECT = "bracket_f1"

    def __init__(self) -> None:
        self._graph = Graph()
        self._source = ""

    def fit(self, episodes: Sequence[Episode]) -> None:
        floor = fit_floor(episodes)
        self._graph = floor.predict(self.SELECT)
        self._source = floor.sources.get(self.SELECT, "")

    def parse(self, text: str) -> Graph:
        return self._graph

    def n_parameters(self) -> int:
        return len(self._graph)

    def describe(self) -> str:
        return f"{self.name}: constant graph from {self._source or '(unfitted)'}"
