"""``legacy-001``: the existing parser layer, lifted into the harder codomain.

``symbolic_ai_models.parsers`` produces a ``ParseResult``, not a ``TermGraph``, and
the two are not interchangeable — see :mod:`symbolic_ai_parsers.base` for why
this package supersedes rather than wraps it. But one field of a ``ParseResult``
*does* determine a structure without anything being invented: ``facts``, a list
of ``(predicate, *arguments)`` tuples, which is a term graph one level deep.

So the old layer gets exactly one bridge, and it is a control rather than a
contribution. It answers a question that would otherwise be settled by assertion
in a commit message: given the harder target, does the parser layer that already
exists in this repo beat a five-line layout baseline? The wrapper adds no
heuristics of its own beyond the record/field/list scaffolding every graph in
this curriculum has, so whatever it scores is the old clause splitter's score.

It is expected to lose, and for a reason visible in its own docstring: its
clauses break on commas and its head guess is a guess. Registering it means that
expectation is measured.
"""

from __future__ import annotations

from symbolic_ai_core.data.term_graph import TermGraph
from symbolic_ai_models.parsers import build as build_legacy

from ...base import Parser, register

MAX_NODES = 512


@register("legacy-001", learned=False,
          doc="symbolic_ai_models.parsers' regex clause facts, lifted into a graph.")
class LegacyFactsParser(Parser):
    """``facts`` from the old ``regex`` parser, as ``(record (facts (list ...)))``."""

    def __init__(self) -> None:
        self._inner = build_legacy("regex")

    def parse(self, text: str) -> TermGraph:
        g = TermGraph()
        root = g.add("", "record", -1, 0)
        f = g.add("facts", "field", root, 0)
        lst = g.add("", "list", f, 0)
        try:
            facts = self._inner.parse(text).facts
        except Exception:
            facts = []
        for k, fact in enumerate(facts):
            if len(g) >= MAX_NODES or not fact:
                break
            p = g.add(str(fact[0]).lower(), "pred", lst, k)
            for a, arg in enumerate(fact[1:]):
                if len(g) >= MAX_NODES:
                    break
                is_num = isinstance(arg, (int, float)) and not isinstance(arg, bool)
                g.add(str(arg).lower(), "num" if is_num else "ident", p, a)
        return g
