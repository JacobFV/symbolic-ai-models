"""Reason by binding and unbinding hypervectors, not by counting contexts.

Every other rule-based model here answers "what usually stands in this slot" by
looking the slot up in a table. That is a commitment: it says the generator's
structure is a *partition of contexts*, and two contexts are either the same
cell or unrelated. It is why the family decides well and estimates badly, and
why widening the reach (``omegaclaw_reach``) bought nothing — a table cannot
interpolate between neighbouring cells, only split them further.

A vector-symbolic architecture makes a different commitment, and it is the one
this curriculum's generator actually satisfies. An episode is a set of
role-filler bindings; ``(parent alice frank)`` binds ``alice`` to
*argument-0-of-parent* and ``frank`` to *argument-1-of-parent*. So represent it
that way::

    trace = sum_j  role(j) * filler(j)             bind, then superpose
    probe = role(i) * trace                        unbind at the masked role
          ~ filler(i) + noise

with ``*`` elementwise multiplication over bipolar (+/-1) hypervectors — the MAP
algebra, where binding is its own inverse and unbinding is one more multiply.
Reading ``filler(i)`` back out is a nearest-neighbour cleanup against the
codebook.

Three properties follow, and each answers a specific thing measured in this repo.

**Graded, not tabular.** Cleanup returns a *similarity to every candidate*, not
a cell lookup, so near-misses score near-hits and the output is a distribution
by construction rather than a winner plus a bolted-on confidence. This is the
fuzziness the counting models cannot express and the reason they sit at 8 bits
while deciding well.

**Superposition is how exponentially many things fit in fixed width.** With
``d`` dimensions, ``k`` superposed bindings recover at signal-to-noise about
``sqrt(d/k)``: capacity degrades *smoothly* rather than failing at a cell
boundary. There is no vocabulary-sized table anywhere in this model — the whole
episode is one ``d``-vector, and the parameters are one hypervector per symbol.

**No learned layers, so the cost thesis survives.** Every operation is
elementwise multiply, add, and sign over a ``d``-vector. There is no matmul, no
gradient, no stack of layers; fitting is building a codebook and calibrating one
mixture weight. The measured throughput of this family is 150k-235k tokens/sec
on one CPU core and nothing here changes that order.

The one knob, and it is the whole experiment
--------------------------------------------
``codebook`` selects where a symbol's hypervector comes from:

``random``
    Independent bipolar vectors. Symbol identity carries *no* information — only
    which symbol is which — so the model is **exactly equivariant under
    renaming** by construction, and every point it scores is structure.

``distributional``
    Vectors seeded from symbol co-occurrence, so symbols used alike are *similar*
    rather than orthogonal. That is semantic generalisation of the kind a
    pretrained embedding table or a curated word graph would supply — a random
    projection of co-occurrence is the cheap, dependency-free stand-in for one,
    and a real table drops into the same interface.

The two differ in that one line and nothing else, so the sweep prices the seed
directly: what it buys in accuracy and bits, and what it costs in equivariance.
Seeding necessarily breaks exact equivariance — a symbol's vector now depends on
which symbol it is — and it should also *reduce* VSA capacity, because
correlated codewords interfere where orthogonal ones do not. Both are predictions
this pair can refute.

What it does not do
-------------------
It does not learn the role decomposition. ``role`` is built from parent type,
slot and depth by binding, which is an assertion that those are the generator's
coordinates. That assertion is exactly the "intentional structure" this model
exists to test, and if it is wrong the model will fail in a legible way — the
probe will be noise and the cleanup flat — rather than by quietly memorising.
"""

from __future__ import annotations

import collections
from typing import Sequence

import numpy as np

from symbolic_ai_core.calibration import MassCalibrator
from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.graph import TYPE_TO_ID
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from ..base import ModelConfig
from ..registry import register
from ..symbolic import ABSTAIN, GraphView, RuleBasedModel, Votes

__all__ = ["VSAModel", "VSARandom", "VSASeeded"]


def _bipolar(rng: np.random.Generator, n: int, d: int) -> np.ndarray:
    """``n`` independent +/-1 hypervectors. Near-orthogonal for large ``d``."""
    return rng.choice(np.array([-1.0, 1.0], dtype=np.float32), size=(n, d))


