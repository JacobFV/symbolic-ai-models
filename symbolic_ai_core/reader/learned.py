"""A learned reader: one implementation, no domain lexicon, fitted per domain.

`flood.content@1` is a research instrument and a good one, but every phrasing it
recognises was written by hand, which means it answers *"can a person write
patterns for this surface"* and not *"can this be read"*. This reads the same
surfaces with nothing domain-specific in the source: it is given aligned
`(unit of text, claim)` pairs and induces the rest.

What is knowledge of **English** and stays in the code:

- sentence and paragraph segmentation;
- a tokenizer, and two date formats (`2026-05-02`, `24 May 2026`) with the month
  names. Dates are the one place a normaliser must know the language.

What is knowledge of the **domain** and is induced from the alignment:

- the predicate inventory, and which units realise nothing (a `distractor` is a
  label like any other, learned, not filtered by a stop list);
- which token shapes and which literal forms name entities -- a shape is trusted
  only when it is *productive* (many distinct fillers, almost always an entity),
  so `region_0` generalises to `region_84` while `group` has to be memorised;
- the role signature of every predicate, each role's filler type, and the unit
  of every quantity;
- which roles are filled from **earlier text** rather than from the unit, which
  is where reference resolution enters;
- the constant temporal envelope, when the corpus has one that is never stated.

Two models, both averaged perceptrons over sparse features, both trained on the
alignment:

1. **the unit classifier** -- which predicate, if any, this unit realises. Its
   features are the abstracted token n-grams plus the *signature* (how many
   entities, numbers and dates the unit contains). The signature is the feature
   the hand readers were built around; here it is one feature among thousands and
   the fit decides what it is worth.
2. **the role ranker** -- which candidate fills which role, scored on the
   candidate's index, the tokens either side of it, and its type. An ordinal rule
   ("first entity is `a`, second is `b`") is a special case the ranker can learn,
   and it can also learn the phrasings that invert the order, which an ordinal
   rule cannot.

The output is a `ReadResult`, so what the reader could not settle survives:
a reference with two plausible antecedents becomes a **mention with candidate
entities** and an **XOR factor** over the claims they would produce, rather than
a silent pick.
"""

from __future__ import annotations

import math
import re
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from symbolic_ai_core.artifact.value import Interval
from symbolic_ai_core.world import Claim, EntityRef, Quantity

from .abi import Alignment, Factor, Mention, ReadResult

__all__ = ["LearnedSpanReader", "Unit", "Token", "segment", "tokenize",
           "shape", "supervise", "Lexicon", "LexiconMentions",
           "CapitalisedMentions"]

NONE = "∅"          #: the label for a unit that realises no claim

_MONTHS = ("january", "february", "march", "april", "may", "june", "july",
           "august", "september", "october", "november", "december")
_ISO = r"\d{4}-\d{2}-\d{2}"
_LONG = rf"\d{{1,2}} (?:{'|'.join(m.capitalize() for m in _MONTHS)}) \d{{4}}"
_TOKEN = re.compile(
    rf"{_ISO}|{_LONG}|[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?|[^\sA-Za-z0-9]")


# --------------------------------------------------------------------------
# text -> units and tokens.  English, not domain.
# --------------------------------------------------------------------------

def segment(text: str) -> list[tuple[int, int]]:
    """Character ranges of sentences, respecting decimals and blank lines.

    A splitter on ``.`` alone cuts ``184.19`` in half and turns one filing into
    two unreadable units, so a full stop only ends a sentence when whitespace or
    the end of the text follows it.
    """
    out: list[tuple[int, int]] = []
    start = i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in ".?!" and (i + 1 >= n or text[i + 1].isspace()):
            out.append((start, i + 1))
            i += 1
            while i < n and text[i].isspace():
                i += 1
            start = i
            continue
        if ch == "\n":
            if text[start:i].strip():
                out.append((start, i))
            i += 1
            while i < n and text[i].isspace():
                i += 1
            start = i
            continue
        i += 1
    if text[start:].strip():
        out.append((start, n))
    return [(s, e) for s, e in out if text[s:e].strip()]


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int

    @property
    def kind(self) -> str:
        if _is_date(self.text):
            return "date"
        if re.fullmatch(r"\d+(?:\.\d+)?", self.text):
            return "num"
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", self.text):
            return "word"
        return "punct"


def _is_date(tok: str) -> bool:
    return bool(re.fullmatch(_ISO, tok) or re.fullmatch(_LONG, tok))


def _iso(tok: str) -> str:
    if re.fullmatch(_ISO, tok):
        return tok
    d, mon, y = tok.split()
    return f"{y}-{_MONTHS.index(mon.lower()) + 1:02d}-{int(d):02d}"


def tokenize(text: str, offset: int = 0) -> list[Token]:
    return [Token(m.group(0), offset + m.start(), offset + m.end())
            for m in _TOKEN.finditer(text)]


