"""Masked-node prediction over the episode's term graph.

The structural counterpart to next-token prediction, and the reason this repo
exists. ``langcurriculum`` builds every episode as a typed term and only then
renders it as prose, so for each episode there is a graph that is not a parse of
the text but the thing the text was generated *from*. Hiding a node in that
graph and asking a model to name it is a question about structure that has an
exact answer, no annotator, and no way to be right for surface reasons.

Two heads, reported separately and never averaged into one number:

* **type** — what kind of node sits here: a predicate, a list, a named field, an
  identifier. The structural question. A model can do well here while
  understanding nothing about reference, because term trees have strong shape
  regularities.
* **label** — *which* predicate, *which* variable, *which* field name. The
  symbolic question, and the harder of the two.

  It is harder for a *different reason* than this docstring claimed for a long
  time. The claim was that the curriculum invents its vocabulary per episode, so
  the answer is usually a name the model has never seen. Measured across all 179
  lessons, **100.0%** of scored labels are symbols that appear in training: the
  generator varies which name fills a slot, not the pool it draws from. What
  makes the label hard is choosing among familiar symbols, not naming unfamiliar
  ones — and a model that refuses to memorise is handicapping itself for a
  benefit this task does not pay.

Structural nodes carry no label and are scored on type alone, so that predicting
the empty label of a list — which is free — cannot inflate the score.
"""

from __future__ import annotations

import collections
from typing import Sequence

import numpy as np
import torch

from symbolic_ai_core.data.batch import (IGNORE, answer_nodes, choose_hidden,
                                         collate_graph)
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import STRUCTURAL, TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..models.base import ModelOutput
from .base import Task, TaskOutput, Totals, empirical_floor, ratio, score_block

__all__ = ["MaskedNode"]


def _pointer_counts(out: ModelOutput, batch) -> dict[str, float]:
    """Score a pointer by *what it picked*, never by index.

    Several nodes usually carry the same label, so an index-equality check would
    mark a correct copy wrong whenever the model chose a different valid source.
    Correctness is therefore ``label_group[picked] == label_group[asked]``.

    Scored over every masked node that has a label, including the ones the
    vocabulary cannot name. That is the point: those are 88.5% invented `ident`
    names, they are 80.7% copyable, and the label head drops them.
    """
    logits = getattr(out, "source_logits", None)
    if logits is None or batch.label_group is None:
        return {}
    asked = batch.label_group != IGNORE
    masked = batch.target_types != IGNORE
    scored = asked & masked
    if not bool(scored.any()):
        return {}
    # A pointer may not choose a padded position, and must not choose itself --
    # a node cannot be its own evidence when its label is what is hidden.
    valid = batch.pad_mask.clone()
    eye = torch.eye(valid.shape[1], dtype=torch.bool, device=valid.device)
    allowed = valid[:, None, :] & ~eye[None]
    picked = logits.masked_fill(~allowed, float("-inf")).argmax(-1)
    picked_group = torch.gather(batch.label_group, 1, picked)
    correct = (picked_group == batch.label_group) & scored
    return {"copy_n": float(scored.sum()), "copy_correct": float(correct.sum())}


def _copy_counts(batch) -> dict[str, float]:
    """How much of the answer is already sitting in the graph, in plain sight.

    The label head is scored as a choice among 8,192 symbols, but the task is
    mostly *binding*: the generator picks names arbitrarily and reuses them, so
    the question is usually "which node do I corefer with", not "which symbol is
    this". On the full curriculum 71.9% of scored answers already appear on a
    visible node of the same episode, while the best model in the table sits
    near 0.36 accuracy -- roughly half the reachable signal is untouched, and
    none of the models has a pointer.

    ``copy_censored`` counts the positions that are copyable but excluded from
    the label score because the vocabulary cannot name them. Those are 88.5%
    invented ``ident`` names on the full curriculum, and they are exactly where
    copying is the *only* available route, so a metric that drops them rewards
    naming and hides binding.
    """
    src = getattr(batch, "target_source", None)
    if src is None or batch.target_tokens is None:
        return {}
    has_source = src != IGNORE
    scored = batch.target_tokens != IGNORE
    return {"copy_reachable": float((has_source & scored).sum()),
            "copy_censored": float((has_source & ~scored).sum())}


