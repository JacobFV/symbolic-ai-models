"""The masked graph, and the vote — the two types both packages already shared.

These lived in :mod:`symbolic_ai_models.models.symbolic`, and
:mod:`symbolic_ai_agents.envs.base` imported :class:`GraphView` out of it: a
package reaching into its sibling for a pure data type, which is the exact
arrangement ``symbolic_ai_core`` was split out to end. Nothing here is about
models — a ``GraphView`` is what a *reader* of a masked term is allowed to see,
whether that reader is scored by a task or by an environment — so it belongs
below both.

The old import paths still resolve; ``tests/test_layering.py`` pins that by
identity rather than by equality, because a shim that rebound a *copy* of
``GraphView`` would pass an equality check and then fail every ``isinstance``
in the agents package.

Why the vote type is here too
-----------------------------

:data:`Votes` is ``({symbol id: weight}, confidence)`` and the agents package's
``Preference`` is ``({action string: weight}, confidence)``. They are the same
object over different key spaces, and both are consumed by the same mixture

    p(x) = (1 - confidence) * floor(x) + confidence * votes(x)

written out twice, once in each package. Naming it once here is what makes a
**readout** possible at all: a readout is exactly the thing that decides which
key space a vote is read in, and it cannot be a knob while the two spaces are
two unrelated tuples in two unrelated files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Hashable, Mapping, TypeVar

import numpy as np

from .data.tokenizer import SymbolTokenizer

__all__ = ["GraphView", "Votes", "Preference", "ABSTAIN", "ABSTAIN_ACTION",
           "node_context"]

K = TypeVar("K", bound=Hashable)

#: ``({symbol id: weight}, confidence in [0, 1])`` — what a rule-based model
#: emits about one site before any readout has decided what it means.
Votes = tuple[Mapping[int, float], float]

#: The same thing keyed by action string, which is what an environment's legal
#: action set is indexed by. One readout's output is the other's.
Preference = tuple[Mapping[str, float], float]

#: What a reader returns when it has nothing to say: no votes, no confidence.
#: The mixture then reduces exactly to the floor, which is the honest reading of
#: "I don't know" and is why abstention costs nothing beyond the prior it
#: declined to improve on.
ABSTAIN: Votes = ({}, 0.0)

#: :data:`ABSTAIN` in the action key space. Two constants rather than one
#: because an empty mapping typed as ``Mapping[int, float]`` is not an empty
#: mapping typed as ``Mapping[str, float]`` to anything that checks.
ABSTAIN_ACTION: Preference = ({}, 0.0)


@dataclass
class GraphView:
    """A masked graph, as a reader is allowed to see it.

    ``labels[i]`` and ``types[i]`` are ``None`` exactly where the reader is
    being asked to predict. There is no second field holding the true value: a
    reader that wanted to cheat would have nothing to read. The relations in
    ``rel`` have already had the coreference edges of hidden nodes withheld by
    :func:`~symbolic_ai_core.data.batch.relation_matrix`, so the shape of the
    tree is visible and the identity of the hidden symbol is not.
    """

    labels: list[int | None]
    types: list[str | None]
    parent: list[int]
    slot: list[int]
    depth: list[int]
    rel: np.ndarray
    hidden: list[int]
    tok: SymbolTokenizer
    #: The episode's prompt, or "" when the collator supplied none. The answer
    #: is never here: it names the hidden symbol *and* locates it, which the
    #: prompt does not (see `shortcuts.node_text_leak`).
    text: str = ""
    #: Which language pack rendered :attr:`text`, or "" when unknown.
    #:
    #: This is a fact about the surface and about nothing else, which is worth
    #: stating because it is easy to assume otherwise. ``Lesson.structured``
    #: takes no language, so every field above except ``text`` is byte-identical
    #: across all seven packs for a given seed — measured on 179 lessons x 3
    #: seeds. A rule reading only the graph therefore has the same reliability
    #: in every language *by construction*, and conditioning on this field can
    #: only pay for a rule that reads ``text``.
    language: str = ""

    def __len__(self) -> int:
        return len(self.labels)

    def mentions(self, i: int) -> int:
        """How often node ``i``'s symbol occurs in the prompt, or -1 if hidden.

        Prompt frequency picks the right copy source over a random wrong one at
        AUC 0.621 — weak on its own, and the four pointers are separated by only
        0.023 of copy lift, so weak is not nothing here.
        """
        word = self.word(i)
        if word is None or not self.text:
            return -1
        return len(re.findall(r"\b" + re.escape(word) + r"\b", self.text,
                              flags=re.IGNORECASE))

    def word(self, i: int) -> str | None:
        """The label of node ``i`` as text, or ``None`` if it is hidden."""
        v = self.labels[i]
        return None if v is None else self.tok.itos[v]

    def children(self, i: int) -> list[int]:
        return [j for j, p in enumerate(self.parent) if p == i]

    def siblings(self, i: int) -> list[int]:
        p = self.parent[i]
        return [] if p < 0 else [j for j in self.children(p) if j != i]

    def parent_type(self, i: int) -> str:
        p = self.parent[i]
        return self.types[p] or "mask" if 0 <= p < len(self.types) else "ROOT"

    def path(self, i: int, depth: int = 3) -> tuple:
        """The chain of ancestor types above ``i``, nearest first."""
        out: list[str] = []
        p = self.parent[i]
        while 0 <= p < len(self.types) and len(out) < depth:
            out.append(self.types[p] or "mask")
            p = self.parent[p]
        return tuple(out)


def node_context(view: GraphView, node: int) -> tuple:
    """The structural situation, symbol-free, keyed exactly as the floor keys it.

    Deliberately the same tuple in four places: the masked-node floor's lookup
    table, the back-off a rule-based model falls to when it abstains,
    :meth:`symbolic_ai_agents.envs.repair.Repair.context_key`, and
    ``OmegaClaw.perceive``'s default. The back-off a reader falls to should be
    the baseline it is measured against, not some near-miss of it — and four
    hand-copied near-misses is how that stops being true without anyone
    noticing, which is why the tuple is written once, here.
    """
    p = view.parent[node]
    return ((view.types[p] or "mask") if p >= 0 else "ROOT",
            min(view.slot[node], 8), min(view.depth[node], 8),
            bool(view.children(node)))
