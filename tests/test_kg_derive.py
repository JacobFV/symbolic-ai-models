"""Guards for the derivability arms, ordered by what they would catch, worst first.

The worst thing that could happen here is the thing that happened last time: an
arm and a control that are **the same experiment twice**, producing a null no
artefact can distinguish from no experiment at all. See
``notes/lessons/2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control.md``.
So the first test in this file is not a smoke test, it is the claim itself:

1. **The treatment carries a channel the control does not.** The value is a
   deterministic function of the kind *across episodes* in ``derive:wordnet``
   and independent of it in ``derive:wordnet-perm``, stated as mutual
   information over a corpus. A mechanism that is present and inert looks
   exactly like one that is working, and only an assertion of the claim
   separates them —
   ``notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property.md``.
2. **The arms are matched in everything else.** Same tree shapes, same
   vocabulary, same value multiset per episode, same collision structure and
   therefore the same copyable share. A control that moved the bucket would make
   ``acc | not copyable`` a comparison of two populations rather than of two
   models —
   ``notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md``.
3. **The derivation actually fires**, on every scene object rather than on a
   flattering subset.
4. **The base curriculum did not move**, and each arm has its own fingerprint.
"""

from __future__ import annotations

import collections
import math

import pytest

from symbolic_ai_core.data import curriculum as C
from symbolic_ai_core.data import fingerprint as F
from symbolic_ai_kg import load
from symbolic_ai_kg.derive import DeriveBinder, anchor_map

DERIVE_ARMS = ("derive:wordnet", "derive:wordnet-perm", "derive:wordnet-shuffled")

# Lessons that put a scene object into the term. Named rather than discovered so
# the test costs seconds; nothing here reports a score, so a fixture is
# legitimate — see
# ``notes/lessons/2026-08-13-slices-have-inverted-results-eight-times.md``.
SCENE = ["symbol_grounding", "counting_quantifier", "negation",
         "compositional_reference", "symbol_equivalence"]


def _pairs(curriculum: str, lessons=SCENE, n: int = 6):
    """``kind -> Counter(value)`` over a corpus, read from the binder itself."""
    make = C._binder_factory(curriculum)
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for lid in lessons:
        for s in range(n):
            b = make(lid, s)
            for k in b.kinds:
                out[k][b.value_for(k)] += 1
    return out


def _mutual_information(pairs) -> float:
    """``I(kind; value)`` in bits over the corpus-wide joint the binder induces."""
    total = sum(sum(c.values()) for c in pairs.values())
    pk = {k: sum(c.values()) / total for k, c in pairs.items()}
    pv: dict[str, float] = collections.defaultdict(float)
    for c in pairs.values():
        for v, n in c.items():
            pv[v] += n / total
    mi = 0.0
    for k, c in pairs.items():
        for v, n in c.items():
            p = n / total
            mi += p * math.log2(p / (pk[k] * pv[v]))
    return mi


# ------------------------------------------------- the claim, asserted
def test_the_treatment_carries_a_channel_the_control_does_not():
    """The whole experiment in one assertion.

    ``derive:wordnet`` states one bijection over and over, so knowing an
    object's kind determines its value and ``I(kind; value)`` is
    ``log2(6) = 2.585`` bits. ``derive:wordnet-perm`` re-draws the assignment
    every episode, so the same corpus carries **no** cross-episode information
    and a learner with the treatment's map scores 1/6 here.

    If this ever ties, the two arms are one problem relabelled and every number
    drawn on them is a null by construction — which is exactly what the previous
    semantic-constraint line produced, and what nothing in it could have caught.
    """
    treat = _mutual_information(_pairs("derive:wordnet"))
    control = _mutual_information(_pairs("derive:wordnet-perm"))
    assert treat == pytest.approx(math.log2(6), abs=1e-9), treat
    assert control < 0.35, (
        f"the control carries {control:.3f} bits of kind->value information; "
        "it is supposed to carry none, and a control that carries the "
        "treatment's channel cannot fail")
    assert treat - control > 2.0


def test_the_scrambled_arm_is_also_a_fixed_map_which_is_why_it_is_predicted_to_tie():
    """Recorded as a property, not as a hope.

    ``derive:wordnet-shuffled`` states a *different* bijection just as
    consistently, so it carries the same 2.585 bits. That is the argument for
    predicting it to tie with the treatment for any learner whose only input is
    this corpus, and it is why it is run as a check of an argument rather than as
    a load-bearing control.
    """
    got = _mutual_information(_pairs("derive:wordnet-shuffled"))
    assert got == pytest.approx(math.log2(6), abs=1e-9)


