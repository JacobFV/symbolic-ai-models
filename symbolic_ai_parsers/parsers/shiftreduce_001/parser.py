"""``shiftreduce-001``: greedy transition-based, averaged-perceptron oracle.

The third search over the same grammar, and the one that learns *how to search*
rather than being told. At each step the parser is in a trie state with a
lookahead token and must choose one of three actions — shift the token as
``ARG``, shift it as itself, or reduce the completed production it is sitting on
— and an averaged perceptron scores them from features of the state and the
tokens around it.

Trained by imitation: every clause in the treebank determines its own gold
action sequence, since the rule fixes which positions are arguments and where
the reduce falls. Standard structured-perceptron updates, averaged over
iterations, which is the classical remedy for the last update dominating.

Why it is here rather than being a fourth flavour of the same thing: ``cky-001``
searches exhaustively with a fixed scoring function, ``lr-001`` searches not at
all with a fixed scoring function, and this one searches not at all with a
*fitted* one. Those are the three corners that matter, and the interesting
question is whether a learned oracle recovers what the chart gets by searching —
which is the claim transition-based parsing has always made.

What refutes it: if it does not beat ``lr-001``, the features carry nothing the
lexical model did not already have, and the perceptron is decoration on a
maximal-munch parser.
"""

from __future__ import annotations

import collections
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode

from ...base import register
from ...grammar import Derivation
from ..classical import ClassicalParser

#: Passes over the treebank. Three is the usual number for an averaged
#: perceptron on a corpus this size and it was not swept.
EPOCHS = 3


def _features(state_depth: int, has_rule: bool, token: str, seen: bool,
              nxt: str, action: str) -> list[str]:
    """Sparse, hashed by string. Deliberately few: this is a baseline."""
    return [f"{action}|d={min(state_depth, 6)}",
            f"{action}|r={int(has_rule)}",
            f"{action}|t={token}",
            f"{action}|s={int(seen)}",
            f"{action}|n={nxt}",
            f"{action}|d={min(state_depth, 6)},s={int(seen)}"]


@register("shiftreduce-001", learned=True,
          doc="Greedy transition-based parse over the induced grammar, perceptron oracle.")
class ShiftReduceParser(ClassicalParser):
    strategy = "greedy transitions, averaged perceptron"

    def __init__(self) -> None:
        super().__init__()
        self._w: dict[str, float] = collections.defaultdict(float)

    # ---- the oracle -----------------------------------------------------
    def train(self, episodes: Sequence[Episode]) -> None:
        w: dict[str, float] = collections.defaultdict(float)
        acc: dict[str, float] = collections.defaultdict(float)
        n = 0
        for _ in range(EPOCHS):
            for sample in self.treebank.samples:
                gold = self._gold_actions(sample)
                if gold is None:
                    continue
                for feats_by_action, right in gold:
                    n += 1
                    pred = max(feats_by_action,
                               key=lambda a: sum(w[f] for f in feats_by_action[a]))
                    if pred != right:
                        for f in feats_by_action[right]:
                            w[f] += 1.0
                        for f in feats_by_action[pred]:
                            w[f] -= 1.0
                    for f, v in w.items():
                        acc[f] += v
        self._w = ({f: v / n for f, v in acc.items()} if n else {})

    def _gold_actions(self, sample):
        """``[(features per action, the right action)]`` for one clause."""
        node = self.grammar.root
        args = {i for i, _ in sample.arg_slots}
        out = []
        for i, token in enumerate(sample.tokens):
            cat = "ARG" if i in args else token
            nxt = sample.tokens[i + 1] if i + 1 < len(sample.tokens) else ""
            seen = token in self.grammar.bg_logp
            opts = self._options(node, token, nxt, seen)
            right = "shift_arg" if cat == "ARG" else "shift_lit"
            if right not in opts:
                return None
            out.append((opts, right))
            step = node.kids.get(cat)
            if step is None:
                return None
            node = step
        nxt = ""
        opts = self._options(node, "", nxt, True)
        if "reduce" in opts:
            out.append((opts, "reduce"))
        return out

    def _options(self, node, token: str, nxt: str, seen: bool) -> dict[str, list[str]]:
        depth_marker = len(node.kids)
        opts: dict[str, list[str]] = {}
        if node.rules:
            opts["reduce"] = _features(depth_marker, True, token, seen, nxt, "reduce")
        if token and "ARG" in node.kids:
            opts["shift_arg"] = _features(depth_marker, bool(node.rules), token,
                                          seen, nxt, "shift_arg")
        if token and token in node.kids:
            opts["shift_lit"] = _features(depth_marker, bool(node.rules), token,
                                          seen, nxt, "shift_lit")
        return opts

    def _score(self, feats: list[str]) -> float:
        return sum(self._w.get(f, 0.0) for f in feats)

    # ---- the parse ------------------------------------------------------
    def decode(self, tokens: Sequence[str]) -> list[Derivation]:
        g = self.grammar
        n = len(tokens)
        out: list[Derivation] = []
        i = 0
        while i < n:
            node, j = g.root, i
            emitted = False
            while j <= n:
                token = tokens[j] if j < n else ""
                nxt = tokens[j + 1] if j + 1 < n else ""
                opts = self._options(node, token, nxt, token in g.bg_logp)
                if not opts:
                    break
                action = max(opts, key=lambda a: self._score(opts[a]))
                if action == "reduce":
                    out.append(Derivation(start=i, end=j, rule=node.rules[0]))
                    i, emitted = j, True
                    break
                cat = "ARG" if action == "shift_arg" else token
                node = node.kids[cat]
                j += 1
            if not emitted:
                i += 1
        return out