def _answer_node_counts(out: ModelOutput, batch) -> dict[str, float]:
    """The label score restricted to the nodes that carry the episode's answer.

    ``answer`` masking hides the answer node *and its subtree*, so a handful of
    descendants are hidden too — 8 of 283 answer-bearing episodes have any. They
    are hidden inputs, not the question, and folding them into the headline
    would make the number quietly not the one being compared with `answer_acc`.
    So they are excluded here and the two numbers are reported side by side.

    ``ansnode_episodes`` counts the batch elements that had an answer node at
    all; the rest contributed nothing and are **unscored rather than zero**.
    """
    positions = (batch.meta or {}).get("answer_nodes")
    if not positions or batch.target_tokens is None:
        return {}
    keep = torch.zeros_like(batch.target_tokens, dtype=torch.bool)
    covered = 0
    for b, idx in enumerate(positions):
        if idx:
            covered += 1
            keep[b, torch.tensor(idx, dtype=torch.long)] = True
    if not bool(keep.any()):
        return {"ansnode_episodes": float(covered),
                "ansnode_seen": float(len(positions))}
    targets = torch.where(keep, batch.target_tokens,
                          torch.full_like(batch.target_tokens, IGNORE))
    with torch.no_grad():
        _, counts = score_block(out.symbol_logits.detach(), targets, "ansnode")
    return {**counts, "ansnode_episodes": float(covered),
            "ansnode_seen": float(len(positions))}


