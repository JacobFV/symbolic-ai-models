"""The ``-004`` role embeddings: the claims, and the controls that could sink them.

``tests/test_vsa_perm.py`` pins the defect these models respond to — a role
built from a *product* of independent random atoms has an inner product of
``d +/- 0`` on an exact tuple match and ``4 +/- 60`` otherwise, a hard partition
with no middle. What is asserted here is the five things ``vsa_spec_004`` claims
and its predecessors do not:

* that the candidate score really is the role Gram, which is the identity every
  other claim in the module rests on;
* that **superposing** the same four atoms instead of binding them makes that
  Gram a graded count of agreeing coordinates — a back-off ladder in one vector;
* that the **heat-kernel signature** gives a graded Gram keyed on structural
  similarity rather than on graph proximity, and that the Laplacian eigenmap
  gives one keyed on proximity, which is the distinction the family turns on;
* that the **shuffled controls** preserve the Gram's entire value distribution
  exactly while destroying its correspondence with the graph;
* that a role never reads a label, so the family stays exactly equivariant.
"""

from __future__ import annotations

import collections
import math

import numpy as np
import pytest

from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_core.invariance import (build_renaming, label_accuracy,
                                         rename_episodes)
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]
VARIANTS = ["vsa_sum-004", "vsa_spec-004", "vsa_spec_shuf-004", "vsa_hks-004",
            "vsa_hks_shuf-004", "vsa_hks_sum-004", "vsa_hks_ll-004",
            "vsa_perm_hks-004", "vsa_null-004", "vsa_hks_wide-004",
            "vsa_spec_wide_pure-004", "vsa_spec_shuf16_pure-004"]


def cfg_for(tok):
    return ModelConfig(vocab_size=len(tok), max_len=160, max_nodes=128)


@pytest.fixture(scope="module")
def fixtures():
    train = list(generate(LESSONS, n=10))
    evaluation = list(generate(LESSONS, n=8, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1600), train)
    return train, evaluation, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    return cfg_for(fixtures[2])


def fit(name, fixtures, cfg):
    train, _, tok = fixtures
    model = build(name, cfg)
    model.fit_on(train, tok)
    return model


def big_views(model, episodes, tok, seed=3, least=16, take=8):
    views = [v for v, _ in model.training_views(episodes, tok, repeats=1,
                                                seed=seed, max_nodes=128)]
    return [v for v in views if len(v) >= least][:take]


def hop_distances(view) -> np.ndarray:
    """All-pairs shortest path over the tree's undirected edges, ``99`` if none."""
    n = len(view)
    adjacent = collections.defaultdict(list)
    for i, p in enumerate(view.parent):
        if 0 <= p < n and p != i:
            adjacent[i].append(p)
            adjacent[p].append(i)
    dist = np.full((n, n), 99, dtype=np.int64)
    for source in range(n):
        dist[source, source] = 0
        queue = collections.deque([source])
        while queue:
            u = queue.popleft()
            for v in adjacent[u]:
                if dist[source, v] == 99:
                    dist[source, v] = dist[source, u] + 1
                    queue.append(v)
    return dist


def gram(model, view) -> np.ndarray:
    roles = model._roles_for(view)
    return roles @ roles.T / model._d


# ---------------------------------------------------------------------------
# the identity every other claim rests on
# ---------------------------------------------------------------------------
def test_the_candidate_score_is_the_role_gram(fixtures, cfg):
    """``score(s) = sum_{j: label_j = s} <role_i, role_j>``, to the crosstalk.

    This is why swapping the role construction and touching nothing else is a
    controlled experiment rather than a rewrite: every property of the retrieval
    is a property of that matrix. It holds because the codebook is bipolar, so
    ``cb[s] ** 2 == 1`` elementwise, and because a masked node's own binding is
    never in the trace. If either stopped being true the whole module's
    reasoning would be wrong, so it is checked rather than argued.
    """
    train, _, tok = fixtures
    model = fit("vsa_hks-004", fixtures, cfg)      # bipolar roles: least crosstalk
    checked = 0
    for view in big_views(model, train, tok):
        g = gram(model, view)
        trace = model._trace(view)
        for node in view.hidden:
            probe = model._probe(view, node, trace)
            sims, cands = model._similarities(probe, model._candidates(view))
            if sims is None:
                continue
            scale = float(np.linalg.norm(probe)) / np.sqrt(model._d)
            for wanted, actual in zip(cands, sims):
                predicted = sum(g[node, j] for j in range(len(view))
                                if view.labels[j] is not None
                                and int(view.labels[j]) == wanted)
                assert abs(actual * scale - predicted) < 0.3, (
                    "the candidate score is not the role Gram; the module's "
                    "entire argument depends on it being so")
                checked += 1
    assert checked > 50, "not enough candidates scored to mean anything"