# ------------------------------------------------- the map
def test_the_map_is_a_bijection_and_the_control_shares_its_anchor_set():
    kinds, values = anchor_map(load("wordnet"))
    assert len(kinds) == len(set(kinds)) == 6
    assert len(values) == len(set(values)) == 6
    assert not set(kinds) & set(values)
    for arm in DERIVE_ARMS:
        b = C._binder_factory(arm)("symbol_grounding", 0)
        assert b.kinds == kinds, (
            f"{arm} anchors a different kind set; the control would then differ "
            "from its treatment in vocabulary as well as in correspondence")


def test_the_scramble_changes_the_values_and_not_the_kinds():
    a = C._binder_factory("derive:wordnet")("symbol_grounding", 0)
    b = C._binder_factory("derive:wordnet-shuffled")("symbol_grounding", 0)
    assert a.kinds == b.kinds
    assert set(a.values) != set(b.values)


def test_the_map_is_read_off_a_real_edge_of_the_graph():
    """Not written down here. Every pair is an edge the vendored graph states."""
    kg = load("wordnet")
    kinds, values = anchor_map(kg)
    by_word: dict[str, list[int]] = collections.defaultdict(list)
    for n in range(len(kg)):
        by_word[kg.word(n)].append(n)
    for k, v in zip(kinds, values):
        assert any(kg.word(t) == v
                   for n in by_word[k] for t in kg.out("part", n)), (k, v)


# ------------------------------------------------- the arms are matched
def test_the_arms_have_the_same_tree_shapes():
    """A score difference between the arms has to be about symbols.

    Unlike the ``kg:`` arms, this holds with **no** exceptions: the value slot's
    collision structure is the kind slot's in every arm, so a rejection loop that
    reads the symbols accepts or rejects identically. Measured at 0 of 1,432
    episodes over 179 lessons x 8 seeds.
    """
    ref = list(C.generate(SCENE, n=4, seed0=0, curriculum="derive:wordnet"))
    for arm in DERIVE_ARMS[1:]:
        other = list(C.generate(SCENE, n=4, seed0=0, curriculum=arm))
        assert len(ref) == len(other)
        for a, b in zip(ref, other):
            assert a.instance_id == b.instance_id
            assert a.graph.types == b.graph.types, (a.lesson_id, a.seed, arm)
            assert a.graph.parent == b.graph.parent, (a.lesson_id, a.seed, arm)


def test_the_arms_hand_out_the_same_vocabulary():
    """``derive`` and ``derive-perm`` differ in the assignment and in nothing
    else: same six kinds, same six values, same order, so an episode's lexicon is
    identical and only which value goes with which kind moves."""
    a = C._binder_factory("derive:wordnet")("symbol_grounding", 3)
    b = C._binder_factory("derive:wordnet-perm")("symbol_grounding", 3)
    assert a.vocabulary("shape", ["x"] * 6) == b.vocabulary("shape", ["x"] * 6)
    assert a.vocabulary("color", ["x"] * 6) == b.vocabulary("color", ["x"] * 6)


def test_the_control_preserves_the_collision_structure_of_the_treatment():
    """Two objects share a value iff they share a kind, in **both** arms.

    A bijection composed with a permutation is a bijection. This is what keeps
    the copyable share — the denominator of every ``acc | not copyable`` number —
    from differing between treatment and control, and a difference there would
    have made the comparison one between two buckets rather than two models.
    """
    kinds, values = anchor_map(load("wordnet"))
    scene = [{"id": f"o{i}", "color": "red", "shape": k}
             for i, k in enumerate(["ship", "ship", "shoe", "body", "shoe",
                                    "auto"])]
    for permute in (False, True):
        for seed in range(6):
            b = DeriveBinder(kinds=kinds, values=values, lesson_id="x",
                             seed=seed, permute=permute, graph="wordnet")
            got = [b.entity(o)["color"] for o in scene]
            for i, oi in enumerate(scene):
                for j, oj in enumerate(scene):
                    assert (got[i] == got[j]) == (oi["shape"] == oj["shape"])


