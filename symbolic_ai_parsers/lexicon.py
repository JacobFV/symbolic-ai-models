"""Which words are the template and which words are the episode.

Every lesson in the curriculum is a template plus a draw. ``analogy`` always
says ``outranks``; it says ``kgvl`` or ``dave`` depending on the seed. Telling
those two apart is the single most useful thing a parser of this corpus can
know, because the template words are the *structure* — they say what the record
field is and which predicate a line instantiates — and the drawn words are the
*content*, which has to be copied out of the text and cannot be memorised.

A :class:`Lexicon` is that judgement, per lesson: a word is **frame** if it
appears in nearly every episode of its lesson, and content otherwise. The same
test is applied to graph labels.

Dictionary seeding
------------------

The judgement is a frequency estimate, so it gets better with more episodes, and
episodes are free — ``langcurriculum`` will draw as many as asked. A parser can
therefore be handed a lexicon built from the **full curriculum vocabulary**
(:meth:`Lexicon.from_curriculum`) instead of estimating one from the handful of
training episodes it was fitted on (:meth:`Lexicon.from_episodes`). That is a
real head start and it is the sort of thing one does to make an evaluation cheap
— but it is also exactly the kind of shortcut that quietly turns a grammar
result into a vocabulary result.

**So it is a knob with a control registered beside it, never a default.**
``template-001`` estimates its lexicon from its own training episodes;
``template-seeded`` is handed the curriculum's. The bare name ``template``
resolves to ``-001``, the unseeded one, so nothing can ask for "the template
parser" and silently get the seeded version — the registry's numbered-resolution
rule is doing load-bearing work here, which is why it was copied over.

Seeding uses **training seeds only** (0 upward). Building the dictionary from
episodes at eval seeds would be tuning against the evaluation set with extra
steps, and it would not even be detectable in the resulting score.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Sequence

from symbolic_ai_core.data.curriculum import Episode, generate, lesson_ids

from .features import words_of

__all__ = ["Lexicon", "FRAME_THRESHOLD"]

#: A word is frame if it appears in at least this share of its lesson's
#: episodes. Set once, on the reasoning that a template constant appears in
#: *all* of them and the margin is for optional clauses; not swept, and not
#: chosen by looking at any score.
FRAME_THRESHOLD = 0.9

_CURRICULUM_CACHE: dict[tuple, "Lexicon"] = {}


@dataclass
class Lexicon:
    """Per-lesson frame vocabulary, and the same for graph labels."""

    frame_words: dict[str, frozenset[str]] = field(default_factory=dict)
    frame_labels: dict[str, frozenset[str]] = field(default_factory=dict)
    #: episodes per lesson the estimate rests on — the thing seeding changes
    n_per_lesson: dict[str, int] = field(default_factory=dict)
    source: str = "none"

    def words_for(self, lesson: str) -> frozenset[str]:
        return self.frame_words.get(lesson, frozenset())

    def labels_for(self, lesson: str) -> frozenset[str]:
        return self.frame_labels.get(lesson, frozenset())

    def size(self) -> int:
        return sum(len(v) for v in self.frame_words.values())

    # ---- construction -------------------------------------------------
    @classmethod
    def from_episodes(cls, episodes: Sequence[Episode], *,
                      source: str = "train") -> "Lexicon":
        """Estimate from whatever episodes the parser was fitted on."""
        docs: dict[str, list[set[str]]] = collections.defaultdict(list)
        labs: dict[str, list[set[str]]] = collections.defaultdict(list)
        for ep in episodes:
            docs[ep.lesson_id].append(set(words_of(ep.prompt)))
            labs[ep.lesson_id].append({l for l in ep.graph.labels if l})
        lex = cls(source=source)
        for lid in docs:
            lex.n_per_lesson[lid] = len(docs[lid])
            lex.frame_words[lid] = _frame(docs[lid])
            lex.frame_labels[lid] = _frame(labs[lid])
        return lex

    @classmethod
    def from_curriculum(cls, *, n: int = 64, language: str = "english",
                        lessons: Sequence[str] | None = None,
                        max_nodes: int = 128) -> "Lexicon":
        """Draw ``n`` fresh **training** episodes of every lesson and estimate.

        This is the seeded dictionary. It costs a few seconds and needs no
        training run, which is the whole appeal and the whole danger.
        """
        names = tuple(lessons) if lessons is not None else tuple(lesson_ids())
        key = (names, n, language, max_nodes)
        if key not in _CURRICULUM_CACHE:
            eps = list(generate(list(names), n=n, seed0=0, language=language,
                                max_nodes=max_nodes, on_error="skip"))
            _CURRICULUM_CACHE[key] = cls.from_episodes(
                eps, source=f"curriculum:{len(names)}x{n}:{language}")
        return _CURRICULUM_CACHE[key]


def _frame(docs: Sequence[set[str]]) -> frozenset[str]:
    if not docs:
        return frozenset()
    df: collections.Counter[str] = collections.Counter()
    for d in docs:
        df.update(d)
    cut = FRAME_THRESHOLD * len(docs)
    return frozenset(w for w, c in df.items() if c >= cut)