def shape(tok: str) -> str:
    """``region_0`` -> ``a_9``, ``184.19`` -> ``9.9``, ``2026-05-02`` -> ``date``.

    Runs collapse, so the shape is a statement about the *form* of a name and not
    about its length -- which is what lets a shape learned on `region_0` accept
    `region_84` without the reader ever having seen it.
    """
    if _is_date(tok):
        return "date"
    out: list[str] = []
    for ch in tok:
        c = "9" if ch.isdigit() else ("a" if ch.isalpha() else ch)
        if not out or out[-1] != c:
            out.append(c)
    return "".join(out)


@dataclass
class Unit:
    """One sentence, its tokens, and (in training) the claim it realises."""

    start: int
    end: int
    text: str
    tokens: list[Token] = field(default_factory=list)
    claim: Claim | None = None
    index: int = 0
    #: The whole document this unit came from. A role is often decided by
    #: document-level facts a sentence cannot see -- which entity the document is
    #: ABOUT is never the one a relation points at -- and a feature function
    #: that only receives the sentence cannot ask. Set by `_units`, so training
    #: and inference see the same thing.
    doc_text: str = ""
    #: What the reading is FOR. `P(Y | Z, Q)` has a `Q` in it, and a role
    #: decision is one of the places it earns its keep: an article about Sony
    #: Music states a parent, and the parent is not Sony Music. Carried on the
    #: unit so a feature function can ask, and set identically at fit time and
    #: at inference so the two never diverge.
    query: str = ""


def _units(text: str) -> list[Unit]:
    out = []
    for k, (s, e) in enumerate(segment(text)):
        u = Unit(s, e, text[s:e], tokenize(text[s:e], s), None, k, text)
        out.append(u)
    return out


def supervise(text: str, spans: Sequence[Any],
              claims: Sequence[Claim]) -> list[Unit]:
    """Attach each surface span's claim to the unit that mostly contains it.

    The generators align spans, not sentences, and the reader must segment for
    itself at inference; training on the reader's own units rather than on the
    gold ones keeps the two identical. A span that lands mostly outside every
    unit is dropped rather than forced -- silence is the honest supervision.
    """
    units = _units(text)
    for sp in spans:
        if sp.claim is None:
            continue
        best, cover = None, 0.0
        for u in units:
            ov = max(0, min(u.end, sp.end) - max(u.start, sp.start))
            if ov > cover:
                best, cover = u, ov
        if best is not None and cover >= 0.5 * (sp.end - sp.start) \
                and best.claim is None:
            best.claim = claims[sp.claim]
    return units


# --------------------------------------------------------------------------
# the two models
# --------------------------------------------------------------------------

class Perceptron:
    """Multiclass averaged perceptron. Sparse features, integer timestamps."""

    def __init__(self) -> None:
        self.w: dict[str, dict[str, float]] = defaultdict(dict)
        self._acc: dict[str, dict[str, float]] = defaultdict(dict)
        self._last: dict[str, dict[str, int]] = defaultdict(dict)
        self._t = 0
        self.labels: list[str] = []

    def score(self, feats: Iterable[str]) -> dict[str, float]:
        out = {y: 0.0 for y in self.labels}
        for f in feats:
            for y, v in self.w.get(f, {}).items():
                out[y] += v
        return out

    def predict(self, feats: Sequence[str]) -> tuple[str, float]:
        s = self.score(feats)
        if not s:
            return NONE, 0.0
        best = max(s, key=lambda y: (s[y], y))
        vals = sorted(s.values(), reverse=True)
        margin = vals[0] - (vals[1] if len(vals) > 1 else 0.0)
        return best, margin

    def _bump(self, f: str, y: str, d: float) -> None:
        w, acc, last = self.w[f], self._acc[f], self._last[f]
        acc[y] = acc.get(y, 0.0) + (self._t - last.get(y, 0)) * w.get(y, 0.0)
        last[y] = self._t
        w[y] = w.get(y, 0.0) + d

    def update(self, feats: Sequence[str], gold: str, pred: str,
               weight: float = 1.0) -> None:
        """``weight`` is how much this confusion costs downstream.

        A perceptron update of size ``w`` is the mistake-driven form of a
        weighted loss: the decision boundary moves ``w`` times as far for an
        error the kernels are ``w`` times as sensitive to. This is where
        ``L_reader = sum_i s_i L_i`` enters, and it needs nothing
        differentiable on the other side of the boundary.
        """
        self._t += 1
        if gold == pred:
            return
        for f in feats:
            self._bump(f, gold, weight)
            self._bump(f, pred, -weight)

    def average(self) -> None:
        for f, w in self.w.items():
            acc, last = self._acc[f], self._last[f]
            for y in list(w):
                total = acc.get(y, 0.0) + (self._t - last.get(y, 0)) * w[y]
                w[y] = total / max(1, self._t)


