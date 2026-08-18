"""Inductive Logic Programming: learn Horn clauses with variables, FOIL-style.

Everything else rule-based in this repo is **propositional**. ``ruleinduce``
induces good rules, but the things its rules can conclude are drawn from a list
somebody wrote down — ``copy:peer``, ``copy:parent`` — so the *relational chain*
that reaches the answer was designed rather than learned. That is the gap this
model exists to close, and it is a large one: first-order induction is the
classical symbolic learning paradigm, and the curriculum's whole subject is
variable binding.

A hypothesis here is a clause with variables::

    answer(X, L) :- parent(X, P), label(P, H), parent(Y, Q), label(Q, H),
                    slot(X, S), slot(Y, S), label(Y, L).

Read: *the label of X is whatever stands in the same slot of another subtree
whose head is the same*. ``ruleinduce`` has that rule because it was enumerated
as ``copy:peer``; here it is **derived**, by adding one literal at a time under
FOIL's information gain, and a different chain — two steps up and one across, a
sibling of an ancestor — costs nothing extra to discover.

The consequence that matters is generalisation over invented vocabulary. The
clause binds ``L`` to another node's label rather than naming a symbol, so a
clause induced over episodes full of ``o0``/``o1`` applies unchanged to an
episode full of ``w7``/``w8``. A network has to have seen the symbol to put
probability on it; this does not have to have seen the *episode*.

Search is FOIL's: greedy top-down, one literal at a time, each scored by
information gain over the bindings it survives, clauses accumulated
separate-and-conquer until the positives are covered or nothing pays. Bounded by
clause length, variable count and candidate literals, all in ``extra``.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.term_graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["ILPModel", "Clause", "Literal"]

#: The relations a clause body may use. Each maps a bound variable to a new one,
#: which is what keeps the search a chain rather than a cross product.
RELATIONS = ("parent", "child", "sibling", "peer", "ancestor")


@dataclass(frozen=True)
class Literal:
    """``relation(source, target)`` or a test on one variable."""

    kind: str                 # a relation name, "type", "slot", or "head"
    source: str               # bound variable
    target: str = ""          # the variable it introduces (relations only)
    value: Any = None         # the constant it tests (tests only)

    def __repr__(self) -> str:
        if self.kind in RELATIONS:
            return f"{self.kind}({self.source},{self.target})"
        return f"{self.kind}({self.source})={self.value!r}"


@dataclass
class Clause:
    """``answer(X, L) :- body``, where ``L`` is the label of ``answer_var``."""

    body: tuple[Literal, ...] = ()
    answer_var: str = "X"
    support: int = 0
    correct: int = 0

    @property
    def confidence(self) -> float:
        return self.correct / max(self.support, 1)

    def body_str(self) -> str:
        return ", ".join(repr(l) for l in self.body) or "true"

    def __repr__(self) -> str:
        return (f"answer(X,L) :- {self.body_str()}, label({self.answer_var},L)."
                f"   [{self.correct}/{self.support}]")


class _Bindings(dict):
    """A substitution from variable names to node indices."""


@register("ilp-001", doc="FOIL-style first-order clause induction; rules bind variables, not symbols.")
class ILPModel(RuleBasedModel):
    """Learn relational clauses whose conclusion is another node's label."""

    LEARNED = ("clauses", "type_clauses", "max_body", "max_vars")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_body = int(cfg.get("max_body", 3))
        self.max_vars = int(cfg.get("max_vars", 4))
        self.max_clauses = int(cfg.get("max_clauses", 12))
        # Set from measured wall clock, never from eval lift. The cap bounds
        # runtime and nothing else, so the rule is "the largest value fitting
        # 300s on the full curriculum", well under synth's 1,500s which this
        # sweep already tolerates. The old value was a guessed constant.
        # The one model that cannot be uncapped: it ran past a 900s timeout, and 48,000
        # costs 462s. 24,000 costs 240s and fits. Its curve is flat too.
        self.max_examples = int(cfg.get("max_examples", 24_000))
        self.min_confidence = float(cfg.get("min_confidence", 0.15))
        self.clauses: list[Clause] = []
        self.type_clauses: list[tuple[Clause, int]] = []

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        examples = self._examples(episodes, tok)
        self.clauses = self._induce_label(examples)
        self.type_clauses = self._induce_type(examples)

    def _examples(self, episodes: Sequence[Episode], tok: SymbolTokenizer
                  ) -> list[tuple[GraphView, int, int, int]]:
        """``(view, node, true label, true type)``, from masked views only.

        The same discipline as everywhere else in the rule-based half: a clause
        that reads a neighbour's label is only worth inducing if that label is
        there when the clause fires, and on a masked graph it sometimes is not.
        """
        out = []
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (label_id, type_id) in targets.items():
                out.append((view, node, label_id, type_id))
        if len(out) > self.max_examples:
            step = len(out) / self.max_examples
            out = [out[int(i * step)] for i in range(self.max_examples)]
        return out

    def _induce_label(self, examples: Sequence[tuple]) -> list[Clause]:
        """Separate-and-conquer over clauses that conclude a *bound* label."""
        remaining = [e for e in examples if e[2] >= 0]
        clauses: list[Clause] = []
        while remaining and len(clauses) < self.max_clauses:
            clause = self._grow(remaining)
            if clause is None:
                break
            # A weak clause is still worth keeping. Abstaining does not fall
            # back on something better -- it falls back on the unigram prior,
            # which is far below the structural floor these are scored against,
            # so a clause that is right a third of the time beats silence. Its
            # confidence travels with it and the mixture weights it accordingly.
            if clause.confidence >= self.min_confidence:
                clauses.append(clause)
            covered = {id(e) for e in remaining if self._fires(clause, e) is not None}
            nxt = [e for e in remaining if id(e) not in covered]
            if len(nxt) == len(remaining):           # made no progress
                break
            remaining = nxt
        return clauses

    def _grow(self, examples: Sequence[tuple]) -> Clause | None:
        """FOIL: add the literal with the best information gain, repeatedly.

        The gain is Quinlan's — the positives a literal *keeps*, times the
        improvement in log-precision it buys over the clause it extends. It has
        to be a difference: an absolute log-precision is never positive, so
        scoring candidates on one alone would mean nothing could ever beat the
        empty clause, and the induction would return no clauses at all.
        """
        clause = Clause(body=(), answer_var="X")
        support, correct = _support(self, clause, examples)
        while len(clause.body) < self.max_body:
            best, best_gain, best_counts = None, 1e-9, (0, 0)
            for candidate in self._candidates(clause):
                s, c = _support(self, candidate, examples)
                if s < 3 or c == 0:
                    continue
                gain = c * (_log_precision(c, s) - _log_precision(correct, support))
                if gain > best_gain:
                    best, best_gain, best_counts = candidate, gain, (s, c)
            if best is None:
                break
            clause, (support, correct) = best, best_counts
        if not clause.body or not correct:
            return None
        clause.support, clause.correct = support, correct
        return clause

    def _candidates(self, clause: Clause) -> Iterator[Clause]:
        """Every one-literal extension: a new relation, or a test on a variable.

        New variables are introduced only by relations, and the answer variable
        may be moved onto any bound variable — which is how the clause learns
        *where* to read the answer from rather than being told.
        """
        bound = _variables(clause)
        fresh = f"V{len(bound)}"
        if len(bound) < self.max_vars:
            for relation in RELATIONS:
                for source in bound:
                    body = clause.body + (Literal(relation, source, fresh),)
                    # the new variable is only useful if the answer can come
                    # from it, or if a later literal constrains it
                    yield Clause(body=body, answer_var=fresh)
                    yield Clause(body=body, answer_var=clause.answer_var)
        for kind, values in (("slot", range(4)), ("type", _TYPE_IDS)):
            for source in bound:
                for value in values:
                    yield Clause(body=clause.body + (Literal(kind, source, "", value),),
                                 answer_var=clause.answer_var)

    def _induce_type(self, examples: Sequence[tuple]) -> list[tuple[Clause, int]]:
        """Type is a small closed class, so clauses conclude a constant here.

        The relational machinery is the same; only the head differs, which is
        the honest way to handle a target that genuinely is a fixed symbol
        rather than a binding.
        """
        out: list[tuple[Clause, int]] = []
        by_type: dict[int, list] = collections.defaultdict(list)
        for e in examples:
            if e[3] >= 0:
                by_type[e[3]].append(e)
        for type_id, positives in sorted(by_type.items(),
                                         key=lambda kv: -len(kv[1]))[:8]:
            negatives = [e for e in examples if e[3] >= 0 and e[3] != type_id]
            clause = self._grow_for_type(positives, negatives)
            if clause is not None:
                out.append((clause, type_id))
        return out

    def _grow_for_type(self, positives: Sequence[tuple],
                       negatives: Sequence[tuple]) -> Clause | None:
        """The same FOIL gain, against a target that is a constant not a binding."""
        clause = Clause(body=(), answer_var="X")
        p = len(positives)
        n = len(negatives)
        while len(clause.body) < self.max_body:
            best, best_gain, best_counts = None, 1e-9, (0, 0)
            for candidate in self._candidates(clause):
                cp = sum(1 for e in positives if self._fires(candidate, e) is not None)
                cn = sum(1 for e in negatives if self._fires(candidate, e) is not None)
                if cp < 3:
                    continue
                gain = cp * (_log_precision(cp, cp + cn) - _log_precision(p, p + n))
                if gain > best_gain:
                    best, best_gain, best_counts = candidate, gain, (cp, cn)
            if best is None:
                break
            clause, (p, n) = best, best_counts
        if not clause.body:
            return None
        clause.support, clause.correct = p + n, p
        return clause if clause.confidence >= self.min_confidence else None

    # ---- resolution ----------------------------------------------------
    def _fires(self, clause: Clause, example: tuple) -> int | None:
        """Resolve the body against the graph; return the answer node, or None.

        A depth-first walk with no backtracking past the first success, which is
        all a chain-shaped body needs and keeps induction affordable.
        """
        view, node = example[0], example[1]
        for bindings in _resolve(clause.body, _Bindings({"X": node}), view):
            target = bindings.get(clause.answer_var)
            if target is not None:
                return target
        return None

    # ---- prediction -----------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            out[i] = (self._label_vote(view, i), self._type_vote(view, i))
        return out

    def _label_vote(self, view: GraphView, i: int) -> Votes:
        votes: collections.Counter = collections.Counter()
        weight = 0.0
        for clause in self.clauses:
            target = self._fires(clause, (view, i, -1, -1))
            if target is None:
                continue
            label = view.labels[target]
            if label is None:                 # the source is hidden too
                continue
            # Every clause that fires votes, weighted by how often it was right.
            # First-clause-wins throws away the agreement between clauses, which
            # is the main evidence a theory of several rules provides.
            votes[label] += clause.confidence
            weight = max(weight, clause.confidence)
        if not votes:
            return ABSTAIN
        return dict(votes), min(0.15 + 0.8 * weight, 0.92)

    def _type_vote(self, view: GraphView, i: int) -> Votes:
        for clause, type_id in self.type_clauses:
            if self._fires(clause, (view, i, -1, -1)) is not None:
                return {type_id: 1.0}, min(0.15 + 0.8 * clause.confidence, 0.92)
        return ABSTAIN

    def n_symbolic_parameters(self) -> int:
        return (sum(len(c.body) + 1 for c in self.clauses)
                + sum(len(c.body) + 1 for c, _ in self.type_clauses))

    def render(self) -> str:
        """The theory, as a logic program. This is the whole model."""
        label = [repr(c) for c in self.clauses] or ["% (none)"]
        # A type clause concludes a constant, so it has no `label(V,L)` tail;
        # printing one would misdescribe what was learned.
        types = [f"type(X,{t}) :- {c.body_str()}.   [{c.correct}/{c.support}]"
                 for c, t in self.type_clauses] or ["% (none)"]
        return "\n".join(["% label", *label, "", "% type", *types])


