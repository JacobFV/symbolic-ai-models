"""Claws that read the prose, because it is the only thing the language changes.

The eleven claws in :mod:`~symbolic_ai_models.models.omegaclaw.base` read the
term graph and nothing else, and ``Lesson.structured`` takes no language — the
graph is byte-identical across all seven packs, measured on 179 lessons x 3
seeds. So a graph-only rule has, by construction and not by accident, the same
reliability in every language. Conditioning ``perceive`` on the language would
partition the evidence table into copies of one distribution: strictly worse
than not doing it, and incapable of producing the per-language reliability
differences that the whole "cluster the languages by their rules" argument needs
as input.

``GraphView.text`` is the exception. It is the rendered prompt, it is already
carried through the collator, and it is the one field that moves when the
language does. Measured share of graph labels appearing verbatim in the prompt,
179 lessons x 2 seeds::

    symbols          0.978
    english          0.808
    english_synonym  0.808
    swahili          0.693
    turkish          0.650
    spanish          0.498
    chinese          0.285

That is a real span, and note before reading anything into it that the order is
**not** genealogical: Spanish, the one language here that is a relative of
English, sits second from the bottom, because it inflects nouns and adjectives
for gender and number and a bare label stops matching. What varies here is
morphological richness and whether the orthography puts breaks around words —
Chinese is last because it has no spaces, so ``\\b`` finds no boundary between a
label and the character next to it.

Three claws, and why these three
--------------------------------
Each pairs a **structurally defined candidate set** with a **surface decision**
inside it. That split is deliberate: it keeps the claws pointer-valued, so the
family's exact equivariance under renaming survives — every claim still names a
visible node of this episode and returns that node's own label, never a
remembered symbol. What the prose supplies is only *which* of several
structurally admissible nodes to point at.

They refuse to fire when the prose names none of the candidates. That is what
makes the firing rate itself a measurement: in Chinese these claws mostly stay
silent, and silence is the signal, not a defect to be papered over with a
structural fallback.

What this costs, stated plainly
-------------------------------
Adding claws means a model using them differs from ``omegaclaw_ctx-001`` in two
places at once, which the family's whole design exists to prevent. That is why
the sweep registers ``omegaclaw_text-002`` (these claws, no language) alongside
``omegaclaw_textlang-002`` (these claws, plus language): the reach is held fixed
between *those* two, so their difference is the value of knowing the language and
cannot be the value of the wider reach.
"""

from __future__ import annotations

import re
from typing import Mapping

from .base import CLAWS, Claim, Claw, Scan, _at

__all__ = ["SURFACE_CLAWS", "TEXT_CLAWS", "Surface", "surface_of"]


class Surface:
    """Where each visible label occurs in the prompt. Built once per view.

    One :func:`re.finditer` pass with a single alternation over every distinct
    visible label, rather than :meth:`GraphView.mentions` per candidate. The
    claws below ask about a handful of nodes each, for every hidden node of
    every view, over four masking passes — per-candidate regex would run the
    same search hundreds of times against the same string.
    """

    __slots__ = ("count", "first")

    def __init__(self, scan: Scan) -> None:
        self.count: dict[str, int] = {}
        self.first: dict[str, int] = {}
        text = scan.view.text
        words = {w.lower() for i in range(scan.n)
                 if (w := scan.view.word(i))}
        if not text or not words:
            return
        # Longest first, so `o1` inside `o10` cannot win the alternation.
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in
                              sorted(words, key=len, reverse=True)) + r")\b",
            re.IGNORECASE)
        for match in pattern.finditer(text):
            word = match.group(0).lower()
            self.count[word] = self.count.get(word, 0) + 1
            self.first.setdefault(word, match.start())

    def mentions(self, scan: Scan, node: int) -> int:
        word = scan.view.word(node)
        return 0 if word is None else self.count.get(word.lower(), 0)

    def position(self, scan: Scan, node: int) -> int | None:
        word = scan.view.word(node)
        return None if word is None else self.first.get(word.lower())


def surface_of(scan: Scan) -> Surface:
    """The surface index for this scan, built on first use and cached on it.

    Cached on the ``Scan`` rather than held in a module-level dict so that it
    dies with the view it describes; a global cache keyed by view would be a
    slow leak across a 25,000-episode corpus.
    """
    found = getattr(scan, "_surface_index", None)
    if found is None:
        found = Surface(scan)
        scan._surface_index = found              # type: ignore[attr-defined]
    return found


def _most_mentioned(scan: Scan, candidates: list[int]) -> int | None:
    """The candidate the prose names most often, or nothing if it names none.

    Ties break towards the lower node index — deterministic across processes,
    which a set-derived or dict-derived order would not be. Refusing on ties
    instead was considered and rejected: two siblings each named once is the
    common case in short prose, and a claw that declined it would fire so rarely
    that its per-language rate would be noise.
    """
    best, best_count = None, 0
    for node in candidates:
        count = surface_of(scan).mentions(scan, node)
        if count > best_count:
            best, best_count = node, count
    return best


def claw_text_sibling(scan: Scan, node: int) -> Claim | None:
    """Of this node's siblings, the one the prose talks about most."""
    return _at(scan, _most_mentioned(scan, scan.siblings(node)), 0.45)


def claw_text_slotmate(scan: Scan, node: int) -> Claim | None:
    """Of the visible nodes filling this kind of slot, the most talked about.

    ``slotmate`` in the base set answers the same structural question by
    frequency *in the graph*; this one answers it by frequency *in the prose*,
    which is the same operator reading a different surface. Whether that is
    worth anything is exactly what the sweep is for.
    """
    key = scan.slot_key(node)
    mates = [i for i in range(scan.n)
             if i != node and scan.labels[i] is not None
             and scan.slot_key(i) == key]
    return _at(scan, _most_mentioned(scan, mates), 0.35)


def claw_text_first(scan: Scan, node: int) -> Claim | None:
    """Whichever visible label the prose introduces first.

    The prose orders its material; the graph does not order it the same way. In
    ``symbols`` — an s-expression notation — first mention is close to a
    linearisation of the tree, and in Chinese it is very often nothing at all,
    which is the spread this claw exists to expose.
    """
    surface = surface_of(scan)
    best, best_at = None, None
    for i in range(scan.n):
        if i == node or scan.labels[i] is None:
            continue
        at = surface.position(scan, i)
        if at is not None and (best_at is None or at < best_at):
            best, best_at = i, at
    return _at(scan, best, 0.3)


#: The surface reach on its own.
SURFACE_CLAWS: Mapping[str, Claw] = {
    "text_sibling": claw_text_sibling,
    "text_slotmate": claw_text_slotmate,
    "text_first": claw_text_first,
}

#: The base reach plus the surface reach. Base first, so that a winner-take-all
#: tie still breaks exactly where it broke for ``omegaclaw_ctx-001``.
TEXT_CLAWS: Mapping[str, Claw] = {**CLAWS, **SURFACE_CLAWS}
