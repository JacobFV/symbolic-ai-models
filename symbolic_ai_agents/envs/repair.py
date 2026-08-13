"""Masked-node prediction with the teacher forcing taken out.

This is the environment the whole package was written for. The model harness's
headline task hides 15% of a term graph's nodes and asks a model to name each
one *given the true value of every other node*. That is a fair way to score a
predictor and it is not a way to find out whether reasoning survives its own
mistakes: every question is asked against a perfect history, so an error at node
7 costs exactly one node and never reaches node 30.

Here the nodes are asked about **one at a time, in order, and each answer stays
on the page**. A wrong fill is what the agent sees when it reaches a node whose
peer is that one. The score is the same quantity — the fraction of hidden labels
named correctly — but under compounding error, and the gap between an agent's
number here and the same reasoner's number in the model harness is the size of
the teacher-forcing subsidy. ``ROADMAP.md`` records that this harness "is
teacher-forced scoring with no trajectories and no reward, so it cannot
reproduce those" results; this is the missing half, and it reuses the model
harness's :class:`~symbolic_ai_models.models.symbolic.GraphView` so that what an
agent may read here is exactly what a rule-based model may read there.

What is asked, and what is not
------------------------------
The action set is **pointer-valued**: the candidates for a node are the distinct
labels carried by the nodes nearest to it in the pre-order linearisation. This
is the same commitment :mod:`symbolic_ai_models.models.omegaclaw` makes, and it
carries the same caveat, which is worth repeating rather than rediscovering: on
this curriculum 100% of scored labels recur in training, so refusing to memorise
buys robustness under renaming and costs accuracy. Here it also buys something
concrete — a finite, stated action set, which is what makes this an environment
rather than open-ended generation.

Two consequences follow and both make this **easier than the model harness's
masked-node task**, so the two scores must not be put in one column:

* Only nodes whose answer is carried by a *permanently visible* node within the
  candidate window are ever asked about. Nothing is unanswerable, and
  ``recoverable`` reports what share of the drawn nodes survived that filter —
  about half on the lessons this has been run on.
* Naming one of twenty-four candidates is easier than naming one of eight
  thousand vocabulary entries. The floor moves with it — that is what the floor
  is for — but the accuracies are not comparable.

The candidate set is fixed at ``reset`` and does not move as the agent fills
nodes in. An action set that shrank or grew in response to the agent's own
mistakes would make two agents face different worlds, and then the comparison
between them would be measuring the environment.
"""

from __future__ import annotations

import numpy as np

from symbolic_ai_models.data.batch import relation_matrix
from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.graph import STRUCTURAL
from symbolic_ai_models.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.models.symbolic import GraphView

from .base import Environment, Observation, Step
from .registry import register

__all__ = ["Repair"]


