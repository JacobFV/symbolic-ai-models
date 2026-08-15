"""The graph itself, and the handful of queries a variable binder needs.

Deliberately small and deliberately dumb: integer node ids, adjacency lists per
relation, no caching that depends on iteration order. Two properties matter more
than convenience here.

**Determinism.** Everything that returns a set of candidates returns a *sorted
tuple*. A binder draws from these with a seeded ``random.Random``, and an episode
is a pure function of its seed — which is the property the whole resource rests
on. A ``set`` iterated directly would make generation depend on
``PYTHONHASHSEED``, which is the failure ``tests/test_models.py``'s
cross-process test exists to catch one layer up.

**Substitutability.** Nothing above this module knows the graph is WordNet. The
binder asks for ``kinds_under(node)``, ``substances_of(node)``,
``animate(node)``; a larger graph arriving later answers the same questions from
different data. Where a query has no WordNet-independent meaning it is not here.
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

__all__ = ["KnowledgeGraph", "RELATIONS", "ANIMATE_FRAMES", "INANIMATE_FRAMES"]

#: The relations a projection may carry. ``isa`` is hypernymy for both nouns and
#: verbs; ``part``/``substance``/``member`` are meronymies written source-has-
#: target; ``attr`` links an adjective to the noun naming the dimension it is a
#: value of; ``similar`` and ``antonym`` are the adjective's own structure.
#:
#: ``property`` and ``can`` are **not in WordNet's projection** and every query
#: over them returns the empty tuple there, which is what lets a graph that has
#: them arrive without moving a single published WordNet number. They are what a
#: commonsense graph states and a lexical one does not: ``property`` is
#: thing -> adjective ("a lemon is sour"), ``can`` is thing -> verb.
#:
#: No graph is required to carry all of these. The list is what the loader will
#: index if it finds it, not a schema anything must satisfy.
RELATIONS = ("isa", "part", "substance", "member", "attr", "similar", "antonym",
             "property", "can")

#: WordNet sentence frames whose subject slot is "Somebody". Princeton's own
#: numbering, not a judgement made here: frame 2 is "Somebody ----s", 8 is
#: "Somebody ----s something", 9 "Somebody ----s somebody".
ANIMATE_FRAMES = frozenset({2, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23,
                            24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35})
#: Frames whose subject slot is "Something": 1, 10, 11, 22, 27.
INANIMATE_FRAMES = frozenset({1, 10, 11, 22, 27})


@dataclass
class KnowledgeGraph:
    """Nodes, typed edges, and the queries a dependency DAG walks."""

    name: str
    lemmas: list[tuple[str, ...]]
    pos: list[str]
    lex: list[str]
    edges: dict[str, list[tuple[int, int]]]
    frames: dict[int, tuple[int, ...]] = field(default_factory=dict)
    selection: str = ""
    provenance: Mapping[str, str] = field(default_factory=dict)
    #: Which relations this graph states at the *parent* and therefore have to
    #: be read through the hypernym chain to be visible at a leaf. It is a
    #: property of the source, not of the relation name, and getting it wrong is
    #: silent in both directions:
    #:
    #: * WordNet states meronymy at the parent — ``penguin`` has no ``part``
    #:   edges and ``bird`` has ``beak`` and ``wing`` — so *without* the climb
    #:   the relation is empty exactly where a curriculum draws;
    #: * ConceptNet states properties at the concept, and *with* the climb every
    #:   chain reaches a general ancestor carrying most of the adjective
    #:   vocabulary, so six different kinds license the same ~1,130 words and
    #:   the constrained draw is a uniform draw with more machinery.
    #:
    #: Both failures produce a graph that loads, generates and looks fine.
    inherit: frozenset[str] = frozenset({"part", "substance", "member"})

    _fwd: dict[str, dict[int, tuple[int, ...]]] = field(default_factory=dict, repr=False)
    _rev: dict[str, dict[int, tuple[int, ...]]] = field(default_factory=dict, repr=False)
    #: Memo for the two walks everything else is built on. A graph is immutable
    #: in use and both are pure functions returning tuples, so this changes no
    #: value anywhere — asserted by the fingerprints, which did not move when it
    #: was added. It is here because the binder re-walks the same few hundred
    #: families once per episode: on the 36k-node commonsense graph that was the
    #: dominant cost of generating a corpus.
    _anc: dict[tuple[int, int], tuple[int, ...]] = field(default_factory=dict, repr=False)
    _desc: dict[tuple[int, int], tuple[int, ...]] = field(default_factory=dict, repr=False)

    # ---- construction ------------------------------------------------
    def __post_init__(self) -> None:
        self._index()

    def _index(self) -> None:
        self._fwd, self._rev = {}, {}
        self._anc, self._desc = {}, {}
        for rel in self.edges:
            f: dict[int, list[int]] = {}
            r: dict[int, list[int]] = {}
            for a, b in self.edges[rel]:
                f.setdefault(a, []).append(b)
                r.setdefault(b, []).append(a)
            self._fwd[rel] = {k: tuple(sorted(v)) for k, v in f.items()}
            self._rev[rel] = {k: tuple(sorted(v)) for k, v in r.items()}

    @classmethod
    def from_payload(cls, d: Mapping) -> "KnowledgeGraph":
        nodes = d["nodes"]
        return cls(
            name=d["name"],
            lemmas=[tuple(n["w"]) for n in nodes],
            pos=[n["p"] for n in nodes],
            lex=[n["x"] for n in nodes],
            edges={rel: [(a, b) for a, b in pairs] for rel, pairs in d["edges"].items()},
            frames={int(k): tuple(v) for k, v in d.get("frames", {}).items()},
            selection=d.get("selection", ""),
            provenance=dict(d.get("source", {})),
            # Absent in the WordNet artefact, which predates the field; its
            # default is that artefact's behaviour, so the bytes already
            # committed keep meaning what they meant.
            inherit=frozenset(d["inherit"]) if "inherit" in d
            else frozenset({"part", "substance", "member"}),
        )

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeGraph":
        with gzip.open(path, "rb") as f:
            return cls.from_payload(json.loads(f.read().decode("utf-8")))

    def replacing_edges(self, edges: Mapping[str, Sequence[tuple[int, int]]],
                        *, name: str) -> "KnowledgeGraph":
        """A copy with different wiring and identical everything else.

        The scrambled control is built through here so it cannot accidentally
        differ in node count, lemma, part of speech or lexname — the things it
        is supposed to hold fixed.
        """
        return KnowledgeGraph(
            name=name, lemmas=list(self.lemmas), pos=list(self.pos),
            lex=list(self.lex),
            edges={rel: [tuple(e) for e in pairs] for rel, pairs in edges.items()},
            frames=dict(self.frames), selection=self.selection,
            provenance=dict(self.provenance), inherit=frozenset(self.inherit))

    # ---- basics ------------------------------------------------------
    def __len__(self) -> int:
        return len(self.lemmas)

    def n_edges(self) -> int:
        return sum(len(v) for v in self.edges.values())

    def word(self, n: int) -> str:
        """The lemma this repo will print. First alphabetically, so a graph and
        its scramble name the same node the same way."""
        return self.lemmas[n][0]

    def out(self, rel: str, n: int) -> tuple[int, ...]:
        return self._fwd.get(rel, {}).get(n, ())

    def inc(self, rel: str, n: int) -> tuple[int, ...]:
        return self._rev.get(rel, {}).get(n, ())

    def degree(self, rel: str, n: int) -> tuple[int, int]:
        return len(self.out(rel, n)), len(self.inc(rel, n))

    # ---- taxonomy ----------------------------------------------------
    def hypernyms(self, n: int) -> tuple[int, ...]:
        return self.out("isa", n)

    def hyponyms(self, n: int) -> tuple[int, ...]:
        return self.inc("isa", n)

    def ancestors(self, n: int, *, limit: int = 32) -> tuple[int, ...]:
        """The transitive hypernym closure, breadth-first and sorted per level.

        Sorted rather than set-ordered on purpose; see the module docstring.
        """
        got = self._anc.get((n, limit))
        if got is not None:
            return got
        seen: set[int] = set()
        order: list[int] = []
        frontier = [n]
        for _ in range(limit):
            nxt = []
            for m in frontier:
                for h in self.hypernyms(m):
                    if h not in seen:
                        seen.add(h); order.append(h); nxt.append(h)
            if not nxt:
                break
            frontier = sorted(nxt)
        got = self._anc[(n, limit)] = tuple(order)
        return got

    def descendants(self, n: int, *, max_depth: int = 3) -> tuple[int, ...]:
        """Everything under ``n`` within ``max_depth`` hyponym hops.

        Direct children are not enough, and finding that out cost a round of
        this seam. Six *siblings* share their whole ancestor chain, WordNet
        states meronymy at the parent rather than restating it at each child, so
        the inherited part list of six siblings is **identical** — and a
        "constrained" draw whose candidate set is the same for every kind is a
        uniform draw with more machinery. Reaching down three levels gives kinds
        at different depths with different chains, which is what makes the
        per-object constraint bite. ``tests/test_kg.py``'s
        ``two_objects_of_different_kinds_draw_from_different_candidate_sets`` is
        the assertion that caught it.
        """
        got = self._desc.get((n, max_depth))
        if got is not None:
            return got
        seen: set[int] = set()
        frontier = [n]
        for _ in range(max_depth):
            nxt: list[int] = []
            for m in frontier:
                for h in self.hyponyms(m):
                    if h not in seen:
                        seen.add(h); nxt.append(h)
            if not nxt:
                break
            frontier = sorted(nxt)
        got = self._desc[(n, max_depth)] = tuple(sorted(seen))
        return got

    def kinds_under(self, n: int, *, min_lemmas: int = 1) -> tuple[int, ...]:
        """Direct hyponyms with at least ``min_lemmas`` printable lemmas."""
        return tuple(m for m in self.hyponyms(n) if len(self.lemmas[m]) >= min_lemmas)

    def siblings(self, n: int) -> tuple[int, ...]:
        """Co-hyponyms: everything sharing a direct hypernym with ``n``."""
        out: set[int] = set()
        for h in self.hypernyms(n):
            out.update(self.hyponyms(h))
        out.discard(n)
        return tuple(sorted(out))

    def is_a(self, n: int, ancestor: int) -> bool:
        return ancestor in self.ancestors(n)

    # ---- what a thing is made of and made from -----------------------
    def parts_of(self, n: int, *, inherited: bool | None = None) -> tuple[int, ...]:
        return self._meronyms("part", n, inherited)

    def substances_of(self, n: int, *, inherited: bool | None = None) -> tuple[int, ...]:
        return self._meronyms("substance", n, inherited)

    def members_of(self, n: int, *, inherited: bool | None = None) -> tuple[int, ...]:
        return self._meronyms("member", n, inherited)

    def properties_of(self, n: int, *, inherited: bool | None = None) -> tuple[int, ...]:
        """Adjectives the graph licenses for this kind. **Not inherited.**

        Empty on every graph without a ``property`` relation, WordNet's
        projection included — which is the property that lets a commonsense
        graph be added beside it without redefining anything already published.

        The default differs from :meth:`parts_of` and that difference is the
        whole point. Meronymy *has* to be inherited on WordNet: ``penguin`` has
        no part edges and ``bird`` has ``beak`` and ``wing``, so without the
        climb the relation is empty at the leaves where a curriculum draws.
        Property assertions are the opposite — ConceptNet states them at the
        concept (``penguin HasProperty black``) — and inheriting them is a
        WordNet-shaped assumption that does not transfer.

        Measured before this default was chosen, because the failure it avoids
        is silent. With inheritance on, ``penguin``, ``dog``, ``brick``, ``car``,
        ``chair`` and ``apple`` each end up licensing ~1,130 properties out of
        the graph's 1,315 adjectives, because every chain reaches a general
        ancestor that has been assigned everything. Six kinds with the same
        candidate set is a uniform draw with more machinery — the exact defect
        the seam exists to remove, reintroduced one relation over. Direct
        assertions give ``penguin`` 12 and ``dog`` 284, which differ.
        """
        return self._meronyms("property", n, inherited)

    def abilities_of(self, n: int, *, inherited: bool | None = None) -> tuple[int, ...]:
        """Verbs this kind is asserted capable of. Empty without ``can``.

        Not inherited, for the reason :meth:`properties_of` gives.
        """
        return self._meronyms("can", n, inherited)

    def _meronyms(self, rel: str, n: int, inherited: bool | None) -> tuple[int, ...]:
        """Read a relation at ``n``, climbing the taxonomy iff the graph says to.

        ``inherited=None`` means "ask the graph", which is the only correct
        default: whether a relation is stated at the parent or at the concept is
        a fact about the source. See :attr:`inherit`.
        """
        if inherited is None:
            inherited = rel in self.inherit
        got = list(self.out(rel, n))
        if inherited:
            for a in self.ancestors(n):
                got.extend(self.out(rel, a))
        seen, order = set(), []
        for m in got:
            if m not in seen:
                seen.add(m); order.append(m)
        return tuple(order)

    # ---- adjectives as values of a dimension -------------------------
    def dimension_of(self, adj: int) -> tuple[int, ...]:
        """The noun naming the attribute this adjective is a value of."""
        direct = self.out("attr", adj)
        if direct:
            return direct
        out: list[int] = []
        for s in self.out("similar", adj) + self.inc("similar", adj):
            out.extend(self.out("attr", s))
        return tuple(sorted(set(out)))

    def values_of(self, dim: int) -> tuple[int, ...]:
        """Every adjective that is a value of this dimension, satellites folded
        in. ``weight`` yields ``heavy``, ``light``, ``weightless`` ..."""
        heads = self.inc("attr", dim)
        out = set(heads)
        for h in heads:
            out.update(self.out("similar", h))
            out.update(self.inc("similar", h))
        return tuple(sorted(out))

    def dimensions(self, *, min_values: int = 2) -> tuple[int, ...]:
        """Every attribute noun with at least ``min_values`` adjectives on it."""
        return tuple(sorted(d for d in self._rev.get("attr", {})
                            if len(self.values_of(d)) >= min_values))

    def antonyms(self, adj: int) -> tuple[int, ...]:
        return tuple(sorted(set(self.out("antonym", adj)) | set(self.inc("antonym", adj))))

    # ---- verbs and what they can take as a subject -------------------
    def animate(self, n: int) -> bool:
        """Whether the graph places this noun under a living thing.

        ``lex`` alone would do most of the work (``noun.animal``,
        ``noun.person``), but the lexname is a filing decision and the taxonomy
        is a claim, so the taxonomy is asked first and the lexname is the
        fallback for nodes whose ancestry the projection truncated.
        """
        for a in (n,) + self.ancestors(n):
            if self.lex[a] in ("noun.animal", "noun.person"):
                return True
        return self.lex[n] in ("noun.animal", "noun.person")

    def verbs_for(self, animate: bool) -> tuple[int, ...]:
        """Verbs whose WordNet frames admit a subject of this animacy.

        This is the selectional restriction the current curriculum has no way to
        state. ``sleep`` takes "Somebody ----s"; ``glow`` takes "Something
        ----s"; a graph that knows the difference can refuse "the red idea
        sleeps furiously" while the present generator cannot.
        """
        want = ANIMATE_FRAMES if animate else INANIMATE_FRAMES
        return tuple(sorted(v for v, fr in self.frames.items()
                            if want.intersection(fr)))

    # ---- lookups -----------------------------------------------------
    def by_lemma(self) -> dict[str, tuple[int, ...]]:
        out: dict[str, list[int]] = {}
        for i, ws in enumerate(self.lemmas):
            for w in ws:
                out.setdefault(w, []).append(i)
        return {k: tuple(v) for k, v in sorted(out.items())}

    def census(self) -> dict[str, int]:
        d = {"nodes": len(self), "edges": self.n_edges(),
             "frames": len(self.frames)}
        d.update({f"edge:{r}": len(v) for r, v in sorted(self.edges.items())})
        for p in ("n", "v", "a"):
            d[f"pos:{p}"] = sum(1 for x in self.pos if x == p)
        return d


def _iter_pairs(edges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(int(a), int(b)) for a, b in edges]
