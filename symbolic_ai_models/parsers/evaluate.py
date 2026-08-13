"""Scoring a parser against the structure the text was generated *from*.

This is the thing the curriculum makes possible and almost no other corpus does.
``langcurriculum`` renders every episode from a typed term and hands that term
over, so for each string there is a true structure that no one annotated and no
one can disagree with. A parser can therefore be scored **exactly**, and — since
episodes are a pure function of their seed — on an unbounded supply of fresh
ones, so a parser cannot be quietly tuned until it fits a fixed test set.

The metric avoids span alignment on purpose. The generator does not record which
characters a subterm produced, so any bracket-level score would rest on a
heuristic alignment between labels and token positions, and a number resting on
a heuristic is a poor thing to compare parsers with. What *is* exact is the role
each symbol plays:

    a word's **true role** = the set of ``(parent label, slot)`` positions it
    occupies in the term graph

Two words share a role if they are ever used the same way by the generator —
which is precisely what a parser's classes are supposed to capture. So the score
is a pairwise clustering agreement between "the parser put these two words in
one class" and "the generator used these two words in the same position":

* **precision** — of the word pairs the parser grouped, how many really share a
  role;
* **recall** — of the pairs that share a role, how many the parser grouped;
* **F1** — the two together, and the number to compare parsers on.

A floor travels with it, as everywhere else in this repo: the score a parser
gets by putting every word in one class (perfect recall, precision equal to the
base rate of role-sharing). A parser below that has learned nothing and is worse
than not trying.
"""

from __future__ import annotations

import collections
import itertools
from dataclasses import dataclass, field
from typing import Any, Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer, split_words
from .base import ParseResult, Parser

__all__ = ["ParserReport", "true_roles", "evaluate_parser", "class_agreement"]


@dataclass
class ParserReport:
    """What a parser recovered, against what the generator actually did."""

    parser: str
    learned: bool
    n_episodes: int
    n_words: int
    n_classes: int
    precision: float
    recall: float
    f1: float
    floor_f1: float
    #: share of the words it saw that it actually assigned a class to. A parser
    #: with a fine score over 5% of its input is not a good parser, and an F1
    #: computed only over what it answered would not say so.
    coverage: float
    bracket_rate: float
    fact_rate: float
    parameters: int = 0

    @property
    def lift(self) -> float:
        """F1 rescaled into the headroom above the one-big-class floor."""
        room = 1.0 - self.floor_f1
        return 0.0 if room < 1e-12 else (self.f1 - self.floor_f1) / room

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["lift"] = self.lift
        return d

    def row(self) -> str:
        flag = "learned" if self.learned else "written"
        return (f"{self.parser:<14}{flag:<9}{self.parameters:>9,}"
                f"{self.n_classes:>9}{self.coverage:>9.2f}"
                f"{self.precision:>9.3f}{self.recall:>9.3f}"
                f"{self.f1:>9.3f}{self.floor_f1:>9.3f}{self.lift:>9.3f}"
                f"{self.bracket_rate:>9.2f}{self.fact_rate:>9.2f}")

    @staticmethod
    def header() -> str:
        head = (f"{'parser':<14}{'kind':<9}{'params':>9}{'classes':>9}"
                f"{'cover':>9}{'prec':>9}{'recall':>9}{'F1':>9}{'floor':>9}"
                f"{'lift':>9}{'brackets':>9}{'facts':>9}")
        return head + "\n" + "-" * len(head)


def true_roles(episodes: Sequence[Episode]) -> dict[str, frozenset]:
    """``word -> the set of (parent label, slot) it occupies in the term graphs``.

    Read straight off the generator's own structure. Nothing here is inferred,
    which is why it can serve as ground truth.
    """
    roles: dict[str, set] = collections.defaultdict(set)
    for ep in episodes:
        g = ep.graph
        for i, label in enumerate(g.labels):
            if not label:
                continue
            p = g.parent[i]
            parent = g.labels[p] if p >= 0 else "ROOT"
            roles[label].add((parent, min(g.slot[i], 6), g.types[i]))
    return {word: frozenset(rs) for word, rs in roles.items()}


def class_agreement(assignment: dict[str, str],
                    roles: dict[str, frozenset]) -> tuple[float, float, float]:
    """Pairwise ``(precision, recall, F1)`` of a clustering against the roles.

    Over word *types*, not tokens, so a common word cannot dominate the score by
    appearing often. Two words count as sharing a role if their role sets
    intersect at all — the generator used them the same way at least once.
    """
    words = sorted(set(assignment) & set(roles))
    if len(words) < 2:
        return 0.0, 0.0, 0.0

    same_class = same_role = both = 0
    for a, b in itertools.combinations(words, 2):
        grouped = assignment[a] == assignment[b]
        shares = bool(roles[a] & roles[b])
        same_class += grouped
        same_role += shares
        both += grouped and shares

    precision = both / same_class if same_class else 0.0
    recall = both / same_role if same_role else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return precision, recall, f1


def _floor(roles: dict[str, frozenset], words: Sequence[str]) -> float:
    """The F1 of putting every word in one class.

    Recall is 1 by construction, precision is the base rate of role-sharing. A
    parser that cannot beat this has not carved anything.
    """
    words = sorted(set(words) & set(roles))
    if len(words) < 2:
        return 0.0
    pairs = shares = 0
    for a, b in itertools.combinations(words, 2):
        pairs += 1
        shares += bool(roles[a] & roles[b])
    precision = shares / pairs if pairs else 0.0
    return 2 * precision / (precision + 1) if precision else 0.0


def evaluate_parser(parser: Parser, episodes: Sequence[Episode],
                    tok: SymbolTokenizer) -> ParserReport:
    """Parse every episode; score the classes the parser assigned.

    A word is given the class the parser assigned it most often, so a parser
    that is inconsistent about a word is penalised through the disagreement it
    creates rather than being silently allowed several answers.
    """
    roles = true_roles(episodes)
    votes: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    seen: set[str] = set()
    bracketed = with_facts = 0

    for ep in episodes:
        result = parser.parse(ep.prompt)
        for i, token in enumerate(result.tokens):
            seen.add(token)
            # Scored on what the parser actually *assigned*, not on
            # `class_of`'s convenience fallback to the token itself. The
            # fallback is right for a consumer — it means "no opinion, here is
            # the word" — but reading it as a class makes a parser that assigns
            # nothing indistinguishable from one that put every word in its own
            # class, and silently gives it a coverage of 1.0.
            assigned = result.classes.get(i)
            if assigned:
                votes[token][assigned] += 1
        bracketed += bool(result.constituents)
        with_facts += bool(result.facts)

    assignment = {word: counter.most_common(1)[0][0]
                  for word, counter in votes.items() if counter}
    precision, recall, f1 = class_agreement(assignment, roles)
    n = max(len(episodes), 1)
    scorable = seen & set(roles)
    return ParserReport(
        parser=parser.name, learned=parser.learned, n_episodes=len(episodes),
        n_words=len(set(assignment) & set(roles)),
        n_classes=len(set(assignment.values())),
        precision=precision, recall=recall, f1=f1,
        # The floor is measured over every word the parser *saw*, not only the
        # ones it chose to classify, so a parser cannot raise its own floor by
        # declining to answer for the hard words.
        floor_f1=_floor(roles, list(scorable)),
        coverage=len(set(assignment) & set(roles)) / max(len(scorable), 1),
        bracket_rate=bracketed / n, fact_rate=with_facts / n,
        parameters=parser.n_parameters())


