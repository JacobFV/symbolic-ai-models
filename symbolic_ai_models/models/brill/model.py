"""Transformation-based error-driven learning, after Brill (1995).

The method that carried part-of-speech tagging for a decade, and the one whose
shape is genuinely unlike everything else here. A decision list asks a question
about the *input* and reads off an answer. Brill's learner starts from a
baseline guess and then learns an ordered list of **corrections**::

    guess the commonest label for this context
    then: if the parent's head is `parent` and the slot is 1, change it to the peer's label
    then: if the type is `field`, change it to the commonest field name
    ...

Each rule is chosen to repair more errors than it causes, greedily, on the
output of every rule before it. So the hypothesis is a *program over its own
predictions* rather than a classifier, and later rules exist only because
earlier ones were wrong — which makes the learned list a readable record of what
the baseline got wrong and in what order it mattered.

Two properties make it worth its place here. It is **error-driven**, so it
spends its capacity where the baseline actually fails rather than modelling the
easy majority again; and it is **interpretable in sequence**, which is a
different and often more useful thing than a decision list's interpretability —
you can read the corrections as a narrative about the data.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["BrillModel", "Transformation"]

#: Where a corrected label may be read from. Same pointer idea as elsewhere —
#: naming a symbol would not survive the next episode's invented vocabulary.
SOURCES = ("peer", "parent", "prev_sibling", "first_child")


@dataclass(frozen=True)
class Transformation:
    """``if <condition> then take the label from <source>``."""

    feature: str
    value: Any
    source: str
    fixed: int = 0
    broke: int = 0

    @property
    def net(self) -> int:
        return self.fixed - self.broke

    def __repr__(self) -> str:
        return (f"IF {self.feature}={self.value!r} THEN label := {self.source}"
                f"   [+{self.fixed} -{self.broke}]")


@register("brill", doc="Transformation-based learning: a baseline plus ordered error corrections.")
class BrillModel(RuleBasedModel):
    """Guess, then learn the corrections, in the order they pay off."""

    LEARNED = ("transformations", "type_transformations", "baseline_type",
               "baseline_label", "max_rules")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_rules = int(cfg.get("max_rules", 20))
        self.min_net = int(cfg.get("min_net", 3))
        # Set from measured wall clock, never from eval lift. The cap bounds
        # runtime and nothing else, so the rule is "the largest value fitting
        # 300s on the full curriculum", well under synth's 1,500s which this
        # sweep already tolerates. The old value was a guessed constant.
        # Uncapped: 200s over all 179 lessons, comfortably inside budget.
        self.max_examples = int(cfg.get("max_examples", 200_000))
        self.transformations: list[Transformation] = []
        self.type_transformations: list[Transformation] = []
        self.baseline_type: dict[str, int] = {}
        self.baseline_label: dict[tuple, int] = {}

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        examples = []
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, type_id) in targets.items():
                examples.append((view, node, label_id, type_id))
        if len(examples) > self.max_examples:
            step = len(examples) / self.max_examples
            examples = [examples[int(i * step)] for i in range(self.max_examples)]

        self._fit_baseline(examples)
        self.transformations = self._learn_rules(
            examples, target=2, guess=self._guess_label, apply=_source_label)
        self.type_transformations = self._learn_rules(
            examples, target=3, guess=self._guess_type, apply=_source_type)

    def _fit_baseline(self, examples: Sequence[tuple]) -> None:
        """The starting guess: commonest type per parent type, commonest label
        per (parent head, slot). Deliberately weak — the corrections are the
        model, and a strong baseline would leave them nothing to learn from."""
        types: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        labels: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, node, label_id, type_id in examples:
            if type_id >= 0:
                types[_parent_type(view, node)][type_id] += 1
            if label_id >= 0:
                labels[_label_key(view, node)][label_id] += 1
        self.baseline_type = {k: c.most_common(1)[0][0] for k, c in types.items()}
        self.baseline_label = {k: c.most_common(1)[0][0] for k, c in labels.items()}

    def _learn_rules(self, examples: Sequence[tuple], *, target: int,
                     guess: Callable, apply: Callable) -> list[Transformation]:
        """Greedy: repeatedly take the correction with the best net repair.

        Scored on the *current* predictions, so every rule after the first is
        chosen in the knowledge of what its predecessors already fixed. That
        ordering is the algorithm; scoring them all against the baseline would
        make it an ensemble of independent rules and a different method.
        """
        current = [guess(view, node) for view, node, _, _ in examples]
        rules: list[Transformation] = []

        for _ in range(self.max_rules):
            tally: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0])
            for i, (view, node, *truth) in enumerate(examples):
                gold = truth[target - 2]
                if gold < 0:
                    continue
                for feature, value in _conditions(view, node):
                    for source in SOURCES:
                        proposed = apply(view, node, source)
                        if proposed is None or proposed == current[i]:
                            continue
                        slot = tally[(feature, value, source)]
                        slot[0 if proposed == gold else 1] += 1

            best, best_net = None, self.min_net - 1
            for (feature, value, source), (fixed, broke) in tally.items():
                if fixed - broke > best_net:
                    best_net = fixed - broke
                    best = Transformation(feature, value, source, fixed, broke)
            if best is None:
                break

            rules.append(best)
            for i, (view, node, *_) in enumerate(examples):
                if (best.feature, best.value) in _conditions(view, node):
                    proposed = apply(view, node, best.source)
                    if proposed is not None:
                        current[i] = proposed
        return rules

    # ---- prediction ---------------------------------------------------
    def _guess_label(self, view: GraphView, node: int) -> int | None:
        return self.baseline_label.get(_label_key(view, node))

    def _guess_type(self, view: GraphView, node: int) -> int | None:
        return self.baseline_type.get(_parent_type(view, node))

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            out[i] = (
                _vote(self._run(view, i, self._guess_label(view, i),
                                self.transformations, _source_label)),
                _vote(self._run(view, i, self._guess_type(view, i),
                                self.type_transformations, _source_type)),
            )
        return out

    @staticmethod
    def _run(view: GraphView, node: int, guess: int | None,
             rules: Sequence[Transformation], apply: Callable
             ) -> tuple[int | None, float]:
        """Apply the corrections in order; confidence tracks the last one used."""
        conditions = _conditions(view, node)
        value, confidence = guess, 0.3 if guess is not None else 0.0
        for rule in rules:
            if (rule.feature, rule.value) not in conditions:
                continue
            proposed = apply(view, node, rule.source)
            if proposed is None:
                continue
            value = proposed
            total = rule.fixed + rule.broke
            confidence = min(0.25 + 0.7 * rule.fixed / max(total, 1), 0.9)
        return value, confidence

    def n_symbolic_parameters(self) -> int:
        return (len(self.transformations) * 3 + len(self.type_transformations) * 3
                + len(self.baseline_type) + len(self.baseline_label))

    def render(self) -> str:
        parts = ["=== label ===",
                 f"  baseline: {len(self.baseline_label)} context defaults"]
        parts += [f"  {i + 1}. {r}" for i, r in enumerate(self.transformations)]
        parts += ["=== type ===",
                  f"  baseline: {len(self.baseline_type)} context defaults"]
        parts += [f"  {i + 1}. {r}" for i, r in enumerate(self.type_transformations)]
        return "\n".join(parts)


# ---------------------------------------------------------------------------
def _vote(result: tuple[int | None, float]) -> Votes:
    value, confidence = result
    if value is None or confidence <= 0.0:
        return ABSTAIN
    return {int(value): 1.0}, confidence


def _conditions(view: GraphView, node: int) -> frozenset:
    """The tests a transformation may be conditioned on."""
    p = view.parent[node]
    return frozenset({
        ("parent_type", _parent_type(view, node)),
        ("slot", min(view.slot[node], 6)),
        ("depth", min(view.depth[node], 6)),
        ("arity", min(len(view.children(node)), 4)),
        ("parent_head", view.labels[p] if p >= 0 else None),
        ("has_peer", bool(_source_label(view, node, "peer") is not None)),
    })


def _parent_type(view: GraphView, node: int) -> str:
    p = view.parent[node]
    return (view.types[p] or "mask") if p >= 0 else "ROOT"


def _label_key(view: GraphView, node: int) -> tuple:
    p = view.parent[node]
    return (view.labels[p] if p >= 0 else None, min(view.slot[node], 6))


def _source_node(view: GraphView, node: int, source: str) -> int | None:
    if source == "parent":
        p = view.parent[node]
        return p if p >= 0 else None
    if source == "prev_sibling":
        sibs = [j for j in view.siblings(node) if j < node]
        return sibs[-1] if sibs else None
    if source == "first_child":
        kids = view.children(node)
        return kids[0] if kids else None
    if source == "peer":
        p = view.parent[node]
        if p < 0 or view.labels[p] is None:
            return None
        head, slot = view.labels[p], view.slot[node]
        for other in range(len(view)):
            if other != p and view.labels[other] == head:
                kids = view.children(other)
                if slot < len(kids):
                    return kids[slot]
    return None


def _source_label(view: GraphView, node: int, source: str) -> int | None:
    target = _source_node(view, node, source)
    return None if target is None else view.labels[target]


def _source_type(view: GraphView, node: int, source: str) -> int | None:
    target = _source_node(view, node, source)
    if target is None or view.types[target] is None:
        return None
    return TYPE_TO_ID[view.types[target]]
