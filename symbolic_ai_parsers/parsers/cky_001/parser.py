"""``cky-001``: exhaustive chart parse, Viterbi best derivation of each clause.

The classical statistical parser, and the baseline the other two searches are
read against. The grammar's productions are flat, so the chart collapses from
the usual ``O(n^3)`` triangle to a linear Viterbi over start positions: a
segment is a sequence of clauses and background tokens, and

    best[i] = max( background(t_i) + best[i+1],
                   max over rules r matching t_i..t_j of  logP(r) + lex + best[j] )

Every derivation is considered, which is exactly what distinguishes it from
``lr-001``: nothing is committed to before the end of the segment.

The background term is what lets a partial parse be compared with a full one on
one scale, and it is a fitted unigram rather than a skip penalty someone chose.
A hand-set penalty here would be a single free parameter sitting underneath
every classical row at once, which is the kind of harness decision this repo has
repeatedly found to outweigh the thing it was trying to measure.
"""

from __future__ import annotations

from typing import Sequence

from ...base import register
from ...grammar import Derivation
from ..classical import ClassicalParser


@register("cky-001", learned=True,
          doc="Chart parse over a PCFG induced from an aligned treebank; Viterbi.")
class CKYParser(ClassicalParser):
    strategy = "exhaustive chart, Viterbi"

    def decode(self, tokens: Sequence[str]) -> list[Derivation]:
        n = len(tokens)
        if not n:
            return []
        g = self.grammar
        best = [0.0] * (n + 1)
        back: list[tuple[int, object] | None] = [None] * (n + 1)
        for i in range(n - 1, -1, -1):
            score = g.background(tokens[i]) + best[i + 1]
            choice: tuple[int, object] | None = None
            for end, rule, lex in g.matches(tokens, i):
                if end <= i:
                    continue
                cand = rule.logp + lex + best[end]
                if cand > score:
                    score, choice = cand, (end, rule)
            best[i], back[i] = score, choice

        out: list[Derivation] = []
        i = 0
        while i < n:
            step = back[i]
            if step is None:
                i += 1
                continue
            end, rule = step
            out.append(Derivation(start=i, end=int(end), rule=rule))  # type: ignore[arg-type]
            i = int(end)
        return out
