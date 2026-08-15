"""Guards for the semantic-constraint seam.

Ordered by what they would catch, worst first.

1. **The base curriculum did not move.** Rule 1 of
   ``notes/decisions/2026-08-14-semantic-constraint-from-a-knowledge-graph.md``:
   every published number in this repo is defined on the current generator, so
   the KG curriculum is a *separately named* curriculum and the 179-lesson
   fingerprint stays green. ``tests/test_curriculum_fingerprint.py`` is the
   primary guard; the one here is the cheap English-only version that fails in
   seconds rather than minutes.
2. **The vendored graph is the bytes that were vendored.** Same rule as
   ``symbolic_ai_data``: a checksum, not a promise.
3. **The control matches its treatment where it is supposed to.** Node count,
   per-node degree, density and acyclicity identical; wiring different. A
   scrambled graph that quietly kept most of its edges would look like a control
   and behave like the treatment.
4. **The manipulation is symbols-only.** The KG arms must not move a tree shape,
   or a score difference is a shape difference and no reading of it is possible.
5. **An episode is still a pure function of its address.**
"""

from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from symbolic_ai_core.data import curriculum as C
from symbolic_ai_core.data import fingerprint as F
from symbolic_ai_kg import _vendor, load
from symbolic_ai_kg.bind import KGBinder, pools_for
from symbolic_ai_kg.registry import KG_NAMES, SHUFFLE_ROUNDS, SHUFFLE_SEED
from symbolic_ai_kg.scramble import degree_preserving_shuffle, swap_report

# A handful of lessons, named, for the tests that only need generation to work.
# Every claim about *scores* in this repo comes from the full 179; nothing here
# reports a number, so a fixture is legitimate. See
# ``notes/lessons/2026-08-13-slices-have-inverted-results-eight-times.md``.
SOME = ["symbol_grounding", "set_operations", "negation", "counting_quantifier",
        "dialogue_game", "knowledge_update"]


# ---------------------------------------------------------------- vendoring
def test_the_vendored_graph_is_the_bytes_that_were_vendored():
    """A projection of somebody else's data, pinned by checksum.

    Not a style rule. ``symbolic_ai_core/data/langdb.py`` records what an
    unpinned data path costs: 58 languages were unreachable and every published
    number was measured on seven because a file was absent rather than because
    seven was the design.
    """
    got = hashlib.sha256(_vendor.GRAPH_PATH.read_bytes()).hexdigest()
    assert got == _vendor.GRAPH_SHA256, (
        f"the vendored graph is not the one recorded in _vendor.py "
        f"({got} != {_vendor.GRAPH_SHA256}). Rebuild it with "
        f"`uv run python scripts/build_wordnet_kg.py`, or if the change is "
        f"intended, re-record the constant *and* every number drawn on it.")


def test_the_licence_travels_with_the_data():
    """WordNet 3.0 may be redistributed only with its copyright notice."""
    text = _vendor.LICENSE_PATH.read_text(encoding="utf-8")
    assert "WordNet 3.0 Copyright 2006 by Princeton University" in text
    assert "Permission to use, copy, modify and distribute" in text


def test_the_graph_carries_its_own_provenance():
    """A run directory has to be explainable without this test file."""
    with gzip.open(_vendor.GRAPH_PATH, "rb") as f:
        payload = json.loads(f.read().decode("utf-8"))
    assert payload["source"]["sha256"] == _vendor.UPSTREAM_SHA256
    assert payload["source"]["url"] == _vendor.UPSTREAM_URL
    assert payload["selection"] == _vendor.SELECTION


def test_nothing_in_the_package_reaches_the_network():
    """The one thing that downloads is a script, and it is not importable from
    the package. ``symbolic_ai_data``'s ``site-languages.db.gz`` was recorded as
    unread on the strength of a claim; this is the assertion version."""
    import pathlib
    for p in pathlib.Path(_vendor.ROOT).rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        for bad in ("urllib.request", "requests.", "httpx", "socket."):
            assert bad not in src, f"{p.name} mentions {bad}"


