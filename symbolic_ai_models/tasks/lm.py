"""Next-token prediction over the rendered episode."""

from __future__ import annotations

import collections
import math
from typing import Sequence

from ..data.batch import collate_text
from ..data.curriculum import Episode
from ..data.tokenizer import SymbolTokenizer
from ..models.base import ModelOutput
from .base import Task, TaskOutput, Totals, ratio, score_block

__all__ = ["LanguageModelling"]


class LanguageModelling(Task):
    """The familiar objective, on prose the curriculum generated.

    The text is the prompt and its answer joined, so a model that gets good at
    this is at some point predicting the answer token and not only the question.
    That is what makes the language-modelling score comparable with the
    curriculum evaluation in :mod:`symbolic_ai_models.agent`, where the same head is
    asked to choose between the episode's options.
    """

    name = "lm"

    def __init__(self, max_len: int = 512) -> None:
        self.max_len = max_len

    def collate(self, episodes: Sequence[Episode], tok: SymbolTokenizer):
        return collate_text(episodes, tok, max_len=self.max_len)

    def compute(self, out: ModelOutput, batch) -> TaskOutput:
        loss, counts = score_block(out.symbol_logits, batch.target_tokens, "token")
        return TaskOutput(loss=loss, counts=counts)

    def summarize(self, totals: Totals) -> dict[str, float]:
        return ratio(totals, "token")

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode]) -> dict[str, float]:
        """A unigram model fitted on the training text, scored on the eval text.

        This is the right floor for next-token prediction: it knows exactly how
        often each symbol occurs and nothing at all about context, so any margin
        below it is the value of context. A model that does not beat it has
        learned the vocabulary and stopped.
        """
        train_counts: collections.Counter[int] = collections.Counter()
        for ep in train:
            train_counts.update(tok.encode(ep.text, bos=True, eos=True))
        eval_counts: collections.Counter[int] = collections.Counter()
        for ep in episodes:
            # Skip position 0: <bos> is given, never predicted, exactly as in
            # `collate_text`, where the target array is the sequence shifted.
            eval_counts.update(tok.encode(ep.text, bos=True, eos=True)[1:])

        n = sum(eval_counts.values())
        total, vocab = sum(train_counts.values()), len(tok)
        if not n or not total:
            return {"token_acc": float("nan"), "token_bits": float("nan"), "token_n": 0.0}

        # Laplace smoothing, so a symbol the training text never used is
        # expensive rather than infinitely so.
        denom = total + vocab
        nll = sum(c * -math.log2((train_counts[t] + 1) / denom)
                  for t, c in eval_counts.items())
        best = max(train_counts, key=lambda t: train_counts[t])
        return {"token_acc": eval_counts.get(best, 0) / n,
                "token_bits": nll / n, "token_n": float(n)}