# ---------------------------------------------------------------------------
# graded without a graph: superposition instead of binding
# ---------------------------------------------------------------------------
def test_superposing_the_atoms_counts_agreeing_coordinates(fixtures, cfg):
    """``vsa_sum-004``'s whole claim, in one assertion.

    ``role = ptype + slot + depth + arity`` gives
    ``<role_i, role_j> = d * (how many of the four agree)``, so a
    three-of-four match scores three quarters of an exact one where ``vsa-002``
    scored noise. That is the back-off ladder, expressed as a superposition.

    Refuted if the Gram were not a near-integer multiple of ``d / 4``, which is
    what a partition — or a construction that had quietly gone real-valued and
    lost the count — would produce.
    """
    train, _, tok = fixtures
    model = fit("vsa_sum-004", fixtures, cfg)
    pooled: dict[int, list[float]] = collections.defaultdict(list)
    for view in big_views(model, train, tok):
        g = gram(model, view)
        keys = [_atom_key(view, i) for i in range(len(view))]
        for i in range(len(view)):
            for j in range(len(view)):
                agree = sum(a == b for a, b in zip(keys[i], keys[j]))
                pooled[agree].append(float(g[i, j]) / 4.0)
    assert set(pooled) >= {1, 2, 3, 4}, "no graded pairs to check"
    for agree, values in sorted(pooled.items()):
        assert abs(np.mean(values) - agree / 4.0) < 0.06, (
            f"{agree}-of-4 agreement scored {np.mean(values):.3f}, not "
            f"{agree / 4:.3f}; the superposition is not counting coordinates")


def _atom_key(view, node) -> tuple:
    from symbolic_ai_core.data.term_graph import TYPE_TO_ID
    parent = view.parent[node]
    ptype = (view.types[parent] or "mask") if parent >= 0 else "ROOT"
    return (TYPE_TO_ID.get(ptype, 0) % 32, min(view.slot[node], 11),
            min(view.depth[node], 11), min(len(view.children(node)), 5))


# ---------------------------------------------------------------------------
# the two graph embeddings mean different things, and that is the finding
# ---------------------------------------------------------------------------
def test_the_eigenmap_scores_proximity_and_the_signature_scores_the_opposite(
        fixtures, cfg):
    """The distinction the family turns on, as a number rather than an argument.

    A diffusion kernel on the tree is a *locality* embedding: its Gram falls off
    with hop distance. A heat-kernel signature is a *structural* one — two nodes
    are alike when they sit in similar local structure, whether or not they are
    anywhere near each other — and on a term tree that comes out **anti**-correlated
    with distance, because a parent and its child are adjacent and structurally
    as different as two nodes get, while two leaves in different subtrees are far
    apart and structurally identical.

    That is the whole reason the eigenmap arm fails and the signature arm does
    not: the answer is never at hop 1 in this curriculum, and the eigenmap puts
    all its mass there. Refuted if the two constructions ordered pairs the same
    way, which would mean they were measuring the same thing after all.
    """
    train, _, tok = fixtures
    eigenmap = fit("vsa_spec-004", fixtures, cfg)
    eigenmap._knob, eigenmap._cache = 4.0, None
    signature = fit("vsa_hks-004", fixtures, cfg)
    views = big_views(eigenmap, train, tok)

    near, far = _by_hop(eigenmap, views)
    assert near - far > 0.3, (
        f"the eigenmap is meant to score proximity: hop1 {near:.3f}, "
        f"hop>=4 {far:.3f}")
    near, far = _by_hop(signature, views)
    assert far - near > 0.2, (
        f"the signature is meant to score structure, not proximity: "
        f"hop1 {near:.3f}, hop>=4 {far:.3f}")


def _by_hop(model, views) -> tuple[float, float]:
    one: list[float] = []
    away: list[float] = []
    for view in views:
        g = gram(model, view)
        dist = hop_distances(view)
        one.extend(g[dist == 1].tolist())
        away.extend(g[(dist >= 4) & (dist < 99)].tolist())
    return float(np.mean(one)), float(np.mean(away))