class Logistic:
    """Multinomial logistic regression over sparse features, fitted by SGD.

    The perceptron it stands beside is a *margin* machine: its score is an
    arbitrary scale, and squashing or isotonically calibrating it produced a
    belief with **two values** on these corpora -- 0.95 and 0.47 -- which is
    enough to rank two readings of one sentence and not enough for any threshold
    to act on. Measured: per-predicate assertion thresholds derived from the
    kernels changed exactly zero claims in three domains.

    This emits a probability by construction. It is the cheapest way to get a
    graded posterior and it is not a neural network -- the point is calibration,
    not capacity.
    """

    def __init__(self, epochs: int = 12, lr: float = 0.2,
                 l2: float = 1e-6) -> None:
        self.w: dict[str, dict[str, float]] = defaultdict(dict)
        self.labels: list[str] = []
        self.epochs = epochs
        self.lr = lr
        self.l2 = l2

    def score(self, feats: Iterable[str]) -> dict[str, float]:
        out = {y: 0.0 for y in self.labels}
        for f in feats:
            for y, v in self.w.get(f, {}).items():
                out[y] += v
        return out

    def probs(self, feats: Sequence[str]) -> dict[str, float]:
        s = self.score(feats)
        if not s:
            return {}
        top = max(s.values())
        exp = {y: math.exp(min(30.0, v - top)) for y, v in s.items()}
        z = sum(exp.values()) or 1.0
        return {y: v / z for y, v in exp.items()}

    def predict(self, feats: Sequence[str]) -> tuple[str, float]:
        """``(label, P(label))`` -- the second value is already a probability,
        which is the whole reason this class exists."""
        p = self.probs(feats)
        if not p:
            return NONE, 0.0
        best = max(p, key=lambda y: (p[y], y))
        return best, p[best]

    def fit(self, data: Sequence[tuple[Sequence[str], str]],
            weights: Mapping[str, float] | None = None) -> "Logistic":
        self.labels = sorted({y for _, y in data})
        for epoch in range(self.epochs):
            lr = self.lr / (1.0 + epoch)
            for feats, gold in data:
                p = self.probs(feats)
                w = 1.0 if weights is None else float(weights.get(gold, 1.0))
                for f in feats:
                    row = self.w[f]
                    for y in self.labels:
                        g = ((1.0 if y == gold else 0.0) - p.get(y, 0.0))
                        row[y] = (row.get(y, 0.0) * (1.0 - lr * self.l2)
                                  + lr * w * g)
        return self

    def average(self) -> None:                # symmetry with Perceptron
        return None


def _unit_features(u: Unit, ments: Sequence[Token]) -> list[str]:
    """Abstracted n-grams plus the signature.

    Every token that names something becomes ``<E>``/``<N>``/``<D>``, so the
    classifier keys on the *phrasing* and cannot memorise the vocabulary -- the
    trap this repo has fallen into more than once. The signature counts are the
    hand readers' entire basis, present here as three features among thousands.
    """
    abst: list[str] = []
    ne = nn = nd = 0
    inside = {i for m in ments for i in range(m.start, m.end)}
    starts = {m.start for m in ments}
    for t in u.tokens:
        if t.start in starts:
            abst.append("<E>")
            ne += 1
        elif t.start in inside:
            continue                      # the rest of a multi-word name
        elif t.kind == "num":
            abst.append("<N>")
            nn += 1
        elif t.kind == "date":
            abst.append("<D>")
            nd += 1
        elif t.kind == "punct":
            continue
        else:
            abst.append(t.text.lower())
    feats = ["bias", f"#E={min(ne, 4)}", f"#N={min(nn, 4)}", f"#D={min(nd, 4)}",
             f"sig={min(ne,4)},{min(nn,4)},{min(nd,4)}"]
    feats += [f"u={w}" for w in abst]
    feats += [f"b={a}|{b}" for a, b in zip(abst, abst[1:])]
    feats += [f"t={a}|{b}|{c}" for a, b, c in zip(abst, abst[1:], abst[2:])]
    if abst:
        feats.append(f"first={abst[0]}")
        feats.append(f"last={abst[-1]}")
    return feats


def _role_features(pred: str, role: str, cands: Sequence[Token],
                   j: int, u: Unit, extra: Any = None) -> list[str]:
    """Why *this* candidate fills *this* role.

    Index among candidates of the same type covers the ordinal cases; the words
    either side cover the ones that invert the order (*between A and B* against
    *A adjoins B*), which is exactly what a positional rule cannot express.
    """
    t = cands[j]
    k = [i for i, x in enumerate(u.tokens) if x.start == t.start]
    i = k[0] if k else 0
    prev = u.tokens[i - 1].text.lower() if i else "^"
    nxt = u.tokens[i + 1].text.lower() if i + 1 < len(u.tokens) else "$"
    prev2 = u.tokens[i - 2].text.lower() if i >= 2 else "^"
    base = f"{pred}:{role}"
    feats = ["bias", f"{base}|idx={j}", f"{base}|idx={j}/{len(cands)}",
             f"{base}|rev={len(cands) - 1 - j}",
             f"{base}|prev={prev}", f"{base}|next={nxt}",
             f"{base}|prev2={prev2}", f"{base}|prev,next={prev}|{nxt}",
             f"{base}|first={1 if i == 0 else 0}"]
    if extra is not None:
        feats += [f"{base}|{f}" for f in extra(pred, role, cands, j, u)]
    return feats


