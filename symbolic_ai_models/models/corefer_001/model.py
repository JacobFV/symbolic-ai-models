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

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
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


def _pair_features(view: GraphView, i: int, j: int, *,
                   prose: bool = True) -> tuple:
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
    # How loudly the episode's prose talks about the candidate. Audited before
    # use: the prompt names a hidden symbol without ever locating it, so this
    # reads content rather than the answer. Bucketed rather than raw, because
    # naive Bayes over a count would give a symbol mentioned nine times nine
    # times the evidence of one mentioned once, which is not what the signal is.
    said = view.mentions(j)
    said = -1 if said < 0 else min(said, 3)
    base = (
        ("rel", rel),
        ("dist", dist),
        ("dir", delta > 0),
        ("query_rel", (query, rel)),
        ("query_dist", (query, dist)),
    )
    return base + (("said", said),) if prose else base


def _rerank_features(view: GraphView, i: int, j: int, rank: int) -> tuple:
    """Richer evidence, affordable because it only sees a handful of candidates.

    Stage one has to score every visible node, so its features must be dense
    enough to have been seen often. Stage one *also* demonstrated what happens
    when a sparse feature is used at that scale: interacting the prose count with
    the query context made every head worse. Over ten candidates the same
    sparseness is affordable, and the joint contexts that were unusable become
    the point.

    `rank` is included deliberately. Without it stage two could reorder
    confidently on thin evidence; with it, agreeing with stage one is the default
    and disagreeing has to be earned.
    """
    pi = view.parent[i]
    q = ((view.types[pi] if pi >= 0 and view.types[pi] else "ROOT"),
         min(view.slot[i], 6), min(view.depth[i], 6))
    rel = _relation(view, i, j)
    said = view.mentions(j)
    said = -1 if said < 0 else min(said, 3)
    delta = i - j
    dist = min(int(math.log2(abs(delta))) if delta else 0, 6)
    return (
        ("joint", (q, rel, dist)),
        ("q_rel_said", (q, rel, said)),
        ("cand_type", view.types[j]),
        ("q_cand_type", (q, view.types[j])),
        ("rank", min(rank, 5)),
        ("rank_rel", (min(rank, 5), rel)),
        ("rel_said", (rel, said)),
    )


def _type_keys(view: GraphView, i: int, pointed: str | None) -> list[tuple]:
    """Structural descriptions of node ``i``, most specific first.

    The type question is not a binding question. Copying the type of whichever
    node the pointer chose answers "which thing is this" when what was asked is
    "what kind of thing sits here", and the two come apart -- 86% of the time the
    pointer's mistaken pick had the *right* type anyway, so type carries almost
    no information about identity and identity carries little about type.

    So the type head gets its own estimator: a backed-off conjunctive lookup,
    the shape the structure-only floor already proves is strong here (0.795 from
    four features). The pointed node's type enters as one conjunct in the most
    specific key rather than as the answer, which is the only thing the pointer
    is contributing that the floor does not have.
    """
    p = view.parent[i]
    ptype = (view.types[p] if p >= 0 and view.types[p] else "ROOT")
    slot, depth = min(view.slot[i], 8), min(view.depth[i], 8)
    arity = min(len(view.children(i)), 4)
    sibs = [view.types[j] for j in view.siblings(i) if view.types[j]]
    sib = collections.Counter(sibs).most_common(1)[0][0] if sibs else None
    return [
        (ptype, slot, depth, arity, sib, pointed),
        (ptype, slot, depth, arity, sib),
        (ptype, slot, depth, arity),
        (ptype, slot, depth),
        (ptype, slot),
        (ptype,),
    ]


