"""Lexical types and the transition table over them.

Ported verbatim from symbolic-ai-001 (`agents/symcontrol_001/lexicon.py`).

The source system this release reimplements carried a 35,000-entry tagged
lexicon shipped alongside the model. That is a perfectly respectable thing to
do -- but it makes the demonstration depend on a downloaded artifact, and it
hides which part of the behaviour is *knowledge* and which is *rule*. So the
typing here is split into the two things it actually is:

  **closed classes, written down.** Determiners, prepositions, pronouns,
  auxiliaries, conjunctions and the negator are finite lists that have not
  changed in centuries. Enumerating them is not cheating and not "hardcoding a
  task"; it is stating the part of English that is genuinely a fixed inventory.

  **open classes, decided morphologically.** Everything else gets its type from
  its ending, by the same ordered rule chain the source used as its last-resort
  guesser. No lexicon, no download, no per-corpus tuning.

The *transition constraints* are then counted from whatever corpus the agent is
shown -- they are data, not a table someone wrote. ``type_bigrams`` is the whole
of that: a count of which type follows which. A transition never observed scores
zero and is therefore penalized, which is the only sense in which this system
"knows grammar".

Nothing here hashes anything, so the typing is identical in every process.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Mapping, Sequence

__all__ = ["TOKEN_RE", "tokenize", "normalize", "lexical_type", "lemma", "type_bigrams",
           "DET", "PREP", "PRON", "AUX", "CONJ", "CLOSED", "OPEN_TYPES", "BOS"]

BOS = "<s>"

# The tokenizer is first-match alternation, deliberately: a bracketed or
# parenthesized span (a coordinate, a vector) is ONE token, because splitting it
# would destroy the only thing that makes it answerable as a location.
TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?|\[[^\]]+\]|\([^)]+\)|[^\w\s]")

DET = frozenset("a an the this that these those his her its their our my your no every "
                "each some any all both either neither which what whose".split())
PREP = frozenset("of in on at by for from with to into onto over under near about after before "
                 "during through within without inside outside between among across against "
                 "toward towards upon around behind beside beyond below above off out up down "
                 "than as like per via".split())
PRON = frozenset("i you he she it we they me him us them who whom myself yourself himself "
                 "herself itself ourselves themselves one".split())
AUX = frozenset("is are was were be been being am do does did have has had can could will "
                "would shall should may might must ought".split())
CONJ = frozenset("and or but nor so yet if then because although though while whereas "
                 "unless until when where".split())
NEG = frozenset({"not", "n't", "never", "no"})

CLOSED: dict[str, str] = {}
for _w in DET:
    CLOSED[_w] = "DET"
for _w in PREP:
    CLOSED.setdefault(_w, "PREP")
for _w in PRON:
    CLOSED.setdefault(_w, "PRON")
for _w in AUX:
    CLOSED.setdefault(_w, "AUX")
for _w in CONJ:
    CLOSED.setdefault(_w, "CONJ")
for _w in NEG:
    CLOSED.setdefault(_w, "NEG")

OPEN_TYPES = ("NOUN", "VERB", "ADJ", "ADV", "NUM")


def normalize(w: str) -> str:
    return w.lower().replace("’", "'")


def tokenize(s: str) -> list[str]:
    return TOKEN_RE.findall(s or "")


def lexical_type(word: str) -> str:
    """The word's type: closed-class lookup, then morphology, then NOUN.

    Order is load-bearing and follows the source's chain. ``VALUE`` is its own
    type so that a coordinate never gets treated as a noun phrase.
    """
    if not word:
        return "NOUN"
    if (word[0] == "[" and word[-1] == "]") or (word[0] == "(" and word[-1] == ")"):
        return "VALUE"
    if re.fullmatch(r"[^\w\s]", word):
        return "PUNCT"
    w = normalize(word)
    if w in CLOSED:
        return CLOSED[w]
    if w[0].isdigit():
        return "NUM"
    for suffix, t in (("ly", "ADV"), ("ing", "VERB"), ("ed", "VERB"),
                      ("ous", "ADJ"), ("ive", "ADJ"), ("al", "ADJ"), ("able", "ADJ")):
        if w.endswith(suffix) and len(w) > len(suffix) + 1:
            return t
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return "NOUN"
    return "NOUN"


def lemma(word: str) -> str:
    """Rule-based stemming, so that ``sensors`` and ``sensor`` are one concept.

    Deliberately conservative: an over-eager stemmer merges concepts that the
    overlap score then treats as evidence they are not.
    """
    w = normalize(word)
    t = lexical_type(word)
    if t == "VERB":
        if w.endswith("ing") and len(w) > 5:
            return w[:-3]
        if w.endswith("ed") and len(w) > 4:
            return w[:-2]
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and not w.endswith(("ss", "us", "is")) and len(w) > 3:
        return w[:-1]
    return w


def type_bigrams(token_streams: Iterable[Sequence[str]]) -> dict[str, dict[str, int]]:
    """Count which type follows which, over whatever corpus we were shown.

    This is the "part-of-speech transition constraint": it is *counted*, so an
    unseen transition scores zero and a common one scores high, and the table is
    a property of the corpus rather than of the author's intuitions.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for stream in token_streams:
        prev = BOS
        for tok in stream:
            t = lexical_type(str(tok))
            counts[prev][t] += 1
            prev = t
    return {k: dict(sorted(v.items())) for k, v in sorted(counts.items())}