def _agreement(a_model, b_model, views) -> float:
    """Correlation of two models' Grams, entry by entry, off the diagonal.

    The construction-agnostic way to say "these two disagree about which pairs
    are alike". Correlating against hop distance instead does not work here: the
    signature's Gram is strongly *non-monotone* in distance, because a term tree
    alternates functor and argument levels and so pairs at even distances are
    structurally alike where pairs at odd distances are not. A summary that
    averaged over that parity would report a real, large effect as ``-0.096``.
    """
    left: list[float] = []
    right: list[float] = []
    for view in views:
        a, b = gram(a_model, view), gram(b_model, view)
        off = ~np.eye(len(view), dtype=bool)
        left.extend(a[off].tolist())
        right.extend(b[off].tolist())
    return float(np.corrcoef(left, right)[0, 1])


def test_the_diffusion_time_interpolates_partition_to_unigram(fixtures, cfg):
    """``t`` spans two named degenerate models, so a fitted value means something.

    At the bottom the eigenmap kernel is the identity — a partition *finer* than
    ``vsa-002``'s, under which nothing is ever retrieved, because a node's own
    binding is the one thing never in the trace. At the top it is all-ones —
    every node has the same role and the cleanup is an episode unigram.
    """
    train, _, tok = fixtures
    model = fit("vsa_spec-004", fixtures, cfg)
    views = big_views(model, train, tok)
    low, high = {}, {}
    for target, knob in ((low, 0.25), (high, 64.0)):
        model._knob, model._cache = knob, None
        pooled: dict[int, list[float]] = collections.defaultdict(list)
        for view in views:
            g = gram(model, view)
            dist = hop_distances(view)
            for hop in range(5):
                if (dist == hop).any():
                    pooled[hop].extend(g[dist == hop].tolist())
        target.update({h: float(np.mean(v)) for h, v in pooled.items()})
    assert low[1] < 0.2, f"t=0.25 is meant to be near the identity: {low}"
    assert all(high[h] > 0.95 for h in range(4)), (
        f"t=64 is meant to be near all-ones: {high}")


# ---------------------------------------------------------------------------
# the controls
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("plain,shuffled",
                         [("vsa_spec-004", "vsa_spec_shuf-004"),
                          ("vsa_hks-004", "vsa_hks_shuf-004")])
def test_shuffling_keeps_every_gram_value_and_loses_the_correspondence(
        fixtures, cfg, plain, shuffled):
    """What makes these controls controls and not different models.

    Permuting the feature rows permutes the Gram, so the multiset of pairwise
    similarities is **bit-identical** — same values, same effective softmax
    sharpness, same statistics reaching the gate. Only the attachment between a
    coordinate and the node it describes is destroyed. If the sorted values
    stopped matching, the control would be confounded with a change in the score
    distribution and a null from it would mean nothing.
    """
    train, _, tok = fixtures
    treatment = fit(plain, fixtures, cfg)
    control = fit(shuffled, fixtures, cfg)
    control._knob, control._cache = treatment._knob, None   # one knob, not two

    views = big_views(treatment, train, tok, seed=5)
    moved = 0
    for view in views:
        a, b = gram(treatment, view), gram(control, view)
        assert np.allclose(np.sort(a, axis=None), np.sort(b, axis=None)), (
            "the shuffle changed the distribution of similarities, so it is "
            "not a control for the embedding alone")
        if not np.array_equal(a, b):
            moved += 1
    assert moved, "the shuffle was a no-op on every graph"

    assert _agreement(treatment, treatment, views) > 0.99, "sanity"
    overlap = _agreement(treatment, control, views)
    assert abs(overlap) < 0.15, (
        f"{shuffled} still says the same thing as {plain} about which pairs "
        f"are alike (r = {overlap:+.3f}); it is not destroying the "
        "correspondence it is meant to destroy")


