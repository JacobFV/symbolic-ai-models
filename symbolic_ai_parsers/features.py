"""Three views of a prompt, and the one I got wrong.

The cross-language experiment turns on keeping "the shape of the document" and
"the words in it" apart, so they are separate functions rather than one function
with a flag. A parser asks for one and says which in its registration, so a
table row always states what the parser was allowed to see.

``word_features`` reads word identity, hashed into a fixed vector so that
retrieval is a matrix multiply. It is the part that cannot survive translation.

``layout_features`` was meant to be the part that does: punctuation, line
structure, and coarse token shape. **It is not, and that is the most useful
thing measured in this package.** It reads token counts, mean token length, and
how many tokens are ASCII — and every one of those is a fact about the
*tokenisation*, not about the layout. Chinese splits into far more, far shorter,
non-ASCII pieces for the same document, so the vector moves wholesale. Measured
on held-out **training** episodes (seeds 200-201, never the eval range), nearest
-neighbour lesson identification:

===================  =======  =======  =======  =======
feature set          english  chinese  turkish  swahili
===================  =======  =======  =======  =======
``layout_features``    0.983    0.014    0.084    0.966
``shape_features``     0.933    0.690    0.860    0.860
===================  =======  =======  =======  =======

So ``shape_features`` is the corrected one: punctuation counts and line
structure only, nothing that counts or measures tokens. It costs 0.05 in English
and buys 0.68 in Chinese, and ``template-002`` uses it while ``template-001``
keeps ``layout_features`` so the difference stays measured rather than asserted.

Two further things fell out of that measurement and are recorded because both
were tried and one is a null:

* **NFKC is not enough for CJK punctuation.** It folds ``：`` and ``；`` (which
  are compatibility forms) but not ``、`` or ``。`` (which are distinct
  characters). The ideographic comma is the list separator in the Chinese
  rendering, so leaving it unfolded reads as a document with no separators:
  Chinese identification is 0.212 without :data:`CJK_FOLD` and 0.690 with it.
* **Counting identifiers and digits looks language-independent and is not.**
  Adding "how many ASCII identifier tokens" raised English to 0.969 and dropped
  Chinese to 0.159, because in English that count includes every English word
  and in Chinese it includes only the untranslated symbols. It is a
  vocabulary-size feature wearing a shape feature's name. Not used.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np

from symbolic_ai_models.data.tokenizer import split_words

__all__ = ["normalise", "fold", "words_of", "layout_features", "LAYOUT_DIM",
           "shape_features", "SHAPE_DIM", "word_features", "WORD_DIM",
           "standardise", "CJK_FOLD"]

#: CJK punctuation that NFKC leaves alone because it is not a compatibility
#: form. Each entry is the ASCII mark playing the same role in the rendering.
#: Written down once and not tuned; its worth is priced in the module docstring.
CJK_FOLD = str.maketrans({
    "、": ",", "。": ".", "；": ";", "：": ":", "，": ",", "？": "?", "！": "!",
    "（": "(", "）": ")", "《": "<", "》": ">", "「": '"', "」": '"',
    "【": "[", "】": "]", "·": ".", "…": ".",
})

#: Punctuation whose count is a layout fact. Fixed list, in a fixed order, so a
#: feature index means the same thing in every run.
_PUNCT = tuple(":;,.?!|()[]{}<>=+-*/%#_\"'")

_BULLET = re.compile(r"^\s*[-*•]\s")
_DIGITS = re.compile(r"^\d+$")
_ASCII_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

LAYOUT_DIM = len(_PUNCT) + 12
SHAPE_DIM = len(_PUNCT) + 3
WORD_DIM = 512


def normalise(text: str) -> str:
    """NFKC. Folds full-width punctuation onto ASCII so ``：`` is a colon."""
    return unicodedata.normalize("NFKC", text)


def fold(text: str) -> str:
    """NFKC, then :data:`CJK_FOLD`. What NFKC alone leaves as a foreign mark."""
    return normalise(text).translate(CJK_FOLD)


def shape_features(text: str) -> np.ndarray:
    """Punctuation counts and line structure. Nothing that counts tokens.

    The corrected ``layout_features``; see the module docstring for the numbers
    that made the correction, all of them measured on training seeds.
    """
    t = fold(text)
    lines = t.split("\n")
    return np.array([t.count(p) for p in _PUNCT] + [
        len(lines),
        sum(bool(_BULLET.match(l)) for l in lines),
        sum(not l.strip() for l in lines),
    ], dtype=np.float64)


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