class _Ranker:
    """A binary-scored ranker: one weight vector, argmax over candidates."""

    def __init__(self) -> None:
        self.w: dict[str, float] = defaultdict(float)
        self._acc: dict[str, float] = defaultdict(float)
        self._last: dict[str, int] = defaultdict(int)
        self._t = 0

    def score(self, feats: Sequence[str]) -> float:
        return sum(self.w[f] for f in feats)

    def tick(self) -> None:
        """One example seen. Averaging counts EXAMPLES, not mistakes.

        Counting mistakes instead is a real bug with a quiet symptom: once the
        ranker converges the clock stops, so the average is dominated by the
        first few chaotic updates and the fitted model is worse than the last
        iterate. Measured here -- solvency's `owns` inverted parent and child on
        two of its four phrasings at 0.796 F1, and reached 1.000 the moment the
        clock counted examples.
        """
        self._t += 1

    def update(self, gold: Sequence[str], pred: Sequence[str]) -> None:
        for f in gold:
            self._acc[f] += (self._t - self._last[f]) * self.w[f]
            self._last[f] = self._t
            self.w[f] += 1.0
        for f in pred:
            self._acc[f] += (self._t - self._last[f]) * self.w[f]
            self._last[f] = self._t
            self.w[f] -= 1.0

    def average(self) -> None:
        for f in list(self.w):
            total = self._acc[f] + (self._t - self._last[f]) * self.w[f]
            self.w[f] = total / max(1, self._t)


# --------------------------------------------------------------------------
# the induced lexicon
# --------------------------------------------------------------------------

class LexiconMentions:
    """Mentions are whatever the induced lexicon calls a name.

    Right for corpora whose entities are identifiers. Wrong for English prose,
    where a name is `Ministry of Communications` -- three tokens, one of them
    lowercase, and no shape to generalise.
    """

    def __init__(self, lex: "Lexicon") -> None:
        self.lex = lex

    def find(self, u: Unit) -> list[Token]:
        return [t for t in u.tokens if self.lex.is_entity(t)]


class CapitalisedMentions:
    """Runs of capitalised words, joined across lowercase connectives.

    Knowledge of English, not of any domain -- the same category as the
    tokenizer and the date formats. A capitalised run is the cheapest honest
    proposer for prose, and it is deliberately over-generous: the ranker decides
    which proposal fills which role, and a proposer that missed the answer would
    put a ceiling on the reader that no amount of fitting could lift.
    """

    JOIN = frozenset({"of", "the", "and", "for", "de", "van", "von", "du",
                      "da", "di", "la", "le", "el", "&"})

    def __init__(self, *, sentence_initial: bool = False) -> None:
        #: A sentence's first word is capitalised because it is first. Dropping
        #: it loses every name that opens a sentence, so it is KEPT and the
        #: cost is paid in false proposals rather than in missed answers.
        self.sentence_initial = sentence_initial

    def find(self, u: Unit) -> list[Token]:
        out: list[Token] = []
        run: list[Token] = []

        def flush() -> None:
            while run and run[-1].text.lower() in self.JOIN:
                run.pop()
            if run:
                out.append(Token(u.text[run[0].start - u.start:
                                        run[-1].end - u.start],
                                 run[0].start, run[-1].end))
            run.clear()

        for t in u.tokens:
            cap = t.kind == "word" and t.text[:1].isupper()
            if cap:
                run.append(t)
            elif run and t.text.lower() in self.JOIN:
                run.append(t)
            else:
                flush()
        flush()
        return out


@dataclass
class Lexicon:
    """What counts as a name, learned rather than declared.

    ``productive`` shapes are the generalising half: a shape earns membership by
    appearing with many distinct fillers and almost always being one, which is
    what lets the reader accept an entity it has never seen. Everything else has
    to be in ``forms``, so a common word does not become an entity because one
    entity happened to be spelled like a word.
    """

    forms: set[str] = field(default_factory=set)
    productive: set[str] = field(default_factory=set)

    def is_entity(self, t: Token) -> bool:
        if t.kind in ("num", "date", "punct"):
            return False
        return t.text in self.forms or shape(t.text) in self.productive

    @classmethod
    def induce(cls, units: Sequence[Unit], *, min_forms: int = 5,
               purity: float = 0.9) -> "Lexicon":
        ent_tokens: Counter[str] = Counter()
        all_tokens: Counter[str] = Counter()
        for u in units:
            names = _claim_entities(u.claim) if u.claim is not None else set()
            for t in u.tokens:
                if t.kind == "punct":
                    continue
                all_tokens[t.text] += 1
                if t.text in names:
                    ent_tokens[t.text] += 1
        by_shape_ent: dict[str, set[str]] = defaultdict(set)
        by_shape_all: dict[str, set[str]] = defaultdict(set)
        for tok in all_tokens:
            by_shape_all[shape(tok)].add(tok)
        for tok in ent_tokens:
            by_shape_ent[shape(tok)].add(tok)
        productive = {s for s, e in by_shape_ent.items()
                      if len(e) >= min_forms
                      and len(e) >= purity * len(by_shape_all[s])}
        forms = {t for t in ent_tokens if shape(t) not in productive}
        return cls(forms=forms, productive=productive)


