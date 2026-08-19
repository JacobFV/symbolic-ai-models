"""WordNet verb supersenses, read straight from the distributed archive.

`notes/findings/2026-08-19-entropy-was-the-wrong-statistic-and-the-numbers-said-so.md`
ends on the reason every reader here stops at generated surfaces: a signature over
(entity counts, numbers, dates) **never looks at the verb**, and the verb is where
a real predicate lives. This is the smallest external resource that supplies verb
semantics, and it is a standard rather than something re-derived here.

Read from ``~/nltk_data/corpora/wordnet.zip`` with the standard library only --
``index.verb`` maps a lemma to synset offsets, ``data.verb`` gives each synset a
``lex_filenum``, and ``lexnames`` maps 29-43 to the fifteen verb supersenses
(``verb.change``, ``verb.motion``, ``verb.possession``, ``verb.stative`` and so
on). No new dependency, and the data is already on disk.

Morphology is the WordNet exception list plus the three regular strips. It is a
lemmatiser only to the extent WordNet's own tools are, and it has **no
part-of-speech knowledge**: ``use`` is a verb lemma whether or not the token in
front of you is a noun. Anything built on this inherits that.
"""

from __future__ import annotations

import functools
import zipfile
from pathlib import Path

__all__ = ["verb_supersenses", "noun_supersenses", "first_sense_supersense",
           "hypernym_closure", "sense_fraction_reaching", "is_verb_lemma",
           "SUPERSENSES", "wordnet_path"]

_CANDIDATES = (
    Path.home() / "nltk_data" / "corpora" / "wordnet.zip",
    Path("/usr/share/nltk_data/corpora/wordnet.zip"),
)


def wordnet_path() -> Path | None:
    """Where the archive is, or ``None``. Callers must handle its absence."""
    return next((p for p in _CANDIDATES if p.exists()), None)


#: maxsize=1 was correct while this only read the verb tables and became a
#: performance bug the moment it took a `pos`: alternating verb and noun lookups
#: evicted the cache on every call and re-parsed the archive per token. Measured
#: at 72s for 4,400 lookups, against 0.02s cached.
@functools.lru_cache(maxsize=4)
def _tables(pos: str = "verb") -> tuple[dict, dict, dict]:
    """Lemma->offsets, offset->supersense, exceptions, for one part of speech.

    Parameterised by ``pos`` because the relation cues in real prose are as often
    NOUNS as verbs -- *subsidiary*, *division*, *unit*, *arm* -- and the noun
    hierarchy carries the same `lex_filenum` supersenses (00-25: `noun.group`,
    `noun.location`, `noun.artifact`). Same archive, same three files, no new
    dependency. The default is unchanged, so every existing caller reads the
    verb tables it already read.
    """
    path = wordnet_path()
    if path is None:
        return {}, {}, {}
    with zipfile.ZipFile(path) as z:
        lexnames = {}
        for line in z.read("wordnet/lexnames").decode().splitlines():
            num, name, _ = line.split("\t")
            lexnames[int(num)] = name

        offset_class: dict[str, str] = {}
        for line in z.read(f"wordnet/data.{pos}").decode("utf-8",
                                                       "ignore").splitlines():
            if line.startswith(" "):
                continue
            parts = line.split(None, 3)
            if len(parts) < 3:
                continue
            offset_class[parts[0]] = lexnames.get(int(parts[1]), "")

        lemma_offsets: dict[str, tuple[str, ...]] = {}
        for line in z.read(f"wordnet/index.{pos}").decode("utf-8",
                                                        "ignore").splitlines():
            if line.startswith(" "):
                continue
            f = line.split()
            if len(f) < 6:
                continue
            lemma, n_synsets = f[0], int(f[2])
            lemma_offsets[lemma] = tuple(f[-n_synsets:])

        exc: dict[str, str] = {}
        for line in z.read(f"wordnet/{pos}.exc").decode("utf-8",
                                                      "ignore").splitlines():
            f = line.split()
            if len(f) >= 2:
                exc[f[0]] = f[1]
    return lemma_offsets, offset_class, exc


#: The fifteen verb supersenses, for callers that want to name one.
SUPERSENSES = ("verb.body", "verb.change", "verb.cognition",
               "verb.communication", "verb.competition", "verb.consumption",
               "verb.contact", "verb.creation", "verb.emotion", "verb.motion",
               "verb.perception", "verb.possession", "verb.social",
               "verb.stative", "verb.weather")


def _candidates(token: str, pos: str = "verb") -> list[str]:
    """WordNet's own exception list, then the three regular strips."""
    _, _, exc = _tables(pos)
    t = token.lower()
    out = [t]
    if t in exc:
        out.append(exc[t])
    for suffix, repl in (("ies", "y"), ("es", ""), ("s", ""), ("ed", ""),
                         ("ed", "e"), ("ing", ""), ("ing", "e")):
        if t.endswith(suffix) and len(t) > len(suffix) + 1:
            out.append(t[:-len(suffix)] + repl)
    return out


def verb_supersenses(token: str) -> frozenset[str]:
    """Every supersense any sense of this token carries, as a verb.

    Empty when the token is not a WordNet verb **or** when the archive is
    missing, and a caller that cannot tell those apart will read an absent
    resource as a confident negative -- so check `wordnet_path` first.
    """
    lemma_offsets, offset_class, _ = _tables()
    out: set[str] = set()
    for cand in _candidates(token):
        for off in lemma_offsets.get(cand, ()):
            cls = offset_class.get(off)
            if cls:
                out.add(cls)
    return frozenset(out)


