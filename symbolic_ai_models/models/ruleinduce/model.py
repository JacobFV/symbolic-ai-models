"""rule-induce-001, as a predictive model: a decision list you can read.

The learned object is not a checkpoint. It is a few dozen ordered rules, induced
by greedy separate-and-conquer with an MDL stopping criterion, and you can print
it and argue with it::

    IF slot(1) AND parent_head(parent) THEN copy:peer
    ELSE IF parent_type(record) THEN const:query
    ELSE ...

The design decision that makes this work at all is what the rules *predict*. The
curriculum invents its vocabulary every episode, so a rule of the form "in this
context the answer is ``o2``" is worthless — ``o2`` will not exist in the next
episode. The rules therefore predict **actions**, not symbols:

===================  ==================================================
``copy:parent``      whatever the parent node is called
``copy:sibling_k``   whatever the k-th sibling is called
``copy:peer``        the same slot of another subtree with the same head
``copy:prev``        the nearest labelled node before this one
``const:X``          a specific symbol, for the few that recur across episodes
===================  ==================================================

An action is resolved against the graph at prediction time, so a rule induced
over one episode's invented names applies unchanged to another's. This is the
sharpest structural advantage the rule-based family has over the networks here:
a transformer has to see ``o2`` in training to put probability on it, and this
does not.

The hypothesis language is generated from the observed facts by
``candidate_literals`` — nothing task-specific is written down, and no lesson is
named anywhere in this file.
"""

from __future__ import annotations

import collections
from typing import Any, Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes
from .dlist import DecisionList, induce_decision_list
from .facts import FactSet, candidate_literals

__all__ = ["RuleInductionModel"]

MAX_SIBLING = 3


@register("ruleinduce", doc="Decision-list induction over structural context; rules predict pointers.")
class RuleInductionModel(RuleBasedModel):
    """Induce ordered rules mapping structural context to a copy action."""

    LEARNED = ("label_rules", "type_rules", "text_rules", "frequent")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_examples = int(cfg.get("max_examples", 4000))
        self.max_conditions = int(cfg.get("max_conditions", 3))
        self.n_constants = int(cfg.get("n_constants", 24))
        self.label_rules: DecisionList | None = None
        self.type_rules: DecisionList | None = None
        self.text_rules: DecisionList | None = None
        self.frequent: list[int] = []

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        counts: collections.Counter = collections.Counter()
        for ep in episodes:
            counts.update(tok.label_id(l) for l in ep.graph.labels if l)
        self.frequent = [s for s, _ in counts.most_common(self.n_constants)]

        # Induce on masked views. A rule conditioned on the parent's label is
        # only worth learning if the parent's label is *there* when the rule
        # fires, and on a masked graph it sometimes is not — so the induction
        # has to see that, or it will happily learn rules that never apply.
        label_ex, type_ex = [], []
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_len):
            wrapped = _View.from_graph_view(view)
            for node, (label_id, type_id) in targets.items():
                fs = _node_facts(wrapped, node)
                if type_id >= 0:
                    type_ex.append((fs, type_id))
                if label_id >= 0:
                    action = self._best_action(wrapped, node, label_id)
                    if action is not None:
                        label_ex.append((fs, action))
        self.label_rules = self._induce(label_ex)
        self.type_rules = self._induce(type_ex)

        text_ex = []
        for ep in episodes:
            ids = tok.encode(ep.text, bos=True, eos=True)
            for t in range(len(ids) - 1):
                text_ex.append((_text_facts(ids, t, tok), self._text_action(ids, t)))
        self.text_rules = self._induce(text_ex)

    def _induce(self, examples: list) -> DecisionList | None:
        if not examples:
            return None
        # Subsample rather than truncate: the induction is greedy over the whole
        # set, so handing it the first N examples would hand it the first N
        # lessons in registry order and induce rules about those.
        if len(examples) > self.max_examples:
            step = len(examples) / self.max_examples
            examples = [examples[int(i * step)] for i in range(self.max_examples)]
        literals = candidate_literals([fs for fs, _ in examples], max_literals=300)
        return induce_decision_list(examples, literals,
                                    max_conditions=self.max_conditions)

    def _best_action(self, view: "_View", i: int, truth: int) -> Any:
        """The most transferable action that would have been right here.

        ``truth`` is passed in rather than read off the view, because on a
        masked view ``view.labels[i]`` is ``None`` — which is exactly the point.
        The action is resolved against the graph the model can actually see, and
        only the comparison uses the answer.

        Copy actions are preferred over constants even when both are correct,
        because a constant is a bet that the next episode reuses the symbol and
        a pointer is not. Ordering the search this way is what keeps the induced
        list general instead of a lookup table with extra steps.
        """
        for action in _ACTIONS:
            if _resolve(view, i, action) == truth:
                return action
        return ("const", truth) if truth in self.frequent else None

    @staticmethod
    def _text_action(ids: Sequence[int], t: int) -> Any:
        """Copying an earlier token beats naming it, for the same reason."""
        nxt = ids[t + 1]
        for k in (1, 2, 3, 4):
            if t + 1 - k >= 0 and ids[t + 1 - k] == nxt:
                return ("back", k)
        return ("const", nxt)

    # ---- prediction ---------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        assert self.tok is not None
        if self.text_rules is None:
            return [ABSTAIN] * len(ids)
        out: list[Votes] = []
        for t in range(len(ids)):
            action, rule = self.text_rules.explain(_text_facts(ids, t, self.tok))
            symbol = None
            if isinstance(action, tuple):
                if action[0] == "back" and t + 1 - action[1] >= 0:
                    symbol = ids[t + 1 - action[1]]
                elif action[0] == "const":
                    symbol = action[1]
            out.append(({symbol: 1.0}, _confidence(rule)) if symbol is not None
                       else ABSTAIN)
        return out

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        wrapped = _View.from_graph_view(view)
        for i in view.hidden:
            fs = _node_facts(wrapped, i)
            out[i] = (self._label_vote(wrapped, i, fs), self._type_vote(fs))
        return out

    def _label_vote(self, view: "_View", i: int, fs: FactSet) -> Votes:
        if self.label_rules is None:
            return ABSTAIN
        action, rule = self.label_rules.explain(fs)
        symbol = _resolve(view, i, action) if action is not None else None
        if symbol is None and isinstance(action, tuple) and action[0] == "const":
            symbol = action[1]
        return ({symbol: 1.0}, _confidence(rule)) if symbol is not None else ABSTAIN

    def _type_vote(self, fs: FactSet) -> Votes:
        if self.type_rules is None:
            return ABSTAIN
        type_id, rule = self.type_rules.explain(fs)
        return ({int(type_id): 1.0}, _confidence(rule)) if type_id is not None else ABSTAIN

    def n_symbolic_parameters(self) -> int:
        return sum(dl.n_parameters for dl in
                   (self.label_rules, self.type_rules, self.text_rules) if dl)

    def render(self) -> str:
        """The whole model, as text. This is what a symbolic artifact buys you."""
        parts = []
        for name, dl in (("label", self.label_rules), ("type", self.type_rules),
                         ("text", self.text_rules)):
            parts.append(f"=== {name} ===\n{dl!r}" if dl else f"=== {name} === (none)")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------