# ---------------------------------------------------------------- the graph
def test_the_graph_says_something_a_uniform_draw_cannot():
    """The whole premise: a kind constrains what can be said about it.

    Without this the binder would be a vocabulary swap with extra steps.
    """
    kg = load("wordnet")
    by = kg.by_lemma()
    dog = by["dog"][0]
    assert kg.animate(dog)
    assert "paw" in {kg.word(m) for m in kg.parts_of(dog)}
    oak = by["oak"][0]
    assert not kg.animate(oak)
    assert "acorn" in {kg.word(m) for m in kg.parts_of(oak)}
    # and the two do not license the same things
    assert set(kg.parts_of(dog)) != set(kg.parts_of(oak))


def test_verb_frames_separate_animate_from_inanimate_subjects():
    """The selectional restriction the present curriculum cannot state."""
    kg = load("wordnet")
    a, i = set(kg.verbs_for(True)), set(kg.verbs_for(False))
    assert a and i
    assert a != i


def test_queries_are_sorted_so_generation_cannot_depend_on_hash_order():
    """Iterating a set of ints is stable, but iterating one built from a dict
    of strings is not across processes. Every candidate list a binder draws from
    must be sorted, or an episode stops being a pure function of its seed and
    every published number flaps between runs while looking reproducible inside
    one interpreter."""
    kg = load("wordnet")
    n = kg.by_lemma()["dog"][0]
    for got in (kg.siblings(n), kg.hypernyms(n), kg.hyponyms(n),
                kg.dimensions(), kg.verbs_for(True)):
        assert list(got) == sorted(got)


# ------------------------------------------------------------- the control
def test_the_control_is_the_same_graph_with_different_wiring():
    """Node count, node attributes, edge count and per-node degree identical.

    This is what makes "semantics helped" separable from "more structure
    helped" — the failure that
    ``notes/lessons/2026-08-13-a-control-that-could-fail.md`` is a list of.
    """
    kg, sh = load("wordnet"), load("wordnet-shuffled")
    assert len(kg) == len(sh)
    assert kg.lemmas == sh.lemmas and kg.pos == sh.pos and kg.lex == sh.lex
    assert kg.frames == sh.frames
    assert sorted(kg.edges) == sorted(sh.edges)
    for rel in kg.edges:
        assert len(kg.edges[rel]) == len(sh.edges[rel]), rel
        for n in range(len(kg)):
            assert kg.degree(rel, n) == sh.degree(rel, n), (rel, n)


def test_the_control_actually_rewired_most_of_its_edges():
    """A control that kept its edges is the treatment with a longer name.

    Reported as a share rather than asserted as a bool, because the number is
    what a write-up has to quote — the same reason a fitted scalar is reported
    with its grid.
    """
    kg = load("wordnet")
    rep = swap_report(kg, seed=SHUFFLE_SEED, rounds=SHUFFLE_ROUNDS)
    for rel, d in rep.items():
        if d["edges"] < 100:          # `member` has 23; a swap needs room
            continue
        assert d["kept_share"] < 0.05, (rel, d)


def test_the_control_is_still_a_taxonomy():
    """`isa` must stay acyclic. A scramble that returned cycles would differ
    from the real graph structurally as well as semantically, which is the
    confound the control exists to remove."""
    kg = load("wordnet-shuffled")
    seen: set[int] = set()
    stack: set[int] = set()

    def visit(n: int) -> None:
        if n in seen:
            return
        seen.add(n); stack.add(n)
        for m in kg.out("isa", n):
            assert m not in stack, f"cycle through {n} -> {m}"
            visit(m)
        stack.discard(n)

    for n in range(len(kg)):
        visit(n)


def test_the_control_is_not_the_treatment():
    """The cheapest detector this repo has: two things identical to every digit
    are one thing. ``vsa_full_gated-002`` came out bit-identical to its own
    baseline and the whole experiment measured nothing."""
    kg, sh = load("wordnet"), load("wordnet-shuffled")
    assert kg.edges != sh.edges
    dog = kg.by_lemma()["dog"][0]
    assert set(kg.ancestors(dog)) != set(sh.ancestors(dog))


def test_the_scramble_is_deterministic():
    a = degree_preserving_shuffle(load("wordnet"), seed=7, rounds=4)
    b = degree_preserving_shuffle(load("wordnet"), seed=7, rounds=4)
    assert a.edges == b.edges