def test_the_multiset_property_belongs_to_a_shared_bandwidth_not_to_the_shuffle(
        fixtures, cfg):
    """Added by an independent refuter, 2026-08-14.

    The test above overwrites the control's fitted knob with the treatment's
    (``control._knob = treatment._knob``) before comparing, so what it asserts is
    that *permuting rows permutes the Gram* — true by arithmetic, for any
    bandwidth. It cannot see the case that actually occurred in
    ``runs/vsa_role``: **``vsa_spec-004`` fitted ``t = 16`` and
    ``vsa_spec_shuf-004`` refitted to ``t = 1``**, two different kernels, so for
    the published eigenmap pair the "bit-identical value multiset" property — the
    whole reason a shuffle is a control and not a different model — is false as
    run. (``vsa_hks-004`` and ``vsa_hks_shuf-004`` both fitted 0.5, so the pair
    the finding leans on is genuinely matched. That was luck, not construction.)

    This pins both halves: that the property fails at the knobs the sweep chose,
    and that ``vsa_spec_shuf16_pure-004`` restores it by pinning the grid.
    """
    train, _, tok = fixtures
    treatment = fit("vsa_spec-004", fixtures, cfg)
    drifted = fit("vsa_spec_shuf-004", fixtures, cfg)
    views = big_views(treatment, train, tok, seed=5)

    treatment._knob, treatment._cache = 16.0, None   # what the sweep fitted
    drifted._knob, drifted._cache = 1.0, None        # what the control fitted
    moved = sum(not np.allclose(np.sort(gram(treatment, v), axis=None),
                                np.sort(gram(drifted, v), axis=None))
                for v in views)
    assert moved == len(views), (
        "the published eigenmap pair fitted different bandwidths; if their Gram "
        "multisets now agree anyway, the knob has stopped reaching the kernel "
        "and something else is wrong")

    matched = fit("vsa_spec_shuf16_pure-004", fixtures, cfg)
    assert matched.knob_grid == (16.0,) and matched._knob == 16.0, (
        "the matched control exists to be unable to drift")
    treatment._cache = None
    for view in views:
        assert np.allclose(np.sort(gram(treatment, view), axis=None),
                           np.sort(gram(matched, view), axis=None)), (
            "vsa_spec_shuf16_pure-004 is meant to be the eigenmap's control "
            "with the value multiset preserved exactly")


def test_the_null_row_has_no_gradedness_and_no_correspondence(fixtures, cfg):
    """Added by an independent refuter, 2026-08-14: the family's missing bottom.

    The finding note reads ``vsa_hks_shuf_pure-004``'s -0.071 as "the gradedness
    of the Gram contributes nothing on its own". Nothing in the family measured
    what *nothing* scores, so there was no row for "contributes nothing" to be
    compared against — and a shuffled signature does not merely fail to help, it
    asserts gradedly and confidently that unrelated nodes are alike.
    ``vsa_null-004`` is the reference: i.i.d. bipolar roles, every off-diagonal
    Gram entry ``0 +/- 1/sqrt(d)``, no gradedness and no correspondence.

    Refuted if the null Gram turned out to carry structure — which is what would
    happen if the seeding accidentally keyed on something about the node.
    """
    train, _, tok = fixtures
    model = fit("vsa_null-004", fixtures, cfg)
    views = big_views(model, train, tok, seed=5)
    off_diagonal: list[float] = []
    for view in views:
        g = gram(model, view)
        off_diagonal.extend(g[~np.eye(len(view), dtype=bool)].tolist())
    assert max(abs(v) for v in off_diagonal) < 8.0 / math.sqrt(model._d), (
        "the null roles are not orthogonal; this row is not a null")
    signature = fit("vsa_hks-004", fixtures, cfg)
    assert abs(_agreement(model, signature, views)) < 0.05, (
        "the null row agrees with the signature about which pairs are alike")


def test_the_shuffle_is_the_same_permutation_every_time_it_is_asked(fixtures, cfg):
    """A control that reshuffles between fitting and prediction measures nothing.

    The permutation is drawn from the model seed and an FNV digest of the
    graph's own shape, so it is a deterministic function of the view. Python's
    ``hash`` would not do: it is salted per process for some types and is not
    promised to be stable, and a control whose model changed between the fit and
    the sweep would fail silently and flatteringly.
    """
    train, _, tok = fixtures
    model = fit("vsa_hks_shuf-004", fixtures, cfg)
    for view, _ in model.training_views(train, tok, repeats=1, seed=7,
                                        max_nodes=128):
        first = model._roles_for(view).copy()
        model._cache = None
        assert np.array_equal(first, model._roles_for(view))


# ---------------------------------------------------------------------------
# what a role is not allowed to read
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["vsa_spec-004", "vsa_hks-004", "vsa_sum-004"])
def test_a_role_is_a_function_of_the_tree_and_of_nothing_else(fixtures, cfg, name):
    """Overwrite every label and the roles must not move by one sign.

    This is the mechanism behind the equivariance claim, checked per node rather
    than on average, and it is stronger than a renaming score: it says the
    embedding could not read symbol identity even if the arithmetic downstream
    wanted it to.
    """
    train, _, tok = fixtures
    model = fit(name, fixtures, cfg)
    for view in big_views(model, train, tok):
        before = model._roles_for(view).copy()
        view.labels = [None if v is None else 0 for v in view.labels]
        model._cache = None
        assert np.array_equal(before, model._roles_for(view)), (
            f"{name}: a role changed when the labels did")


@pytest.mark.parametrize("name", ["vsa_sum_pure-004", "vsa_spec_pure-004",
                                  "vsa_hks_pure-004", "vsa_hks_shuf_pure-004",
                                  "vsa_perm_hks_pure-004"])
