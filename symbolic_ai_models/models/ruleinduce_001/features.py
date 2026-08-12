"""rule-induce-001's reading of a prompt: role-tagged clauses and their links.

The hypothesis language is generated from what was observed, never written down
per task — that is the property the induction rests on. What this file commits to
is only that a prompt has *clauses*, that some of them are premises and one of
them is the question, and that clauses can share terms. Nothing here knows what a
syllogism is, what evidence is, or what any env rewards.

Three fact families come out:

    head(role, first-token)              what kind of statement each clause is
    term(role, index, word)              its content words, by position
    link(role_i, i, role_j, j)           two clauses share a term at those positions

`link` is the one that matters and the one a bag of words cannot express. "All A
are B; all B are C; therefore all A are C" and "...therefore all C are A" have
identical heads and identical words; they differ only in which positions the
shared terms occupy.
"""

from __future__ import annotations

from ...parsers.primitives import clauses as parse
from .facts import FactSet

# The layout rule in practice: symbolic-ai-001 defined this morphology first, so
# it is imported from there rather than copied or promoted into a shared utils.
from ...parsers.primitives.lexicon import singular

STOP = frozenset(
    "a an the is are was were be been do does did not no-op of to in on at by for "
    "and or but if then than that this these those there it its".split()
)

CONCLUSION_MARKERS = ("conclusion", "therefore", "hence", "thus", "so")

MAX_CLAUSES = 8
"""Beyond this the link family grows quadratically for no observed benefit."""


def role_of(clause: str, index: int, total: int) -> str:
    """premise / conclusion / query — decided by shape, not by task knowledge."""
    lowered = clause.strip().lower()
    if lowered.endswith("?") or lowered.startswith(("does ", "is ", "are ", "what ", "which ")):
        return "query"
    if lowered.startswith(CONCLUSION_MARKERS):
        return "conclusion"
    return "premise"


def content_terms(clause: str) -> list[str]:
    """The words that carry reference, in order, singularized so plural and
    singular mentions of one class are one term."""
    words = [w for w in parse.words(clause) if w.lower() not in STOP]
    return [singular(w.lower()) for w in words]


def clauses_of(text: str) -> list[tuple[str, str]]:
    """(role, clause), skipping the line that spells out the answer vocabulary —
    an options line is instructions, not a statement about the world."""
    out: list[tuple[str, str]] = []
    raw = [c for c in parse.clauses(text) if c.strip() and not parse.options_from_text(c)]
    for i, clause in enumerate(raw[:MAX_CLAUSES]):
        out.append((role_of(clause, i, len(raw)), clause))
    return out


def facts_for(text: str) -> FactSet:
    """The agent's own reading of one prompt, as a `FactSet` the inducer can use."""
    facts: set[tuple] = set()
    parsed = clauses_of(text)
    per_clause: list[tuple[str, int, list[str]]] = []
    seen_roles: dict[str, int] = {}
    for role, clause in parsed:
        position = seen_roles.get(role, 0)
        seen_roles[role] = position + 1
        terms = content_terms(clause)
        head = (parse.words(clause) or [""])[0].lower()
        facts.add(("head", f"{role}{position}", head))
        for index, term in enumerate(terms[:6]):
            facts.add(("term", f"{role}{position}:{index}", term))
        per_clause.append((role, position, terms[:6]))

    for a_i, (role_a, pos_a, terms_a) in enumerate(per_clause):
        for role_b, pos_b, terms_b in per_clause[a_i + 1 :]:
            for i, term_a in enumerate(terms_a):
                for j, term_b in enumerate(terms_b):
                    if term_a == term_b:
                        # Endpoints are single tokens so that a two-constraint
                        # literal names a whole link; `candidate_literals`
                        # constrains at most two argument positions.
                        facts.add((
                            "link", f"{role_a}{pos_a}:{i}", f"{role_b}{pos_b}:{j}"
                        ))
    return FactSet(frozenset(facts), {})