# ------------------------------------------------------------ the curricula
def test_the_base_curriculum_did_not_move():
    """Rule 1. English only and one lesson family, so it costs seconds; the
    full seven-language 179-lesson version is
    ``tests/test_curriculum_fingerprint.py`` and is the one that licenses a
    merge. **If this fails, the guard is working** — fix the binding, never the
    golden file."""
    golden = F.load_golden()
    got = F.curriculum_fingerprint(lessons=SOME, languages=["english"])
    for lid in SOME:
        assert golden["lessons"][lid]["raw"] == got["lessons"][lid]["raw"], lid
        assert (golden["lessons"][lid]["text"]["english"]
                == got["lessons"][lid]["text"]["english"]), lid


@pytest.mark.parametrize("curriculum",
                         ["kg:wordnet", "kg:wordnet-shuffled", "kg:wordnet-flat"])
def test_each_kg_curriculum_has_its_own_fingerprint(curriculum):
    """One golden file per curriculum. A KG arm sharing the base file would be
    exactly the silent redefinition the module exists to prevent."""
    path = F.golden_path_for(curriculum)
    assert path != F.GOLDEN_PATH
    golden = F.load_golden(path)
    got = F.curriculum_fingerprint(lessons=SOME, languages=["english"],
                                   curriculum=curriculum)
    for lid in SOME:
        assert golden["lessons"][lid]["raw"] == got["lessons"][lid]["raw"], lid


def test_the_curricula_are_four_different_worlds():
    """A KG arm that reproduced the base arm would be a null by construction,
    and a control that reproduced its treatment would be no control. Two rows
    identical to every digit are one row -- the cheapest detector this repo
    has, and the one that caught `vsa_full_gated-002` reproducing its own
    baseline."""
    got = {c: [ep.prompt for ep in C.generate(SOME, n=3, seed0=0, curriculum=c)]
           for c in C.CURRICULA}
    for a in C.CURRICULA:
        for b in C.CURRICULA:
            if a < b:
                assert got[a] != got[b], (a, b)


def test_the_kg_arms_change_symbols_and_not_tree_shapes():
    """The load-bearing property of the whole experiment.

    Every bound value is chosen by *indexing* into a candidate set with the
    position the ordinary uniform draw already produced, so no extra randomness
    is consumed and the scene size, the coordinates and the question are the
    ones the baseline drew. If a tree shape moves, a score difference is a shape
    difference and nothing can be attributed to semantics.

    Two exceptions are named rather than hidden, and both are counted in
    ``notes/findings/2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-
    can-reach.md`` (3 of 2,148 episodes, +0.026% of nodes):

    * a **rejection loop whose acceptance test reads the symbols**.
      ``symbol_grounding`` redraws until its query identifies one object;
      constrained attributes collide more often, so the loop rejects more often
      and the accepted scene is a different size. Nothing about consuming the
      same random bits can prevent that — the stream is identical, the number of
      draws from it is not — and removing the collision would mean removing the
      constraint.
    * a lesson that spells a word into a ``Str`` field gets one graph node per
      character, so a longer word is a longer graph.

    ``symbol_grounding`` is therefore checked here at the seeds where it holds,
    and the general claim lives in the note with its measured exception rate.
    """
    lessons = [l for l in SOME if l != "few_shot_language_learning"]
    base = list(C.generate(lessons, n=4, seed0=0, curriculum="base"))
    for cur in [c for c in C.CURRICULA if c != "base"]:
        other = list(C.generate(lessons, n=4, seed0=0, curriculum=cur))
        assert len(base) == len(other)
        for a, b in zip(base, other):
            assert a.instance_id == b.instance_id
            assert a.graph.types == b.graph.types, (a.lesson_id, a.seed, cur)
            assert a.graph.parent == b.graph.parent, (a.lesson_id, a.seed, cur)


def test_a_kg_episode_is_a_pure_function_of_its_address():
    for cur in [c for c in C.CURRICULA if c != "base"]:
        a = [ep.to_dict() for ep in C.generate(SOME, n=3, seed0=5, curriculum=cur)]
        b = [ep.to_dict() for ep in C.generate(SOME, n=3, seed0=5, curriculum=cur)]
        assert a == b


