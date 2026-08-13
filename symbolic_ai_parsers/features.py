"""Two views of a prompt: its layout, and its words.

The whole cross-language experiment turns on keeping these apart, so they are
separate functions in one file rather than one function with a flag.

``layout_features`` reads only punctuation, line structure and coarse token
shape. Every one of those survives translation in this curriculum — checked, not
assumed: Chinese, Turkish and Swahili renderings all keep the ``"\\n  - "``
bullet, the blank line before the answer options, and the ``|`` between them.
Chinese writes ``：`` where English writes ``:``, which would otherwise read as a
different document, so the text is NFKC-normalised first. That normalisation is
a Unicode standard applied uniformly and before any number was looked at; it is
not a knob and it is not fitted.

``word_features`` reads word identity, hashed into a fixed vector so that
retrieval is a matrix multiply rather than a set intersection. It is exactly the
part that cannot survive translation, and the point of the experiment is to find
out how much of a parser's score was resting on it.

The two are never concatenated into one vector by default. A parser asks for one
or the other and says which in its registration, so a table row always states
what the parser was allowed to see.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from symbolic_ai_models.data.tokenizer import split_words

__all__ = ["normalise", "words_of", "layout_features", "LAYOUT_DIM",
           "word_features", "WORD_DIM", "standardise"]

#: Punctuation whose count is a layout fact. Fixed list, in a fixed order, so a
#: feature index means the same thing in every run.
_PUNCT = tuple(":;,.?!|()[]{}<>=+-*/%#_\"'")

_BULLET = re.compile(r"^\s*[-*•]\s")
_DIGITS = re.compile(r"^\d+$")
_ASCII_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

LAYOUT_DIM = len(_PUNCT) + 12
WORD_DIM = 512


def normalise(text: str) -> str:
    """NFKC. Folds full-width punctuation onto ASCII so ``：`` is a colon."""
    return unicodedata.normalize("NFKC", text)


def words_of(text: str) -> list[str]:
    """The repo's own word splitter, on normalised text. One splitter, shared
    with the graph side, so a token here and a label there are comparable."""
    return split_words(normalise(text))


def layout_features(text: str) -> np.ndarray:
    """Punctuation, lines, bullets and coarse token shape. No word identity."""
    t = normalise(text)
    lines = t.split("\n")
    toks = split_words(t)
    n = max(len(toks), 1)
    digits = sum(bool(_DIGITS.match(w)) for w in toks)
    ascii_w = sum(bool(_ASCII_WORD.match(w)) for w in toks)
    nonascii = sum(any(ord(c) > 127 for c in w) for w in toks)
    bullets = sum(bool(_BULLET.match(l)) for l in lines)
    blanks = sum(not l.strip() for l in lines)
    lens = [len(w) for w in toks] or [0]
    counts = [t.count(p) for p in _PUNCT]
    return np.array(counts + [
        len(lines), bullets, blanks, len(t) / 100.0, len(toks),
        len(set(toks)), digits, ascii_w, nonascii,
        sum(lens) / n, max(lens), sum(1 for w in toks if len(w) >= 5),
    ], dtype=np.float64)


def word_features(text: str) -> np.ndarray:
    """Hashed bag of words, L2-normalised. Word identity and nothing else."""
    v = np.zeros(WORD_DIM, dtype=np.float64)
    for w in words_of(text):
        v[hash_word(w)] += 1.0
    norm = float(np.linalg.norm(v))
    return v / norm if norm else v


def hash_word(word: str) -> int:
    """A stable hash. ``hash()`` is randomised per process, and this repo has
    already had a number flap between runs because something rested on it."""
    h = 2166136261
    for b in word.encode("utf-8"):
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h % WORD_DIM


def standardise(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """``(mean, scale)`` of a feature matrix. Scale is never zero."""
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale < 1e-9] = 1.0
    return mean, scale