def test_the_arms_score_the_same_derived_positions():
    """The measured version of the test above, on real episodes.

    ``acc | derived, not copyable`` is read per arm and subtracted, so if the
    arms score slightly different populations the difference is partly a bucket
    difference —
    ``notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md``.

    They *do* differ before the intersection, and the mechanism is worth more
    than the number: ``compositional_reference`` redraws colours in a rejection
    loop **after** ``bind_scene`` has run, so on some episodes an object's value
    is a fresh uniform draw and which objects survive depends on the arm — 114
    positions against 112 here. ``matched_episodes`` intersects over the arms,
    which is what this asserts.
    """
    from scripts.derived_split import matched_episodes
    share = {}
    for arm in DERIVE_ARMS:
        rows = matched_episodes(arm, DERIVE_ARMS, SCENE, n=6, seed0=0,
                                max_nodes=128)
        uniq = tot = 0
        for ep, pos in rows:
            g = ep.graph
            for vi, _ki in pos:
                tot += 1
                uniq += sum(1 for j in range(len(g))
                            if g.labels[j] == g.labels[vi]) == 1
        share[arm] = (uniq, tot, [(e.lesson_id, e.seed, tuple(sorted(v for v, _ in p)))
                                  for e, p in rows])
    ref = share["derive:wordnet"]
    assert ref[1] > 0
    for arm, got in share.items():
        assert got[2] == ref[2], arm      # the very same positions, episode by episode
        assert abs(got[0] / got[1] - ref[0] / ref[1]) < 0.05, \
            {a: (v[0], v[1]) for a, v in share.items()}


# ------------------------------------------------- the derivation fires
def test_every_scene_object_is_derived_rather_than_a_flattering_subset():
    """The ``kg:`` binder fired on 53% of scene objects and reported it. This one
    fires on all of them, because the kind slot is itself the map's domain — and
    a binder that quietly fell back would be a treatment behaving like its
    baseline, which is
    ``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md``.
    """
    from symbolic_ai_data.binding import using
    make = C._binder_factory("derive:wordnet")
    seen = bound = 0
    for lid in SCENE:
        for s in range(6):
            b = make(lid, s)
            with using(b):
                C._lc().get(lid).structured(s)
            d = b.describe()
            seen += d["entities_seen"]
            bound += d["entities_bound"]
            assert not d["slots_fallback"], d
    assert seen > 0
    assert bound == seen, (bound, seen)


def test_the_derived_value_is_not_the_one_the_generator_drew():
    """A derivation that agreed with the uniform draw would be inert."""
    base = list(C.generate(SCENE, n=6, seed0=0, curriculum="base"))
    got = list(C.generate(SCENE, n=6, seed0=0, curriculum="derive:wordnet"))
    changed = sum(1 for a, b in zip(base, got) if a.prompt != b.prompt)
    assert changed >= len(base) // 2, (changed, len(base))


def test_a_bijection_is_required_of_the_map():
    with pytest.raises(ValueError):
        DeriveBinder(kinds=("a", "b"), values=("x", "x"), lesson_id="l", seed=0)
    with pytest.raises(ValueError):
        DeriveBinder(kinds=("a", "a"), values=("x", "y"), lesson_id="l", seed=0)
    with pytest.raises(ValueError):
        DeriveBinder(kinds=("a", "b"), values=("x",), lesson_id="l", seed=0)


# ------------------------------------------------- nothing else moved
def test_the_base_curriculum_did_not_move():
    """Rule 1: a new curriculum goes beside the old one. If this fails the guard
    is working — fix the binder, never the golden file."""
    golden = F.load_golden()
    got = F.curriculum_fingerprint(lessons=SCENE, languages=["english"])
    for lid in SCENE:
        assert golden["lessons"][lid]["raw"] == got["lessons"][lid]["raw"], lid
        assert (golden["lessons"][lid]["text"]["english"]
                == got["lessons"][lid]["text"]["english"]), lid


@pytest.mark.parametrize("curriculum", DERIVE_ARMS)
def test_each_derive_curriculum_has_its_own_fingerprint(curriculum):
    path = F.golden_path_for(curriculum)
    assert path != F.GOLDEN_PATH
    golden = F.load_golden(path)
    got = F.curriculum_fingerprint(lessons=SCENE, languages=["english"],
                                   curriculum=curriculum)
    for lid in SCENE:
        assert golden["lessons"][lid]["raw"] == got["lessons"][lid]["raw"], lid


def test_a_derive_episode_is_a_pure_function_of_its_address():
    for arm in DERIVE_ARMS:
        a = [ep.to_dict() for ep in C.generate(SCENE, n=3, seed0=5, curriculum=arm)]
        b = [ep.to_dict() for ep in C.generate(SCENE, n=3, seed0=5, curriculum=arm)]
        assert a == b