def test_the_embedding_family_is_exactly_equivariant(name):
    """Renaming must cost these models nothing, with the shared floor off.

    The sample is deliberately larger than the module fixture. The same check on
    24 episodes reported the *permutation* family at a +0.051 drop that turned
    out to be sampling noise — see
    ``test_vsa_perm.py::test_the_reaching_family_is_still_equivariant`` for the
    table. A small renaming sample has produced a confident wrong sign in this
    repo before.

    ``vsa_hks_ll-004`` is **deliberately absent** from this list. Fitting the
    softmax temperature flattens the cleanup, the gate hands most of the mass to
    the shared unigram back-off, and the model inherits that back-off's
    vocabulary dependence: it measures a +0.05 drop where every row here is at
    zero. That is the same finding as its accuracy collapse, seen from the other
    side, and it is reported rather than tested away.
    """
    train = list(generate(LESSONS, n=25))
    evaluation = list(generate(LESSONS, n=64, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1600), train)
    model = build(name, cfg_for(tok))
    model.fit_on(train, tok)
    renaming = build_renaming(evaluation, tok)
    assert len(renaming), "nothing to permute"
    kw = {"max_nodes": 128, "mask_rate": 0.15}
    plain = label_accuracy(model, evaluation, tok, **kw)
    renamed = label_accuracy(model, rename_episodes(evaluation, renaming), tok,
                             **kw)
    assert abs(plain - renamed) < 0.02, (
        f"{name} is not equivariant: {plain:.3f} -> {renamed:.3f}")


# ---------------------------------------------------------------------------
# the models exist, answer, and survive a round trip
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", VARIANTS)
def test_every_variant_answers_and_fits_inside_its_own_grid(fixtures, cfg, name):
    """A model that abstained everywhere would pass every claim above vacuously.

    **The grid check below is NOT a guard against a boundary optimum**, whatever
    an earlier version of this docstring said. ``_fit_scalars`` searches
    ``knob_grid`` and assigns from it, so ``model._knob in model.knob_grid`` is
    true by construction and can never fail — including when the fit pins to an
    endpoint, which is the case it was believed to catch. An independent refuter
    found all four registered heat-kernel rows fitted ``knob = 0.5``, the bottom
    of ``(0.5, 1, 2, 4)``, with this assertion passing the whole time; extended,
    the fit lands interior at 0.25 and the row gains +0.053 of label lift
    (``vsa_hks_wide-004``, ``notes/findings/2026-08-14-the-graph-roles-survive-
    the-attack-and-their-bandwidth-does-not.md``).

    The assertion is kept because it does catch a knob assigned from *outside*
    the grid, which is a different and real bug. The boundary check that would
    have caught the real defect is "extend the grid past the optimum and refit",
    and it cannot live in a unit test on three lessons — it is a registered row
    and a sweep. ``vsa_hks_wide-004`` and ``vsa_spec_wide_pure-004`` are those
    rows for this module.
    """
    train, evaluation, tok = fixtures
    model = fit(name, fixtures, cfg)
    voted = sum(1 for view, _ in model.training_views(evaluation, tok, repeats=1,
                                                      seed=13, max_nodes=128)
                for v, _ in model.node_votes(view).values() if v[0])
    assert voted > 0, f"{name} never voted on a label"
    assert model._knob in model.knob_grid, f"{name} fitted a knob off its grid"
    assert model.sharpness in model.sharpness_grid or not model.fit_sharpness


def test_the_projections_survive_a_save_and_reload_bit_identically(fixtures, cfg):
    """The role matrices are regenerated from the seed, so they have to regenerate.

    ``VSAModel.symbolic_state`` drops the codebook rather than pickle 177MB of
    regenerable noise, and this family drops two more such matrices — the
    bipolar ``R`` that projects the eigenmap and the Gaussian ``W`` that carries
    the random Fourier features. If any came back different, every published
    ``-004`` row would silently move, which is the failure that convention
    exists to prevent.
    """
    train, evaluation, tok = fixtures
    for name in ("vsa_spec-004", "vsa_hks-004"):
        model = fit(name, fixtures, cfg)
        clone = build(name, cfg)
        clone.load_symbolic_state(model.symbolic_state(), tok)
        assert clone._knob == model._knob and clone.n_eig == model.n_eig
        assert clone.sharpness == model.sharpness
        assert np.array_equal(clone.codebook, model.codebook)
        for view, _ in model.training_views(evaluation, tok, repeats=1, seed=17,
                                            max_nodes=128):
            assert np.array_equal(model._roles_for(view),
                                  clone._roles_for(view)), name