@register("repair", doc="Fill a term graph's hidden nodes one at a time; errors stay.")
class Repair(Environment):
    """Masked-node prediction as a trajectory, not as a batch."""

    interactive = True

    def __init__(self, mask_rate: float = 0.15, max_nodes: int = 256,
                 max_steps: int = 8, max_actions: int = 24) -> None:
        self.mask_rate = float(mask_rate)
        self.max_nodes = int(max_nodes)
        self.max_steps = int(max_steps)
        self.max_actions = int(max_actions)
        self.horizon = self.max_steps
        self._reset_state()

    def _reset_state(self) -> None:
        self._tok: SymbolTokenizer | None = None
        self._ep: Episode | None = None
        self._labels: list[int | None] = []
        self._types: list[str | None] = []
        self._gold: dict[int, int] = {}
        self._candidates: dict[int, tuple[str, ...]] = {}
        self._order: list[int] = []
        self._at = 0
        self._right = 0
        self._rel = np.zeros((0, 0), dtype=np.uint8)
        self._parent: list[int] = []
        self._slot: list[int] = []
        self._depth: list[int] = []
        self._hidden: list[int] = []
        self._children: list[list[int]] = []
        self._eligible = (0, 0)
        self._done = True

    def _salt(self) -> str:
        return f"{self.mask_rate}:{self.max_nodes}:{self.max_steps}:{self.max_actions}"

    # ---- setting up one episode ----------------------------------------
    def reset(self, ep: Episode, *, tok: SymbolTokenizer) -> Observation:
        self._reset_state()
        self._tok, self._ep = tok, ep
        g = ep.graph
        n = min(len(g), self.max_nodes)
        ids = [tok.label_id(l) if l else -1 for l in g.labels[:n]]

        # Maskable exactly where `collate_graph` would score: a real label, a
        # non-structural type, and a vocabulary that can name it. Keeping the
        # same exclusion is what lets the two harnesses' numbers be discussed in
        # the same paragraph even though they are not in the same column.
        maskable = [i for i in range(n)
                    if g.types[i] not in STRUCTURAL and ids[i] >= 0
                    and ids[i] != tok.unk_id]

        rng = self.episode_rng(ep)
        drawn = [i for i in maskable if rng.random() < self.mask_rate]
        if not drawn and maskable:                # always ask at least one
            drawn = [maskable[rng.randrange(len(maskable))]]
        drawn = drawn[:self.max_steps]
        visible = [i for i in range(n) if i not in set(drawn)]

        asked: list[int] = []
        for i in drawn:
            options = self._nearby(i, visible, ids, tok)
            if tok.itos[ids[i]] in options:
                asked.append(i)
                self._candidates[i] = options
                self._gold[i] = ids[i]
        self._eligible = (len(asked), len(drawn))

        if not asked:
            # Nothing recoverable by pointing. The episode still runs and still
            # counts, scored as a single no-op: dropping it would let the
            # environment quietly select the episodes it flatters.
            self._order, self._done = [], True
            self._install(n, ids, g, [])
            return self._empty_observation(ep)

        self._order = asked
        self._install(n, ids, g, asked)
        self._at, self._right, self._done = 0, 0, False
        return self._observe()

    def _install(self, n: int, ids: list[int], g, hidden: list[int]) -> None:
        """Build the view the agent reads. Hidden labels are dropped, not stored."""
        hide = set(hidden)
        self._labels = [None if i in hide else ids[i] for i in range(n)]
        self._types = [None if i in hide else g.types[i] for i in range(n)]
        self._parent = list(g.parent[:n])
        self._slot = list(g.slot[:n])
        self._depth = list(g.depth[:n])
        self._hidden = list(hidden)
        kids: list[list[int]] = [[] for _ in range(n)]
        for i in range(n):
            p = self._parent[i]
            if 0 <= p < n:
                kids[p].append(i)
        # Built once per episode rather than rescanned per node: rendering the
        # term is done on every step of every episode of every agent, and a
        # per-node scan of the parent list makes that quadratic for no reason.
        self._children = kids
        # Coreference edges of hidden nodes are withheld by `relation_matrix`,
        # for the same reason they are withheld in the model harness: a
        # `same_label` edge to a masked node *is* the answer.
        self._rel = relation_matrix(g, n, hidden=hidden)

    def _nearby(self, i: int, visible: list[int], ids: list[int],
                tok: SymbolTokenizer) -> tuple[str, ...]:
        """Distinct labels of the nearest permanently-visible nodes.

        Nearest in the pre-order linearisation, which is a structure-free
        ordering on purpose: ordering by tree distance would make the candidate
        set itself a hint about where to look, and the point is to test the
        agent's reaching rather than the environment's.
        """
        out: list[str] = []
        seen: set[str] = set()
        for j in sorted(visible, key=lambda j: (abs(j - i), j)):
            label = ids[j]
            if label < 0 or label == tok.unk_id:
                continue
            word = tok.itos[label]
            if word in seen:
                continue
            seen.add(word)
            out.append(word)
            if len(out) >= self.max_actions:
                break
        return tuple(out)

    # ---- observing ------------------------------------------------------
    def _view(self) -> GraphView:
        assert self._tok is not None
        return GraphView(labels=list(self._labels), types=list(self._types),
                         parent=self._parent, slot=self._slot, depth=self._depth,
                         rel=self._rel, hidden=[self._order[self._at]],
                         tok=self._tok)

    def _observe(self) -> Observation:
        ep, node = self._ep, self._order[self._at]
        assert ep is not None
        return Observation(
            text=self._render(node), actions=self._candidates[node],
            graph=self._view(), node=node, step=self._at,
            remaining=len(self._order) - self._at,
            key=f"{ep.instance_id}:node{node}",
            info={"lesson_id": ep.lesson_id, "instance_id": ep.instance_id,
                  "n_targets": len(self._order)})

    def _empty_observation(self, ep: Episode) -> Observation:
        """An episode with nothing recoverable. One no-op action, no reward."""
        return Observation(
            text=f"{ep.prompt}\n\n(nothing in this graph can be named by "
                 f"pointing at it)", actions=("",), step=0, remaining=1,
            key=f"{ep.instance_id}:none",
            info={"lesson_id": ep.lesson_id, "instance_id": ep.instance_id,
                  "n_targets": 0})

    def _render(self, target: int) -> str:
        """The partially repaired term, as an s-expression, with ``?`` at the target.

        Filled nodes show what the agent said, right or wrong. That is the whole
        experiment: the agent reads its own history rather than the truth.
        """
        assert self._tok is not None and self._ep is not None
        parts: list[str] = []

        def render(i: int) -> str:
            kids = self._children[i]
            if i == target:
                head = "?"
            elif self._labels[i] is None:
                head = "_"
            else:
                head = self._tok.itos[self._labels[i]].strip() \
                    or (self._types[i] or "node")
            return head if not kids else "(" + " ".join(
                [head] + [render(k) for k in kids]) + ")"

        roots = [i for i, p in enumerate(self._parent) if p < 0]
        for r in roots:
            parts.append(render(r))
        return ("name the node marked ? — the answer is a label already "
                "somewhere in this term\n\n" + "\n".join(parts))

    # ---- acting ---------------------------------------------------------
    def oracle(self) -> str | None:
        if self._done or not self._order or self._tok is None:
            return None
        return self._tok.itos[self._gold[self._order[self._at]]]

    def step(self, action: str) -> Step:
        if self._ep is None:                              # pragma: no cover
            raise RuntimeError("repair: step() before reset()")
        if not self._order:
            return Step(reward=0.0, done=True, correct=None,
                        info={"solved": 0.0, "recoverable": float(self._eligible[0]),
                              "drawn": float(self._eligible[1])})
        assert self._tok is not None
        node = self._order[self._at]
        gold = self._gold[node]
        correct = action == self._tok.itos[gold]
        self._right += int(correct)

        # The guess goes into the graph whether or not it was right. Its type
        # goes in too, taken from the node it was read off rather than from the
        # truth: the agent is told nothing by having filled something in.
        self._labels[node] = self._tok.stoi.get(action, self._tok.unk_id)
        self._types[node] = self._ep.graph.types[node] if correct else "token"

        self._at += 1
        share = 1.0 / len(self._order)
        info = {"fills": 1.0, "fills_right": float(correct)}
        if self._at >= len(self._order):
            self._done = True
            return Step(reward=share if correct else 0.0, done=True,
                        correct=correct,
                        feedback="right" if correct else
                                 f"no — it was {self._tok.itos[gold].strip()}",
                        info={**info,
                              "solved": float(self._right == len(self._order)),
                              "recoverable": float(self._eligible[0]),
                              "drawn": float(self._eligible[1])})
        return Step(reward=share if correct else 0.0, done=False,
                    correct=correct,
                    feedback="filled" if correct else "filled (wrongly)",
                    next_obs=self._observe(), info=info)

    # ---- reporting -------------------------------------------------------
    def context_key(self, obs: Observation) -> tuple:
        """The masked-node floor's own key, exactly.

        ``(parent type, slot, depth, has children)`` — the same tuple
        :meth:`symbolic_ai_models.tasks.masked_node.MaskedNode.floor` builds its
        lookup table on, and the same one
        :meth:`symbolic_ai_models.models.omegaclaw.base.OmegaClaw.perceive`
        defaults to. Sharing it means the lookup-table agent here is the model
        harness's floor, moved into a trajectory, rather than a near-miss of it.
        """
        view, node = obs.graph, obs.node
        if view is None or node < 0:
            return super().context_key(obs)
        p = view.parent[node]
        return ((view.types[p] or "mask") if 0 <= p < len(view.types) else "ROOT",
                min(view.slot[node], 8), min(view.depth[node], 8),
                bool(view.children(node)))

    def summarize(self, totals) -> dict[str, float]:
        """Adds the two numbers this environment exists to report.

        ``label_acc`` is per *node*, not per episode, so it is the quantity the
        model harness calls ``label_acc`` and can be discussed beside it.
        ``recoverable`` is the share of *drawn* nodes whose answer turned out to
        be reachable by pointing, and therefore the share that was actually
        asked about — the honest statement of how much of the task this
        environment declined to pose. It is deliberately not a share of every
        maskable node: that would fold the mask rate into it and report a
        different quantity than its name claims, which is what the first version
        did (0.09 at ``mask_rate=0.15``, and nothing wrong with the filter).
        """
        from .base import summarize as base_summarize
        out = base_summarize(totals)
        fills = totals.get("fills", 0.0)
        drawn = totals.get("drawn", 0.0)
        out["label_acc"] = (totals.get("fills_right", 0.0) / fills
                            if fills else float("nan"))
        out["recoverable"] = (totals.get("recoverable", 0.0) / drawn
                              if drawn else float("nan"))
        out["fills"] = fills
        return out