class MaskedNode(Task):
    """Hide nodes; predict their type and their label."""

    name = "node"

    #: Which nodes a draw hides — see :data:`symbolic_ai_core.data.batch.MASK_MODES`.
    #: A subclass changes this and nothing else; the metrics, the floors and the
    #: pointer bookkeeping are all shared, which is what makes the regimes
    #: comparable rather than merely adjacent.
    mask_mode = "scatter"

    def __init__(self, mask_rate: float = 0.15, type_weight: float = 0.5,
                 max_nodes: int = 256, seed: int = 0,
                 readouts: "dict | None" = None) -> None:
        self.mask_rate = mask_rate
        self.type_weight = type_weight
        self.max_nodes = max_nodes
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        # The readouts scored *beside* the two heads below, never instead of
        # them. `label_*` and `copy_*` are what every published number in this
        # repo means, and a readout computing something nearly the same would
        # redefine all of them silently. Built lazily so that constructing a
        # task cannot import the readout package, which imports the models.
        self._readouts = readouts

    @property
    def readouts(self) -> dict:
        if self._readouts is None:
            from ..readouts import REGISTRY
            self._readouts = {n: REGISTRY.get(n)() for n in ("symbol", "node")}
        return self._readouts

    def collate(self, episodes: Sequence[Episode], tok: SymbolTokenizer):
        return collate_graph(episodes, tok, max_nodes=self.max_nodes,
                             mask_rate=self.mask_rate, rng=self.rng,
                             mask_mode=self.mask_mode)

    def compute(self, out: ModelOutput, batch) -> TaskOutput:
        label_loss, label_counts = score_block(
            out.symbol_logits, batch.target_tokens, "label")
        type_loss, type_counts = score_block(
            out.type_logits, batch.target_types, "type")
        readout_counts: dict[str, float] = {}
        for readout in self.readouts.values():
            readout_counts.update(readout.score(out, batch))
        return TaskOutput(loss=label_loss + self.type_weight * type_loss,
                          counts={**label_counts, **type_counts,
                                  **_copy_counts(batch),
                                  **_pointer_counts(out, batch),
                                  **_answer_node_counts(out, batch),
                                  **readout_counts})

    def summarize(self, totals: Totals) -> dict[str, float]:
        """Both heads, plus how much of the masked set the label score covers.

        Every masked node has a type target, but only a node whose label the
        vocabulary can name has a label target — and the ones it cannot name are
        systematically the *interesting* ones, the per-episode invented symbols.
        About 16% of masked labels are dropped this way on the full curriculum,
        so ``label_acc`` is an accuracy over the nameable 84% and is optimistic
        for exactly that reason. Reporting the coverage is the least that can be
        done about it short of giving the models a copy mechanism.
        """
        out = {**ratio(totals, "label"), **ratio(totals, "type")}
        scored, masked = out.get("label_n", 0.0), out.get("type_n", 0.0)
        out["label_coverage"] = scored / masked if masked else float("nan")

        # The ceiling, reported next to the score so the gap is visible in every
        # run rather than in a scratch script somebody has to rediscover.
        if totals.get("copy_n"):
            out["copy_acc"] = totals.get("copy_correct", 0.0) / totals["copy_n"]
            out["copy_scored_n"] = totals["copy_n"]

        if totals.get("ansnode_n"):
            out.update(ratio(totals, "ansnode"))
            seen = totals.get("ansnode_seen", 0.0)
            out["ansnode_coverage"] = (totals.get("ansnode_episodes", 0.0) / seen
                                       if seen else float("nan"))

        reachable = totals.get("copy_reachable", 0.0)
        out["copy_ceiling"] = reachable / scored if scored else float("nan")
        censored = totals.get("copy_censored", 0.0)
        out["copy_censored"] = censored

        for readout in self.readouts.values():
            out.update(readout.summarize(totals))
        return out

    def floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
              train: Sequence[Episode]) -> dict[str, float]:
        """A **structure-only** baseline, fitted on train, scored on eval.

        A constant guess is far too weak a floor here, and reporting one would
        badly overstate the result. Node type is very nearly determined by the
        shape of the tree: a ``field`` node is always the child of a record, a
        ``char`` always the child of a string. On the curriculum's graphs, a
        lookup table keyed on nothing but ``(parent type, slot, depth)`` gets
        about 0.96 — so a model scoring 0.95 against a majority-class floor of
        0.33 has not learned something worth 0.9 lift, it has learned less than
        the table.

        So the floor is that table: the most common answer for each structural
        context, backing off to the global majority for a context the training
        graphs never showed. It knows the shape of the tree and nothing about
        any symbol in it, which makes the lift above it the part of the score
        that is actually about reference.

        Fitted on train and scored on eval, and — since the correction described
        in :meth:`_nodes` — under the same masking the models face, so the floor
        is what a structure-only lookup gets *given what a model is given*
        rather than given the whole graph. Several masked draws are averaged so
        that sampling 15% of nodes does not put noise into the one number
        everything else is compared against.
        """
        # Several masked draws per training episode, so the lookup is fitted on
        # a comparable amount of evidence to the models', which also see
        # repeated maskings of the same graphs.
        type_rule, label_rule = _ContextRule(), _ContextRule()
        rng = np.random.default_rng(4)
        for _ in range(4):
            for ep in train:
                for ctx, label, type_, _is_ans, _cp in self._nodes(ep, tok, rng):
                    type_rule.observe(ctx, type_)
                    if label is not None:
                        label_rule.observe(ctx, label)

        type_hits = type_n = label_hits = label_n = 0
        ans_hits = ans_n = 0
        eval_types: collections.Counter[str] = collections.Counter()
        eval_labels: collections.Counter[int] = collections.Counter()
        eval_answers: collections.Counter[int] = collections.Counter()
        # Averaged over several draws for the same reason it is fitted over
        # several: one 15% sample of an evaluation set is a few hundred nodes,
        # and the floor is the fixed point every lift in the repo is measured
        # against, so it cannot be the noisiest number in the table.
        scoring = np.random.default_rng(12345)
        for _ in range(8):
            for ep in episodes:
                for ctx, label, type_, is_ans, copyable in self._nodes(ep, tok, scoring):
                    type_hits += type_rule.predict(ctx) == type_
                    type_n += 1
                    eval_types[type_] += 1
                    if label is not None:
                        hit = label_rule.predict(ctx) == label
                        label_hits += hit
                        label_n += 1
                        eval_labels[label] += 1
                        if is_ans:
                            ans_hits += hit
                            ans_n += 1
                            eval_answers[label] += 1

        copy_acc = self._copy_floor(episodes, train, tok)

        _, type_bits = empirical_floor(dict(eval_types))
        _, label_bits = empirical_floor(dict(eval_labels))
        out = {
            "type_acc": type_hits / type_n if type_n else float("nan"),
            "type_bits": type_bits, "type_n": float(type_n),
            "label_acc": label_hits / label_n if label_n else float("nan"),
            "label_bits": label_bits, "label_n": float(label_n),
            "copy_acc": copy_acc,
        }
        # The readout floors are these floors, renamed -- not second opinions
        # computed alongside. Two near-identical copies of a floor drift, and a
        # floor is the one number in a table that nothing else is checked
        # against, so the drift would be invisible. `SymbolReadout.floor` and
        # `NodeReadout.floor` exist for callers holding a readout and no task
        # and go through this same method to get here.
        out.update({"rsymbol_acc": out["label_acc"],
                    "rsymbol_bits": out["label_bits"],
                    "rsymbol_n": out["label_n"], "rnode_acc": copy_acc})
        # Emitted only in `answer` mode, and therefore absent from every `node`
        # summary this repo has ever written. It is the same lookup, the same
        # draws and the same ladder, restricted to the positions that carry the
        # answer -- the floor for the one number that is comparable with
        # `answer_acc`.
        if ans_n:
            _, ans_bits = empirical_floor(dict(eval_answers))
            out.update({"ansnode_acc": ans_hits / ans_n,
                        "ansnode_bits": ans_bits, "ansnode_n": float(ans_n)})
        return out

    def split_floor(self, episodes: Sequence[Episode], tok: SymbolTokenizer,
                    train: Sequence[Episode], *,
                    fit_per_bucket: bool = False) -> dict[str, float]:
        """The label floor, computed **separately** on copyable and non-copyable fills.

        Not part of :meth:`floor` and deliberately so: every `node` summary ever
        written carries a fixed set of keys, and a run whose file grows a column
        is a published artefact that changed. This is a second question asked of
        the same machinery by whoever wants it — `scripts/copyable_split.py`.

        It is the same rule, the same context ladder and the same masking draw as
        :meth:`floor`, with one extra bucket, which is why the pooled number it
        produces is bit-identical to ``floor()["label_acc"]``. That equality is
        the guard against this having drifted into a second implementation of the
        floor, and the caller asserts it.

        ``fit_per_bucket`` fits **one rule per bucket** instead of one rule
        scored in two, and is an **upper bound rather than a floor**. A floor
        fitted pooled and merely *reported* bucketed is not the best a
        structure-only lookup does on the sub-population — the pooled table
        answers every context with the label commonest over both buckets, which
        is the copyable bucket's answer wherever they disagree. But the bucket
        is not a feature any predictor may use: copyability is whether the
        **hidden** label appears on a visible node, so conditioning on it is
        conditioning on the answer. Splitting the score by it is a legitimate
        decomposition; splitting the *predictor* by it is not a floor. What this
        gives is the ceiling of the bucketed lookup, which is the honest way to
        ask whether the reported column was too weak. The pooled value it
        returns is **not** the run's ``label_floor``, and a caller must not
        assert it against one.
        """
        rules: dict[bool, _ContextRule] = {True: _ContextRule(),
                                           False: _ContextRule()}
        pooled = _ContextRule()
        rng = np.random.default_rng(4)
        for _ in range(4):
            for ep in train:
                for ctx, label, _t, _a, copyable in self._nodes(ep, tok, rng):
                    if label is not None:
                        (rules[copyable] if fit_per_bucket
                         else pooled).observe(ctx, label)

        hit = {True: 0, False: 0}
        n = {True: 0, False: 0}
        scoring = np.random.default_rng(12345)
        for _ in range(8):
            for ep in episodes:
                for ctx, label, _t, _a, copyable in self._nodes(ep, tok, scoring):
                    if label is None:
                        continue
                    rule = rules[copyable] if fit_per_bucket else pooled
                    n[copyable] += 1
                    hit[copyable] += rule.predict(ctx) == label
        total = n[True] + n[False]
        return {
            "floor_copyable": hit[True] / n[True] if n[True] else float("nan"),
            "floor_not_copyable": hit[False] / n[False] if n[False] else float("nan"),
            "floor_pooled": (hit[True] + hit[False]) / total if total else float("nan"),
            "n_copyable": float(n[True]), "n_not_copyable": float(n[False]),
        }

    def split_copy_floor(self, episodes: Sequence[Episode],
                         tok: SymbolTokenizer,
                         train: Sequence[Episode]) -> dict[str, float]:
        """The **equivariant** floor for each bucket: a structure-only pointer.

        :meth:`split_floor` is a lookup table over *symbol identities*, so it is
        renaming-**variant** by construction — permute the vocabulary and it
        scores zero. Reading a renaming-invariant model against it on the
        non-copyable bucket compares two hypothesis classes on the one
        sub-population where the extra membership is the whole question, and the
        comparison is decided before any model runs: on a fill whose label sits
        on no visible node, an exactly equivariant predictor has nothing to
        point at, so *every* member of that class — the oracle included — scores
        0. ``acc | not copyable`` for such a model measures its
        non-equivariance, not its reasoning.

        This is that comparison made explicit. Same masking draw and the same
        rule as :meth:`_copy_floor` — the commonest relative offset to a
        same-label node per structural context, applied blind — restricted to
        the fills the **label** score covers, and reported per bucket.
        ``ceiling_*`` is the oracle pointer: 1.0 where a source exists and 0.0
        where none does, which is the copyable partition restated and the
        strongest score any equivariant model can reach.

        One difference from :meth:`_copy_floor`, and it is not a refinement but
        a different question. ``copy_acc`` counts a landing on **any** node with
        the same label, hidden ones included, and so does the pointer score in
        :func:`_pointer_counts` — consistently, which is what makes them
        comparable to each other. That is the right rule for "which node
        corefers with this one" and the wrong one for a floor on the *label*
        score: a symbol on a masked node cannot be read, so a landing there
        names nothing. ``anynode_*`` is the ``copy_acc`` rule, reported beside
        the visible-only one so the difference is a measured number rather than
        a remark — it is why ``anynode_not_copyable`` is above zero while
        ``copyfloor_not_copyable`` is exactly zero.
        """
        rule: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        rng = np.random.default_rng(4)
        for _ in range(4):
            for ep in train:
                for ctx, i, source, *_ in self._pointer_examples(ep, rng, tok):
                    if source is not None:
                        rule[ctx][i - source] += 1

        overall: collections.Counter = collections.Counter()
        for counts in rule.values():
            overall.update(counts)
        fallback = overall.most_common(1)[0][0] if overall else 1

        hit = {True: 0, False: 0}
        anyhit = {True: 0, False: 0}
        n = {True: 0, False: 0}
        scoring = np.random.default_rng(12345)
        for _ in range(8):
            for ep in episodes:
                for ctx, i, source, labels, scorable, hidden in \
                        self._pointer_examples(ep, scoring, tok):
                    if not scorable:
                        continue
                    counts = rule.get(ctx)
                    offset = counts.most_common(1)[0][0] if counts else fallback
                    j = i - offset
                    copyable = source is not None
                    n[copyable] += 1
                    landed = (0 <= j < len(labels) and j != i
                              and labels[j] == labels[i])
                    anyhit[copyable] += landed
                    hit[copyable] += landed and j not in hidden
        total = n[True] + n[False]
        div = lambda a, b: a / b if b else float("nan")
        return {
            "copyfloor_copyable": div(hit[True], n[True]),
            "copyfloor_not_copyable": div(hit[False], n[False]),
            "copyfloor_pooled": div(hit[True] + hit[False], total),
            "anynode_copyable": div(anyhit[True], n[True]),
            "anynode_not_copyable": div(anyhit[False], n[False]),
            "anynode_pooled": div(anyhit[True] + anyhit[False], total),
            "ceiling_copyable": 1.0, "ceiling_not_copyable": 0.0,
            "copyfloor_n_copyable": float(n[True]),
            "copyfloor_n_not_copyable": float(n[False]),
        }

    def _copy_floor(self, episodes: Sequence[Episode],
                    train: Sequence[Episode], tok: SymbolTokenizer) -> float:
        """What a structure-only pointer gets: copy from a fixed relative offset.

        The copy head needs a floor for the same reason the other two do. A
        random pointer scores about 0.05 and an oracle 0.73, and quoting a copy
        accuracy between those without saying which end is cheap would be
        exactly the mistake this repo keeps having to undo.

        The rule knows the shape of the tree and nothing about any symbol: for
        each structural context it learns the commonest *offset* to a node that
        turned out to carry the same label, then applies that offset blind. It
        cannot read what any node says, so whatever a real pointer scores above
        this is the part that came from reading the episode.
        """
        rule: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        rng = np.random.default_rng(4)
        for _ in range(4):
            for ep in train:
                for ctx, i, source, *_ in self._pointer_examples(ep, rng):
                    if source is not None:
                        rule[ctx][i - source] += 1

        overall: collections.Counter = collections.Counter()
        for counts in rule.values():
            overall.update(counts)
        fallback = overall.most_common(1)[0][0] if overall else 1

        hits = total = 0
        scoring = np.random.default_rng(12345)
        for _ in range(8):
            for ep in episodes:
                for ctx, i, _s, labels, *_ in self._pointer_examples(ep, scoring):
                    counts = rule.get(ctx)
                    offset = counts.most_common(1)[0][0] if counts else fallback
                    j = i - offset
                    total += 1
                    hits += 0 <= j < len(labels) and j != i \
                        and labels[j] == labels[i]
        return hits / total if total else float("nan")

    def _pointer_examples(self, ep: Episode, rng: np.random.Generator,
                          tok: SymbolTokenizer | None = None):
        """``(context, node, a visible same-label node or None, labels, scorable)``.

        Same masking regime as everything else here, and the same reason: a
        floor measured under conditions the models do not face is not a floor.

        ``scorable`` is :meth:`_scorable` — whether the **label** score covers
        this fill — and is ``True`` for every fill when no tokenizer is given,
        which is what :meth:`_copy_floor` wants: the copy head is scored over
        every labelled masked node, including the ones the vocabulary cannot
        name. :meth:`split_copy_floor` passes a tokenizer because it is a floor
        for the *label* score and has to cover the same fills that does.

        ``hidden`` rides along because *whether the node a pointer lands on is
        visible* is not a question this method's other outputs can answer, and
        it decides what the pointer is worth. ``copy_acc`` — the model's score
        and this floor alike — counts a landing on a **hidden** same-label node
        as a hit, which is right for "which node corefers with this one" and
        wrong for any floor on the **label** score, since a model cannot read a
        symbol it cannot see. See :meth:`split_copy_floor`.
        """
        g = ep.graph
        n = min(len(g), self.max_nodes)
        if not n:
            return
        hidden = self._hidden(ep, n, rng)
        labels = list(g.labels[:n])
        for i in sorted(hidden):
            if not labels[i] or g.types[i] in STRUCTURAL:
                continue
            p = g.parent[i]
            parent_type = ("ROOT" if not 0 <= p < n
                           else ("mask" if p in hidden else g.types[p]))
            ctx = (parent_type, min(g.slot[i], 8), min(g.depth[i], 8))
            source = next((j for j in range(n)
                           if j not in hidden and labels[j] == labels[i]), None)
            scorable = (True if tok is None
                        else self._scorable(g.labels[i], g.types[i], tok))
            yield ctx, i, source, labels, scorable, hidden

    def _hidden(self, ep: Episode, n: int, rng: np.random.Generator) -> set[int]:
        """The nodes this draw hides, by the *same* rule the collator uses.

        The floor exists to say what a structure-only lookup gets given what a
        model is given, so it has to be fitted and scored under the model's
        masking regime rather than a copy of it. It goes through
        :func:`~symbolic_ai_core.data.batch.choose_hidden` for that reason: two
        implementations of one regime is exactly the shape of drift that a floor
        — the one number nothing else is checked against — cannot survive.

        The "ask at least one question" fallback is scatter's, and is not
        applied in ``answer`` mode: an episode whose answer is nowhere in its
        graph is unscored, in the floor as in the batch.
        """
        chosen = choose_hidden(ep.graph, n, rng, mask_rate=self.mask_rate,
                               mode=self.mask_mode, answer=ep.answer)
        if len(chosen) == 0 and not self.mask_mode.startswith("answer"):
            return {int(rng.integers(0, n))}
        return set(int(i) for i in chosen)

    def _answer_positions(self, ep: Episode, n: int) -> set[int]:
        """Positions whose label *is* the answer — empty outside answer modes."""
        if not self.mask_mode.startswith("answer"):
            return set()
        at = answer_nodes(ep.graph, n, ep.answer)
        return set(at[:1] if self.mask_mode == "answer_one" else at)

    def _nodes(self, ep: Episode, tok: SymbolTokenizer,
               rng: np.random.Generator | None = None):
        """``(context, label id or None, type, is the answer)`` for what is hidden.

        The fourth field is ``False`` everywhere except in ``answer`` mode,
        where it marks the positions that carry the episode's answer as opposed
        to its descendants — so the floor can be restricted to the same
        positions the score is, in one pass, rather than by a second and
        drifting copy of this method.

        The context is what a model can *actually* read, which is a stronger
        requirement than it sounds and was got wrong here for a long time. The
        first version read the true parent type straight off the unmasked graph
        and scored every node in it, while a model reads ``mask`` wherever the
        parent is hidden and is scored only where the mask fell. The floor was
        therefore computed with information the models were denied, and it made
        every lift in the repo pessimistic by an unknown amount.

        So the mask is drawn here at the rate evaluation uses, a hidden parent
        contributes ``mask`` exactly as it does in a
        :class:`~symbolic_ai_models.models.symbolic.GraphView`, and only masked
        nodes are yielded. The floor is then what the best structure-only lookup
        gets *under the conditions the model faces*, which is the only version
        of it worth comparing against.

        The mask positions are not the identical ones any particular evaluation
        draws — the floor is a property of the distribution, so matching the
        regime is what matters, not the individual draw.
        """
        rng = rng or np.random.default_rng(0)
        g = ep.graph
        n = min(len(g), self.max_nodes)
        if not n:
            return
        hidden = self._hidden(ep, n, rng)
        answers = self._answer_positions(ep, n)

        children: dict[int, list[int]] = {}
        for k in range(n):
            pk = g.parent[k]
            if 0 <= pk < n:
                children.setdefault(pk, []).append(k)
        has_children = [False] * n
        for i in range(n):
            p = g.parent[i]
            if 0 <= p < n:
                has_children[p] = True
        for i in sorted(hidden):
            p = g.parent[i]
            parent_type = ("ROOT" if not 0 <= p < n
                           else ("mask" if p in hidden else g.types[p]))
            # A ladder of contexts, most specific first, not one context. The
            # old floor was a single four-feature key and it was measurably too
            # weak: a backed-off lookup over the same *kind* of information --
            # still structure only, still no symbol anywhere in it -- reaches
            # 0.946 type accuracy against its 0.795, and beat `rgt` at 0.915.
            # A floor that a counting baseline clears by 15 points is not a
            # floor, it is a number every lift above it was borrowing from.
            arity = min(len(children.get(i, ())), 4)
            sibs = [g.types[k] for k in children.get(g.parent[i], ())
                    if k != i and k not in hidden]
            sib = collections.Counter(sibs).most_common(1)[0][0] if sibs else None
            slot, depth = min(g.slot[i], 8), min(g.depth[i], 8)
            ctx = (
                (parent_type, slot, depth, arity, sib),
                (parent_type, slot, depth, arity),
                (parent_type, slot, depth, has_children[i]),
                (parent_type, slot, depth),
                (parent_type, slot),
                (parent_type,),
            )
            label = (tok.label_id(g.labels[i])
                     if self._scorable(g.labels[i], g.types[i], tok) else None)
            # Exactly `collate_graph`'s `target_source` condition: does some
            # *visible* node of this graph carry the same label string. It rides
            # along here rather than being recomputed by a caller, because a
            # caller cannot see this method's masking draw and would have to
            # reproduce the ladder to align with it.
            copyable = bool(g.labels[i]) and any(
                j not in hidden and g.labels[j] == g.labels[i] for j in range(n))
            yield ctx, label, g.types[i], i in answers, copyable

    @staticmethod
    def _scorable(label: str, type_: str, tok: SymbolTokenizer) -> bool:
        """Mirrors the exclusion in ``collate_graph``: a node counts towards the
        label score only if it has a label and the vocabulary can name it."""
        return bool(label) and type_ not in STRUCTURAL \
            and tok.label_id(label) != tok.unk_id


class _ContextRule:
    """Most common answer per structural context, backing off to the global one.

    ``observe``/``predict`` take a *ladder* of contexts, most specific first, and
    the most specific one with enough support answers. A single key cannot both
    be specific enough to be sharp and general enough to be seen, which is why
    the four-feature version of this floor sat 15 points under a counting model.

    A lookup table, deliberately. The floor is supposed to be the score of
    something that has the tree's shape and no idea what any symbol means, and a
    table is exactly that — there is nothing in it that could be mistaken for
    understanding.
    """

    def __init__(self) -> None:
        self.by_context: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        self.overall: collections.Counter = collections.Counter()

    #: Support a key needs before it is trusted over a more general one.
    MIN_SUPPORT = 5

    def observe(self, contexts: tuple, answer) -> None:
        for context in contexts:
            self.by_context[context][answer] += 1
        self.overall[answer] += 1

    def predict(self, contexts: tuple):
        for context in contexts:
            counts = self.by_context.get(context)
            if counts and sum(counts.values()) >= self.MIN_SUPPORT:
                return counts.most_common(1)[0][0]
        return self.overall.most_common(1)[0][0] if self.overall else None
