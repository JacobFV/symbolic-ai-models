"""Turning a trained model into something the curriculum can grade.

Perplexity is not the question the curriculum asks. It asks whether the right
answer was chosen out of a stated set, and it insists on reporting the floor for
that set alongside — because "55% correct" means one thing on a yes/no lesson
and something else entirely on a nine-way one.

A language model answers a multiple-choice question by scoring each option as a
continuation of the prompt and taking the best. Two details matter enough to
name:

* **Length normalisation.** Raw likelihood prefers short options, which on a
  lesson whose options are ``o0``..``o9`` is harmless and on one whose options
  are whole phrases is fatal. Scores are mean log-probability per token.
* **Only the option's own tokens are scored.** The prompt is identical across
  the options, so including it adds the same constant to every score and
  nothing else, but it also dominates the mean and would drown the signal.

The result is the same accuracy/floor/lift triple ``langcurriculum`` reports, on
episodes drawn from seeds the model was never trained on.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from typing import Sequence

import torch

from .data.batch import collate_text
from .data.curriculum import Episode
from .data.tokenizer import SymbolTokenizer
from .models.base import SymbolicModel
from .tasks.base import lift

__all__ = ["ChoiceResult", "CurriculumReport", "score_choices",
           "evaluate_choices", "as_text_agent"]


@dataclass
class ChoiceResult:
    lesson_id: str
    instance_id: str
    answer: str
    predicted: str
    correct: bool
    n_choices: int


@dataclass
class CurriculumReport:
    """Per-lesson accuracy against the floor the episodes themselves define."""

    results: list[ChoiceResult] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return sum(r.correct for r in self.results) / max(len(self.results), 1)

    @property
    def floor(self) -> float:
        """The higher of the two baselines ``langcurriculum`` uses: guessing
        uniformly within each episode's own answer set, and always answering the
        most common gold label. Taking the max is what keeps a lesson with a
        skewed label distribution from looking solved."""
        return max(self._uniform_floor(), self._majority_floor())

    def _uniform_floor(self) -> float:
        if not self.results:
            return 0.0
        return sum(1.0 / max(r.n_choices, 1) for r in self.results) / len(self.results)

    def _majority_floor(self) -> float:
        by_lesson: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for r in self.results:
            by_lesson[r.lesson_id][r.answer] += 1
        hits = sum(max(c.values()) for c in by_lesson.values())
        return hits / max(len(self.results), 1)

    @property
    def lift(self) -> float:
        return lift(self.accuracy, self.floor)

    def by_lesson(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        groups: dict[str, list[ChoiceResult]] = collections.defaultdict(list)
        for r in self.results:
            groups[r.lesson_id].append(r)
        for lesson, rs in sorted(groups.items()):
            sub = CurriculumReport(rs)
            out[lesson] = {"n": len(rs), "acc": sub.accuracy,
                           "floor": sub.floor, "lift": sub.lift}
        return out

    def table(self, limit: int = 30) -> str:
        rows = sorted(self.by_lesson().items(), key=lambda kv: -kv[1]["lift"])
        head = f"{'lesson':<38}{'n':>5}{'acc':>8}{'floor':>8}{'lift':>8}"
        line = "-" * len(head)
        body = [f"{k:<38}{v['n']:>5}{v['acc']:>8.3f}{v['floor']:>8.3f}{v['lift']:>8.3f}"
                for k, v in rows[:limit]]
        if len(rows) > limit:
            body.append(f"... {len(rows) - limit} more lessons")
        total = (f"{'macro-average':<38}{len(self.results):>5}"
                 f"{self.accuracy:>8.3f}{self.floor:>8.3f}{self.lift:>8.3f}")
        return "\n".join([head, line, *body, line, total])


@torch.no_grad()
def score_choices(model: SymbolicModel, tok: SymbolTokenizer, prompt: str,
                  choices: Sequence[str], *, device: torch.device | str = "cpu",
                  max_len: int = 512) -> list[float]:
    """Mean log-probability per token of each choice, continuing ``prompt``."""
    if not choices:
        return []
    scores: list[float] = []
    for choice in choices:
        ids = tok.encode(prompt + "\n", bos=True)
        cont = tok.encode(choice, eos=True)
        seq = (ids + cont)[-max_len:]
        n_cont = min(len(cont), len(seq) - 1)
        x = torch.tensor(seq, dtype=torch.long, device=device)[None]
        batch = _text_batch(x, tok, device)
        logits = model(batch).symbol_logits[0].float()
        logp = torch.log_softmax(logits[:-1], dim=-1)
        targets = x[0, 1:]
        picked = logp.gather(-1, targets[:, None]).squeeze(-1)
        scores.append(float(picked[-n_cont:].mean()) if n_cont > 0 else float("-inf"))
    return scores


def _text_batch(x: torch.Tensor, tok: SymbolTokenizer, device):
    from .data.graph import TYPE_TO_ID
    from .data.batch import SymbolicBatch
    B, L = x.shape
    return SymbolicBatch(
        tokens=x,
        types=torch.full((B, L), TYPE_TO_ID["text"], dtype=torch.long, device=device),
        pad_mask=torch.ones((B, L), dtype=torch.bool, device=device),
        depth=torch.zeros((B, L), dtype=torch.long, device=device),
        causal=True, rel=None, meta={"task": "lm"})


def evaluate_choices(model: SymbolicModel, tok: SymbolTokenizer,
                     episodes: Sequence[Episode], *,
                     device: torch.device | str = "cpu",
                     max_len: int = 512) -> CurriculumReport:
    """Run the curriculum's own question against a trained model."""
    was_training = model.training
    model.eval()
    report = CurriculumReport()
    for ep in episodes:
        if not ep.choices:
            continue
        scores = score_choices(model, tok, ep.prompt, ep.choices,
                               device=device, max_len=max_len)
        best = ep.choices[max(range(len(scores)), key=lambda i: scores[i])]
        report.results.append(ChoiceResult(
            lesson_id=ep.lesson_id, instance_id=ep.instance_id, answer=ep.answer,
            predicted=best, correct=best == ep.answer, n_choices=len(ep.choices)))
    if was_training:
        model.train()
    return report


#: The line ``langcurriculum``'s default presentation writes the answer set on.
#: Matched by its separator rather than by its wording, so it survives the
#: episode being rendered in Turkish or Swahili.
_OPTIONS_RE = re.compile(r"^[^\n:]*:\s*(.+?\s+\|\s+.+)$", re.MULTILINE)


def as_text_agent(model: SymbolicModel, tok: SymbolTokenizer, *,
                  device: torch.device | str = "cpu", max_len: int = 512):
    """A ``Callable[[str], str]`` for ``langcurriculum.evaluate``.

    Interop, for callers who want the library's own report rather than this
    one. It has to recover the answer set by parsing it back out of the prompt,
    which :func:`evaluate_choices` does not — that reads the choices off the
    episode. Prefer :func:`evaluate_choices` where you have the episodes; this
    exists for pointing ``lc.evaluate`` at a trained model directly.
    """
    def agent(prompt: str) -> str:
        m = _OPTIONS_RE.search(prompt)
        if not m:
            return ""
        choices = [c.strip() for c in m.group(1).split("|") if c.strip()]
        if not choices:
            return ""
        scores = score_choices(model, tok, prompt, choices,
                               device=device, max_len=max_len)
        return choices[max(range(len(scores)), key=lambda i: scores[i])]
    return agent