class VSAModel(RuleBasedModel):
    """Bind roles to fillers, superpose, unbind at the mask, clean up."""

    LEARNED = ("codebook", "roles", "gate_map", "type_rules", "_d", "sharpness")
    #: ``random`` or ``distributional``; see the module docstring.
    codebook_source = "random"

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__(cfg)
        self._d = int(cfg.get("vsa_dim", 4096))
        #: Softmax temperature of the cleanup. An *attribute* rather than a
        #: config read at the point of use, because ``vsa_spec_004`` fits it on
        #: held-out training episodes and the two must be the same number. The
        #: default is unchanged, so every published ``-002`` row is unmoved --
        #: which the sweep re-runs the family to confirm rather than assert.
        self.sharpness = float(cfg.get("vsa_sharpness", 12.0))
        self.seed = int(cfg.get("vsa_seed", 0))
        self.codebook: np.ndarray | None = None
        #: Structural role atoms, bound together to make a node's role.
        self.roles: dict[str, np.ndarray] = {}
        self.gate_map = MassCalibrator()
        self.type_rules: dict[tuple, collections.Counter] = {}
        self.min_support = int(cfg.get("min_support", 5))

    # ---- the codebook --------------------------------------------------
    def _build_codebook(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        return _bipolar(rng, len(tok), self._d)

    def _build_roles(self) -> dict[str, np.ndarray]:
        """One atom per structural coordinate; a role is their product.

        Binding composes, so ``ptype * slot * depth`` is a distinct vector for
        every combination without storing one per combination — the reason a
        role space that would be a large table is a handful of atoms here.
        """
        rng = np.random.default_rng(self.seed + 1)
        atoms: dict[str, np.ndarray] = {}
        for name, count in (("ptype", 32), ("slot", 12), ("depth", 12),
                            ("arity", 6)):
            vectors = _bipolar(rng, count, self._d)
            for i in range(count):
                atoms[f"{name}:{i}"] = vectors[i]
        return atoms

    def _role(self, view: GraphView, node: int) -> np.ndarray:
        """The structural coordinates of ``node``, bound into one vector."""
        parent = view.parent[node]
        ptype = (view.types[parent] or "mask") if parent >= 0 else "ROOT"
        ptype_id = TYPE_TO_ID.get(ptype, 0) % 32
        out = self.roles[f"ptype:{ptype_id}"].copy()
        out *= self.roles[f"slot:{min(view.slot[node], 11)}"]
        out *= self.roles[f"depth:{min(view.depth[node], 11)}"]
        out *= self.roles[f"arity:{min(len(view.children(node)), 5)}"]
        return out

    # ---- fitting -------------------------------------------------------
    def learn(self, episodes: Sequence[Episode], tok: SymbolTokenizer) -> None:
        self.codebook = self._build_codebook(episodes, tok)
        self.roles = self._build_roles()
        cut = max(int(len(episodes) * 0.8), 1)
        self._fit_types(episodes, tok)
        self._fit_gate(episodes[cut:] or episodes, tok)

    def _trace(self, view: GraphView) -> np.ndarray:
        """One vector holding every visible role-filler binding in the episode.

        Superposition, so the whole episode is ``d`` numbers however many nodes
        it has. Interference between bindings is the price and is what limits
        capacity; it is measured rather than assumed.
        """
        trace = np.zeros(self._d, dtype=np.float32)
        for j in range(len(view)):
            label = view.labels[j]
            if label is None or not (0 <= label < len(self.codebook)):
                continue
            trace += self._role(view, j) * self.codebook[label]
        return trace

    def _probe(self, view: GraphView, node: int,
               trace: np.ndarray) -> np.ndarray:
        """Unbind at the masked node's role. MAP binding is its own inverse."""
        return self._role(view, node) * trace

    def _similarities(self, probe: np.ndarray, candidates: Sequence[int]
                      ) -> tuple[np.ndarray | None, Sequence[int]]:
        """Cosine similarity of the recovered filler to each candidate symbol.

        Split out from :meth:`_cleanup` so that a model fitting the softmax
        temperature can compute the similarities once and try several
        temperatures against them, instead of recomputing the probe per
        temperature. The arithmetic is unchanged.
        """
        if not candidates:
            return None, ()
        norm = float(np.linalg.norm(probe))
        if norm <= 0.0:
            return None, ()
        vectors = self.codebook[np.asarray(candidates)]
        return (vectors @ probe) / (norm * np.sqrt(self._d)), candidates

    def _soften(self, sims: np.ndarray | None, candidates: Sequence[int],
                sharpness: float | None = None) -> dict[int, float]:
        """A softmax over the similarities, not an arg-max over them.

        The graded answer is the point: two candidates that are both somewhat
        bound at this role should both keep mass.
        """
        if sims is None or not candidates:
            return {}
        sims = sims - sims.max()
        weights = np.exp(sims * (self.sharpness if sharpness is None
                                 else float(sharpness)))
        total = float(weights.sum())
        if total <= 0.0:
            return {}
        return {int(c): float(w / total)
                for c, w in zip(candidates, weights) if w / total > 1e-3}

    def _cleanup(self, probe: np.ndarray, candidates: Sequence[int]
                 ) -> dict[int, float]:
        """Similarity of the recovered filler to each candidate symbol."""
        return self._soften(*self._similarities(probe, candidates))

    def _fit_gate(self, episodes: Sequence[Episode],
                  tok: SymbolTokenizer) -> None:
        scores: list[float] = []
        votes: list[float] = []
        backoff: list[float] = []
        for view, targets in self.training_views(episodes, tok, repeats=1,
                                                 seed=7,
                                                 max_nodes=self.cfg.max_nodes):
            trace = self._trace(view)
            for node, (label_id, _) in targets.items():
                if label_id < 0:
                    continue
                table = self._label_votes(view, node, trace)
                if not table:
                    continue
                scores.append(max(table.values()))
                votes.append(float(table.get(int(label_id), 0.0)))
                backoff.append(self.backoff_prob(view, node, int(label_id)))
        self.gate_map = MassCalibrator().fit(scores, votes, backoff)

    def _fit_types(self, episodes: Sequence[Episode],
                   tok: SymbolTokenizer) -> None:
        counts: dict[tuple, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for view, targets in self.training_views(episodes, tok,
                                                 max_nodes=self.cfg.max_nodes):
            for node, (_, type_id) in targets.items():
                if type_id >= 0:
                    counts[self._type_key(view, node)][int(type_id)] += 1
        self.type_rules = dict(counts)

    @staticmethod
    def _type_key(view: GraphView, node: int) -> tuple:
        parent = view.parent[node]
        return ((view.types[parent] or "mask") if parent >= 0 else "ROOT",
                min(view.slot[node], 8), min(view.depth[node], 8),
                bool(view.children(node)))

    # ---- prediction -----------------------------------------------------
    def _candidates(self, view: GraphView) -> list[int]:
        """The symbols visible in this episode.

        Restricting cleanup to what is present is not a shortcut: the trace only
        ever had these bound into it, so every other codeword is being scored
        against noise. It is also what makes the model equivariant — nothing
        outside the episode can win.
        """
        seen = {view.labels[j] for j in range(len(view))
                if view.labels[j] is not None}
        return sorted(s for s in seen if 0 <= s < len(self.codebook))

    def _label_votes(self, view: GraphView, node: int,
                     trace: np.ndarray) -> dict[int, float]:
        return self._cleanup(self._probe(view, node, trace),
                             self._candidates(view))

    def node_votes(self, view: GraphView) -> dict[int, tuple[Votes, Votes]]:
        if self.codebook is None:
            return {}
        trace = self._trace(view)
        out: dict[int, tuple[Votes, Votes]] = {}
        for i in view.hidden:
            table = self._label_votes(view, i, trace)
            type_vote = self._type_vote(view, i)
            if not table or not self.gate_map.fitted:
                out[i] = (ABSTAIN, type_vote)
                continue
            gate = float(self.gate_map(max(table.values())))
            out[i] = ((table, gate) if gate > 0.0 else ABSTAIN, type_vote)
        return out

    def source_votes(self, view: GraphView) -> dict[int, Votes]:
        """The same cleanup, read as a binding rather than as a symbol.

        A node scores as a source by how much its *filler* matches the probe, so
        the pointer and the symbol head are one computation here rather than two
        heads that have to be kept consistent.
        """
        if self.codebook is None:
            return {}
        trace = self._trace(view)
        out: dict[int, Votes] = {}
        for i in view.hidden:
            table = self._label_votes(view, i, trace)
            if not table:
                continue
            by_node: dict[int, float] = {}
            for j in range(len(view)):
                label = view.labels[j]
                if label is not None and int(label) in table:
                    by_node[j] = table[int(label)]
            if by_node:
                out[i] = (by_node, min(0.15 + 0.8 * max(by_node.values()), 0.95))
        return out

    def _type_vote(self, view: GraphView, node: int) -> Votes:
        counts = self.type_rules.get(self._type_key(view, node))
        if counts and sum(counts.values()) >= self.min_support:
            total = sum(counts.values())
            top, n = counts.most_common(1)[0]
            return {int(top): 1.0}, min(0.15 + 0.8 * n / total, 0.95)
        return ABSTAIN

    #: Whether the codebook is a pure function of ``vsa_seed`` and the vocabulary
    #: size. True for random codes, and the reason they cost nothing to store or
    #: to count. ``VSASeeded`` sets it False: its codebook is derived from data.
    codebook_is_reconstructible = True

    # ---- what this model actually costs ---------------------------------
    def symbolic_state(self) -> dict:
        """Store the seed, not 134MB of random numbers.

        A random codebook is ``_bipolar(default_rng(seed), len(tok), d)`` — a
        pure function of an integer — and pickling it wrote **177MB per
        checkpoint** for a model whose parameter count is 8,254. Three VSA runs
        came to 533MB of regenerable noise.

        Dropped from the state and rebuilt on load, which must be *bit*
        identical or every published VSA row silently moves; a test asserts it.
        A data-derived codebook is stored, because it genuinely is data.
        """
        state = super().symbolic_state()
        if self.codebook_is_reconstructible:
            state["codebook"] = None
            state["_vocab"] = 0 if self.codebook is None else len(self.codebook)
        return state

    def load_symbolic_state(self, state, tok) -> None:
        super().load_symbolic_state(state, tok)
        if self.codebook is None and self.codebook_is_reconstructible:
            vocab = int(state.get("_vocab") or len(tok))
            self.codebook = _bipolar(np.random.default_rng(self.seed), vocab,
                                     self._d)

    def n_symbolic_parameters(self) -> int:
        """What the model must be *given* to reproduce itself.

        The two variants are deliberately **not** counted the same way, because
        they do not cost the same thing, and reporting one number for both put
        them in a column that meant different things per row.

        A random codebook is one integer plus a vocabulary size, so the honest
        count is the *vectors* the model reaches into — one per symbol, plus the
        role atoms. The 33.5M signs inside them carry no information: regenerate
        them from the seed and you have the same model.

        A seeded codebook is co-occurrence statistics compressed into signs, and
        every one of those signs had to be measured. Counting it as 8,254 would
        understate it about four thousandfold and would let a data-fitted model
        advertise itself as tiny next to one that genuinely is.
        """
        if self.codebook is None:
            return len(self.roles)
        if self.codebook_is_reconstructible:
            return len(self.codebook) + len(self.roles)
        return int(self.codebook.size) + len(self.roles)

    def render(self) -> str:
        return "\n".join([
            f"=== {self.name}: {self.codebook_source} codebook, d={self._d} ===",
            f"  symbols {0 if self.codebook is None else len(self.codebook)}, "
            f"role atoms {len(self.roles)}",
            f"  gate: {'fitted' if self.gate_map.fitted else 'unfitted'}",
            "  (no learned layers; binding, superposition and cleanup only)"])


@register("vsa-002",
          doc="Vector-symbolic: bind roles to fillers, unbind at the mask.")
class VSARandom(VSAModel):
    """Random codebook. Exactly equivariant under renaming, by construction."""

    codebook_source = "random"


@register("vsa_pure-002",
          doc="VSA with the shared structural fallback off: the algebra alone.")
class VSAPure(VSARandom):
    """The same model, scored without the memorising floor every row inherits.

    ``RuleBasedModel.structural_fallback`` puts the commonest label for a
    structural context under every prediction, so an unsure model lands on the
    floor it is measured against rather than on a unigram. That is the right
    thing for a fair *comparison* and it means a published accuracy is the
    model's mechanism **plus** a shared lookup table nobody attributes.

    **Read the full-curriculum row, not the slice.** Turning the fallback off on
    a three-lesson slice took ``vsa-002`` from 0.305 to 0.102 — two thirds of
    its accuracy — and that number was written up before the sweep ran. On all
    179 lessons (``runs/vsa``, the authority) it is 0.219 to 0.200: **9%, not
    67%.** The slice overstated the effect by a factor of seven, and this is the
    sixth time in this repo's history that a small slice has produced a
    confident wrong reading. The claim that survives is narrower and still worth
    the row.

    ==================  =========  =========  =========  ==============
    model               with       without    delta      renaming drop
    ==================  =========  =========  =========  ==============
    ``vsa-002``         0.219      0.200      0.019      +0.029 -> +0.002
    ==================  =========  =========  =========  ==============

    What is real: the fallback is a memorising component every rule-based model
    inherits, it is worth a real if modest slice of accuracy, and **it is where
    this model's renaming sensitivity lives**. With it off the drop is +0.002 —
    which is the proof in ``tests/test_vsa.py`` holding at full scale: the
    winning cleanup score reduces to ``sum(role_i * role_j)`` and cannot depend
    on which symbol won. ``vsa_pure-002`` is therefore the row to quote when the
    question is what the *algebra* is worth, and 0.200 is that number.
    """

    structural_fallback = False


@register("vsa_seeded-002",
          doc="VSA with a codebook seeded from co-occurrence, not random.")
class VSASeeded(VSAModel):
    """Symbols used alike get similar hypervectors, so cleanup generalises.

    A random projection of the symbol co-occurrence matrix, which is the cheap
    dependency-free stand-in for a pretrained embedding table or a curated word
    graph — the same interface takes either. Sign is taken at the end so the
    algebra stays bipolar and every other line of the model is unchanged.

    Two predictions this is here to test, both refutable. It should generalise
    where the random codebook cannot, because an unseen symbol still sits near
    the symbols it behaves like. And it should *lose* capacity and equivariance,
    because correlated codewords interfere in superposition where orthogonal
    ones do not, and because a symbol's vector now depends on which symbol it is.
    """

    codebook_source = "distributional"
    #: Derived from data, so it is stored rather than regenerated, and counted
    #: as the 33.5M measured signs it is rather than as 8,254 vectors.
    codebook_is_reconstructible = False

    def _build_codebook(self, episodes: Sequence[Episode],
                        tok: SymbolTokenizer) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        vocab = len(tok)
        window = int(self.cfg.get("vsa_window", 4))
        # Co-occurrence over the training text only. Node labels feed it too,
        # so a symbol seen mostly in graphs still gets a neighbourhood.
        context: dict[int, collections.Counter] = collections.defaultdict(
            collections.Counter)
        for episode in episodes:
            ids = tok.encode(episode.text)
            for i, a in enumerate(ids):
                for b in ids[max(0, i - window):i + window + 1]:
                    if b != a:
                        context[a][b] += 1
        if not context:
            return super()._build_codebook(episodes, tok)

        # Random projection of the co-occurrence rows: the standard cheap
        # embedding, and the one place dense arithmetic happens. It runs once,
        # at fit time, and nothing at prediction time touches it.
        projection = rng.normal(size=(vocab, self._d)).astype(np.float32)
        projection /= np.sqrt(self._d)
        out = np.zeros((vocab, self._d), dtype=np.float32)
        for symbol, counts in context.items():
            if not (0 <= symbol < vocab):
                continue
            total = sum(counts.values()) or 1
            for other, c in counts.items():
                if 0 <= other < vocab:
                    out[symbol] += projection[other] * (c / total)
        # Symbols with no context keep an independent random code rather than a
        # zero vector, which would bind to nothing and pollute every trace.
        empty = ~out.any(axis=1)
        out[empty] = _bipolar(rng, int(empty.sum()), self._d)
        signs = np.sign(out)
        signs[signs == 0] = 1.0
        return signs.astype(np.float32)
