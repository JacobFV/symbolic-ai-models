"""``template-001`` and its two knobs: recognise the template, refill the slots.

The learned parser. It rests on one fact about this corpus, which is checkable
rather than assumed: an episode is a template plus a draw. Two episodes of
``adversarial_argumentation`` have the same record, the same field names and the
same predicate heads; they differ in twelve nonce symbols. So a parser that can
(a) find which template a string instantiates and (b) work out which words were
drawn this time has recovered the graph, and neither step needs a grammar
written by hand.

The two steps, and what each is allowed to see
----------------------------------------------

**Recognise.** A nearest-neighbour lookup over training prompts. ``template-001``
does it on *layout only* — punctuation, bullets, line counts, token shapes — and
never looks at a word. That is a deliberate handicap in English and the entire
point of the experiment: layout survives translation, so if the grammar is what
was learned, the lookup should still work in Chinese.

**Refill.** The retrieved graph is a template with the previous episode's draw
still in it. Its *content* labels — the ones that vary between episodes of that
lesson, per :mod:`symbolic_ai_parsers.lexicon` — are replaced by this text's
content words, matched in order of first appearance. Frame labels are kept. That
alignment-by-order is the crude step and it is where most of the remaining error
lives; it is written this way because the alternative is a learned alignment,
and a learned alignment would have to be fitted, and this parser is already
carrying enough fitted decisions.

The knobs, both registered
--------------------------

``template-001``  layout lookup, lexicon estimated from the training episodes.
``template-lex``  layout lookup, lexicon **seeded** from the full curriculum.
``template-seeded`` word lookup **and** seeded lexicon — the whole shortcut.

The middle one exists so the two halves of the shortcut are separable. A bundle
that changes two things and moves a number tells you a number moved.

Stated before the numbers, so it cannot be adjusted afterwards
--------------------------------------------------------------

* If seeding the lexicon does nothing in English, the knob is uninteresting and
  the write-up says so; ``FRAME_THRESHOLD`` will not be swept to rescue it.
* The prediction is that ``template-seeded`` wins in English and loses badly in
  Chinese, while ``template-001`` degrades gently. What refutes it: Chinese
  ``retrieval_acc`` for ``template-001`` collapsing too, which would mean the
  layout features are not language-independent after all — plausible, since
  Chinese punctuation is full-width and only NFKC stands between that and a
  different feature vector.
* What would refute the whole approach: ``retrieve-001``, which does no parsing,
  matching ``template-001`` in English. Then "refill" buys nothing and this is a
  lookup table with extra steps.
"""

from __future__ import annotations

from typing import Sequence

from symbolic_ai_models.data.curriculum import Episode
from symbolic_ai_models.data.graph import Graph

from ..base import Parser, register
from ..features import words_of
from ..lexicon import Lexicon
from ..retrieval import LayoutIndex, WordIndex


class TemplateParser(Parser):
    """Retrieve a template graph, then substitute this episode's content words."""

    #: which lookup signal this variant is allowed to use
    lookup: str = "layout"
    #: whether the lexicon is handed over instead of estimated
    seeded: bool = False
    #: episodes per lesson the seeded lexicon is built from
    seed_n: int = 64

    def __init__(self) -> None:
        self._index = LayoutIndex() if self.lookup == "layout" else WordIndex()
        self._episodes: list[Episode] = []
        self._lex = Lexicon()
        #: set by ``parse``; read by the evaluator to report ``retrieval_acc``
        self.last_lesson: str = ""

    # ---- fitting -------------------------------------------------------
    def fit(self, episodes: Sequence[Episode]) -> None:
        self._episodes = list(episodes)
        self._index.fit([ep.prompt for ep in self._episodes])
        if self.seeded:
            lessons = sorted({ep.lesson_id for ep in self._episodes})
            self._lex = Lexicon.from_curriculum(n=self.seed_n, lessons=lessons)
        else:
            self._lex = Lexicon.from_episodes(self._episodes)

    # ---- parsing -------------------------------------------------------
    def parse(self, text: str) -> Graph:
        i = self._index.query(text)
        if i < 0:
            self.last_lesson = ""
            return Graph()
        ex = self._episodes[i]
        self.last_lesson = ex.lesson_id
        return _refill(ex.graph, text, self._lex.words_for(ex.lesson_id),
                       self._lex.labels_for(ex.lesson_id))

    def n_parameters(self) -> int:
        return self._index.n_parameters() + self._lex.size()

    def describe(self) -> str:
        return (f"{self.name}: lookup={self.lookup} lexicon={self._lex.source} "
                f"({self._lex.size():,} frame words)")


def _refill(template: Graph, text: str, frame_words: frozenset[str],
            frame_labels: frozenset[str]) -> Graph:
    """Copy ``template``, replacing its content labels with this text's.

    Order of first appearance on both sides. When the two lists are different
    lengths the shorter one wins and the surplus is left alone — a template
    label that survives is at least a label the lesson uses, whereas a content
    word dropped into an arbitrary slot is noise dressed as an answer.
    """
    slots: list[str] = []
    seen: set[str] = set()
    for label in template.labels:
        if label and label not in frame_labels and label not in seen:
            seen.add(label)
            slots.append(label)
    if not slots:
        return template

    fills: list[str] = []
    got: set[str] = set()
    for word in words_of(text):
        if word not in frame_words and word not in got:
            got.add(word)
            fills.append(word)

    sub = dict(zip(slots, fills))
    if not sub:
        return template
    out = Graph.from_dict(template.to_dict())
    out.labels = [sub.get(l, l) for l in out.labels]
    return out


@register("template-001", learned=True,
          doc="Layout lookup, lexicon estimated from training episodes.")
class TemplateLayout(TemplateParser):
    lookup = "layout"
    seeded = False


@register("template-lex", learned=True,
          doc="Layout lookup, lexicon seeded from the full curriculum vocabulary.")
class TemplateSeededLexicon(TemplateParser):
    lookup = "layout"
    seeded = True


@register("template-seeded", learned=True,
          doc="Word lookup and seeded lexicon: the whole dictionary shortcut.")
class TemplateSeeded(TemplateParser):
    lookup = "words"
    seeded = True
