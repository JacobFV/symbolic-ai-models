"""The floor: the best a parser can do without reading the text.

``symbolic_ai_models.tasks.base`` refuses to report a score without one, and the
argument is stronger here than there. These graphs are not independent draws
from anything: every episode of a lesson is the same record with the same field
names and roughly the same shape, so "emit the graph of some training episode
and ignore the input entirely" already recovers a good deal of the answer. A
bracket F1 of 0.2 sounds like parsing and may be arithmetic about record layout.

A text-blind predictor is a *constant*, so the best one is found by search: take
candidate graphs from one half of the training episodes, score each against the
other half, and keep the argmax. Two things about that are deliberate.

* **Per metric.** The constant that maximises ``label_f1`` is not the one that
  maximises ``bracket_f1`` — the first wants the most typical vocabulary, the
  second the most typical shape. Fitting one constant and quoting it under six
  headings would understate five of the floors, and an understated floor is how
  a null becomes a finding.
* **Held out inside the training set.** Candidates and targets are disjoint
  halves of train. Scoring a candidate against the episode it came from would
  hand the floor a free exact match, and the floor would then be quietly fitted
  to its own answer key.

Eval episodes are never touched during fitting. Seeds >= 1,000,000 are eval
only, and the floor obeys that like everything else.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import Graph

from .scoring import METRICS, Scores, macro_scores, score_graph

__all__ = ["ConstantFloor", "fit_floor"]


@dataclass
class ConstantFloor:
    """One text-blind constant graph per metric, chosen on training episodes."""

    graphs: dict[str, Graph] = field(default_factory=dict)
    #: which training episode each constant came from, for the write-up
    sources: dict[str, str] = field(default_factory=dict)
    #: the training score of each constant, so eval-vs-train drift is visible
    train_scores: dict[str, float] = field(default_factory=dict)

    def predict(self, metric: str) -> Graph:
        return self.graphs.get(metric, Graph())

    def evaluate(self, episodes: Sequence[Episode]) -> dict[str, float]:
        """Score each metric's constant on ``episodes``. Different constants, so
        the six numbers do not come from one prediction and are not claimed to."""
        lessons = [ep.lesson_id for ep in episodes]
        out: dict[str, float] = {}
        for metric in METRICS:
            g = self.graphs.get(metric)
            if g is None:
                out[metric] = float("nan")
                continue
            rows = [score_graph(g, ep.graph) for ep in episodes]
            out[metric] = macro_scores(rows, lessons)[metric]
        return out


def fit_floor(train: Sequence[Episode], *, n_candidates: int = 200,
              n_targets: int = 120, seed: int = 12345) -> ConstantFloor:
    """Search training graphs for the best constant, per metric.

    ``n_candidates`` and ``n_targets`` bound an inherently quadratic search. They
    are sampled without replacement from disjoint halves and the sampling is
    seeded, so the floor is reproducible; they are not tuned, and raising them
    can only raise the floor, which is the safe direction for a control.

    Their size is not a guess. This repo has published a lift that was an
    artefact of a floor 0.065 too low, so the search was measured against a four
    times larger one on all 179 lessons before the defaults were set:

    ==============  =====  =====  ========  ==========  ========
    candidates x    uas    las    type_acc  bracket_f1  label_f1
    targets
    ==============  =====  =====  ========  ==========  ========
    48 x 64         0.071  0.048  0.535     0.0015      0.118
    200 x 120       0.075  0.051  0.548     0.0040      0.123
    ==============  =====  =====  ========  ==========  ========

    Fifteen seconds, and it moves the floor by at most 0.013 — so the search is
    close to converged and the lifts above it are not an artefact of a thin one.
    The larger setting is the default anyway, because there is no reason to
    quote the weaker of two floors you have both of.
    """
    eps = list(train)
    if len(eps) < 4:
        return ConstantFloor()
    rng = random.Random(seed)
    order = list(range(len(eps)))
    rng.shuffle(order)
    half = len(order) // 2
    cand_idx = order[:half][:n_candidates]
    targ_idx = order[half:][:n_targets]
    targets = [eps[i] for i in targ_idx]
    lessons = [ep.lesson_id for ep in targets]

    best: dict[str, tuple[float, int]] = {}
    for ci in cand_idx:
        g = eps[ci].graph
        rows: list[Scores] = [score_graph(g, ep.graph) for ep in targets]
        m = macro_scores(rows, lessons)
        for metric in METRICS:
            if metric not in best or m[metric] > best[metric][0]:
                best[metric] = (m[metric], ci)

    floor = ConstantFloor()
    for metric, (score, ci) in best.items():
        floor.graphs[metric] = eps[ci].graph
        floor.sources[metric] = f"{eps[ci].lesson_id}#{eps[ci].seed}"
        floor.train_scores[metric] = score
    return floor