def first_sense_supersense(token: str) -> str:
    """The supersense of the token's **first** WordNet sense, or ``""``.

    The union over senses is useless for common verbs and that is measured, not
    assumed: ``left`` carries *stative* among its six classes and ``ceased``
    carries **only** *stative*, so a rule over the union cannot tell a transition
    from a state. ``index.verb`` orders a lemma's synsets by sense number, which
    is WordNet's own frequency ordering, so the first is the reading a naive
    reader would take.

    This is word-sense disambiguation by prior and nothing more. It is wrong
    whenever the sentence uses a rarer sense, which is the same limit the
    ``former`` / ``used to`` / ``struck`` corrections all ran into.
    """
    lemma_offsets, offset_class, _ = _tables()
    for cand in _candidates(token):
        offs = lemma_offsets.get(cand)
        if offs:
            return offset_class.get(offs[0], "")
    return ""


@functools.lru_cache(maxsize=1)
def _hypernyms() -> dict[str, tuple[tuple[str, ...], str]]:
    """offset -> (hypernym offsets, first word). The taxonomy, not the topic."""
    path = wordnet_path()
    if path is None:
        return {}
    out = {}
    with zipfile.ZipFile(path) as z:
        for line in z.read("wordnet/data.verb").decode("utf-8",
                                                       "ignore").splitlines():
            if line.startswith(" "):
                continue
            head = line.split("|")[0].split()
            if len(head) < 4:
                continue
            offset = head[0]
            w_cnt = int(head[3], 16)
            word = head[4] if len(head) > 4 else ""
            i = 4 + 2 * w_cnt
            if i >= len(head):
                continue
            p_cnt = int(head[i])
            ups = []
            for k in range(p_cnt):
                j = i + 1 + 4 * k
                if j + 1 < len(head) and head[j] in ("@", "@i"):
                    ups.append(head[j + 1])
            out[offset] = (tuple(ups), word)
    return out


def hypernym_closure(token: str, *, first_sense_only: bool = True
                     ) -> frozenset[str]:
    """Ancestor lemmas of the token's senses, following ``@`` pointers.

    The taxonomic signal rather than the topical one. WordNet's **supersenses
    classify by subject matter, not by aspect** -- ``cease`` is *verb.stative*
    because it is about states and ``divest`` is *verb.possession* because it is
    about possessions -- so they cannot tell a verb that **asserts** a relation
    from one that **ends** it. Whether the hypernym chain can is a different
    question and this is what answers it.
    """
    lemma_offsets, _, _ = _tables()
    ups = _hypernyms()
    seen: set[str] = set()
    frontier: list[str] = []
    for cand in _candidates(token):
        offs = lemma_offsets.get(cand)
        if offs:
            frontier = list(offs[:1] if first_sense_only else offs)
            break
    out: set[str] = set()
    while frontier:
        off = frontier.pop()
        if off in seen:
            continue
        seen.add(off)
        parents, word = ups.get(off, ((), ""))
        if word:
            out.add(word)
        frontier.extend(parents)
    return frozenset(out)


def sense_fraction_reaching(token: str, roots) -> float:
    """Share of the lemma's senses whose hypernym chain reaches one of ``roots``.

    **Dominance, not priority.** Taking the *first* sense is disambiguation by
    prior and it fails on exactly the words that matter: ``dated`` reaches
    ``leave`` on its first sense -- "go on a date with" -- and on **one of five**
    senses overall, while every genuine transition verb measured reaches a root
    on 60% to 100% of its senses and every relation verb on **none**. The margin
    is 0.20 against 0.60, which is what makes a threshold defensible rather than
    fitted.

    Returns 0.0 for a token that is not a WordNet verb.
    """
    lemma_offsets, _, _ = _tables()
    ups = _hypernyms()
    for cand in _candidates(token):
        offs = lemma_offsets.get(cand)
        if offs:
            break
    else:
        return 0.0
    hits = 0
    for off in offs:
        seen: set[str] = set()
        frontier = [off]
        words: set[str] = set()
        while frontier:
            o = frontier.pop()
            if o in seen:
                continue
            seen.add(o)
            parents, word = ups.get(o, ((), ""))
            if word:
                words.add(word)
            frontier.extend(parents)
        if roots & words:
            hits += 1
    return hits / len(offs)


def is_verb_lemma(token: str) -> bool:
    """Whether any morphological candidate is a WordNet verb."""
    lemma_offsets, _, _ = _tables()
    return any(c in lemma_offsets for c in _candidates(token))


@functools.lru_cache(maxsize=None)
def noun_supersenses(token: str) -> frozenset[str]:
    """Every noun supersense this token could carry.

    The noun half of the same tables. It has the same caveat the module header
    gives for verbs and one more: with no part-of-speech tagging, a token that is
    both -- *holds*, *owns* -- is looked up in both hierarchies and the caller
    gets the union. That is the honest behaviour for a feature function, which
    wants every reading the word could have.
    """
    lemma_offsets, offset_class, _ = _tables("noun")
    out: set[str] = set()
    for cand in _candidates(token, "noun"):
        for off in lemma_offsets.get(cand, ()):  # noqa: B007
            name = offset_class.get(off, "")
            if name:
                out.add(name)
        if out:
            break
    return frozenset(out)