def test_an_unknown_curriculum_is_refused_rather_than_ignored():
    with pytest.raises((ValueError, KeyError)):
        list(C.generate(SOME[:1], n=1, curriculum="kg:does-not-exist"))
    with pytest.raises(KeyError):
        load("does-not-exist")


# ------------------------------------------------------------- the binding
def test_the_binder_is_inert_when_nothing_activates_it():
    """The property that lets a hook live inside the vendored generator."""
    from symbolic_ai_data.generators.base import COLORS, SHAPES
    assert list(COLORS) == ["red", "blue", "green", "yellow", "purple", "orange"]
    assert list(SHAPES) == ["cube", "sphere", "cone", "prism", "disc", "rod"]


def test_a_bound_vocabulary_must_keep_its_length():
    """A vocabulary of a different length spends a different number of random
    bits and desynchronises every later draw in the episode."""
    from symbolic_ai_data.binding import SlotVocabulary, using

    class Wrong:
        def vocabulary(self, slot, default):
            return list(default) + ["extra"]

        def entity(self, o):
            return o

        def describe(self):
            return {}

    v = SlotVocabulary("color", ["a", "b"])
    with using(Wrong()):
        with pytest.raises(ValueError):
            list(v)


def test_two_objects_of_different_kinds_draw_from_different_candidate_sets():
    """The edge that makes this a dependency DAG rather than a vocabulary swap.

    Asserted on the binder rather than on an episode, because an episode can
    fail to contain two kinds and then the property is vacuously true.
    """
    kg = load("wordnet")
    b = KGBinder(kg, "symbol_grounding", 0)
    colours = b.vocabulary("color", ["c"] * 6)
    kinds = b.vocabulary("shape", ["s"] * 6)
    sets = []
    for k in kinds:
        lic = b._licensed.get(k) or ()
        sets.append(frozenset(c for c in colours if c in lic))
    assert any(a != c for a in sets for c in sets), sets


def test_the_binder_reports_where_it_fell_back():
    """"I had nothing to say" and "here is a constrained draw" must not be the
    same output — the mechanism
    ``notes/lessons/2026-08-14-no-information-is-not-negative-evidence.md``
    is about, one layer down."""
    kg = load("wordnet")
    b = KGBinder(kg, "pronoun_coreference", 0)
    b.vocabulary("name", ["alice"] * 6)
    b.vocabulary("shape", ["cube"] * 6)
    d = b.describe()
    assert d["slots_fallback"].get("name") == 1
    assert "shape" not in d["slots_fallback"]


def test_no_model_can_read_the_knowledge_graph():
    """The leak guard, and the reason the renaming column is sufficient here.

    The decision note's third refutation condition is that the graph *leaks the
    answer* — a model recovers the graph and the "semantic" win is lookup. The
    guard it names is that a winner must still win when the symbols are permuted
    **and the graph permuted with them**.

    That guard is already the ordinary renaming column, but only while the graph
    is write-only: it shapes the corpus at generation time and no model consults
    it at train or test time, so permuting the symbols *is* permuting the graph
    as far as any model can tell. The moment a model imports
    ``symbolic_ai_kg``, that stops being true and the renaming column stops
    covering the leak — silently, because nothing about the numbers would look
    different.

    So assert the premise rather than trusting it. If this test fails, the
    equivariance column no longer answers the leak question and a separate
    permute-the-graph-with-the-symbols control has to be built.
    """
    import ast
    import pathlib
    import symbolic_ai_models
    root = pathlib.Path(symbolic_ai_models.__file__).resolve().parent
    offenders = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom)
                     else [])
            if any(n.split(".")[0] == "symbolic_ai_kg" for n in names):
                offenders.append(path.name)
    assert not offenders, (
        f"{sorted(set(offenders))} import symbolic_ai_kg. A model that can read "
        f"the graph can memorise it, and the renaming column no longer answers "
        f"the leak question -- see this test's docstring.")


def test_the_pools_are_not_empty():
    """A pool that came out empty would send every slot to its fallback and the
    treatment would silently be the baseline."""
    for name in KG_NAMES:
        P = pools_for(load(name))
        for key in ("families", "dimensions", "persons", "places", "artifacts"):
            assert P[key], (name, key)
