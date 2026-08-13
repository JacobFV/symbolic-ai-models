"""Find the training episode this text is a re-draw of.

Both learned parsers here start the same way: the curriculum is 179 templates,
so the first thing to recover from a string is *which template*. That is a
nearest-neighbour lookup, and the only question is what it is allowed to look
at — which is the whole cross-language experiment, so the two answers are two
classes rather than a boolean argument.

:class:`LayoutIndex` sees punctuation and line structure. :class:`WordIndex`
sees word identity. Neither sees both, so a parser cannot quietly hedge, and a
row in the results table says exactly which signal produced it.

Both report ``retrieval_acc`` — how often the retrieved neighbour came from the
same lesson. That number is the mechanism, not the outcome, and it is worth more
than the outcome when the outcome moves: a parse that collapses because the
lookup went to the wrong lesson is a different failure from a parse that
collapses with the right template in hand.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .features import layout_features, standardise, word_features

__all__ = ["LayoutIndex", "WordIndex"]


class LayoutIndex:
    """Nearest neighbour on standardised layout features. Language-independent."""

    kind = "layout"

    def __init__(self) -> None:
        self._m: np.ndarray | None = None
        self._mean = self._scale = None

    def fit(self, texts: Sequence[str]) -> None:
        raw = np.stack([layout_features(t) for t in texts]) if texts else np.zeros((0, 1))
        self._mean, self._scale = standardise(raw)
        self._m = (raw - self._mean) / self._scale

    def query(self, text: str) -> int:
        if self._m is None or not len(self._m):
            return -1
        v = (layout_features(text) - self._mean) / self._scale
        # Squared Euclidean, argmin. ``argmin`` breaks ties toward the lower
        # index, which is deterministic and does not depend on hash order.
        return int(np.argmin(((self._m - v) ** 2).sum(axis=1)))

    def n_parameters(self) -> int:
        return 0 if self._m is None else int(self._m.size)


class WordIndex:
    """Nearest neighbour on a hashed bag of words. Dies when the words change."""

    kind = "words"

    def __init__(self) -> None:
        self._m: np.ndarray | None = None

    def fit(self, texts: Sequence[str]) -> None:
        self._m = (np.stack([word_features(t) for t in texts]) if texts
                   else np.zeros((0, 1)))

    def query(self, text: str) -> int:
        if self._m is None or not len(self._m):
            return -1
        v = word_features(text)
        # Both sides are L2-normalised, so a dot product is the cosine. An
        # all-zero query (nothing in common with anything) gives an all-zero
        # column and ``argmax`` returns 0, which is a real answer -- the first
        # exemplar -- and is scored as such rather than skipped.
        return int(np.argmax(self._m @ v))

    def n_parameters(self) -> int:
        return 0 if self._m is None else int(self._m.size)
