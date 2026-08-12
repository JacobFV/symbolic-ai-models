"""Extractive answering over a supplied body, with abstention.

Ported verbatim from symbolic-ai-001 (`agents/symcontrol_001/answering.py`).

The pipeline is the source's, reimplemented on text:

    body text -> sentences -> concept lemmas
    query      -> query type + concept lemmas
    rank sentences by normalized conceptual overlap
    if the best sentence does not clear the evidence threshold -> ABSTAIN
    else extract a span whose *type* matches the query type

"Normalized" in the source meant only that the *tokens* were normalized --
case-folded, apostrophe-folded, stopped, lemmatized -- before the sets were
intersected. There was no IDF and no length term, and every shared concept was
worth the same 2.0. The score here is

    2·Σ_{x ∈ Q∩S} w(x) + type_bonus(type, sentence)
                       + 0.35·|{q ∈ Q : q occurs literally in S}|
                       − 0.4·(negation polarity of Q disagrees with S)

with Q the *set* of query concept lemmas, S the sentence's, and ``w(x)`` how
discriminative that concept is **within this body** (see ``_discriminativeness``).
Ties go to the earliest sentence, so the answer never depends on dictionary
ordering.

The threshold is 2.0, which is what one wholly discriminative concept is worth,
and it is tested against the *overlap term alone*: the type bonus decides which
of several relevant sentences to read, not whether any sentence is relevant. A
body that shares nothing but shape with the question yields no answer at all
rather than the best of a bad set. Both departures from the source are measured
in ``answer``'s docstring, and ``admit_on="total"`` restores its rule exactly.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from .lexicon import lemma, lexical_type, normalize, tokenize

__all__ = ["split_sentences", "concepts", "query_type", "type_bonus", "rank_evidence",
           "extract_span", "answer", "Answer", "EVIDENCE_THRESHOLD"]

#: One shared concept lemma is worth exactly this much, so the threshold below
#: reads as "at least one real point of contact with the question".
EVIDENCE_THRESHOLD = 2.0

STOP = frozenset("""
a an the this that these those is are was were be been being do does did have has had
can could will would should may might must to of in on at by for from with as and or but
if then than into inside within outside over under near about after before during through
what which who whom whose where when why how many much tell explain describe please
input body query answer stored last it its
""".split())


def split_sentences(body: str) -> list[str]:
    """Sentence boundaries at newlines and at ``. ! ?`` -- except a decimal point.

    Terminators are kept in the sentence: they are evidence about sentence type
    and dropping them would lose it.
    """
    out: list[str] = []
    buf: list[str] = []
    text = body or ""
    for i, ch in enumerate(text):
        if ch == "\n":
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
            continue
        buf.append(ch)
        if ch in ".!?":
            prev, nxt = (text[i - 1] if i else ""), (text[i + 1] if i + 1 < len(text) else "")
            if ch == "." and prev.isdigit() and nxt.isdigit():
                continue                      # 0.42 is one number, not two sentences
            if nxt in ".!?":
                continue                      # consume the run, split after it
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def concepts(s: str) -> list[str]:
    """Content lemmas: drop punctuation and bracketed values, drop stopwords, stem."""
    out: list[str] = []
    for tok in tokenize(s):
        if not tok or not (tok[0].isalnum()):
            continue
        n = normalize(tok)
        if n in STOP:
            continue
        out.append(lemma(tok))
    return out


_QTYPE_RULES = (
    (re.compile(r"^how\s+many\b"), "count"),
    (re.compile(r"^how\s+much\b"), "amount"),
    (re.compile(r"^where\b"), "where"),
    (re.compile(r"^when\b"), "when"),
    (re.compile(r"^(who|whom|whose)\b"), "who"),
    (re.compile(r"^why\b"), "why"),
    (re.compile(r"^how\b"), "how"),
    (re.compile(r"^(is|are|was|were|do|does|did|can|could|will|has|have)\b"), "boolean"),
)


def query_type(q: str) -> str:
    """What *kind* of thing would answer this. First match wins."""
    n = normalize(q or "").strip()
    for rx, t in _QTYPE_RULES:
        if rx.match(n):
            return t
    return "what"


_BONUS_TESTS = {
    "where": (re.compile(r"\[[^\]]+\]|\([^)]+\)|\b(in|at|on|near|inside|within|outside|above|below|"
                         r"left|right|centered|located|stored)\b", re.I), 3.0),
    "when": (re.compile(r"\b(?:\d{1,2}:\d{2}|\d{4}|monday|tuesday|wednesday|thursday|friday|"
                        r"saturday|sunday|january|february|march|april|may|june|july|august|"
                        r"september|october|november|december|today|tomorrow|yesterday)\b", re.I), 3.0),
    "count": (re.compile(r"\b\d+(?:\.\d+)?\b"), 3.0),
    "amount": (re.compile(r"\b\d+(?:\.\d+)?\b"), 3.0),
    "why": (re.compile(r"\b(because|since|due to|therefore|so that)\b", re.I), 3.0),
    "how": (re.compile(r"\b(by|through|using|with|via)\b", re.I), 2.0),
    "who": (re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"), 2.0),
}


def type_bonus(qtype: str, sentence: str) -> float:
    """Credit a sentence for containing the *kind* of thing the query asks for.

    This is what makes the ranking type-aware rather than a bag-of-words match:
    "Where is X?" prefers a sentence with a place in it even when both candidates
    mention X.
    """
    hit = _BONUS_TESTS.get(qtype)
    if not hit:
        return 0.0
    rx, bonus = hit
    return bonus if rx.search(sentence) else 0.0


_NEG_RE = re.compile(r"\bnot\b|n't|\bno\b")


@dataclass
class Ranked:
    index: int
    sentence: str
    score: float
    overlap: tuple[str, ...]
    concept_score: float = 0.0     # the overlap term alone, before any type bonus


def _discriminativeness(sentences: Sequence[Sequence[str]]) -> dict[str, float]:
    """How much a shared concept is worth, given how common it is *in this body*.

    The source weighted every shared concept equally, and that is the one place
    its ranking is wrong rather than merely simple. A body generated from a
    template shares its predicate words across every sentence -- ask "how many
    faults were logged on the backup drive?" of a body that never mentions the
    backup drive, and half a dozen sentences still share ``fault`` and ``log``.
    Equal weighting reads that as evidence. Weighting by rarity within the body
    reads it as what it is: shape, not content.

    ``w(x) = log((N+1)/(1+df(x))) / log(N+1)`` -- one for a concept unique to one
    sentence, near zero for one in all of them, and defined without a corpus, so
    it needs nothing the body did not already supply.
    """
    n = len(sentences)
    if n == 0:
        return {}
    df: dict[str, int] = {}
    for cs in sentences:
        for x in set(cs):
            df[x] = df.get(x, 0) + 1
    denom = math.log(n + 1)
    return {x: (math.log((n + 1) / (1 + d)) / denom if denom else 1.0) for x, d in df.items()}


def rank_evidence(body: str, query: str) -> tuple[str, list[Ranked], tuple[str, ...]]:
    """(query type, sentences best first, query concepts)."""
    qtype = query_type(query)
    qset = tuple(sorted(set(concepts(query))))
    qnorm = normalize(query or "")
    sentences = split_sentences(body)
    sent_concepts = [concepts(s) for s in sentences]
    weight = _discriminativeness(sent_concepts)
    ranked: list[Ranked] = []
    for i, (sent, cs_list) in enumerate(zip(sentences, sent_concepts)):
        cs = set(cs_list)
        overlap = tuple(x for x in qset if x in cs)
        snorm = normalize(sent)
        # a concept the question mentions and the body never does is maximally
        # discriminative, and its absence here is exactly the signal we want
        concept_score = 2.0 * sum(weight.get(x, 1.0) for x in overlap)
        score = concept_score + type_bonus(qtype, sent)
        score += 0.35 * sum(1 for x in qset if x in snorm)
        if bool(_NEG_RE.search(qnorm)) != bool(_NEG_RE.search(snorm)):
            score -= 0.4
        ranked.append(Ranked(i, sent, round(score, 6), overlap, round(concept_score, 6)))
    # earliest sentence wins ties, so ranking never depends on iteration order
    ranked.sort(key=lambda r: (-r.score, r.index))
    return qtype, ranked, qset


# --------------------------------------------------------------------------
# typed span extraction
# --------------------------------------------------------------------------
def _clean(s: str) -> str:
    return re.sub(r"[.!?]+$", "", (s or "").strip().strip(",;: \t")).strip()


_WHERE_1 = re.compile(r"\b(?:centered|located|positioned|placed|found|stored|kept)\s+"
                      r"(?:in|at|on|near|inside|within)?\s*"
                      r"(\[[^\]]+\]|\([^)]+\)|[^,.;!?]+)", re.I)
_WHERE_2 = re.compile(r"\[[^\]]+\]|\([^)]+\)")
_WHERE_3 = re.compile(r"\b(?:in|at|on|near|inside|within|outside|above|below|left of|right of)\s+"
                      r"([^,.;!?]+)", re.I)
_WHEN = re.compile(r"\b(?:\d{1,2}:\d{2}\s*(?:am|pm)?|\d{4}|monday|tuesday|wednesday|thursday|"
                   r"friday|saturday|sunday|january|february|march|april|may|june|july|august|"
                   r"september|october|november|december|today|tomorrow|yesterday)\b", re.I)
_COUNT = re.compile(r"\b\d+(?:\.\d+)?(?:\s+(?:percent|meters?|centimeters?|millimeters?|seconds?|"
                    r"minutes?|hours?|days?|items?|objects?|samples?|trials?|times?|faults?))?", re.I)
_WHY = re.compile(r"\b(?:because|since|due to)\s+(.+?)(?:[.!?]|$)", re.I)
_HOW = re.compile(r"\b(?:by|through|using|via|with)\s+(.+?)(?:[.!?]|$)", re.I)
_NAME = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")


def extract_span(sentence: str, query: str, qtype: str) -> str | None:
    """Pull out the sub-span of the sentence whose type matches the query type.

    Returning the whole sentence is the last resort, never the first: the point
    of typing the query is to answer with the *thing asked for*.
    """
    s = sentence or ""
    if qtype == "where":
        for rx, group in ((_WHERE_1, 1), (_WHERE_2, 0), (_WHERE_3, 1)):
            m = rx.search(s)
            if m:
                return _clean(m.group(group))
    elif qtype == "when":
        m = _WHEN.search(s)
        if m:
            return _clean(m.group(0))
    elif qtype in ("count", "amount"):
        m = _COUNT.search(s)
        if m:
            return _clean(m.group(0))
    elif qtype == "why":
        m = _WHY.search(s)
        if m:
            return _clean(m.group(1))
    elif qtype == "how":
        m = _HOW.search(s)
        if m:
            return _clean(m.group(1))
    elif qtype == "who":
        in_query = set(_NAME.findall(query or ""))
        for name in _NAME.findall(s):
            if name not in in_query:
                return _clean(name)
    elif qtype == "boolean":
        return "no" if _NEG_RE.search(normalize(s)) else "yes"

    # fall back: a copular definition, then the object of the principal verb
    cs = concepts(query)
    if len(cs) >= 2:
        subject = re.escape(" ".join(cs[-2:]))
        m = re.search(subject + r"\s+(?:is|are|means|refers to)\s+(.+?)(?:[.!?]|$)", s, re.I)
        if m:
            return _clean(m.group(1))
    toks = tokenize(s)
    types = [lexical_type(t) for t in toks]
    if "VERB" in types or "AUX" in types:
        vi = min(i for i, t in enumerate(types) if t in ("VERB", "AUX"))
        obj: list[str] = []
        for i in range(vi + 1, len(toks)):
            if types[i] == "PUNCT":
                break
            if types[i] == "PREP" and obj:
                break
            if types[i] == "DET" and not obj:
                continue
            obj.append(toks[i])
        if obj:
            return _clean(" ".join(obj))
    return _clean(s) or None


@dataclass
class Answer:
    """What the answerer concluded, and why. ``abstain`` is not an error state."""

    text: str | None
    abstain: bool
    qtype: str
    evidence: str | None = None
    score: float = 0.0
    reason: str = ""
    ranked: tuple[Ranked, ...] = field(default_factory=tuple)


def answer(body: str, query: str, *, threshold: float = EVIDENCE_THRESHOLD,
           admit_on: str = "concepts") -> Answer:
    """Answer from the body, or decline.

    Three ways to decline, and all three are declines rather than fallbacks: no
    sentence clears the evidence threshold; the sentence that did shares nothing
    but shape with the question; or no span of the required type can be pulled
    from it.

    ``admit_on`` is the one place this departs from the source, and the departure
    was made on a measurement. The source tested the *total* score against 2.0 --
    a threshold chosen because one shared concept is worth exactly 2.0 -- but the
    type bonus is worth 2.0 or 3.0 by itself, so a sentence with no point of
    contact with the question clears the bar purely for having the right shape.

    ``"concepts"`` (default) tests the overlap term alone, so the type bonus
    *ranks* candidates but does not *admit* them; ``"total"`` restores the
    source's rule exactly. Measured on ``evidence_qa`` over 400 episodes at seed
    1000, that is 48.4% of the unanswerable questions answered against 6.5%, for
    a coverage of 0.80 against 0.64. Those are ledger rows under the
    ``abstention`` experiment, and ``results/abstention.json`` is the view; the
    numbers this docstring used to carry (43% and 4%) were from an earlier
    scoring and had nothing to say that they were stale, which is the whole
    reason a summary field is not allowed to be the source.
    """
    qtype, ranked, _q = rank_evidence(body, query)
    best = ranked[0] if ranked else None
    if best is None:
        return Answer(None, True, qtype, None, 0.0, "the body contains no sentences", ())
    admitted = best.score if admit_on == "total" else best.concept_score
    if admitted < threshold:
        return Answer(None, True, qtype, None, best.score,
                      "no sentence carried enough conceptual evidence: the body has the right "
                      "shape but is not about the thing asked" if best.score >= threshold else
                      "no supporting sentence crossed the evidence threshold",
                      tuple(ranked[:5]))
    span = extract_span(best.sentence, query, qtype)
    if not span:
        return Answer(None, True, qtype, best.sentence, best.score,
                      "supporting sentence found but no span of the required type",
                      tuple(ranked[:5]))
    return Answer(span, False, qtype, best.sentence, best.score, "evidence-bound extraction",
                  tuple(ranked[:5]))
