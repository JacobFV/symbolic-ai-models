"""``lr-001``: SLR(1) shift-reduce, deterministic, shift preferred.

Same grammar as ``cky-001``, no chart. The productions have no nonterminal on
any right-hand side, so the LR(0) item-set automaton *is* the trie of right-hand
sides in :mod:`symbolic_ai_parsers.grammar` — a state is the set of items
sharing a prefix and ``goto`` is "read one more category". This is not an
approximation of LR; for this grammar it is LR.

Two conflicts arise and both get the textbook resolution:

* **Shift/shift.** A token can be read as ``ARG`` or as itself, and both may
  have a transition out of the current state. LR has no such choice because its
  terminals are unambiguous; here the ambiguity is the lexicon's, so it is
  resolved by ``P(category | token)`` — the same lexical model the chart uses.
* **Shift/reduce.** A state can carry a completed production and still have a
  transition out. Resolved by **preferring the shift**, which is yacc's default
  and the reason it is the default: it produces maximal munch, and the longer
  production is nearly always the right one in a templated corpus. The last
  state seen that carried a completed production is remembered, so when the
  shift chain finally dies the parser reduces there rather than failing.

Deterministic and single-pass, so it commits before it has seen the end of the
clause. The prediction, before running it: it should track ``cky-001`` closely
wherever the grammar is unambiguous, and lose exactly where two productions
share a prefix and differ later — which is where a chart earns its cubic time.
If it *matches* the chart everywhere, the grammar has no ambiguity worth
searching and the chart is wasted work.
"""

from __future__ import annotations

from typing import Sequence

from ...base import register
from ...grammar import Derivation
from ..classical import ClassicalParser


@register("lr-001", learned=True,
          doc="SLR(1) shift-reduce over the induced grammar; shift-preferred, no chart.")
class LRParser(ClassicalParser):
    strategy = "deterministic shift-reduce, maximal munch"

    def decode(self, tokens: Sequence[str]) -> list[Derivation]:
        g = self.grammar
        n = len(tokens)
        out: list[Derivation] = []
        i = 0
        while i < n:
            node, j, score = g.root, i, 0.0
            best: tuple[int, object, float] | None = None
            while j < n:
                options = g.step(node, tokens[j])
                if not options:
                    break
                # Shift/shift: take the likelier category. Ties break toward
                # the first option, which is a fixed order, not a hash order.
                node, _cat, sc = max(options, key=lambda o: o[2])
                score += sc
                j += 1
                if node.rules:
                    rule = node.rules[0]           # sorted by log probability
                    total = rule.logp + score
                    if best is None or total > best[2]:
                        best = (j, rule, total)
            if best is None:
                i += 1                              # background token
                continue
            end, rule, _ = best
            out.append(Derivation(start=i, end=int(end), rule=rule))  # type: ignore[arg-type]
            i = int(end)
        return out
