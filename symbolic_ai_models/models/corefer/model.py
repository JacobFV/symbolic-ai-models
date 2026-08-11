"""A pointer keyed on coreference rather than on structural resemblance.

The measured reason this exists. `evidence` retrieves the structurally most
similar node and copies it, and as a pointer that scores **0.283 against a
fixed-offset floor of 0.266** — a lift of +0.023 with 0.44 of headroom left to
the 0.722 ceiling. Structural resemblance turns out to be barely better than
"copy from the usual place", so the answer is not a better similarity metric.

The relation that actually decides a label here is **coreference**: two nodes
carry the same symbol because the episode is talking about the same thing
twice. That is a different question from "do these two nodes sit in similar
places", and it has different evidence — the same predicate appearing twice with
the same argument position, a variable bound in one clause and used in the next.

So this model learns, from training graphs alone, which *pairwise* features
predict that two nodes share a label, and points using those. Deliberately naive
Bayes over the features rather than a joint table: the feature combinations are
sparse, and a joint count would memorise pairs it saw and abstain everywhere
else. Independence is wrong here — `same_parent_head` and `same_grandparent` are
plainly correlated — but wrong in a way that costs calibration rather than
ranking, and only the ranking is used.
"""

from __future__ import annotations

import collections
import math
from typing import Sequence

from ...data.curriculum import Episode
from ...data.graph import TYPE_TO_ID
from ...data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["CoreferModel"]

#: Laplace smoothing, so a feature never seen on one side does not produce an
#: infinite log-ratio the moment it appears.
ALPHA = 1.0


def _relation(view: GraphView, i: int, j: int) -> str:
    """One name for how `i` and `j` sit relative to each other.

    A single categorical, chosen most-specific-first, and this is the whole
    lesson of the first version. That one had `siblings`, `same_grandparent`,
    `same_depth` and `same_ptype` as separate booleans, which are four views of
    one fact; naive Bayes added all four, a sibling collected roughly +8 of
    evidence from what is really one observation, and **99.3% of its picks
    landed at the same depth as the query**. Coreference routinely crosses
    depths — a variable bound in a clause head and used inside the body — so the
    pointer could not reach the cases that matter.

    Counting the fact once is a fix to the model, not a tuning knob: it removes
    a double count that was there by mistake.
    """
    pi, pj = view.parent[i], view.parent[j]
    head_i = view.labels[pi] if pi >= 0 else None
    head_j = view.labels[pj] if pj >= 0 else None
    if head_i is not None and head_i == head_j and view.slot[i] == view.slot[j]:
        return "same_head_same_slot"      # two uses of one predicate, one argument
    if pi >= 0 and pi == pj:
        return "sibling"
    if head_i is not None and head_i == head_j:
        return "same_head"
    gi = view.parent[pi] if pi >= 0 else -1
    gj = view.parent[pj] if pj >= 0 else -1
    if gi >= 0 and gi == gj:
        return "same_grandparent"
    if view.depth[i] == view.depth[j]:
        return "same_depth"
    return "other"


def _pair_features(view: GraphView, i: int, j: int) -> tuple:
    """What might make `i` and `j` the same symbol.

    Three near-independent things: how they are related, how far apart they are,
    and in which direction. Every one is readable with `j` visible and `i`
    hidden — nothing consults `labels[i]`, which is the answer.
    """
    delta = i - j
    rel = _relation(view, i, j)
    dist = min(int(math.log2(abs(delta))) if delta else 0, 6)
    pi = view.parent[i]
    # Which kind of node is *asking*. Without this the model learns one global
    # ranking function, and a global ranking loses to the floor by construction:
    # the floor learns a separate offset per structural context, so it is
    # already conditioned on the query and this was not.
    query = ((view.types[pi] if pi >= 0 and view.types[pi] else "ROOT"),
             min(view.slot[i], 6))
    return (
        ("rel", rel),
        ("dist", dist),
        ("dir", delta > 0),
        ("query_rel", (query, rel)),
        ("query_dist", (query, dist)),
    )