def _claim_entities(c: Claim | None) -> set[str]:
    if c is None:
        return set()
    return {v.id for v in c.roles.values() if isinstance(v, EntityRef)}


# --------------------------------------------------------------------------
# the reader
# --------------------------------------------------------------------------

@dataclass
class _RoleSpec:
    """One role of one predicate: what fills it and where it comes from."""

    role: str
    filler: str                       #: "entity" | "quantity" | "literal"
    unit: str = ""                    #: for quantities
    vocab: set[str] = field(default_factory=set)
    #: share of training units in which the filler was *not* in the unit, i.e.
    #: stated earlier and referred back to
    external: float = 0.0
    #: share in which the filler appears **nowhere in the document**. Such an
    #: entity is not referred to at all -- it is introduced by the relation
    #: (*the road bridges the river*: a bridge now exists and has no name), and
    #: the only honest reading mints an identity for it. Coreference and minting
    #: are different acts and the fit tells them apart rather than a flag.
    latent: float = 0.0


class LearnedSpanReader:
    """`text -> ReadResult`, with every domain fact induced from alignments."""

    def __init__(self, id: str = "learned.span@1", *, epochs: int = 8,
                 weights: Mapping[str, float] | None = None,
                 mentions: Any = None, extra_features: Any = None,
                 extra_role_features: Any = None, model: str = "perceptron"
                 ) -> None:
        """``weights`` maps a predicate to its downstream sensitivity.

        Measured by intervention, not by correlation --
        ``scripts/sensitivity_weights.py`` deletes one gold claim and re-runs the
        kernels, so the number is a property of the task and survives any change
        to the reader. Absent, every claim costs the same, which is claim F1's
        assumption and is false in every domain measured: flood spans 6.6x.

        The per-example weight is `s_p` and the per-document contribution
        `n_p s_p` follows, because a predicate with `n_p` claims contributes
        `n_p` examples.
        """
        self.id = id
        self.epochs = epochs
        self.weights = dict(weights or {})
        #: "perceptron" keeps every published number; "logistic" emits a
        #: probability instead of a margin, which is what a derived threshold
        #: needs in order to act at all.
        self.model = model
        if model not in ("perceptron", "logistic"):
            raise ValueError(f"unknown model {model!r}; "
                             "expected 'perceptron' or 'logistic'")
        self.mentions = mentions
        #: ``(unit, mentions) -> [feature]``. The place an external lexical
        #: resource enters -- WordNet supersenses, say -- without the reader
        #: importing one. A corpus too small to learn that `subsidiary`,
        #: `division` and `unit` behave alike can be handed the fact.
        self.extra = extra_features
        #: ``(pred, role, candidates, j, unit) -> [feature]``. The ranker's own
        #: hook. A relation stated as *X is a subsidiary of Y* is a fact about
        #: which SLOT Y fills, so the words between two mentions belong here and
        #: not only in the sentence classifier -- which is where they were first
        #: put, and why they bought nothing.
        self.extra_role = extra_role_features
        #: predicate -> ScoreCalibrator, fitted on HELD-OUT documents by
        #: :meth:`calibrate`. Until then a belief is a squashed margin, which is
        #: monotone in confidence and means nothing quantitatively -- enough to
        #: rank two readings of one sentence, not enough to arbitrate between
        #: this reader and another one. Measured: letting an uncalibrated
        #: learned reader override a pattern reader on disagreement costs 0.03
        #: on every relation, while letting it speak only where the other
        #: abstains gains on every relation.
        self.calibrators: dict[str, Any] = {}
        self.lex = Lexicon()
        self.clf: Any = (Logistic(epochs=epochs) if model == "logistic"
                         else Perceptron())
        self.rankers: dict[str, _Ranker] = defaultdict(_Ranker)
        self.specs: dict[str, list[_RoleSpec]] = {}
        self.envelope: dict[str, tuple[Interval, Interval]] = {}
        self.tx_role: dict[str, str] = {}     #: predicate -> "transaction"
        self.fitted = False

    # -- fitting ---------------------------------------------------------
    def fit(self, docs: Sequence[Sequence[Unit]]) -> "LearnedSpanReader":
        units = [u for d in docs for u in d]
        if self.mentions is None:
            self.lex = Lexicon.induce(units)
            self.mentions = LexiconMentions(self.lex)
        self._induce_specs(docs)
        self._fit_classifier(docs)
        self._fit_rankers(units)   # noqa: E501 - rankers are per-unit
        self.fitted = True
        return self

    def _induce_specs(self, docs: Sequence[Sequence[Unit]]) -> None:
        roles: dict[str, dict[str, Counter]] = defaultdict(
            lambda: defaultdict(Counter))
        units_seen: Counter[str] = Counter()
        vocab: dict[tuple[str, str], set[str]] = defaultdict(set)
        qunit: dict[tuple[str, str], Counter] = defaultdict(Counter)
        absent: dict[tuple[str, str], list[int]] = defaultdict(list)
        envel: dict[str, Counter] = defaultdict(Counter)
        tx_seen: dict[str, Counter] = defaultdict(Counter)
        latent: dict[tuple[str, str], list[int]] = defaultdict(list)
        for doc in docs:
            # Built from PROPOSED MENTIONS, not raw tokens. `Ministry of
            # Communications` is never one token, so a token-level test says it
            # appears nowhere and every such role is minted a fresh identity --
            # which is why the first real-prose run scored 0.000 exact against
            # 0.149 lenient: the answers were skolems, not names.
            in_doc = {t.text for u in doc for t in self.mentions.find(u)}
            for u in doc:
                c = u.claim
                if c is None:
                    continue
                for role, v in c.roles.items():
                    if isinstance(v, EntityRef):
                        latent[(c.predicate, role)].append(v.id not in in_doc)
        for u in [x for d in docs for x in d]:
            c = u.claim
            if c is None:
                continue
            units_seen[c.predicate] += 1
            surface = {t.text for t in self.mentions.find(u)}
            surface |= {t.text for t in u.tokens}
            iso = {_iso(t.text) for t in u.tokens if t.kind == "date"}
            for role, v in c.roles.items():
                if isinstance(v, EntityRef):
                    roles[c.predicate][role]["entity"] += 1
                    absent[(c.predicate, role)].append(v.id not in surface)
                elif isinstance(v, Quantity):
                    roles[c.predicate][role]["quantity"] += 1
                    qunit[(c.predicate, role)][v.unit] += 1
                    absent[(c.predicate, role)].append(
                        not any(_close(t.text, v.value) for t in u.tokens
                                if t.kind == "num"))
                else:
                    roles[c.predicate][role]["literal"] += 1
                    vocab[(c.predicate, role)].add(str(v).lower())
                    absent[(c.predicate, role)].append(
                        str(v).lower() not in {s.lower() for s in surface})
            envel[c.predicate][(_ival(c.valid_time), _ival(c.transaction_time))] += 1
            tx_seen[c.predicate][
                _ival(c.transaction_time)[0] in iso if iso else False] += 1
        for pred, rs in roles.items():
            specs = []
            for role, kinds in rs.items():
                kind = kinds.most_common(1)[0][0]
                spec = _RoleSpec(
                    role=role, filler=kind,
                    unit=(qunit[(pred, role)].most_common(1)[0][0]
                          if qunit[(pred, role)] else ""),
                    vocab={v for v in vocab[(pred, role)]},
                    external=(sum(absent[(pred, role)])
                              / max(1, len(absent[(pred, role)]))),
                    latent=(sum(latent[(pred, role)])
                            / max(1, len(latent[(pred, role)]))))
                specs.append(spec)
            self.specs[pred] = sorted(specs, key=lambda s: s.role)
            # A temporal envelope is only *learned* when it is constant: a
            # corpus that never states its quarter has taught the reader one
            # fact, and a corpus that varies it has taught it nothing.
            (vt, tt), n = envel[pred].most_common(1)[0]
            if n == units_seen[pred] and (vt != (None, None)
                                          or tt != (None, None)):
                self.envelope[pred] = (Interval(*vt), Interval(*tt))
            if tx_seen[pred][True] > 0.5 * units_seen[pred]:
                self.tx_role[pred] = "date"

    def _fit_classifier(self, docs: Sequence[Sequence[Unit]]) -> None:
        data = [(self.features(u),
                 u.claim.predicate if u.claim is not None else NONE)
                for d in docs for u in d]
        if isinstance(self.clf, Logistic):
            self.clf.fit(data, self.weights or None)
            return
        self.clf.labels = sorted({y for _, y in data})
        for _ in range(self.epochs):
            for feats, gold in data:
                pred, _ = self.clf.predict(feats)
                # Priced at the MAX of the two labels' sensitivities: missing a
                # load-bearing claim and inventing one are both errors against
                # it, and a cost that only looked at the gold label would leave
                # false positives on critical predicates unpriced.
                w = max(self._weight(gold), self._weight(pred))
                self.clf.update(feats, gold, pred, w)
        self.clf.average()

    def calibrate(self, docs: Sequence[Sequence[Unit]]) -> "LearnedSpanReader":
        """Fit score -> accuracy per predicate, on documents NOT used to fit.

        A margin is an arbitrary scale. `ScoreCalibrator` bins it against the
        outcomes it actually produced and enforces monotonicity, so a belief
        becomes the accuracy that score has earned. The caller supplies held-out
        documents; calibrating on the fitting set produces a map that is
        confidently wrong exactly where the model is.
        """
        from symbolic_ai_core.calibration import ScoreCalibrator
        scores: dict[str, list[float]] = defaultdict(list)
        oks: dict[str, list[bool]] = defaultdict(list)
        for doc in docs:
            for u in doc:
                pred, margin = self.clf.predict(self.features(u))
                if pred == NONE:
                    continue
                gold = u.claim.predicate if u.claim is not None else NONE
                scores[pred].append(margin)
                oks[pred].append(pred == gold)
        self.calibrators = {}
        for p, sc in scores.items():
            cal = ScoreCalibrator().fit(sc, oks[p])
            if cal.fitted:
                self.calibrators[p] = cal
        return self

    def _belief(self, pred: str, margin: float) -> float:
        cal = self.calibrators.get(pred)
        if cal is not None:
            return float(cal(margin))
        # A logistic score IS a probability; squashing it again would flatten
        # exactly the gradation this model exists to provide.
        return margin if isinstance(self.clf, Logistic) else _sigmoid(margin)

    def features(self, u: Unit) -> list[str]:
        """Every feature of one unit, including whatever a resource adds."""
        found = self.mentions.find(u)
        feats = _unit_features(u, found)
        if self.extra is not None:
            feats = feats + list(self.extra(u, found))
        return feats

    def _weight(self, label: str) -> float:
        """The cost of getting this label wrong.

        ``NONE`` may be named explicitly, and on a distantly supervised corpus it
        has to be: the negative class outnumbers every relation by an order of
        magnitude, so a margin-based classifier abstains almost everywhere and no
        feature set can fix it. When it is not named it falls back to the mean,
        which is the neutral choice for a corpus whose classes are balanced by
        construction.
        """
        if not self.weights:
            return 1.0
        if label == NONE:
            return self.weights.get(NONE,
                                    statistics.mean(self.weights.values()))
        return self.weights.get(label, 1.0)

    def _fit_rankers(self, units: Sequence[Unit]) -> None:
        examples = []
        for u in units:
            c = u.claim
            if c is None:
                continue
            for spec in self.specs.get(c.predicate, []):
                cands = self._candidates(u, spec)   # noqa: E501
                if len(cands) < 2:
                    continue
                gold = _gold_index(cands, c.roles.get(spec.role))
                if gold is None:
                    continue
                examples.append((c.predicate, spec, u, cands, gold))
        for _ in range(self.epochs):
            for pred, spec, u, cands, gold in examples:
                r = self.rankers[f"{pred}:{spec.role}"]
                r.tick()
                scores = [r.score(_role_features(pred, spec.role, cands, j,
                                                 u, self.extra_role))
                          for j in range(len(cands))]
                best = max(range(len(cands)), key=lambda j: scores[j])
                if best != gold:
                    r.update(_role_features(pred, spec.role, cands, gold, u,
                                            self.extra_role),
                             _role_features(pred, spec.role, cands, best, u,
                                            self.extra_role))
        for r in self.rankers.values():
            r.average()

    # -- reading ---------------------------------------------------------
    def _candidates(self, u: Unit, spec: _RoleSpec) -> list[Token]:
        if spec.filler == "entity":
            return self.mentions.find(u)
        if spec.filler == "quantity":
            return [t for t in u.tokens if t.kind == "num"]
        return [t for t in u.tokens if t.text.lower() in spec.vocab]

    def run(self, text: str, *, query: str | None = None,
            context: Sequence[str] = ()) -> ReadResult:
        if not self.fitted:
            raise RuntimeError(
                f"reader {self.id!r} has not been fitted; call fit(docs) with "
                "aligned units first. An unfitted reader that returned an empty "
                "reading would look like a document with nothing in it.")
        started = time.perf_counter()
        q = (query or "").strip()
        # Earlier documents contribute MENTIONS and never claims. That is the
        # whole of the cross-document state this reader needs: an antecedent is
        # a name that was written down, and re-deriving the claims around it
        # would be re-reading, which is the cost a persistent world exists to
        # avoid. Cost here is a lexicon lookup per token, not a parse.
        recent: list[str] = []          #: every mention, in order of reading
        for prior in context:
            for pu in _units(prior):
                recent.extend(t.text for t in self.mentions.find(pu))
        units = _units(text)
        for u in units:
            u.query = q
        claims: list[Claim] = []
        belief: dict[int, float] = {}
        aligns: list[Alignment] = []
        mentions: list[Mention] = []
        factors: list[Factor] = []
        unresolved: list[str] = []
        for u in units:
            here: list[str] = []
            found = self.mentions.find(u)
            for t in found:
                mentions.append(Mention(t.start, t.end, t.text,
                                        entities=(t.text,), belief=(1.0,)))
                here.append(t.text)
            feats = _unit_features(u, found)
            if self.extra is not None:
                feats = feats + list(self.extra(u, found))
            pred, margin = self.clf.predict(feats)
            roles, alts, missing = ({}, {}, []) if pred == NONE else \
                self._fill(u, pred, recent, here)
            # BEFORE the early return, because a sentence that realises no claim
            # is exactly where an antecedent lives: the flood surface introduces
            # the vehicle in a sentence written to be pure scaffolding and then
            # says "It can take a further N kg". Advancing the mention history
            # only on claim-bearing units loses that antecedent and attaches the
            # payload to whatever region was named two paragraphs earlier -- one
            # wrong claim per document, and the answer wrong every time.
            recent.extend(here)
            if pred == NONE:
                continue
            if missing:
                unresolved.append(
                    f"unit {u.index}: {pred} missing {', '.join(missing)}")
                continue
            vt, tt = self.envelope.get(pred, (Interval(), Interval()))
            if pred in self.tx_role:
                dates = [_iso(t.text) for t in u.tokens if t.kind == "date"]
                if dates:
                    tt = Interval(start=dates[0], end=dates[0])
            base = len(claims)
            claims.append(Claim(predicate=pred, roles=roles,
                                valid_time=vt, transaction_time=tt))
            belief[base] = self._belief(pred, margin)
            aligns.append(Alignment(u.start, u.end, base))
            for role, others in alts.items():
                idx = [base]
                for filler in others:
                    idx.append(len(claims))
                    claims.append(Claim(predicate=pred,
                                        roles={**roles, role: filler},
                                        valid_time=vt, transaction_time=tt))
                    belief[idx[-1]] = self._belief(pred, margin) * 0.5
                    aligns.append(Alignment(u.start, u.end, idx[-1]))
                factors.append(Factor("xor", tuple(idx),
                                      detail=f"{pred}.{role} antecedent"))
        return ReadResult(
            claims=tuple(claims), belief=belief, factors=tuple(factors),
            mentions=tuple(mentions), unresolved=tuple(unresolved),
            alignments=tuple(aligns), provenance=self.id,
            cost_s=time.perf_counter() - started,
            diagnostics={"units": len(units),
                         "entity_forms": len(self.lex.forms),
                         "productive_shapes": sorted(self.lex.productive)})

    def _fill(self, u: Unit, pred: str, before: Sequence[str],
              here: Sequence[str]):
        """Fill every role, and say which references stayed open.

        Collapse is deliberately late: when a role has to come from earlier text,
        the two nearest antecedents both survive as an XOR rather than the
        nearest one being taken silently. Identity is partly settled by the
        relation, and a reader that picks at the mention has thrown that away.
        """
        roles: dict[str, Any] = {}
        alts: dict[str, list[Any]] = {}
        missing: list[str] = []
        used: set[int] = set()
        for spec in self.specs.get(pred, []):
            if spec.filler == "entity" and spec.latent > 0.5:
                # Decided BEFORE the candidates are looked at. A role whose
                # filler is never written cannot be filled from the sentence,
                # and reaching for a candidate anyway is how `bridge_on.via`
                # became the first region in the sentence -- a reading that is
                # wrong in a way no downstream kernel can detect, because the
                # id it produces is a real entity of the wrong kind.
                roles[spec.role] = EntityRef(_mint(here))
                continue
            cands = self._candidates(u, spec)
            free = [t for t in cands if t.start not in used]
            pool = free or cands
            if pool:
                r = self.rankers.get(f"{pred}:{spec.role}")
                if r is not None and len(pool) > 1:
                    j = max(range(len(pool)),
                            key=lambda j: r.score(
                                _role_features(pred, spec.role, pool, j, u,
                                               self.extra_role)))
                else:
                    j = 0
                tok = pool[j]
                used.add(tok.start)
                roles[spec.role] = _make(spec, tok)
                continue
            if spec.filler == "entity" and before and spec.external > 0.05:
                back: list[str] = []
                for e in reversed(before):
                    if e not in back:
                        back.append(e)
                    if len(back) == 2:
                        break
                roles[spec.role] = EntityRef(back[0])
                if len(back) > 1:
                    alts[spec.role] = [EntityRef(back[1])]
                continue
            missing.append(spec.role)
        return roles, alts, missing


