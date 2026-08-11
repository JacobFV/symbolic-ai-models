"""seq-synth-001, as a predictive model: the hypothesis is a program.

A token sequence is a sequence of integers, so the synthesiser can be pointed
straight at it. At each position it holds a program — an expression over the
index, the two previous values and a few constants — that reproduces the prefix
it has seen, and its prediction for the next token is that program evaluated one
step further. When the program is contradicted it is thrown away and a new one
is enumerated from the prefix, shortest first, with observational-equivalence
pruning to keep the search tractable.

This is the one model here with **no training distribution to speak of**. A
pattern it has never encountered costs it nothing so long as the pattern is
expressible in the language, and a pattern that is not expressible costs it
everything — there is no partial credit and no smoothing inside the hypothesis.
That is the sharpest contrast in the repo with a network, which can only
reproduce what it was fitted on but degrades gracefully everywhere.

The expected result is bimodal and that is the point: near-useless on English
prose, where no short arithmetic program generates the next word, and genuinely
strong on the lessons whose content is a generated sequence. A single averaged
number would hide both halves, which is why the per-lesson breakdown in
``symbolic_ai_models eval --curriculum`` is worth more here than the aggregate.

Search is bounded — a maximum program size, a cap on programs enumerated, and a
cap on how many times one sequence may refit. When the budget runs out the model
abstains for the rest of the sequence rather than spending unbounded CPU, and
the abstention is reported.
"""

from __future__ import annotations

from typing import Sequence

from ...data.curriculum import Episode
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes
from .dsl import Program, SequenceSynthesizer

__all__ = ["SynthesisModel"]


@register("synth", doc="Enumerative program synthesis over token and label sequences.")
class SynthesisModel(RuleBasedModel):
    """Online synthesis: hold a program, predict from it, refit when refuted."""

    LEARNED = ("found", "attempts")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_size = int(cfg.get("max_size", 5))
        self.max_programs = int(cfg.get("max_programs", 20_000))
        self.max_refits = int(cfg.get("max_refits", 24))
        self.window = int(cfg.get("window", 24))
        self.min_run = int(cfg.get("min_run", 2))
        self.found = 0
        self.attempts = 0

    def _synth(self) -> SequenceSynthesizer:
        return SequenceSynthesizer(max_size=self.max_size,
                                   modulus=max(self.cfg.vocab_size, 2),
                                   max_programs=self.max_programs)

    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Nothing is fitted across episodes, and that is the claim.

        The synthesiser's whole argument is that it has no training
        distribution: it searches the same space for every sequence it is shown,
        so an unfamiliar pattern is no harder than a familiar one. Fitting
        anything here would quietly turn it into a different method, so the
        counters below only record what the search did.
        """
        self.found = 0
        self.attempts = 0

    # ---- text ---------------------------------------------------------
    def text_votes(self, ids: Sequence[int]) -> list[Votes]:
        return self._run(list(ids))

    def _run(self, seq: list[int]) -> list[Votes]:
        """Walk the sequence, refitting whenever the held program is refuted.

        Everything read at step ``t`` comes from ``seq[:t + 1]``: the program is
        fitted on the prefix and evaluated one step past it, so the value being
        predicted is never in the search's evidence.
        """
        out: list[Votes] = [ABSTAIN] * len(seq)
        synth = self._synth()
        program: Program | None = None
        run = 0
        refits = 0

        for t in range(len(seq)):
            prefix = seq[:t + 1]
            if program is not None:
                predicted = synth.predict_next(prefix, program)
                if predicted is not None and run >= self.min_run and t + 1 < len(seq):
                    # A program that has held for `min_run` steps is worth
                    # betting on; one that just appeared is not.
                    out[t] = ({predicted: 1.0}, min(0.4 + 0.1 * run, 0.9))
                if t + 1 < len(seq):
                    if predicted == seq[t + 1]:
                        run += 1
                        continue
                    program, run = None, 0
            if t + 1 >= len(seq) or refits >= self.max_refits:
                continue
            window = prefix[-self.window:]
            if len(window) <= 3:
                continue
            refits += 1
            self.attempts += 1
            program = synth.fit(window, min_index=2)
            run = 0
            if program is not None:
                self.found += 1
        return out

    # ---- graph --------------------------------------------------------
    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        """Synthesise over the pre-order label sequence.

        The same method, applied to structure instead of to order. A hidden node
        is predicted from a program fitted to the labels that precede it in the
        traversal — which is exactly right for the lessons whose graphs hold a
        generated sequence, and hopeless for the ones whose graphs hold a scene.
        """
        labels = view.labels
        out: dict[int, tuple[Votes, Votes]] = {}
        synth = self._synth()
        for i in view.hidden:
            prefix = [v for v in labels[:i] if v is not None]
            if len(prefix) <= 3:
                continue
            self.attempts += 1
            program = synth.fit(prefix[-self.window:], min_index=2)
            if program is None:
                continue
            self.found += 1
            predicted = synth.predict_next(prefix[-self.window:], program)
            if predicted is not None:
                out[i] = (({predicted: 1.0}, 0.6), ABSTAIN)
        return out

    def n_symbolic_parameters(self) -> int:
        """Six search knobs. The hypothesis is rebuilt per sequence and is not
        carried between episodes, so there is nothing else to count."""
        return 6