# ---------------------------------------------------------------------------
# the little resolution engine
# ---------------------------------------------------------------------------
_TYPE_IDS = tuple(TYPE_TO_ID[t] for t in ("pred", "ident", "field", "list",
                                          "record", "num", "token", "char"))


def _variables(clause: Clause) -> list[str]:
    seen = ["X"]
    for literal in clause.body:
        if literal.target and literal.target not in seen:
            seen.append(literal.target)
    return seen


def _resolve(body: Sequence[Literal], bindings: _Bindings,
             view: GraphView) -> Iterator[_Bindings]:
    """Every substitution satisfying ``body``. Chain-shaped, so this stays small."""
    if not body:
        yield bindings
        return
    head, rest = body[0], body[1:]
    source = bindings.get(head.source)
    if source is None:
        return
    if head.kind in RELATIONS:
        for target in _related(view, source, head.kind):
            extended = _Bindings(bindings)
            extended[head.target] = target
            yield from _resolve(rest, extended, view)
    elif head.kind == "slot":
        if view.slot[source] == head.value:
            yield from _resolve(rest, bindings, view)
    elif head.kind == "type":
        t = view.types[source]
        if t is not None and TYPE_TO_ID[t] == head.value:
            yield from _resolve(rest, bindings, view)


def _related(view: GraphView, node: int, relation: str) -> list[int]:
    if relation == "parent":
        p = view.parent[node]
        return [p] if p >= 0 else []
    if relation == "child":
        return view.children(node)
    if relation == "sibling":
        return view.siblings(node)
    if relation == "ancestor":
        out, p = [], view.parent[node]
        while p >= 0 and len(out) < 4:
            out.append(p)
            p = view.parent[p]
        return out
    if relation == "peer":
        # the same slot of another subtree whose head matches — the relation
        # that makes a term tree analogical rather than merely hierarchical
        p = view.parent[node]
        if p < 0 or view.labels[p] is None:
            return []
        head, slot = view.labels[p], view.slot[node]
        out = []
        for other in range(len(view)):
            if other == p or view.labels[other] != head:
                continue
            kids = view.children(other)
            if slot < len(kids):
                out.append(kids[slot])
        return out
    return []


def _support(model: ILPModel, clause: Clause,
             examples: Sequence[tuple]) -> tuple[int, int]:
    support = correct = 0
    for e in examples:
        target = model._fires(clause, e)
        if target is None:
            continue
        support += 1
        if e[0].labels[target] == e[2]:
            correct += 1
    return support, correct


def _log_precision(correct: int, support: int) -> float:
    """Laplace-smoothed log precision, the term FOIL's gain differences."""
    return math.log2((correct + 1) / (support + 2))
