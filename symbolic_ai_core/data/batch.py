"""One batch type for both tasks.

This is the harness. Every model in this repo consumes exactly one thing — a
:class:`SymbolicBatch` — and the two tasks differ only in how that batch was
filled in:

============  ==========================  ================================
              next-token                  masked node
============  ==========================  ================================
``tokens``    text pieces                 node labels, some replaced by
                                          ``<mask>``
``types``     all ``text``                the term type of each node
``rel``       ``None`` (positions are     the relation between every pair
              a chain, so a model uses    of nodes: parent, child-slot-k,
              relative-position bias)     sibling, ancestor, same-label
``causal``    ``True``                    ``False``
``target_*``  the next token              the hidden label and type
============  ==========================  ================================

Because the shape is shared, an architecture is written once and is
immediately answerable on both questions, which is the only way the comparison
this repo is for can be made honestly. And because ``tokens`` indexes the same
vocabulary in both columns, the output head is shared too: predicting the next
word and naming a masked predicate are the same classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import torch

from .curriculum import Episode
from .graph import STRUCTURAL, TYPE_TO_ID, Graph
from .tokenizer import SymbolTokenizer

__all__ = ["SymbolicBatch", "RELATIONS", "N_RELATIONS", "MAX_SLOT",
           "relation_matrix", "collate_text", "collate_graph", "IGNORE"]

#: The loss ignores this index, matching ``F.cross_entropy``'s default.
IGNORE = -100

#: How many child slots get their own relation before they share the generic
#: ``child`` one. Eight covers every arity the curriculum's terms actually use
#: except long lists, where "which slot exactly" stops being the useful fact.
MAX_SLOT = 8

RELATIONS = (
    "none", "self", "parent", "child", "sibling", "ancestor", "descendant",
    "same_label",
    *[f"child_{k}" for k in range(MAX_SLOT)],
    *[f"parent_{k}" for k in range(MAX_SLOT)],
)
REL = {r: i for i, r in enumerate(RELATIONS)}
N_RELATIONS = len(RELATIONS)


@dataclass
class SymbolicBatch:
    """A padded batch of symbol sequences, with optional explicit relations."""

    tokens: torch.Tensor              # [B, L] long — symbol ids
    types: torch.Tensor               # [B, L] long — node-type ids
    pad_mask: torch.Tensor            # [B, L] bool — True where real
    depth: torch.Tensor               # [B, L] long — tree depth (0 for text)
    causal: bool                      # whether attention must not look ahead
    rel: torch.Tensor | None = None   # [B, L, L] uint8 — relation ids, graphs only
    target_tokens: torch.Tensor | None = None   # [B, L] long, IGNORE where none
    target_types: torch.Tensor | None = None    # [B, L] long, IGNORE where none
    #: [B, L] long — for each masked node, the index of a **visible** node of the
    #: same graph carrying the same label, or IGNORE if the answer appears
    #: nowhere else. The label task is largely a binding problem: on the full
    #: curriculum 71.9% of scored answers are already present on a visible node,
    #: so they want copying rather than naming. Several sources are usually
    #: valid, and only the first is stored — a pointer must therefore be scored
    #: by the *label* of the node it picks, never by the index matching this one.
    target_source: torch.Tensor | None = None
    #: [B, L] long — a per-episode identifier for *which symbol* a node carries,
    #: IGNORE where it carries none. Vocabulary ids cannot serve here: every
    #: out-of-vocabulary label collapses to ``unk``, so two different invented
    #: names compare equal and a pointer that copied the wrong one would score
    #: as correct. These ids are assigned from the label strings themselves, so
    #: equality means equality, and the censored 18% becomes scorable.
    label_group: torch.Tensor | None = None
    #: [B, L] bool — positions whose target is a token of the answer itself.
    #: Text batches only; used for reporting, never for the input or the loss.
    answer_mask: torch.Tensor | None = None
    meta: dict[str, Any] | None = None

    @property
    def batch_size(self) -> int:
        return int(self.tokens.shape[0])

    @property
    def length(self) -> int:
        return int(self.tokens.shape[1])

    def to(self, device: torch.device | str) -> "SymbolicBatch":
        move = lambda t: None if t is None else t.to(device, non_blocking=True)
        return SymbolicBatch(
            tokens=move(self.tokens), types=move(self.types),
            pad_mask=move(self.pad_mask), depth=move(self.depth),
            causal=self.causal, rel=move(self.rel),
            target_tokens=move(self.target_tokens),
            target_types=move(self.target_types),
            target_source=move(self.target_source),
            label_group=move(self.label_group),
            answer_mask=move(self.answer_mask), meta=self.meta)


# ---------------------------------------------------------------------------
# relations
# ---------------------------------------------------------------------------
def relation_matrix(g: Graph, n: int,
                    hidden: Sequence[int] | None = None) -> np.ndarray:
    """``[n, n]`` relation ids for the first ``n`` nodes of ``g``.

    Assignment runs weakest-first so that a stronger relation overwrites a
    weaker one: two nodes that are siblings *and* share a label are recorded as
    siblings, because that is the more specific fact about the pair.

    ``same_label`` keys on the label **string**, not on its vocabulary id. A
    per-episode invented name like ``o2`` is very often out of vocabulary, and
    keying on ids would make every out-of-vocabulary node coreferent with every
    other — which is precisely backwards for the variable-binding lessons this
    relation exists to serve.

    ``hidden`` lists nodes whose labels the model is about to be asked for.
    Their coreference edges are **withheld**, because ``same_label`` is derived
    from the very string being predicted: telling a model that the masked node
    shares a label with node 7 hands it the answer, and a masked-node score
    computed with those edges present measures nothing. The structural
    relations — parent, child slot, sibling, ancestor — are kept, since those
    are properties of the tree rather than of the hidden symbol.
    """
    m = np.zeros((n, n), dtype=np.uint8)
    parent = np.asarray(g.parent[:n], dtype=np.int64)
    slot = np.asarray(g.slot[:n], dtype=np.int64)

    if n:
        uniq: dict[str, int] = {}
        lab = np.asarray([uniq.setdefault(l, len(uniq)) if l else -1
                          for l in g.labels[:n]], dtype=np.int64)
        if hidden is not None and len(hidden):
            lab = lab.copy()
            lab[np.asarray(hidden, dtype=np.int64)] = -1
        same = (lab[:, None] == lab[None, :]) & (lab[:, None] >= 0)
        m[same] = REL["same_label"]

    # ancestor / descendant, by walking each node up to the root
    for i in range(n):
        p = parent[i]
        while 0 <= p < n:
            m[i, p] = REL["ancestor"]        # p is an ancestor of i
            m[p, i] = REL["descendant"]
            p = parent[p]

    # siblings: same parent, excluding the diagonal and excluding roots
    if n:
        real = parent >= 0
        sib = (parent[:, None] == parent[None, :]) & real[:, None] & real[None, :]
        np.fill_diagonal(sib, False)
        m[sib] = REL["sibling"]

    # immediate parent / child, tagged with the slot the child sits in
    idx = np.arange(n)
    has_p = parent >= 0
    ci, pi = idx[has_p], parent[has_p]
    s = np.minimum(slot[has_p], MAX_SLOT - 1)
    m[ci, pi] = REL["parent_0"] + s          # "my parent, and I am its slot s"
    m[pi, ci] = REL["child_0"] + s           # "my slot-s child"

    np.fill_diagonal(m, REL["self"])
    return m


# ---------------------------------------------------------------------------
# collators
# ---------------------------------------------------------------------------
def collate_text(episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                 max_len: int = 512) -> SymbolicBatch:
    """Next-token prediction over the rendered episode.

    Each sequence is ``<bos> prompt \\n answer <eos>``, truncated from the left
    so the answer always survives — a batch of truncated questions with no
    answers would train the model on the half of the episode that carries no
    supervision.

    The sequence is built from the two halves separately rather than by encoding
    ``ep.text`` in one go. Concatenating the pieces gives byte-identical text, so
    nothing about the model's input changes — but it makes the boundary between
    question and answer *exactly* known, which is what ``answer_mask`` needs.

    ``answer_mask`` marks the positions whose target is a token of the answer
    itself. It carries no gradient and changes no input; it exists because
    without it the language-modelling score is uninterpretable. Across the
    curriculum the answer is about **1.4%** of the scored positions — the other
    98.6% is the question and the boilerplate that frames it — so an
    undifferentiated ``token_bits`` mostly measures how well a model reproduces
    "Answer with exactly one of:". See :mod:`symbolic_ai_models.tasks.lm`.
    """
    seqs, answer_spans = [], []
    for ep in episodes:
        prefix = tok.encode(ep.prompt + "\n", bos=True)
        answer = tok.encode(ep.answer, eos=True)
        seq = prefix + answer
        start = len(prefix)
        if len(seq) > max_len:                       # keep the tail: the answer
            cut = len(seq) - max_len
            seq, start = seq[cut:], max(start - cut, 0)
        seqs.append(seq)
        # the answer's own tokens, excluding the <eos> that closes it
        answer_spans.append((start, len(seq) - 1))

    L = max(len(s) for s in seqs)
    B = len(seqs)
    tokens = torch.full((B, L), tok.pad_id, dtype=torch.long)
    pad_mask = torch.zeros((B, L), dtype=torch.bool)
    answer_mask = torch.zeros((B, L), dtype=torch.bool)
    for b, s in enumerate(seqs):
        tokens[b, :len(s)] = torch.tensor(s, dtype=torch.long)
        pad_mask[b, :len(s)] = True
        first, last = answer_spans[b]
        # position t predicts token t+1, so the position that predicts the first
        # answer token is one before it.
        if last > first:
            answer_mask[b, first - 1:last - 1] = True

    # position t predicts the token at t+1; the last real position has no target
    targets = torch.full((B, L), IGNORE, dtype=torch.long)
    targets[:, :-1] = torch.where(pad_mask[:, 1:], tokens[:, 1:],
                                  torch.full_like(tokens[:, 1:], IGNORE))
    return SymbolicBatch(
        tokens=tokens,
        types=torch.full((B, L), TYPE_TO_ID["text"], dtype=torch.long),
        pad_mask=pad_mask, depth=torch.zeros((B, L), dtype=torch.long),
        causal=True, rel=None, target_tokens=targets, answer_mask=answer_mask,
        meta={"task": "lm", "lesson_ids": [ep.lesson_id for ep in episodes],
              # The episode's true term graph, in row order. **For the oracle
              # parser and nothing else.** It is the answer key: 85.3% of
              # answers on the full curriculum are literally the label of one of
              # its nodes, so a model reading it unrestricted while predicting
              # the next token is cheating and its numbers are worthless. The
              # only consumer is `OraclePrefix`, which is flagged
              # `needs_truth = True`, is documented as a ceiling rather than a
              # system, and returns only the part of it whose symbols the reader
              # has already read -- see `symbolic_ai_models.prefix`. Nothing
              # else in the repo may read this key.
              "graphs": [ep.graph for ep in episodes]})


def text_batch(ids: Sequence[int], tok: SymbolTokenizer,
               device: torch.device | str = "cpu") -> SymbolicBatch:
    """One unpadded text sequence as a batch of one, with no targets.

    What a decoder and a choice-scorer need: the model's own input format, built
    from ids that are already in hand rather than from an episode. Causal, so a
    model reading it can only see what precedes each position.
    """
    x = torch.as_tensor(list(ids), dtype=torch.long, device=device)[None]
    B, L = x.shape
    return SymbolicBatch(
        tokens=x,
        types=torch.full((B, L), TYPE_TO_ID["text"], dtype=torch.long, device=device),
        pad_mask=torch.ones((B, L), dtype=torch.bool, device=device),
        depth=torch.zeros((B, L), dtype=torch.long, device=device),
        causal=True, rel=None, meta={"task": "lm"})


def collate_graph(episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                  max_nodes: int = 256, mask_rate: float = 0.15,
                  rng: np.random.Generator | None = None,
                  mask_all: bool = False) -> SymbolicBatch:
    """Masked-node prediction over the episode's term graph.

    A masked node loses **both** its label and its type, and both are predicted:
    the type is the structural question (what kind of thing sits here) and the
    label is the symbolic one (which predicate, which variable, which field).
    Reporting them separately is the point — a model can be good at shape and
    bad at reference, and one number would hide that.

    Structural types carry no label, so they are masked for their type only and
    excluded from the label loss; predicting the empty label of a list is free
    and would otherwise pad the score.
    """
    rng = rng or np.random.default_rng()
    graphs = [ep.graph for ep in episodes]
    lens = [min(len(g), max_nodes) for g in graphs]
    L, B = max(max(lens), 1), len(graphs)

    tokens = torch.full((B, L), tok.pad_id, dtype=torch.long)
    types = torch.full((B, L), TYPE_TO_ID["pad"], dtype=torch.long)
    depth = torch.zeros((B, L), dtype=torch.long)
    pad_mask = torch.zeros((B, L), dtype=torch.bool)
    rel = torch.zeros((B, L, L), dtype=torch.uint8)
    tgt_tok = torch.full((B, L), IGNORE, dtype=torch.long)
    tgt_typ = torch.full((B, L), IGNORE, dtype=torch.long)
    tgt_src = torch.full((B, L), IGNORE, dtype=torch.long)
    lab_grp = torch.full((B, L), IGNORE, dtype=torch.long)

    n_masked = 0
    for b, (g, n) in enumerate(zip(graphs, lens)):
        label_ids = [tok.label_id(l) if l else -1 for l in g.labels[:n]]
        type_ids = [TYPE_TO_ID[t] for t in g.types[:n]]
        tokens[b, :n] = torch.tensor(label_ids, dtype=torch.long).clamp(min=tok.unk_id)
        types[b, :n] = torch.tensor(type_ids, dtype=torch.long)
        depth[b, :n] = torch.tensor(g.depth[:n], dtype=torch.long).clamp(max=63)
        pad_mask[b, :n] = True

        # Choose what to hide *before* building the relations, so the relations
        # can be built without them. See `relation_matrix`.
        chosen = (np.arange(n) if mask_all
                  else np.flatnonzero(rng.random(n) < mask_rate))
        if len(chosen) == 0 and n:          # always ask at least one question
            chosen = rng.integers(0, n, size=1)
        rel[b, :n, :n] = torch.from_numpy(relation_matrix(g, n, hidden=chosen))
        sel = torch.from_numpy(np.asarray(chosen, dtype=np.int64))
        tgt_typ[b, sel] = types[b, sel]
        scored = torch.tensor(
            [g.types[i] not in STRUCTURAL and label_ids[i] != tok.unk_id
             and label_ids[i] >= 0 for i in chosen], dtype=torch.bool)
        if scored.any():
            tgt_tok[b, sel[scored]] = tokens[b, sel[scored]]
        # Where else does this answer appear, in plain sight? Computed over
        # every masked node with a label, including the ones the vocabulary
        # cannot name -- those are 88.5% invented `ident` names on the full
        # curriculum and 80.7% of them are copyable, so excluding them from this
        # is excluding the clearest case of the thing being measured.
        groups: dict[str, int] = {}
        for i in range(n):
            label = g.labels[i]
            if label and g.types[i] not in STRUCTURAL:
                lab_grp[b, i] = groups.setdefault(label, len(groups))

        hidden_set = set(int(i) for i in chosen)
        for i in chosen:
            i = int(i)
            label = g.labels[i]
            if not label or g.types[i] in STRUCTURAL:
                continue
            for j in range(n):
                if j not in hidden_set and g.labels[j] == label:
                    tgt_src[b, i] = j
                    break

        tokens[b, sel] = tok.mask_id
        types[b, sel] = TYPE_TO_ID["mask"]
        n_masked += len(chosen)

    return SymbolicBatch(
        tokens=tokens, types=types, pad_mask=pad_mask, depth=depth,
        causal=False, rel=rel, target_tokens=tgt_tok, target_types=tgt_typ,
        target_source=tgt_src, label_group=lab_grp,
        meta={"task": "node", "n_masked": n_masked,
              "lesson_ids": [ep.lesson_id for ep in episodes],
              # The prompt, and deliberately not the answer. Audited before it
              # was added: `shortcuts.node_text_leak` finds the prompt names the
              # hidden symbol about 57% of the time it is absent from the graph
              # and pins it down 0.000% of the time, so it carries the symbol
              # without carrying its position. The answer string would carry
              # both.
              "prompts": [ep.prompt for ep in episodes],
              # Which language each prompt was rendered in. Carried because the
              # graph is *not* a function of it -- `Lesson.structured` takes no
              # language, so the term tree is byte-identical across all seven
              # packs -- which makes the language a fact about the surface and
              # nothing else. A model that conditions on it is conditioning on
              # the only thing that varies. Not an answer and not a shortcut:
              # the label is identical in every language, so knowing which
              # language cannot name the hidden symbol.
              "languages": [ep.language for ep in episodes]})
