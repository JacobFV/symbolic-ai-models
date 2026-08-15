"""A slot that is **not drawn**: the attribute follows from the kind through the graph.

What this is against
--------------------

:mod:`symbolic_ai_kg.bind` re-labels the curriculum. Where the generator drew
``rng.choice(COLORS)`` it draws a graph-consistent colour instead, so an object
becomes a *penguin* that is *black* rather than a random object that is *purple*.
The structure of the task never changes: the answer sits in the same place,
reachable by the same route, requiring the same operation. That is why its
degree-preserving scramble tied at mean −0.0013 and **could not have done
anything else** — a permutation of a fixed graph is a fixed graph, and to a
learner whose only input is this corpus the two arms are one problem under a
relabelling. See
``notes/lessons/2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control.md``.

What this does instead
----------------------

The attribute slot of a scene object is **not sampled**. It is *determined* by
that object's kind through a map the graph states::

    pigboat --has-part--> anchor        =>  a pigboat object's attribute is `anchor`

The map is **fixed for the whole corpus** and is six pairs wide. Both halves of
that sentence are load-bearing:

* *fixed for the whole corpus*, or the association is not learnable from the
  corpus and the arm is a null by construction a second time, this time by
  sparsity rather than by isomorphism;
* *six pairs*, because the previous arm anchored a different family per episode
  and drew kinds from ~13,810 graph words — about ten training instances per
  pair, which no model here could use.

The two properties this buys, and both are the point
----------------------------------------------------

1. **A non-copyable fill that is not a guess.** The curriculum's non-copyable
   quarter is answerable today only by memorising a marginal — ``corefer-001``
   scores 0.003 there and an *oracle pointer* scores 0.000, because there is
   nothing to point at. A derived value is neither copyable nor memorised as a
   marginal: it is inferable from the visible kind beside it plus a rule the
   corpus states over and over.
2. **A control that can fail.** :class:`DeriveBinder` with ``permute=True``
   draws a fresh uniform permutation of the assignment **per episode**. Within
   an episode the value is still a deterministic function of the kind, so the
   value multiset, the collision structure, the copyable share and every marginal
   are identical to the treatment's by construction. Across episodes the
   association is noise. The channel the treatment has and the control does not
   is exactly *cross-episode co-occurrence of two symbols in one term*, and a
   learner that has the treatment's map scores at most 1/6 under the control.

Why the collision structure is preserved, which is what makes the arms matched
-----------------------------------------------------------------------------

A bijection composed with a permutation is a bijection, so two objects share a
value iff they share a kind, in **both** arms. That is what keeps
``copyable_share`` — the thing every ``acc | not copyable`` number is conditioned
on — from differing between treatment and control, and a difference there would
have made the comparison a comparison of two different buckets rather than of two
models. See
``notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md``.

Where the words come from
-------------------------

WordNet's ``part``, not CSKG's ``property``. ``property`` is the semantically
right relation ("a lemon is sour") and under a deterministic selection rule its
values are noise — ``chair → alcoholism``, ``dog → bare`` — while ``part`` gives
``monastery → annex``, ``pigboat → anchor``, ``convent → antechamber``. WordNet
is also the graph every published KG number already rests on.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .graph import KnowledgeGraph

__all__ = ["DeriveBinder", "anchor_map", "DERIVE_RELATION", "DERIVE_WIDTH",
           "KIND_SLOT", "VALUE_SLOT"]

#: The relation the map is read off. A fitted parameter of the *data*, written
#: down rather than inlined — see
#: ``notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md``.
DERIVE_RELATION = "part"

#: How many pairs the map has. Six because that is the width of the curriculum's
#: ``shape`` and ``color`` lists everywhere they are asked for; a map wider than
#: the slot could not be a bijection onto it.
DERIVE_WIDTH = 6

#: The slot whose word is the anchor, and the slot whose word follows from it.
KIND_SLOT = "shape"
VALUE_SLOT = "color"

#: Only single lowercase alphabetic lemmas. A multi-word or hyphenated lemma
#: renders into prose as several tokens and would make the two arms differ in
#: sequence length as well as in symbols.
_LEMMA = re.compile(r"^[a-z]+$")

_MAPS: dict[tuple, tuple[tuple[str, ...], tuple[str, ...]]] = {}


def _key(kg: KnowledgeGraph) -> tuple:
    # Identity *and* shape: a temporary graph can be freed and a different one
    # allocated at the same address. `bind.pools_for` learned this the same way.
    return (id(kg), kg.name, len(kg), kg.n_edges())


def _candidates(kg: KnowledgeGraph, relation: str) -> list[tuple[int, int, list[int]]]:
    out: list[tuple[int, int, list[int]]] = []
    for n in range(len(kg)):
        if kg.pos[n] != "n" or not _LEMMA.match(kg.word(n)):
            continue
        vals = [v for v in kg.out(relation, n)
                if _LEMMA.match(kg.word(v))]
        if vals:
            out.append((-len(vals), n, vals))
    out.sort()
    return out


def anchor_map(kg: KnowledgeGraph, *, relation: str = DERIVE_RELATION,
               width: int = DERIVE_WIDTH,
               kinds: Sequence[str] | None = None
               ) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """``(kinds, values)``: the corpus-wide map, read off this graph.

    Kinds are the nouns the graph says the most about under ``relation``, most
    first, ties by node id. Each kind's value is the thing the graph relates it
    to and **fewest others** — lowest incoming degree in that relation, ties
    alphabetically — so a value names its kind rather than half the graph. Both
    passes are deterministic and consume no randomness: an episode is a pure
    function of its address and a map fitted with an rng would break that.

    ``kinds`` pins the anchor set instead of selecting it, and every control
    passes it. Without that pin the scramble would change *which nouns have the
    most parts* and the arms would differ in their vocabulary as well as in their
    map — the control has to hold everything fixed except the correspondence it
    destroys, and its own census is not enough to say so.
    """
    cache = _MAPS.get((_key(kg), relation, width, tuple(kinds or ())))
    if cache is not None:
        return cache

    # A lemma names several synsets, and pinning by word has to land on the same
    # one the selection rule chose or the control silently anchors on a homonym
    # with no edges. The rule is the selection rule's own key — most values
    # first, ties by node id — and the scramble preserves per-node out-degree in
    # every relation, so the same node wins on a graph and on its scramble.
    by_word: dict[str, int] = {}
    for n in range(len(kg)):
        if kg.pos[n] != "n":
            continue
        w = kg.word(n)
        d = len([v for v in kg.out(relation, n) if _LEMMA.match(kg.word(v))])
        if w not in by_word or d > len([v for v in kg.out(relation, by_word[w])
                                        if _LEMMA.match(kg.word(v))]):
            by_word[w] = n

    if kinds is None:
        order = [n for _d, n, _v in _candidates(kg, relation)]
    else:
        order = [by_word[w] for w in kinds if w in by_word]
        if len(order) != len(kinds):
            missing = [w for w in kinds if w not in by_word]
            raise KeyError(f"{kg.name} has no noun for {missing}")

    # Choose the anchor set greedily, then assign values by **matching**, not
    # greedily. Greedy assignment is order-dependent and fails on a graph where
    # it is only the order that is wrong: on `wordnet-shuffled` the pinned set
    # runs out of distinct values at `manor` while a perfect assignment exists.
    # A control that could not be built for that reason would have quietly
    # become a control on a different anchor set.
    prefs: dict[str, list[str]] = {}
    chosen: list[str] = []
    for n in order:
        w = kg.word(n)
        if w in prefs:
            continue
        vals = [v for v in kg.out(relation, n)
                if _LEMMA.match(kg.word(v))]
        ranked = [kg.word(v) for v in
                  sorted(vals, key=lambda v: (len(kg.inc(relation, v)), kg.word(v)))]
        ranked = [x for i, x in enumerate(ranked) if x != w and x not in ranked[:i]]
        if not ranked:
            continue
        prefs[w] = ranked
        chosen.append(w)
        if kinds is None and len(chosen) == width:
            break
    if kinds is not None:
        missing = [w for w in kinds if w not in prefs]
        if missing:
            raise ValueError(
                f"{kg.name}: no {relation} value at all for {missing}; the "
                "pinned anchor set cannot be mapped on this graph")
        chosen = list(kinds)

    taken: dict[str, str] = {}          # value -> kind holding it

    def _augment(k: str, seen: set[str]) -> bool:
        for v in prefs[k]:
            if v in seen or v in chosen:
                continue
            seen.add(v)
            if v not in taken or _augment(taken[v], seen):
                taken[v] = k
                return True
        return False

    for k in chosen:
        if not _augment(k, set()):
            raise ValueError(
                f"{kg.name}: no distinct {relation} value left for {k!r}; the "
                "anchor set cannot be mapped on this graph")
    assign = {k: v for v, k in taken.items()}
    got_k = list(chosen)
    got_v = [assign[k] for k in got_k]
    if len(got_k) < width:
        raise ValueError(f"{kg.name}: only {len(got_k)} of {width} anchors "
                         f"could be mapped under {relation!r}")
    out = (tuple(got_k), tuple(got_v))
    _MAPS[(_key(kg), relation, width, tuple(kinds or ()))] = out
    return out


@dataclass
class DeriveBinder:
    """One episode's binding, where the value slot is derived rather than drawn.

    Implements the :class:`symbolic_ai_data.binding.Binder` protocol, and is a
    pure function of ``(kinds, values, permute, lesson_id, seed)``.

    Only two slots are touched. That is deliberate and is what makes a
    difference between the arms attributable: `derive` and `derive-perm` share
    every other word in the corpus, so they differ in whether the kind→value
    assignment is the same one twice and in nothing else.
    """

    kinds: tuple[str, ...]
    values: tuple[str, ...]
    lesson_id: str
    seed: int
    #: Draw a fresh uniform permutation of the assignment for this episode. The
    #: **control**: within an episode the value is still a deterministic function
    #: of the kind — so the collision structure, the copyable share and every
    #: marginal are the treatment's — and across episodes the association is
    #: noise. A model carrying the treatment's map scores 1/6 here.
    permute: bool = False
    #: Recorded in the run directory so a number can be explained later.
    graph: str = ""

    _perm: tuple[int, ...] = field(init=False, repr=False)
    _index: dict[str, int] = field(init=False, repr=False)
    _asked: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _fallback: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _seen: int = field(default=0, init=False, repr=False)
    _bound: int = field(default=0, init=False, repr=False)
    _derived: list[tuple[str, str, str]] = field(default_factory=list, init=False,
                                                 repr=False)

    def __post_init__(self) -> None:
        if len(self.kinds) != len(self.values):
            raise ValueError("the map must be a bijection")
        if len(set(self.kinds)) != len(self.kinds) or \
                len(set(self.values)) != len(self.values):
            raise ValueError("the map must be a bijection")
        self._index = {w: i for i, w in enumerate(self.kinds)}
        n = len(self.kinds)
        if self.permute:
            h = hashlib.blake2b(
                f"{self.graph}|perm|{self.lesson_id}|{self.seed}".encode(),
                digest_size=8)
            r = random.Random(int.from_bytes(h.digest(), "big"))
            order = list(range(n))
            r.shuffle(order)
            self._perm = tuple(order)
        else:
            self._perm = tuple(range(n))

    # ---- Binder protocol ---------------------------------------------
    def vocabulary(self, slot: str, default: Sequence[str]) -> Sequence[str]:
        """The kind list and the value list; everything else is left alone.

        A slot asked for a different width than the map is **not** padded or
        truncated: it falls back to the curriculum's own list and the fallback is
        counted, because a value slot the map cannot fill entirely is a slot on
        which the derivation does not hold, and a binder that quietly half-filled
        one would be a treatment behaving like its baseline. See
        ``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md``.
        """
        self._asked[slot] = self._asked.get(slot, 0) + 1
        if slot == KIND_SLOT and len(default) == len(self.kinds):
            return list(self.kinds)
        if slot == VALUE_SLOT and len(default) == len(self.values):
            return list(self.values)
        if slot in (KIND_SLOT, VALUE_SLOT):
            self._fallback[slot] = self._fallback.get(slot, 0) + 1
        return default

    def entity(self, o: Mapping[str, Any]) -> Mapping[str, Any]:
        """Replace the drawn value with the one the kind determines.

        No randomness is consumed: the scene was drawn with the ordinary uniform
        draws and this rewrites a symbol it produced, so the scene size, the
        coordinates and the question are the ones the baseline drew. Same
        discipline as :meth:`symbolic_ai_kg.bind.KGBinder.entity` and for the
        same reason — a draw of a different size desynchronises the rest of the
        episode.
        """
        out = dict(o)
        if VALUE_SLOT not in out or KIND_SLOT not in out:
            return out
        self._seen += 1
        i = self._index.get(out[KIND_SLOT]) if isinstance(out[KIND_SLOT], str) else None
        if i is None:
            return out
        out[VALUE_SLOT] = self.values[self._perm[i]]
        self._bound += 1
        self._derived.append((str(out.get("id", "")), out[KIND_SLOT],
                              out[VALUE_SLOT]))
        return out

    # ---- what the analysis needs -------------------------------------
    def derived(self) -> list[tuple[str, str, str]]:
        """``(object id, kind word, value word)`` for every derived fill.

        Read by ``scripts/derived_split.py`` to locate the positions in the term
        graph exactly, rather than by matching labels against the value list —
        several lessons build an ``obj`` predicate themselves without going
        through ``bind_scene``, and a label match would count one of their
        undetermined pairs as derived once in six by chance, in **both** arms.
        """
        return list(self._derived)

    def value_for(self, kind: str) -> str | None:
        i = self._index.get(kind)
        return None if i is None else self.values[self._perm[i]]

    def describe(self) -> Mapping[str, Any]:
        return {
            "kg": self.graph, "derive": True, "permute": self.permute,
            "lesson": self.lesson_id, "seed": self.seed,
            "kinds": list(self.kinds), "values": list(self.values),
            "assignment": [self.values[self._perm[i]]
                           for i in range(len(self.kinds))],
            "slots_asked": dict(sorted(self._asked.items())),
            "slots_fallback": dict(sorted(self._fallback.items())),
            "entities_seen": self._seen, "entities_bound": self._bound,
        }
