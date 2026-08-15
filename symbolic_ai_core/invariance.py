"""Rename every symbol and see who notices.

A model that solves the masked-node task by structure should not care what
anything is called. Rename ``alice`` to ``bob`` throughout an episode — in the
graph and in the prose — and the answer at each hidden node renames with it, so
a model reading the tree gets exactly as many right as before. A model that
learned "in this context the answer tends to be ``alice``" gets fewer.

The claim being tested is **equivariance, not invariance**, and the difference
matters. Invariance would say the predictions do not change; that is wrong and
would fail every good model, because the correct answer itself has changed.
Equivariance says the predictions change *the same way the world did*. So the
quantity to compare is accuracy, not logits: a structure-only model holds it,
and whatever a model loses is the share of its score that was riding on
vocabulary.

The renaming is a permutation of the labels the training set already contains,
never a jump to fresh strings. Renaming to unseen symbols would make every
answer out-of-vocabulary, drop it from the label score, and measure the
tokenizer rather than the model — the drop would look enormous and mean
nothing.

The model is always fitted on the **original** episodes and tested on renamed
ones. Refitting after the rename would measure whether the method can learn a
relabelled world, which is a different and much easier question.
"""

from __future__ import annotations

import collections
import copy
import re
from dataclasses import dataclass
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode
from symbolic_ai_core.data.tokenizer import SymbolTokenizer

__all__ = ["Renaming", "build_renaming", "rename_episodes"]


@dataclass
class Renaming:
    """A bijection over symbols, and the episodes it was built from."""

    mapping: dict[str, str]

    def apply(self, symbol: str) -> str:
        return self.mapping.get(symbol, symbol)

    def __len__(self) -> int:
        return len(self.mapping)


def build_renaming(episodes: Sequence[Episode], tok: SymbolTokenizer) -> Renaming:
    """A derangement of the in-vocabulary labels appearing in ``episodes``.

    Only labels the vocabulary can name are permuted, and only among
    themselves, so every renamed answer stays scoreable. Rotating the sorted
    list by one is a derangement for any set of two or more, which is what makes
    this a real test — no symbol maps to itself, so nothing can pass by
    accident.
    """
    labels = sorted({label for ep in episodes for label in ep.graph.labels
                     if label and tok.label_id(label) != tok.unk_id})
    if len(labels) < 2:
        return Renaming({})
    rotated = labels[1:] + labels[:1]
    return Renaming(dict(zip(labels, rotated)))


def rename_episodes(episodes: Sequence[Episode],
                    renaming: Renaming) -> list[Episode]:
    """Apply the renaming to the graph labels and to the prose alike.

    Both surfaces move together. Renaming only the graph would leave an episode
    whose text contradicts its structure, and any model reading across the two
    would be measured on an inconsistency rather than on a rename.
    """
    if not renaming.mapping:
        return [copy.deepcopy(ep) for ep in episodes]

    pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in
                          sorted(renaming.mapping, key=len, reverse=True)) + r")\b")

    def substitute(text: str) -> str:
        # One pass with a single alternation, so a symbol renamed into another
        # symbol's name is not renamed again on a later pass.
        return pattern.sub(lambda m: renaming.mapping[m.group(0)], text)

    out: list[Episode] = []
    for ep in episodes:
        fresh = copy.deepcopy(ep)
        fresh.graph.labels = [renaming.apply(l) if l else l
                              for l in fresh.graph.labels]
        fresh.prompt = substitute(fresh.prompt)
        fresh.answer = substitute(fresh.answer)
        fresh.choices = [substitute(c) for c in fresh.choices]
        out.append(fresh)
    return out


def label_accuracy(model, episodes: Sequence[Episode], tok: SymbolTokenizer, *,
                   max_nodes: int = 96, mask_rate: float = 0.15,
                   seed: int = 20_250_811, mask_mode: str = "scatter") -> float:
    """Masked-node label accuracy, on a fixed mask so two runs are comparable.

    The mask rate is the one evaluation uses, not ``mask_all``. Masking every
    node hides every label, so a model that answers by copying a visible
    neighbour — which is most of the structural ones — has nothing to copy and
    scores zero on both halves of the comparison. That produced a table of
    implausible 0.000 baselines and would have made the renaming look
    irrelevant to models it is precisely the test for.

    The seed is fixed and the episode order is unchanged, so the original and
    renamed runs hide the same positions and the two accuracies differ only by
    the renaming. That still holds under ``mask_mode="answer"``, where the
    positions are chosen by matching the answer string rather than by the
    generator: ``rename_episodes`` substitutes into ``answer`` as well as into
    the graph, so the same nodes are selected on both sides.
    """
    import numpy as np
    import torch

    from symbolic_ai_core.data.batch import collate_graph

    batch = collate_graph(episodes, tok, max_nodes=max_nodes,
                          mask_rate=mask_rate, mask_mode=mask_mode,
                          rng=np.random.default_rng(seed))
    was_training = model.training
    model.eval()
    with torch.no_grad():
        logits = model(batch).symbol_logits
    if was_training:
        model.train()
    scored = batch.target_tokens >= 0
    if not bool(scored.any()):
        return float("nan")
    predicted = logits.argmax(-1)
    return float((predicted[scored] == batch.target_tokens[scored]).float().mean())