@register("corefer-001", doc="Pointer over nodes, keyed on learned coreference evidence.")
class CoreferModel(RuleBasedModel):
    """Point at the node most likely to be the same symbol."""

    LEARNED = ("weights", "prior", "rerank", "type_rules")

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self.max_pairs = int(cfg.get("max_pairs", 200_000))
        #: How many of stage one's candidates stage two rescores. Measured
        #: before choosing: the correct node is in stage one's top ten about 78%
        #: of the time it exists, against 44% at top one, so ten is where the
        #: recall curve has flattened without the candidate set going stale.
        self.top_k = int(cfg.get("top_k", 10))
        self.weights: dict[tuple, float] = {}
        self.prior: float = 0.0
        self.rerank: dict[tuple, float] = {}
        self.type_rules: dict[tuple, collections.Counter] = {}
        #: A key must have been seen this often before it is trusted over a more
        #: general one. Without it the longest key wins on a single observation,
        #: which is memorising the training graphs rather than describing them.
        self.min_support = int(cfg.get("min_support", 5))

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
        self._learn_rerank(episodes, tok)
        self._learn_types(episodes, tok)

    def _learn_types(self, episodes: Sequence[Episode],
                     tok: SymbolTokenizer) -> None:
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            pointers = self.source_votes(view, prose=False)
            for i, (_, type_id) in targets.items():
                if type_id is None or type_id < 0:
                    continue
                vote = pointers.get(i)
                pointed = None
                if vote:
                    best = max(vote[0], key=lambda j: vote[0][j])
                    pointed = view.types[best]
                for key in _type_keys(view, i, pointed):
                    counts[key][int(type_id)] += 1
        self.type_rules = dict(counts)

    def _type_vote(self, view: GraphView, i: int, pointed: str | None) -> Votes:
        """Most specific key with enough support wins; back off until one has."""
        for key in _type_keys(view, i, pointed):
            counts = self.type_rules.get(key)
            if counts and sum(counts.values()) >= self.min_support:
                total = sum(counts.values())
                top, n = counts.most_common(1)[0]
                return {int(top): 1.0}, min(0.15 + 0.8 * n / total, 0.95)
        return ABSTAIN

    def _learn_rerank(self, episodes: Sequence[Episode],
                      tok: SymbolTokenizer) -> None:
        """Fit stage two by error-driven ranking, not by counting.

        Stage two was a second naive Bayes, and three separate features that
        measured as informative on their own then failed inside it: a
        cross-episode symbol prior, its cross-fitted repair, and an episode-local
        echo at AUC 0.581. The common thread is the combiner, not the features.
        Naive Bayes adds every feature's evidence as if it were independent, so a
        weak signal correlated with something already present is counted twice
        rather than absorbed for the part that is new -- and most features here
        are correlated by construction, being different readings of one tree.

        An averaged perceptron over the same features was the obvious fix and is
        worse: 0.356 from a cold start and 0.368 warm-started, against 0.404 for
        counting, on the held-out training slice. Discriminative training did not
        rescue correlated features here.

        What did help came out of that attempt. Stage two now trains only on
        questions where the top-k holds **both** a correct and an incorrect
        candidate. A question whose candidates are all correct, or none, has
        nothing to separate and only tilts the counts toward whatever its
        features happen to be. Filtering them: 0.404 -> 0.409.

        Trained on stage one's own top-k, as before: the question is "given these
        ten, which", and a different candidate distribution is a different
        question.
        """
        # Cache the questions once: the features are the expensive part and the
        # perceptron needs several passes over them.
        questions: list[tuple[list[tuple], list[bool]]] = []
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for i, (label_id, _) in targets.items():
                if label_id is None or label_id < 0 or label_id == tok.unk_id:
                    continue
                cands = self._candidates(view, i)
                gold = [view.labels[j] == label_id for j in cands]
                if not any(gold) or all(gold):
                    continue          # nothing to separate
                feats = [_rerank_features(view, i, j, r)
                         for r, j in enumerate(cands)]
                questions.append((feats, gold))
        if not questions:
            return

        # Counting, and only counting. The perceptron this method was written
        # around scored 0.356 cold and 0.368 warm-started against 0.404 for
        # counting, and was removed; what is left is the baseline it failed to
        # beat. Its removal left *two identical copies* of this loop behind, the
        # second silently re-initialising and recomputing what the first had
        # just built. That was a wasted pass over every question and not a wrong
        # number -- verified by computing the table both ways and comparing:
        # the 693 fitted weights are identical, so no result carrying this
        # model's name moves, and it needs no new version.
        counts_pos: collections.Counter = collections.Counter()
        counts_neg: collections.Counter = collections.Counter()
        n_p = n_n = 0
        for feats, gold in questions:
            for fs, g in zip(feats, gold):
                for f in fs:
                    (counts_pos if g else counts_neg)[f] += 1
                n_p += g
                n_n += not g
        if not n_p or not n_n:
            return
        self.rerank = {
            f: (math.log((counts_pos[f] + ALPHA) / (n_p + 2 * ALPHA))
                - math.log((counts_neg[f] + ALPHA) / (n_n + 2 * ALPHA)))
            for f in set(counts_pos) | set(counts_neg)}

    def _candidates(self, view: GraphView, i: int) -> list[int]:
        """Stage one's top-k, in its order."""
        scored = [(self._score(view, i, j), j) for j in range(len(view))
                  if j != i and view.labels[j] is not None]
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [j for _, j in scored[:self.top_k]]

    # ---- prediction ---------------------------------------------------
    def _score(self, view: GraphView, i: int, j: int, *,
               prose: bool = True) -> float:
        return self.prior + sum(self.weights.get(f, 0.0)
                                for f in _pair_features(view, i, j, prose=prose))

    def source_votes(self, view: GraphView,
                     prose: bool = True) -> dict[int, Votes]:
        out: dict[int, Votes] = {}
        if not self.weights:
            return out
        for i in view.hidden:
            if self.rerank and prose:
                # Stage one proposes, stage two orders. Only the label/copy
                # pointer is reranked: the type pointer must stay prose-free,
                # and stage two's features are saturated with prose.
                cands = self._candidates(view, i)
                scores = {j: sum(self.rerank.get(f, 0.0) for f in
                                 _rerank_features(view, i, j, r))
                          for r, j in enumerate(cands)}
            else:
                scores = {j: self._score(view, i, j, prose=prose)
                          for j in range(len(view))
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
        # The type head points *without* the prose feature, and the reason is
        # prior to the measurement: how often a symbol is mentioned is a fact
        # about that symbol's identity, and the type head is asking what kind of
        # node sits here, not which thing it names. Two nodes of the same type
        # routinely differ wildly in how much the episode talks about them.
        # Measured afterwards, it is also large: sharing one pointer costs the
        # type head 0.174 -> 0.004 lift while the label head gains.
        type_pointers = self.source_votes(view, prose=False)
        for i in view.hidden:
            vote = pointers.get(i)
            if vote is None:
                out[i] = (ABSTAIN, ABSTAIN)
                continue
            weights, confidence = vote
            labels: dict[int, float] = collections.defaultdict(float)
            for j, w in weights.items():
                label = view.labels[j]
                if label is not None:
                    labels[int(label)] += w
            type_vote = type_pointers.get(i)
            pointed = None
            if type_vote:
                best = max(type_vote[0], key=lambda j: type_vote[0][j])
                pointed = view.types[best]
            # Each head carries its own pointer's confidence. Using the label
            # pointer's for both is the failure this repo has now paid for four
            # times (design rule 1) -- and I wrote it here anyway, one tick after
            # writing the rule. It is not a subtle bug to introduce: the two
            # votes are right there on adjacent lines.
            out[i] = ((dict(labels), confidence) if labels else ABSTAIN,
                      self._type_vote(view, i, pointed))
        return out

    def n_symbolic_parameters(self) -> int:
        return len(self.weights) + len(self.rerank) + 1

    def render(self) -> str:
        rows = sorted(self.weights.items(), key=lambda kv: -abs(kv[1]))[:20]
        lines = [f"prior log-odds {self.prior:+.3f}", "top evidence:"]
        lines += [f"  {str(k):<40} {v:+.3f}" for k, v in rows]
        return "\n".join(lines)