# --------------------------------------------------------------------------

def _mint(here: Sequence[str]) -> str:
    """A name for something the text never names, from what the text does name.

    Deterministic and relational: *the region_1-region_2 crossing* and *the road
    from region_1 to region_2 bridges the river* mint the same identity, so a
    limit stated in one paragraph attaches to a bridge introduced in another
    without either sentence carrying an id. That is the whole of entity
    resolution for entities that have no names.
    """
    return "~" + "|".join(sorted(set(here))) if here else "~"


def _make(spec: _RoleSpec, tok: Token) -> Any:
    if spec.filler == "entity":
        return EntityRef(tok.text)
    if spec.filler == "quantity":
        return Quantity(value=float(tok.text), unit=spec.unit or "1")
    return tok.text.lower()


def _gold_index(cands: Sequence[Token], filler: Any) -> int | None:
    for j, t in enumerate(cands):
        if isinstance(filler, EntityRef) and t.text == filler.id:
            return j
        if isinstance(filler, Quantity) and _close(t.text, filler.value):
            return j
        if isinstance(filler, str) and t.text.lower() == filler.lower():
            return j
    return None


def _close(tok: str, value: float) -> bool:
    try:
        return abs(float(tok) - float(value)) <= 5e-3 * max(1.0, abs(value))
    except ValueError:
        return False


def _ival(i: Interval) -> tuple[Any, Any]:
    return (i.start, i.end)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x / 4.0))))