_ACTIONS: tuple = (
    ("peer",), ("parent",), ("prev",),
    *[("sibling", k) for k in range(MAX_SIBLING)],
)


def _resolve(view: "_View", i: int, action: Any) -> int | None:
    """Turn an action into an actual symbol, against this graph."""
    if not isinstance(action, tuple) or not action:
        return None
    kind = action[0]
    if kind == "const":
        return action[1]
    if kind == "parent":
        p = view.parent[i]
        return view.labels[p] if p >= 0 else None
    if kind == "prev":
        for j in range(i - 1, -1, -1):
            if view.labels[j] is not None:
                return view.labels[j]
        return None
    if kind == "sibling":
        sibs = view.siblings(i)
        return view.labels[sibs[action[1]]] if action[1] < len(sibs) else None
    if kind == "peer":
        return _peer(view, i)
    return None


def _peer(view: "_View", i: int) -> int | None:
    """The same slot of another subtree whose parent shares this one's head."""
    p = view.parent[i]
    if p < 0 or view.labels[p] is None:
        return None
    head, slot = view.labels[p], view.slot[i]
    for other in range(len(view)):
        if other == p or view.labels[other] != head:
            continue
        kids = view.children(other)
        if slot < len(kids) and view.labels[kids[slot]] is not None:
            return view.labels[kids[slot]]
    return None


def _confidence(rule) -> float:
    """A rule's own measured confidence, damped by how much it covered."""
    if rule is None:
        return 0.25
    return min(0.15 + 0.8 * rule.confidence * (rule.support / (rule.support + 3)), 0.92)


# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------
def _node_facts(view: "_View", i: int) -> FactSet:
    """Structural context of a node — never its own label or type.

    Everything here is readable off the tree with the node itself redacted, so
    the same function serves training and prediction and there is no way for the
    answer to enter through the features.
    """
    p = view.parent[i]
    facts = {
        ("slot", view.slot[i]),
        ("depth", min(view.depth[i], 6)),
        ("arity", len(view.children(i))),
        ("parent_type", view.types[p] if p >= 0 and view.types[p] else "ROOT"),
        ("n_siblings", len(view.siblings(i))),
        ("is_leaf", len(view.children(i)) == 0),
    }
    if p >= 0 and view.labels[p] is not None:
        facts.add(("parent_head", view.labels[p]))
    if _peer(view, i) is not None:
        facts.add(("has_peer",))
    for k, j in enumerate(view.siblings(i)[:MAX_SIBLING]):
        if view.types[j]:
            facts.add(("sibling_type", k, view.types[j]))
    return FactSet(frozenset(facts), {})


def _text_facts(ids: Sequence[int], t: int, tok: SymbolTokenizer) -> FactSet:
    """Context of a token position — strictly ``ids[:t + 1]``."""
    facts = {("pos", min(t, 24))}
    for k in (1, 2, 3):
        if t + 1 - k >= 0:
            facts.add((f"back{k}", ids[t + 1 - k]))
    window = ids[max(0, t - 12):t + 1]
    facts.add(("repeats", len(window) != len(set(window))))
    if t >= 0:
        piece = tok.itos[ids[t]]
        facts.add(("newline", "\n" in piece))
        facts.add(("alpha", piece.strip().isalpha()))
    return FactSet(frozenset(facts), {})


# ---------------------------------------------------------------------------
class _View:
    """A uniform read-only view, so training graphs and masked ones share code."""

    def __init__(self, labels, types, parent, slot, depth) -> None:
        self.labels, self.types = labels, types
        self.parent, self.slot, self.depth = parent, slot, depth
        self._kids: dict[int, list[int]] = collections.defaultdict(list)
        for i, p in enumerate(parent):
            if p >= 0:
                self._kids[p].append(i)

    def __len__(self) -> int:
        return len(self.labels)

    def children(self, i: int) -> list[int]:
        return self._kids.get(i, [])

    def siblings(self, i: int) -> list[int]:
        p = self.parent[i]
        return [] if p < 0 else [j for j in self.children(p) if j != i]

    @classmethod
    def from_graph_view(cls, view: GraphView) -> "_View":
        return cls(view.labels, view.types, view.parent, view.slot, view.depth)
