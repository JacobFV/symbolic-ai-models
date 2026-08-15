"""The dependency DAG: anchor some variables, bind the rest under constraint.

The defect this is against, in one line of the vendored generator::

    {"color": rng.choice(COLORS), "shape": rng.choice(SHAPES), ...}

Two independent uniform draws over two six-word lists. A red cube and a purple
rod are equiprobable, ``alice`` and ``frank`` are interchangeable, and nothing in
the generated term ever distinguishes one entity from another — which is why
every entity symbol in an episode collapses into a single metavariable
component and why the type head is a tree-shape lookup nothing has beaten.

What replaces it
----------------

An episode is bound in a fixed order, and each variable is drawn from a set the
already-bound ones determine. Anchored variables are free draws; the rest are
not.

===============  ============  =====================================
variable         anchored?     drawn from
===============  ============  =====================================
``family``       anchored      graph nodes with enough descendants to
                               fill a slot and about which the graph
                               says at least four *different* things
``dimension``    anchored      attribute nouns with enough values
``agents``       anchored      descendants of a person node
``places``       anchored      descendants of a location node
``kinds``        **bound**     descendants of ``family``
``things``       **bound**     descendants of a *sibling* of ``family``
``animate``      **derived**   whether ``kinds`` sit under a living
                               thing in the graph's own taxonomy
``verbs``        **bound**     verbs whose WordNet sentence frames
                               admit a subject of that animacy
``materials``    **bound**     substance meronyms of ``kinds``,
                               inherited down the taxonomy
``o.color``      **bound**     the part or substance the graph
                               licenses for *that object's own kind*
===============  ============  =====================================

The last row is the one that makes this a DAG rather than a vocabulary swap.
Two objects in the same scene with different kinds get their second slot from
different candidate sets, because the graph says different things about them.

Why no extra randomness is consumed
-----------------------------------

Every bound value is chosen by **indexing** into its candidate set with the
position the ordinary uniform draw already produced, never by a fresh
``rng`` call. See ``symbolic_ai_data/binding.py`` on why: a draw of a different
size desynchronises the rest of the episode's random stream, and then the KG
curriculum would differ from its baseline in the symbols *and* in the scene
size, the coordinates and the question. It differs in the symbols only, which is
what makes a score difference attributable.

Where the graph has nothing to say
----------------------------------

It falls back to the curriculum's own word list, and **counts that it did**.
:meth:`KGBinder.describe` reports the fallback rate per slot. A binder that fell
back on most slots would look like a treatment and behave like the baseline —
the failure ``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-
models-name.md`` is about — so the number is reported next to the result rather
than assumed away.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .graph import KnowledgeGraph

__all__ = ["KGBinder", "SLOT_SOURCES", "pools_for"]

#: slot name -> where its words come from. Data, not code: a new closed word
#: list in the curriculum is a new row here, and a graph that can fill it does.
SLOT_SOURCES: dict[str, str] = {
    # object kinds and the things a scene contains
    "shape": "kinds",
    "kind": "kinds",
    "thing": "things",
    # the second attribute slot; per-object it is re-bound from the object's kind
    "color": "values",
    # `name` is deliberately absent, and this is the interesting exclusion.
    # WordNet has no proper names, so the six people would have to be bound to
    # occupations -- and the language packs key on the *specific* six words:
    # `pronoun_coreference` reads `gender()[n]` for every `n in NAMES`, so
    # rebinding them raises `KeyError: 'initiator'` rather than producing a
    # worse episode. The failure is loud, which is the good case; what it says
    # is that a name in this curriculum is not a free variable at all but a key
    # into a hand-written lexicon, and binding it needs a graph that carries
    # people. Recorded here rather than worked around, and it shows up in the
    # fallback table as a slot that always falls back.
    # where things are
    "place": "places",
    "city": "places",
    "surface": "surfaces",
    # what things are made of
    "material": "materials",
    "substance": "materials",
    # what things do
    "act": "verbs",
    "intransitive": "verbs",
    "transitive": "verbs",
    # events have no physical lexicographer file in the projection
    "event": "things",
    # adjectival slots: values of the episode's anchored dimension
    "property": "dimension_values",
    "size": "dimension_values",
    "activity": "verbs",
}

#: How far under a family the kinds may come from, how large a family may be,
#: and how many distinct candidate sets it has to induce. Recorded as named
#: constants rather than inline numbers because they are fitted parameters of
#: the *data*, and a fitted parameter that is never written down turns a later
#: discrepancy into a bisect — see
#: ``notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md``.
#: The pool sizes they induce on the vendored graph, so the choice is auditable:
#: (depth 3, cap 120, distinct 4) -> 157 families; (3, 200, 4) -> 163;
#: (2, 200, 3) -> 194; (3, 200, 6) -> 98. The cap is what keeps ``entity`` and
#: ``physical_entity`` out, whose descendants are most of the graph and whose
#: "family" therefore constrains nothing.
FAMILY_DEPTH = 3
FAMILY_CAP = 120
FAMILY_MIN_DISTINCT = 4

_POOLS: dict[int, dict[str, Any]] = {}


def pools_for(kg: KnowledgeGraph, *, width: int = 8) -> dict[str, Any]:
    """The candidate pools an episode anchors into, computed once per graph.

    ``width`` is the largest slot the curriculum asks for (``DETECT_CLASSES``
    has eight words), so a family that cannot fill eight is not in the pool and
    no slot ever has to be padded.
    """
    key = id(kg)
    got = _POOLS.get(key)
    if got is not None and got["width"] == width:
        return got

    families = []
    for n in range(len(kg)):
        if kg.pos[n] != "n":
            continue
        d = kg.descendants(n, max_depth=FAMILY_DEPTH)
        if not (width <= len(d) <= FAMILY_CAP):
            continue
        # A family is only useful if the graph says *different* things about its
        # members. Requiring merely "something" was not enough and the failure
        # was silent: six direct siblings inherit one part list from their
        # shared parent, so every object in a scene drew from the same
        # single-element candidate set and the dependency edge did nothing.
        sets = {frozenset(kg.parts_of(x)) | frozenset(kg.substances_of(x))
                for x in d}
        sets.discard(frozenset())
        if len(sets) >= FAMILY_MIN_DISTINCT:
            families.append(n)
    dims = [d for d in kg.dimensions(min_values=width)]
    persons = [n for n in range(len(kg))
               if kg.pos[n] == "n" and kg.lex[n] == "noun.person"
               and len(kg.descendants(n, max_depth=FAMILY_DEPTH)) >= width]
    places = [n for n in range(len(kg))
              if kg.pos[n] == "n" and kg.lex[n] == "noun.location"
              and len(kg.descendants(n, max_depth=FAMILY_DEPTH)) >= width]
    artifacts = [n for n in range(len(kg))
                 if kg.pos[n] == "n" and kg.lex[n] == "noun.artifact"
                 and len(kg.descendants(n, max_depth=FAMILY_DEPTH)) >= width]
    got = {"width": width, "families": sorted(families), "dimensions": sorted(dims),
           "persons": sorted(persons), "places": sorted(places),
           "artifacts": sorted(artifacts)}
    _POOLS[key] = got
    return got


@dataclass
class KGBinder:
    """One episode's binding. A pure function of ``(kg, lesson_id, seed)``.

    Implements the :class:`symbolic_ai_data.binding.Binder` protocol.
    """

    kg: KnowledgeGraph
    lesson_id: str
    seed: int
    width: int = 8

    _rng: random.Random = field(init=False, repr=False)
    _cache: dict[tuple[str, int], list[str]] = field(default_factory=dict, init=False, repr=False)
    _fallback: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _asked: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _trace: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _entity_bound: int = field(default=0, init=False, repr=False)
    _entity_seen: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        h = hashlib.blake2b(
            f"{self.kg.name}|{self.lesson_id}|{self.seed}".encode(), digest_size=8)
        self._rng = random.Random(int.from_bytes(h.digest(), "big"))
        self._anchor()

    # ---- the DAG -----------------------------------------------------
    def _anchor(self) -> None:
        kg, rng = self.kg, self._rng
        P = pools_for(kg, width=self.width)
        t: dict[str, Any] = {}

        # anchored: a family the graph can talk about
        fam = rng.choice(P["families"]) if P["families"] else None
        t["family"] = fam

        # bound: the kinds are this family's descendants
        kinds = list(kg.descendants(fam, max_depth=FAMILY_DEPTH)) if fam is not None else []
        t["kinds"] = kinds

        # bound: the *things* come from a sibling of the family, so a scene's
        # objects and its background vocabulary are related but not the same set
        sibs = [s for s in kg.siblings(fam)
                if len(kg.descendants(s, max_depth=FAMILY_DEPTH)) >= self.width] \
            if fam is not None else []
        if not sibs and P["families"]:
            sibs = [rng.choice(P["families"])]
        thing_fam = rng.choice(sorted(sibs)) if sibs else fam
        t["thing_family"] = thing_fam
        t["things"] = list(kg.descendants(thing_fam, max_depth=FAMILY_DEPTH)) \
            if thing_fam is not None else []

        # derived: animacy of the family, from the graph's own taxonomy
        animate = bool(kinds) and sum(kg.animate(k) for k in kinds) * 2 >= len(kinds)
        t["animate"] = animate
        # bound: verbs whose frames admit that subject
        t["verbs"] = list(kg.verbs_for(animate))

        # bound: what the kinds are made of
        mats: list[int] = []
        for k in kinds:
            mats.extend(kg.substances_of(k))
        seen: set[int] = set()
        t["materials"] = [m for m in mats if not (m in seen or seen.add(m))]

        # anchored: a dimension, kept as the fallback for the attribute slot
        dim = rng.choice(P["dimensions"]) if P["dimensions"] else None
        t["dimension"] = dim
        t["dimension_values"] = list(kg.values_of(dim)) if dim is not None else []
        # bound: the attribute vocabulary is what the graph licenses for *these
        # kinds* -- their substances and their parts, pooled. Pooling matters:
        # several lessons build a query out of the vocabulary rather than out of
        # an object (`generators/extra.py::_formula` picks a colour and asks
        # which objects have it), so every object's attribute has to stay inside
        # the shared word list or those questions stop denoting anything. The
        # constraint then lives in the *joint* draw -- see `entity` -- which is
        # where it belongs anyway.
        lic: list[int] = []
        for k in kinds:
            lic.extend(kg.substances_of(k))
            lic.extend(kg.parts_of(k))
        seen2: set[int] = set()
        t["licensed"] = [m for m in lic if not (m in seen2 or seen2.add(m))]
        # Licensed terms first, then the anchored dimension's values as padding.
        # Padding rather than a choice between the two: the curriculum asks for
        # six or eight words and a kind with three parts would otherwise send
        # the whole slot back to `red, blue, green` — leaving an episode whose
        # shapes are graph kinds and whose colours are the baseline's, which is
        # neither arm of the experiment. Measured before it was fixed: the
        # attribute slot fell back on 41% of episodes.
        t["values"] = t["licensed"] + [m for m in t["dimension_values"]
                                       if m not in seen2]

        # anchored: agents and places
        t["agents"] = list(kg.descendants(rng.choice(P["persons"]), max_depth=FAMILY_DEPTH)) if P["persons"] else []
        t["places"] = list(kg.descendants(rng.choice(P["places"]), max_depth=FAMILY_DEPTH)) if P["places"] else []
        t["surfaces"] = list(kg.descendants(rng.choice(P["artifacts"]), max_depth=FAMILY_DEPTH)) if P["artifacts"] else []

        self._trace = t
        # the per-object candidate table: kind lemma -> what the graph licenses
        self._licensed: dict[str, tuple[str, ...]] = {}
        for k in kinds:
            cand = tuple(dict.fromkeys(
                [self.kg.word(m) for m in kg.substances_of(k)]
                + [self.kg.word(m) for m in kg.parts_of(k)]))
            self._licensed[self.kg.word(k)] = cand

    # ---- Binder protocol ---------------------------------------------
    def vocabulary(self, slot: str, default: Sequence[str]) -> Sequence[str]:
        n = len(default)
        key = (slot, n)
        got = self._cache.get(key)
        if got is not None:
            return got
        self._asked[slot] = self._asked.get(slot, 0) + 1
        src = SLOT_SOURCES.get(slot)
        nodes = self._trace.get(src) if src else None
        words: list[str] = []
        if nodes:
            seen: set[str] = set()
            for m in nodes:
                w = self.kg.word(m)
                if w not in seen:
                    seen.add(w)
                    words.append(w)
        if len(words) < n:
            self._fallback[slot] = self._fallback.get(slot, 0) + 1
            out = list(default)
        else:
            # deterministic, seed-dependent choice of which n of the candidates,
            # so two episodes of the same lesson do not share a lexicon
            r = random.Random(hashlib.blake2b(
                f"{self.kg.name}|{self.lesson_id}|{self.seed}|{slot}|{n}".encode(),
                digest_size=8).digest())
            out = r.sample(words, n)
        self._cache[key] = out
        return out

    def entity(self, o: Mapping[str, Any]) -> Mapping[str, Any]:
        """Re-bind one already-drawn scene object under constraint from its kind.

        This is the edge that makes the binding a DAG rather than a vocabulary
        swap. The ``shape`` slot already holds a graph kind. The ``color`` slot
        is re-drawn from **the subset of the episode's attribute vocabulary that
        the graph licenses for that particular kind** — so two objects in one
        scene with different kinds draw from different candidate sets, and
        ``once o0 is a penguin, what it can be coloured is no longer a uniform
        draw``.

        A *subset* of the shared vocabulary, never a fresh word, so a question
        built out of the vocabulary still denotes. Chosen by indexing with the
        position the ordinary uniform draw already produced, so no randomness is
        consumed and the rest of the episode is untouched.
        """
        out = dict(o)
        if "color" not in out or "shape" not in out:
            return out
        self._entity_seen += 1
        kind = out.get("shape")
        lic = self._licensed.get(kind) if isinstance(kind, str) else None
        if not lic:
            return out
        vocab = self._colour_vocab()
        cand = [c for c in vocab if c in lic]
        if not cand:
            return out
        try:
            i = vocab.index(out["color"])
        except ValueError:
            return out
        out["color"] = cand[i % len(cand)]
        self._entity_bound += 1
        return out

    def _colour_vocab(self) -> list[str]:
        """Whichever ``color`` list this episode actually handed out.

        The curriculum asks for six almost everywhere and eight in one place;
        the binder caches per length, so the object binding has to ask for the
        one that exists rather than assume a size.
        """
        for (slot, _n), words in self._cache.items():
            if slot == "color":
                return words
        return []

    def describe(self) -> Mapping[str, Any]:
        """Everything a run directory needs to explain this episode later."""
        kg = self.kg
        t = self._trace

        def w(n):
            return kg.word(n) if isinstance(n, int) else None

        return {
            "kg": kg.name, "lesson": self.lesson_id, "seed": self.seed,
            "family": w(t.get("family")), "thing_family": w(t.get("thing_family")),
            "dimension": w(t.get("dimension")), "animate": t.get("animate"),
            "n_kinds": len(t.get("kinds") or []),
            "n_verbs": len(t.get("verbs") or []),
            "n_materials": len(t.get("materials") or []),
            "slots_asked": dict(sorted(self._asked.items())),
            "slots_fallback": dict(sorted(self._fallback.items())),
            "entities_seen": self._entity_seen,
            "entities_bound": self._entity_bound,
        }
