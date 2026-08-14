"""A second word splitter, because the shared one is orthographic.

``symbolic_ai_core.data.tokenizer.split_words`` is the repo's one splitter and
:func:`symbolic_ai_parsers.features.words_of` wraps it. It is used for the graph
labels, for the piece vocabulary and for every parser here, and that sharing is
deliberate: a token on one side and a label on the other have to be comparable.

It is also **the largest single language-dependence in this package**, and it is
in the substrate rather than in any model. Its word branch is
``[^\\W\\d_]+`` — a maximal run of characters Python calls letters — and two
things follow that have nothing to do with parsing:

* **Scriptio continua runs together.** Chinese, Japanese, Thai, Lao and Khmer
  write without spaces, so ``alice和面包`` ("alice and bread") is *one* token.
  The argument ``alice`` is then not findable by string match, and
  :class:`~symbolic_ai_parsers.treebank.Treebank` — which locates a clause by
  finding its arguments in it — simply loses the clause.
* **Combining marks are not letters.** A Tamil vowel sign is category ``Mn``,
  which is not ``\\w``, so it falls to the single-character branch and every
  Tamil word shatters into graphemes.

Measured on 179 lessons, 2 episodes per lesson, clause coverage
(:attr:`Treebank.coverage` — the share of clause-shaped graph nodes that found a
segment at all, i.e. the ceiling on everything downstream):

=========  ==============  ==============
language   ``words_of``    :func:`words`
=========  ==============  ==============
english    0.792           0.792
chinese    0.466           (see finding)
tamil      0.755           (see finding)
japanese   0.464           (see finding)
=========  ==============  ==============

So a "cross-language parser" number computed on the shared splitter is partly a
statement about Unicode character categories. This module supplies the
alternative; it does **not** replace the old one anywhere, because
``split_words`` also defines the piece vocabulary and the graph-side labels and
changing it would silently redefine every published number in the repo.
``tests/test_curriculum_fingerprint.py`` exists to make that impossible.

The rule
--------

1. NFKC, then :data:`~symbolic_ai_parsers.features.CJK_FOLD`, so ``、`` is a
   comma. (Same normalisation the old path uses; NFKC alone does not fold it.)
2. One character is one token for the scripts that do not write spaces —
   CJK ideographs, kana, hangul syllables, Thai, Lao, Khmer, Myanmar. This is
   the standard no-dictionary fallback and it is uniform, so it cannot be tuned
   per language.
3. A letter run carries its combining marks. ``ந`` + ``ி`` is one token.
4. Digits, punctuation and a total catch-all, exactly as the old pattern has
   them, so nothing is ever dropped.

Rule 2 is a real approximation: it segments Chinese into characters rather than
words. That is the honest thing to do without a Chinese dictionary, it is what
the argument-matching in the treebank actually needs (the *Latin* argument now
separates from the ideographs around it), and it is applied identically to every
language so it is not a per-language knob.
"""

from __future__ import annotations

import re
import unicodedata

from .features import fold

__all__ = ["words", "SCRIPTIO_CONTINUA"]

#: Blocks written without word spaces. One character, one token.
SCRIPTIO_CONTINUA = (
    "ᄀ-ᇿ"      # hangul jamo
    "⺀-⿟"      # kangxi radicals
    "぀-ヿ"      # hiragana, katakana
    "㄰-㆏"      # hangul compatibility jamo
    "㆐-㆟"      # kanbun
    "ㇰ-ㇿ"      # katakana extensions
    "㐀-䶿"      # CJK ext A
    "一-鿿"      # CJK unified
    "ꥠ-꥿"      # hangul jamo ext A
    "가-퟿"      # hangul syllables
    "豈-﫿"      # CJK compatibility
    "︰-﹏"      # CJK compatibility forms
    "･-ﾟ"      # halfwidth katakana
    "฀-๿"      # thai
    "຀-໿"      # lao
    "က-႟"      # myanmar
    "ក-៿"      # khmer
    "ᥐ-᧟"      # tai le / new tai lue
)


def _marks() -> str:
    """Every combining mark below U+2000, as a character-class body.

    Built by scanning rather than written down: an enumeration of the ranges
    somebody remembered is exactly the failure mode the shared splitter's
    docstring already records for its own alternation.
    """
    out = []
    for cp in range(0x300, 0x2000):
        ch = chr(cp)
        if unicodedata.category(ch)[0] == "M":
            out.append(ch)
    return re.escape("".join(out))


_MARKS = _marks()

_WORD_RE = re.compile(
    rf"[{SCRIPTIO_CONTINUA}][{_MARKS}]*"  # one character of a spaceless script
    # Letters, carrying their marks. The lookahead is load-bearing: without it
    # the letter branch matches ``alice和面包`` whole, because the alternation
    # is tried left to right *at each position* and position 0 is not CJK.
    rf"|(?:(?![{SCRIPTIO_CONTINUA}])[^\W\d_][{_MARKS}]*)+"
    rf"|\d[\d{_MARKS}]*"                 # a number
    rf"|[^\s\w]"                         # punctuation
    rf"|[^\s]",                          # total: nothing is ever dropped
    re.UNICODE,
)


def words(text: str) -> list[str]:
    """Script-aware word split, on folded text. The v2 arm of the experiment."""
    return _WORD_RE.findall(fold(text))
