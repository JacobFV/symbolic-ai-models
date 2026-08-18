"""Multi-paragraph essays realised from a knowledge-graph subgraph.

Everything this repo has measured so far ran on a single terse paragraph of
list-like clauses — ``event: lift, carol, alice and bread; the taxonomy says: …``
— where a whole episode fits in one screen and every referent is in view. That
shape is why the substrate keeps outweighing the models: with all the symbols
visible at once, *pointing* is a short-range operation and vocabulary
memorisation is a viable strategy.

This module generates the opposite: several paragraphs of connected prose about
one topic, where a fact stated in paragraph two is needed to resolve a mention in
paragraph five, and where the same entity appears as a full noun phrase, then a
pronoun, then a definite description.

## The one design decision everything else follows from

**The graph is the ground truth; the essay is one surface realisation of it, and
the alignment between them is recorded.** Every sentence carries the triple it
realises and how many hops that triple was from the topic; every mention carries
its character span, the node it refers to, and its antecedent.

That is what makes this a substrate rather than a pile of text. From one
generator:

* mask a mention span and predict the referent — cross-paragraph coreference,
  which is exactly the *pointing* operation the ``frontier``/``corefer`` work
  spent the week on, now at a range where it cannot be done by copying a
  neighbour;
* ask a question whose answer needs a fact from paragraph *i* and a link from
  paragraph *j* — genuine multi-hop, with the hop count known rather than
  assumed;
* corrupt one sentence and ask which one contradicts the rest — the graph says
  which, so the label is exact;
* and, because spans are recorded, ask *which sentence a model actually used*,
  which no task in this repo has been able to measure.

## What is deliberately not here

No language model writes any of this. Realisation is seeded templates, so the
corpus is reproducible from ``(topic, seed)``, and the prose is duller than a
human's. The trade is intentional: a generated essay whose every clause traces to
a triple can be scrambled, permuted, and ablated as a control, and one written by
an LLM cannot.
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, Sequence

__all__ = [
    "Mention", "Sentence", "Paragraph", "Essay",
    "SECTIONS", "rich_topics", "gather", "plan", "realise", "generate",
    "sections_available", "REQUIRED",
]

#: What this generator cannot run without. Deliberately short: everything else
#: is a section that will silently not appear, which is a *reportable* fact
#: rather than a fatal one -- see :func:`sections_available`.
REQUIRED = ("word", "pos", "hypernyms", "hyponyms", "siblings")


# ---------------------------------------------------------------- content ---

#: A rhetorical section: the graph accessor it draws on, the sentence templates
#: that realise it, and the transition words that open a supporting sentence.
#: Order here is *not* the order they appear in — `plan` permutes them per
#: episode so that "the definition comes first" is never a free cue.
#: **Every template carries ``{S}``.** The first draft let support sentences
#: mention only the object — "one may add the classic to the list" — and the
#: coreference chain collapsed to zero pronouns, which is the one thing the
#: corpus exists to contain. A sentence that does not mention its subject is
#: not a link in a chain, so there are none here.
SECTIONS: dict[str, dict[str, Any]] = {
    "placement": {
        "accessor": "hypernyms",
        "topic": ["{S} is best understood as a kind of {O}.",
                  "Any account of {S} begins by placing it among the {O}.",
                  "To describe {S} is first to say that it belongs with {O}."],
        "support": ["{S} is, more broadly, one of {O}.",
                    "The wider category {S} falls under is {O}.",
                    "{S} inherits what it is from {O}."],
    },
    "varieties": {
        "accessor": "hyponyms",
        "topic": ["The kinds of {S} are not all alike; {O} is one of them.",
                  "{S} covers a range of cases, {O} among them.",
                  "The cases {S} covers are not all the same, and {O} shows why."],
        "support": ["{S} counts {O} as another such kind.",
                    "{O} falls under {S} as well.",
                    "One may add {O} to what {S} covers."],
    },
    "composition": {
        "accessor": "parts_of",
        "topic": ["What {S} is made of matters as much as what it is: it has {O}.",
                  "Structurally, {S} is not simple — {O} is one of its parts.",
                  "Take {S} apart and {O} is among what is found."],
        "support": ["{S} also has {O}.",
                    "Among the parts of {S} is {O}.",
                    "{O} belongs to {S} as well."],
    },
    "substance": {
        "accessor": "substances_of",
        "topic": ["The material question is a separate one: {S} is made of {O}.",
                  "{S} is constituted of {O}, which is not the same as having parts.",
                  "What {S} consists of is {O}."],
        "support": ["{S} is also made of {O}.",
                    "{O} enters into the make-up of {S} too.",
                    "There is {O} in {S} besides."],
    },
    "membership": {
        "accessor": "members_of",
        "topic": ["{S} is a collective thing: {O} is one of its members.",
                  "Membership is what organises {S}, and {O} is a member.",
                  "{S} is made up of members, {O} among them."],
        "support": ["{O} is a member of {S} as well.",
                    "{S} counts {O} among its members too.",
                    "{S} numbers {O} as a member besides."],
    },
    "qualities": {
        "accessor": "properties_of",
        "topic": ["Characteristically, {S} is {O}.",
                  "The quality most often ascribed to {S} is that it is {O}.",
                  "{S} is, above all, {O}."],
        "support": ["{S} is {O} as well.",
                    "One would also call {S} {O}.",
                    "{O} is a further quality of {S}."],
    },
    "behaviour": {
        "accessor": "abilities_of",
        "topic": ["{S} is defined partly by what it does: it can {O}.",
                  "Among the things {S} is able to do is {O}.",
                  "What {S} can do includes {O}."],
        "support": ["{S} can also {O}.",
                    "{S} is able to {O} besides.",
                    "Another of the capacities of {S} is to {O}."],
    },
    "contrast": {
        "accessor": "siblings",
        "topic": ["{S} is easily confused with {O}, though the two differ.",
                  "It is worth setting {S} against {O}.",
                  "{S} shares its category with {O} without being it."],
        "support": ["{S} stands apart from {O} in the same way.",
                    "The same contrast holds between {S} and {O}.",
                    "{O} is a neighbour of {S}, not an instance."],
    },
}

#: Opens a supporting sentence. Keyed loosely by whether the sentence adds to
#: the previous one or qualifies it; `realise` picks by position, not meaning,
#: because the graph does not say which relation holds between two triples.
_ADDITIVE = ("Moreover, ", "In addition, ", "Further, ", "", "", "Besides that, ")
_QUALIFY = ("That said, ", "Even so, ", "At the same time, ", "", "")


def sections_available(kg: Any, *, name: str = "", sample: int = 512
                       ) -> dict[str, float]:
    """Per section, the share of sampled nodes whose accessor returns anything.

    A section whose accessor is populated **nowhere** can never appear, and an
    essay corpus that is quietly missing two of its eight rhetorical sections
    reads exactly like one that is not. Measured rather than assumed, because
    the assumption was wrong: WordNet returns nothing at all for
    ``properties_of`` and ``abilities_of``, so the *qualities* and *behaviour*
    sections have never appeared in any essay this repo has generated.
    """
    from .knowledge_source import capabilities_of

    report = capabilities_of(kg, name=name, sample=sample,
                             names=[spec["accessor"] for spec in SECTIONS.values()])
    return {sec: report.coverage.get(spec["accessor"], 0.0)
            for sec, spec in SECTIONS.items()}


def rich_topics(kg: Any, *, min_sections: int = 3,
                min_items: int = 2) -> list[int]:
    """Nouns with at least ``min_sections`` sections that have real content.

    An essay drawn on a topic with one populated section is a paragraph, and the
    whole point here is cross-paragraph distance, so the floor is enforced at
    selection rather than papered over at realisation.
    """
    out: list[int] = []
    for n in range(len(kg)):
        if kg.pos[n] != "n":
            continue
        filled = 0
        for spec in SECTIONS.values():
            items = getattr(kg, spec["accessor"])(n)
            if len(items) >= min_items:
                filled += 1
        if filled >= min_sections:
            out.append(n)
    return out


def gather(kg: Any, topic: int, *, width: int = 4) -> dict[str, list[int]]:
    """The topic's neighbourhood, one bucket per section, capped at ``width``.

    **Directly stated facts only.** These accessors inherit down the hypernym
    chain by default, so drawing the body of the essay from the inherited set
    would state the very fact the synthesis paragraph claims is unstated — the
    "two-hop" inference would then be one hop and a copy. The first version did
    exactly that: it wrote "it has the anatomy" in the composition paragraph and
    then concluded "must also have the anatomy, even though no such thing was
    said of it directly", which was false on its face.
    """
    content: dict[str, list[int]] = {}
    for name, spec in SECTIONS.items():
        acc = getattr(kg, spec["accessor"])
        try:
            items = list(acc(topic, inherited=False))
        except TypeError:      # hypernyms/hyponyms/siblings take no flag
            items = list(acc(topic))
        if len(items) >= 2:
            content[name] = items[:width]
    return content


# ------------------------------------------------------------- the record ---

@dataclass
class Mention:
    """One reference to a node, and everything needed to score a prediction."""

    start: int
    end: int
    node: int
    #: ``name`` (full noun phrase), ``pronoun``, or ``description``
    form: str
    surface: str
    paragraph: int
    sentence: int
    #: Index into ``Essay.mentions`` of the previous mention of this node, or
    #: ``-1``. The distance between the two is the thing that makes this corpus
    #: harder than the old one, so it is recorded rather than recomputed.
    antecedent: int = -1
    #: Whether this mention is the topic and the *nearest preceding* mention is
    #: some other entity. These are the items that defeat a nearest-neighbour
    #: reader, and they are why distractors are generated at all: the ceiling
    #: analysis measured that ``prev`` — "nearest earlier visible node" — does
    #: 0.288 of frontier's copy work, more than any other single path. A corpus
    #: where ``prev`` is usually right cannot tell pointing from proximity.
    lure: bool = False
    #: Distance to the antecedent, in mentions / sentences / paragraphs. Lift
    #: plotted against these is worth more than lift pooled over all of them.
    d_mentions: int = -1
    d_sentences: int = -1
    d_paragraphs: int = -1

    @property
    def crosses_paragraph(self) -> bool:
        return self.d_paragraphs > 0


@dataclass
class Sentence:
    """One realised sentence and the triple it states."""

    text: str
    start: int
    end: int
    paragraph: int
    index: int
    #: ``(relation, subject_node, object_node)``; relation is a section name,
    #: or ``"inference"`` for the synthesis sentence.
    triple: tuple[str, int, int] | None = None
    #: How many graph edges away from the topic this sentence's content sits.
    #: 1 for a directly stated neighbour, 2 for the synthesis sentence.
    hops: int = 1


@dataclass
class Paragraph:
    section: str
    start: int
    end: int
    index: int
    sentences: list[int] = field(default_factory=list)


@dataclass
class Essay:
    """The text, and the alignment back to the graph that produced it."""

    topic: int
    topic_word: str
    kg: str
    seed: int
    text: str
    paragraphs: list[Paragraph]
    sentences: list[Sentence]
    mentions: list[Mention]
    #: The 2-hop fact the synthesis paragraph states, as
    #: ``(topic, via, object, section)`` — the intended multi-hop payload.
    inference: tuple[int, int, int, str] | None = None

    # -- convenience the tasks are built on ---------------------------------
    def mentions_of(self, node: int) -> list[Mention]:
        return [m for m in self.mentions if m.node == node]

    def long_range(self, *, min_paragraphs: int = 1) -> list[Mention]:
        """Mentions whose antecedent is at least N paragraphs back.

        These are the items the old single-paragraph corpus could not contain,
        and the reason for building this at all.
        """
        return [m for m in self.mentions if m.d_paragraphs >= min_paragraphs]

    def lures(self) -> list[Mention]:
        """Mentions whose nearest preceding mention is a *different* entity.

        The population on which "point at the referent" and "copy the nearest
        noun phrase" give different answers — which is the only population that
        can tell the two strategies apart.
        """
        return [m for m in self.mentions if m.lure]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic, "topic_word": self.topic_word, "kg": self.kg,
            "seed": self.seed, "text": self.text,
            "paragraphs": [asdict(p) for p in self.paragraphs],
            "sentences": [asdict(s) for s in self.sentences],
            "mentions": [asdict(m) for m in self.mentions],
            "inference": list(self.inference) if self.inference else None,
        }

    def stats(self) -> dict[str, Any]:
        return {
            "paragraphs": len(self.paragraphs),
            "sentences": len(self.sentences),
            "words": len(self.text.split()),
            "chars": len(self.text),
            "mentions": len(self.mentions),
            "pronouns": sum(1 for m in self.mentions if m.form == "pronoun"),
            "descriptions": sum(1 for m in self.mentions if m.form == "description"),
            "cross_paragraph": len(self.long_range()),
            "max_hops": max((s.hops for s in self.sentences), default=0),
        }


# ------------------------------------------------------------------ plan ----

def plan(kg: Any, topic: int, *, seed: int, width: int = 4,
         max_sections: int = 5) -> list[tuple[str, list[int]]]:
    """Choose which sections appear and in what order.

    The order is a seeded permutation rather than the fixed order of
    ``SECTIONS``, so that "the definition is the first paragraph" is not a cue a
    model can learn instead of reading.
    """
    rng = random.Random(seed * 7919 + topic)
    content = gather(kg, topic, width=width)
    names = sorted(content)
    rng.shuffle(names)
    names = names[:max_sections]
    return [(n, content[n]) for n in names]


def _phrase(kg: Any, n: int) -> str:
    return kg.word(n).replace("_", " ")


def _np(word: str) -> str:
    return f"the {word}"


# --------------------------------------------------------------- realise ----

class _Writer:
    """Accumulates text while keeping every offset honest.

    Spans are recorded as the text is built, never recovered by searching for a
    substring afterwards — a topic word that also occurs inside a hyponym would
    make that silently wrong.
    """

    def __init__(self) -> None:
        self.buf: list[str] = []
        self.n = 0

    def add(self, s: str) -> tuple[int, int]:
        start = self.n
        self.buf.append(s)
        self.n += len(s)
        return start, self.n

    @property
    def text(self) -> str:
        return "".join(self.buf)


def realise(kg: Any, topic: int, sections: Sequence[tuple[str, list[int]]], *,
            seed: int, pronoun_rate: float = 0.45,
            distractor_rate: float = 0.45) -> Essay:
    """Write the essay, recording every span as it goes.

    ``distractor_rate`` is the difficulty knob that matters. It does not make
    the essay longer; it makes the *nearest* noun phrase wrong more often, which
    is the only way to separate pointing from proximity.
    """
    rng = random.Random(seed * 104729 + topic + 1)
    w = _Writer()
    topic_word = _phrase(kg, topic)
    hyper = kg.hypernyms(topic)
    describe = _phrase(kg, hyper[0]) if hyper else topic_word

    paragraphs: list[Paragraph] = []
    sentences: list[Sentence] = []
    mentions: list[Mention] = []
    last_mention_of: dict[int, int] = {}

    def mention(node: int, form: str, surface: str, para: int, sent: int) -> None:
        start, end = w.add(surface)
        idx = len(mentions)
        ant = last_mention_of.get(node, -1)
        m = Mention(start=start, end=end, node=node, form=form,
                    surface=surface, paragraph=para, sentence=sent,
                    antecedent=ant)
        if ant >= 0:
            a = mentions[ant]
            m.d_mentions = idx - ant
            m.d_sentences = sent - a.sentence
            m.d_paragraphs = para - a.paragraph
            # The lure flag is about the *surface* neighbour, not the
            # coreferent one: a reader that copies the nearest preceding noun
            # phrase gets these wrong by construction.
            m.lure = bool(mentions) and mentions[-1].node != node
        mentions.append(m)
        last_mention_of[node] = idx

    def write_sentence(template: str, para: int, subj: int, obj: int,
                       rel: str, prefix: str = "", hops: int = 1,
                       subj_form: str | None = None,
                       subj_word: str | None = None) -> None:
        """Realise ``template``, emitting each piece in the order it appears.

        The slots may come in either order — ``"{O} is another such kind."``
        puts the object first — so the template is split into a sequence of
        literal and slot pieces rather than assumed to be ``{S} … {O}``.
        Getting this wrong is silent in the alignment: spans still record, they
        just point at the wrong text.
        """
        sent_idx = len(sentences)
        s_start = w.n
        form = subj_form or "name"
        word = subj_word if subj_word is not None else topic_word
        # An adjective or a verb does not take a definite article: "the artist
        # is the tall" and "it can the fly" are what a uniform `the {word}`
        # produces, and both were in the first draft's output.
        bare = kg.pos[obj] in ("a", "v") if hasattr(kg, "pos") else False
        surfaces = {
            "S": (_np(word) if form == "name"
                  else "it" if form == "pronoun" else _np(describe)),
            "O": _phrase(kg, obj) if bare else _np(_phrase(kg, obj)),
        }
        nodes = {"S": subj, "O": obj}
        forms = {"S": form, "O": "name"}

        if prefix:
            w.add(prefix)
        at_start = not prefix       # capitalise the first piece
        lower_next = bool(prefix)   # a prefix already opened the sentence
        for piece in re.split(r"(\{[SO]\})", template):
            if not piece:
                continue
            if piece in ("{S}", "{O}"):
                key = piece[1]
                surface = surfaces[key]
                if at_start:
                    surface = surface[:1].upper() + surface[1:]
                mention(nodes[key], forms[key], surface, para, sent_idx)
            else:
                if lower_next:
                    piece = piece[:1].lower() + piece[1:]
                w.add(piece)
            at_start = False
            lower_next = False
        w.add(" ")
        sentences.append(Sentence(text=w.text[s_start:w.n], start=s_start,
                                  end=w.n, paragraph=para, index=sent_idx,
                                  triple=(rel, subj, obj), hops=hops))

    # Distractors: siblings of the topic, so they share its type and its
    # relation vocabulary. A distractor sentence names its subject in full
    # while the topic is being carried by pronouns, which is what makes the
    # surface-nearest noun phrase the *wrong* antecedent.
    sibs = [s for s in kg.siblings(topic) if s != topic]
    distractors = sibs[:3]

    for p_i, (name, items) in enumerate(sections):
        spec = SECTIONS[name]
        p_start = w.n
        first = True
        sent_ids: list[int] = []
        for k, obj in enumerate(items):
            sent_ids.append(len(sentences))
            if first:
                # A paragraph always opens by naming the topic again: this is
                # what creates the cross-paragraph chain the corpus exists for.
                write_sentence(rng.choice(spec["topic"]), p_i, topic, obj, name,
                               subj_form="name" if p_i == 0 else
                               rng.choice(("name", "description")))
                first = False
                continue

            if distractors and rng.random() < distractor_rate:
                # An aside about a sibling, stated of the sibling and true of
                # it in the same relation. It is not noise — it is a competing
                # antecedent that a relational reader can rule out and a
                # proximity reader cannot.
                d = rng.choice(distractors)
                d_items = list(getattr(kg, spec["accessor"])(d)) or items
                sent_ids.append(len(sentences))
                write_sentence(rng.choice(spec["support"]), p_i, d,
                               rng.choice(d_items), name,
                               prefix=rng.choice(_QUALIFY), subj_form="name",
                               subj_word=_phrase(kg, d))

            pool = _ADDITIVE if k % 3 else _QUALIFY
            form = "pronoun" if rng.random() < pronoun_rate else "description"
            write_sentence(rng.choice(spec["support"]), p_i, topic, obj,
                           name, prefix=rng.choice(pool), subj_form=form)
        w.add("\n\n")
        paragraphs.append(Paragraph(section=name, start=p_start, end=w.n,
                                    index=p_i, sentences=sent_ids))

    inference = _write_inference(kg, topic, sections, w, rng, paragraphs,
                                 sentences, mentions, last_mention_of, describe)

    # Distances and lure flags are derived from the finished mention list in
    # one pass rather than at each write site. The synthesis paragraph appends
    # mentions directly and skipped the per-site computation, which left its
    # distances at -1 while its antecedents were set — caught by the test that
    # recomputes them, not by anything in the output.
    for i, m in enumerate(mentions):
        if m.antecedent < 0:
            m.d_mentions = m.d_sentences = m.d_paragraphs = -1
            m.lure = False
            continue
        a = mentions[m.antecedent]
        m.d_mentions = i - m.antecedent
        m.d_sentences = m.sentence - a.sentence
        m.d_paragraphs = m.paragraph - a.paragraph
        m.lure = i > 0 and mentions[i - 1].node != m.node

    text = w.text.rstrip()
    return Essay(topic=topic, topic_word=topic_word, kg=getattr(kg, "name", "?"),
                 seed=seed, text=text, paragraphs=paragraphs,
                 sentences=sentences, mentions=mentions, inference=inference)


def _write_inference(kg, topic, sections, w, rng, paragraphs, sentences,
                     mentions, last_mention_of, describe):
    """A closing paragraph stating a fact that is *two* hops from the topic.

    This is the multi-hop payload: the fact is true of the topic only by way of
    an ancestor, and both premises are stated in earlier paragraphs, so a model
    that answers it has combined two sentences rather than copied one.
    """
    hyper = kg.hypernyms(topic)
    if not hyper:
        return None
    for accessor, section in (("parts_of", "composition"),
                              ("properties_of", "qualities"),
                              ("abilities_of", "behaviour"),
                              ("substances_of", "substance")):
        # The first draft subtracted the *hypernym's* items from the topic's
        # and always got nothing, because WordNet states these relations at the
        # parent and the accessor already inherits them downward — so the
        # hypernym's set is a subset of the topic's by construction, never a
        # superset. The real two-hop fact runs the other way: what the topic has
        # ONLY by inheritance, which `inherited=False` is exactly the way to
        # find. Getting this backwards was silent — it produced no paragraph
        # rather than a wrong one.
        direct = set(getattr(kg, accessor)(topic, inherited=False))
        inherited = [x for x in getattr(kg, accessor)(topic) if x not in direct]
        if not inherited:
            continue
        obj = inherited[0]
        # Which ancestor actually states it — that is the middle of the chain.
        via = hyper[0]
        for anc in kg.ancestors(topic):
            if obj in set(getattr(kg, accessor)(anc, inherited=False)):
                via = anc
                break
        p_i = len(paragraphs)
        p_start = w.n
        sent_idx = len(sentences)
        s_start = w.n
        w.add("It follows that ")
        mentions.append(Mention(start=w.n, end=w.n, node=topic, form="pronoun",
                                surface="", paragraph=p_i, sentence=sent_idx,
                                antecedent=last_mention_of.get(topic, -1)))
        st, en = w.add(_np(_phrase(kg, topic)))
        mentions[-1].start, mentions[-1].end = st, en
        mentions[-1].form = "name"
        mentions[-1].surface = w.text[st:en]
        last_mention_of[topic] = len(mentions) - 1
        w.add(", being ")
        mention_start, mention_end = w.add(_np(_phrase(kg, via)))
        mentions.append(Mention(start=mention_start, end=mention_end, node=via,
                                form="name", surface=w.text[mention_start:mention_end],
                                paragraph=p_i, sentence=sent_idx,
                                antecedent=last_mention_of.get(via, -1)))
        last_mention_of[via] = len(mentions) - 1
        w.add(", must also ")
        w.add({"parts_of": "have ", "properties_of": "be ",
               "abilities_of": "be able to ", "substances_of": "be made of "}[accessor])
        o_start, o_end = w.add(_phrase(kg, obj) if accessor in
                               ("properties_of", "abilities_of")
                               else _np(_phrase(kg, obj)))
        mentions.append(Mention(start=o_start, end=o_end, node=obj, form="name",
                                surface=w.text[o_start:o_end], paragraph=p_i,
                                sentence=sent_idx,
                                antecedent=last_mention_of.get(obj, -1)))
        last_mention_of[obj] = len(mentions) - 1
        w.add(", even though no such thing was said of it directly. ")
        sentences.append(Sentence(text=w.text[s_start:w.n], start=s_start,
                                  end=w.n, paragraph=p_i, index=sent_idx,
                                  triple=("inference", topic, obj), hops=2))
        w.add("\n\n")
        paragraphs.append(Paragraph(section="synthesis", start=p_start,
                                    end=w.n, index=p_i, sentences=[sent_idx]))
        return (topic, via, obj, section)
    return None


# -------------------------------------------------------------- generate ----

def generate(kg: Any, *, n: int, seed0: int = 0, width: int = 4,
             max_sections: int = 5, min_sections: int = 3,
             topics: Sequence[int] | None = None,
             source: str = "") -> Iterator[Essay]:
    """``n`` essays, one per topic, deterministic in ``(topic, seed)``.

    The source's capabilities are checked **before** anything is generated, and
    a missing one is refused by name. Only the five in :data:`REQUIRED` are
    fatal; the rest are sections that will not appear, which
    :func:`sections_available` reports and this function deliberately does not
    fail on -- WordNet populates two of the eight nowhere, and refusing it
    would refuse every essay corpus this repo has measured.
    """
    from .knowledge_source import capabilities_of, require_capabilities

    require_capabilities(capabilities_of(kg, name=source or "", names=REQUIRED),
                         REQUIRED, who="the essay generator")
    pool = list(topics) if topics is not None else rich_topics(
        kg, min_sections=min_sections)
    if not pool:
        raise ValueError("no topic in this graph has enough populated sections")
    rng = random.Random(seed0)
    for i in range(n):
        seed = seed0 + i
        topic = pool[rng.randrange(len(pool))]
        secs = plan(kg, topic, seed=seed, width=width,
                    max_sections=max_sections)
        if len(secs) < 2:
            continue
        yield realise(kg, topic, secs, seed=seed)
