"""Decision-list induction (CN2/RIPPER-flavoured), with an MDL stopping rule.

Ported verbatim from symbolic-ai-001 (`induction/dlist.py`).


Greedy separate-and-conquer: repeatedly grow the conjunction of literals with
the best information gain on the examples not yet covered, emit it as a rule,
remove what it covers, continue. Stop when no rule pays for its own description
length.

Everything is discrete and countable — no gradients, no embeddings, no
floating-point parameters other than the two thresholds below. The learned
object is a short, readable program:

    IF rel:goal(>0,==0) AND ¬rel:wall(=1,==0) THEN RIGHT
    ELSE IF ...
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Hashable, Iterable, Sequence

from .facts import FactSet, Literal

__all__ = ["Rule", "DecisionList", "induce_decision_list"]


@dataclass
class Rule:
    conditions: tuple[Literal, ...]
    label: Hashable
    support: int = 0
    correct: int = 0

    def matches(self, fs: FactSet) -> bool:
        return all(c.holds(fs) for c in self.conditions)

    @property
    def confidence(self) -> float:
        return self.correct / max(1, self.support)

    def cost(self) -> int:
        """Description length of the rule, in bits-ish units."""
        return 2 + sum(c.cost() for c in self.conditions)

    def __repr__(self) -> str:
        cond = " ∧ ".join(repr(c) for c in self.conditions) or "true"
        return f"IF {cond} THEN {self.label}  [{self.correct}/{self.support}]"


@dataclass
class DecisionList:
    rules: list[Rule] = field(default_factory=list)
    default: Hashable = None
    literals_considered: int = 0

    def predict(self, fs: FactSet) -> Hashable:
        for r in self.rules:
            if r.matches(fs):
                return r.label
        return self.default

    def explain(self, fs: FactSet) -> tuple[Hashable, Rule | None]:
        for r in self.rules:
            if r.matches(fs):
                return r.label, r
        return self.default, None

    def cost(self) -> int:
        return sum(r.cost() for r in self.rules) + 2

    @property
    def n_parameters(self) -> int:
        """Every constraint and label is one discrete parameter. This is the
        honest 'model size' to compare against a neural parameter count."""
        return sum(len(r.conditions) + 1 for r in self.rules) + 1

    def __repr__(self) -> str:
        body = "\n".join(f"  {r}" for r in self.rules)
        return f"DecisionList({len(self.rules)} rules, {self.n_parameters} params)\n{body}\n  ELSE {self.default}"


def _entropy(counts: Counter) -> float:
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


def induce_decision_list(
    examples: Sequence[tuple[FactSet, Hashable]],
    literals: Sequence[Literal],
    *,
    max_conditions: int = 3,
    min_support: int = 2,
    min_confidence: float = 0.6,
    max_rules: int = 40,
    beam: int = 4,
    mdl: bool = True,
) -> DecisionList:
    """Induce an ordered rule list. Five integer/threshold knobs, no gradients."""
    remaining = list(examples)
    dl = DecisionList(literals_considered=len(literals))
    labels_all = Counter(l for _, l in examples)
    dl.default = labels_all.most_common(1)[0][0] if labels_all else None

    while remaining and len(dl.rules) < max_rules:
        rule = _grow_rule(remaining, literals, max_conditions=max_conditions,
                          min_support=min_support, beam=beam)
        if rule is None or rule.confidence < min_confidence:
            break
        if mdl:
            # a rule must save more bits than it costs to state
            covered = [(fs, y) for fs, y in remaining if rule.matches(fs)]
            before = _entropy(Counter(y for _, y in remaining)) * len(covered)
            after = _entropy(Counter(y for _, y in covered)) * len(covered)
            if before - after < rule.cost():
                break
        dl.rules.append(rule)
        remaining = [(fs, y) for fs, y in remaining if not rule.matches(fs)]

    if remaining:
        dl.default = Counter(y for _, y in remaining).most_common(1)[0][0]
    return dl


def _grow_rule(
    examples: Sequence[tuple[FactSet, Hashable]],
    literals: Sequence[Literal],
    *,
    max_conditions: int,
    min_support: int,
    beam: int,
) -> Rule | None:
    """Beam search over conjunctions, scored by information gain per unit cost."""
    # pre-evaluate literals once on this example set
    hits = {l: [l.holds(fs) for fs, _ in examples] for l in literals}
    ys = [y for _, y in examples]
    base_h = _entropy(Counter(ys))
    n = len(examples)

    def score(mask: list[bool]) -> tuple[float, Counter, int]:
        idx = [i for i, m in enumerate(mask) if m]
        if len(idx) < min_support:
            return -1e9, Counter(), 0
        c = Counter(ys[i] for i in idx)
        gain = (base_h - _entropy(c)) * (len(idx) / n)
        return gain, c, len(idx)

    beams: list[tuple[float, tuple[Literal, ...], list[bool]]] = [(0.0, (), [True] * n)]
    best: tuple[float, tuple[Literal, ...], Counter, int] | None = None
    for _ in range(max_conditions):
        nxt: list[tuple[float, tuple[Literal, ...], list[bool]]] = []
        for _, conds, mask in beams:
            for l in literals:
                if l in conds:
                    continue
                m2 = [a and b for a, b in zip(mask, hits[l])]
                s, c, sup = score(m2)
                if s <= 0:
                    continue
                purity = max(c.values()) / max(1, sup)
                adj = s * purity
                nxt.append((adj, conds + (l,), m2))
                if best is None or adj > best[0]:
                    best = (adj, conds + (l,), c, sup)
        if not nxt:
            break
        nxt.sort(key=lambda t: -t[0])
        beams = nxt[:beam]

    if best is None:
        return None
    _, conds, counts, sup = best
    label, correct = counts.most_common(1)[0]
    return Rule(conditions=conds, label=label, support=sup, correct=correct)