@register("corefer", doc="Pointer over nodes, keyed on learned coreference evidence.")
class CoreferModel(RuleBasedModel):
    """Point at the node most likely to be the same symbol."""

    LEARNED = ("weights", "prior")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_pairs = int(cfg.get("max_pairs", 200_000))
        self.weights: dict[tuple, float] = {}
        self.prior: float = 0.0

    # ---- fitting ------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        """Count each feature under coreference and under its absence.

        Negatives are every other visible node of the same graph, not a sample.
        The candidate set at prediction time *is* every visible node, so training
        on a subsample of it would fit a different problem than the one asked.
        """
        pos: collections.Counter = collections.Counter()
        neg: collections.Counter = collections.Counter()
        n_pos = n_neg = 0
        seen = 0

        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for i, (label_id, _) in targets.items():
                if label_id is None or label_id < 0 or label_id == tok.unk_id:
                    continue
                for j in range(len(view)):
                    if j == i or view.labels[j] is None:
                        continue
                    if seen >= self.max_pairs:
                        break
                    seen += 1
                    same = view.labels[j] == label_id
                    bucket, _ = (pos, 1) if same else (neg, 0)
                    for feature in _pair_features(view, i, j):
                        bucket[feature] += 1
                    if same:
                        n_pos += 1
                    else:
                        n_neg += 1

        if not n_pos or not n_neg:
            return
        keys = set(pos) | set(neg)
        self.weights = {
            k: math.log((pos[k] + ALPHA) / (n_pos + 2 * ALPHA))
            - math.log((neg[k] + ALPHA) / (n_neg + 2 * ALPHA))
            for k in keys}
        self.prior = math.log(n_pos / n_neg)

    # ---- prediction ---------------------------------------------------
    def _score(self, view: GraphView, i: int, j: int) -> float:
        return self.prior + sum(self.weights.get(f, 0.0)
                                for f in _pair_features(view, i, j))

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        out: dict[int, Votes] = {}
        if not self.weights:
            return out
        for i in view.hidden:
            scores = {j: self._score(view, i, j) for j in range(len(view))
                      if j != i and view.labels[j] is not None}
            if not scores:
                continue
            best = max(scores.values())
            # Softmax over the candidates, so a clear winner votes confidently
            # and a flat field does not. The margin is what the confidence is
            # actually about: many episodes contain several equally good
            # sources, and being unsure between them is not being wrong.
            weights = {j: math.exp(s - best) for j, s in scores.items()}
            total = sum(weights.values())
            top = max(weights.values()) / total
            out[i] = ({j: w for j, w in weights.items() if w / total > 0.01},
                      min(0.15 + 0.8 * top, 0.9))
        return out

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        """Both heads read the pointer: copy whatever it points at.

        Kept deliberately thin. This model's claim is about *where* to look, and
        giving it a separate symbol-side rule would make the copy result
        impossible to attribute.

        The type head was `ABSTAIN` in the first version and that was a bug, not
        a design choice: it scored **-1.950 type lift**, the same as a model with
        no type opinion at all, because an abstaining model falls through to the
        global type marginal rather than to the structural one. A node that
        corefers with another has the same *type* as it at least as reliably as
        it has the same label, so there was an answer available and the model was
        declining to give it.
        """
        out: dict[int, tuple[Votes, Votes]] = {}
        pointers = self.source_votes(view)
        for i in view.hidden:
            vote = pointers.get(i)
            if vote is None:
                out[i] = (ABSTAIN, ABSTAIN)
                continue
            weights, confidence = vote
            labels: dict[int, float] = collections.defaultdict(float)
            types: dict[int, float] = collections.defaultdict(float)
            for j, w in weights.items():
                label = view.labels[j]
                if label is not None:
                    labels[int(label)] += w
                kind = view.types[j]
                if kind:
                    types[TYPE_TO_ID[kind]] += w
            out[i] = ((dict(labels), confidence) if labels else ABSTAIN,
                      (dict(types), confidence) if types else ABSTAIN)
        return out

    def n_symbolic_parameters(self) -> int:
        return len(self.weights) + 1

    def render(self) -> str:
        rows = sorted(self.weights.items(), key=lambda kv: -abs(kv[1]))[:20]
        lines = [f"prior log-odds {self.prior:+.3f}", "top evidence:"]
        lines += [f"  {str(k):<40} {v:+.3f}" for k, v in rows]
        return "\n".join(lines)
