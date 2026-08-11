"""Next-token prediction over the rendered episode."""

from __future__ import annotations

import collections
import math
from typing import Sequence

import torch

from ..data.batch import IGNORE, collate_text
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
        """Train on every position; report the answer separately.

        The loss is over the whole sequence, because that is what language
        modelling is and restricting it would throw away most of the signal. The
        *reporting* splits, because across the curriculum only about **1.4%** of
        scored positions are the answer and the other 98.6% is the question plus
        the fixed scaffolding around it ("Answer with exactly one of:", "Reply
        with the answer only."). An undifferentiated ``token_bits`` therefore
        measures template reproduction almost entirely, and a model can look
        excellent on it while never once getting an answer right.

        ``answer_*`` is the same cross-entropy restricted to the answer's own
        tokens. It is not added to the loss and carries no gradient.
        """
        loss, counts = score_block(out.symbol_logits, batch.target_tokens, "token")
        if batch.answer_mask is not None:
            answer_targets = torch.where(batch.answer_mask, batch.target_tokens,
                                         torch.full_like(batch.target_tokens, IGNORE))
            with torch.no_grad():
                _, answer_counts = score_block(out.symbol_logits.detach(),
                                               answer_targets, "answer")
            counts = {**counts, **answer_counts}
        return TaskOutput(loss=loss, counts=counts)

    def summarize(self, totals: Totals) -> dict[str, float]:
        return {**ratio(totals, "token"), **ratio(totals, "answer")}

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

        # The answer span gets its own floor. It has to: answers are drawn from
        # a far narrower distribution than prose, so scoring an answer against a
        # floor fitted on the whole text would flatter any model that had merely
        # learned which words are answer-shaped.
        answer_counts: collections.Counter[int] = collections.Counter()
        train_answers: collections.Counter[int] = collections.Counter()
        for ep in train:
            train_answers.update(tok.encode(ep.answer))
        for ep in episodes:
            answer_counts.update(tok.encode(ep.answer))

        out = self._unigram_floor(eval_counts, train_counts, len(tok), "token")
        out.update(self._unigram_floor(answer_counts, train_answers, len(tok),
                                       "answer"))
        return out

    @staticmethod
    def _unigram_floor(evaluation: collections.Counter, train: collections.Counter,
                       vocab: int, prefix: str) -> dict[str, float]:
        n, total = sum(evaluation.values()), sum(train.values())
        if not n or not total:
            return {f"{prefix}_acc": float("nan"), f"{prefix}_bits": float("nan"),
                    f"{prefix}_n": 0.0}
        # Laplace smoothing, so a symbol the training text never used is
        # expensive rather than infinitely so.
        denom = total + vocab
        nll = sum(c * -math.log2((train[t] + 1) / denom)
                  for t, c in evaluation.items())
        best = max(train, key=lambda t: train[t])
        return {f"{prefix}_acc": evaluation.get(best, 0) / n,
                f"{prefix}_bits": nll / n, f"{prefix}_n": float(n)}
