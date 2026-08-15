"""The infilling ladder: a bigger hole, a shaped hole, and the answer's hole.

Four properties are asserted here and every one of them could fail.

**The scattered regime is frozen.** Every published number in this repo was
measured under ``mask_mode="scatter"`` at 0.15, and the whole point of adding
other regimes beside it is that none of those numbers moves.
``test_the_scattered_draw_is_frozen`` hashes the entire batch — inputs, targets,
pointer bookkeeping and the relation matrix — at four rates against a constant
that was checked against ``git show HEAD:symbolic_ai_core/data/batch.py`` before
being written down. It fails on any change to what scattered masking hides.

**No information is not negative evidence.** In ``answer`` mode an episode whose
answer is nowhere in its graph has *nothing to ask*, and the collator's "always
ask at least one question" fallback must not fire there — a random node
substituted for an absent answer makes silence look exactly like a question. See
``notes/lessons/2026-08-14-no-information-is-not-negative-evidence.md``.

**The floor faces the model's regime.** The floor draws its own masks so that it
is what a structure-only lookup gets *given what a model is given*. That is only
true while the two draw the same way. In ``answer`` mode the draw is
deterministic, so the two sets can be compared directly rather than argued about.

**The subtree manipulation manipulates something.** A first version drew
candidate subtrees uniformly and, because these terms are bushy, picked a leaf
almost every time: mean hidden run 1.6 nodes against scattered masking's 1.2,
which is not "a constituent instead of scattered nodes" in any useful sense.
``test_a_subtree_hole_is_much_larger_than_a_scattered_one`` fails on that
version.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from symbolic_ai_core.data.batch import (answer_nodes, choose_hidden,
                                         collate_graph)
from symbolic_ai_core.data.curriculum import generate, resolve_lessons
from symbolic_ai_core.data.tokenizer import SymbolTokenizer
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.models.base import FitContext
from symbolic_ai_models.tasks import GRAPH_TASKS, TASKS, make_task
from symbolic_ai_models.train import TrainConfig, build_tokenizer

RATES = (0.15, 0.35, 0.60, 0.90)

#: The 40 lessons the frozen fingerprint is computed over. Registry order, not a
#: hand-picked set: a fixture chosen for its content is how
#: ``test_encoding_is_lossless`` passed for months while the tokenizer deleted
#: underscores.
FROZEN_LESSONS = 40

#: blake2b-128 over ``tokens``, ``types``, both target arrays, ``target_source``,
#: ``label_group`` and ``rel`` for 80 episodes at each of the four rates.
#: Recorded after checking it equal to the same hash computed from
#: ``git show 8f7c167:symbolic_ai_core/data/batch.py`` — the branch point, whose
#: version of this file is a732588's, the last commit to touch it before the
#: infilling ladder. Equal at all four rates, so the scattered collator in the
#: working tree is the one every published number was measured with.
FROZEN_SCATTER = "13cc5663486ee2f6f224ba5fc7dad539"


def _tokenizer(episodes) -> SymbolTokenizer:
    tok = SymbolTokenizer.build((e.text for e in episodes), max_vocab=2048)
    for ep in episodes:
        for label in ep.graph.labels:
            if label and label not in tok.stoi:
                tok.stoi[label] = len(tok.itos)
                tok.itos.append(label)
    return tok


@pytest.fixture(scope="module")
def frozen():
    lessons = resolve_lessons("all")[:FROZEN_LESSONS]
    eps = [ep for lid in lessons for ep in generate([lid], n=2, seed0=1_000_000)]
    return eps, _tokenizer(eps)


@pytest.fixture(scope="module")
def episodes():
    lessons = ["unification", "symbol_grounding", "center_embedding",
               "color_terms", "spatial_reasoning"]
    lessons = [L for L in lessons if L in set(resolve_lessons("all"))]
    train = list(generate(lessons, n=6))
    ev = list(generate(lessons, n=4, seed0=1_000_000))
    return train, ev, build_tokenizer(TrainConfig(vocab_size=1500), train)


def test_the_scattered_draw_is_frozen(frozen):
    """Nothing that has ever been published may move. This is the whole claim."""
    eps, tok = frozen
    h = hashlib.blake2b(digest_size=16)
    for rate in RATES:
        b = collate_graph(eps, tok, max_nodes=128, mask_rate=rate,
                          rng=np.random.default_rng(2026))
        for t in (b.tokens, b.types, b.target_tokens, b.target_types,
                  b.target_source, b.label_group, b.rel):
            h.update(np.ascontiguousarray(t.numpy()).tobytes())
    assert h.hexdigest() == FROZEN_SCATTER, (
        "the scattered masking regime changed. Every number in RESEARCH_LOG.md "
        "was measured under it; if the change is intended, it needs a new mask "
        "mode beside this one and not an edit to it.")


def test_the_default_mask_mode_is_scatter(frozen):
    eps, tok = frozen
    a = collate_graph(eps[:8], tok, rng=np.random.default_rng(3))
    b = collate_graph(eps[:8], tok, rng=np.random.default_rng(3),
                      mask_mode="scatter")
    assert bool((a.tokens == b.tokens).all())
    assert bool((a.target_tokens == b.target_tokens).all())


def test_an_unknown_mask_mode_is_an_error(frozen):
    eps, tok = frozen
    with pytest.raises(ValueError):
        choose_hidden(eps[0].graph, 8, np.random.default_rng(0), mode="sideways")


# ---------------------------------------------------------------------------
# answer mode
# ---------------------------------------------------------------------------
def test_an_episode_whose_answer_is_absent_is_unscored_rather_than_asked(frozen):
    """The fallback that invents a question must not fire where there is none."""
    eps, tok = frozen
    absent = [ep for ep in eps
              if not answer_nodes(ep.graph, min(len(ep.graph), 128), ep.answer)]
    assert absent, "expected some episodes whose answer is not a node label"
    batch = collate_graph(absent, tok, max_nodes=128, mask_mode="answer",
                          rng=np.random.default_rng(0))
    assert int((batch.target_types != -100).sum()) == 0
    assert int((batch.target_tokens != -100).sum()) == 0
    assert batch.meta["n_masked"] == 0


def test_every_answer_mode_target_is_the_answer_or_under_it(frozen):
    eps, tok = frozen
    present = [ep for ep in eps
               if answer_nodes(ep.graph, min(len(ep.graph), 128), ep.answer)]
    assert present
    batch = collate_graph(present, tok, max_nodes=128, mask_mode="answer",
                          rng=np.random.default_rng(0))
    assert int((batch.target_types != -100).sum()) > 0
    for b, ep in enumerate(present):
        n = min(len(ep.graph), 128)
        roots = set(answer_nodes(ep.graph, n, ep.answer))
        assert roots == set(batch.meta["answer_nodes"][b])
        for i in range(n):
            if int(batch.target_types[b, i]) == -100:
                continue
            # every masked position is an answer node or a descendant of one
            j, seen = i, 0
            while j not in roots and 0 <= ep.graph.parent[j] < n and seen < n:
                j = ep.graph.parent[j]
                seen += 1
            assert j in roots


def test_answer_one_leaves_the_other_copies_visible(frozen):
    """`nodeans`'s control has to actually leave the copy route open.

    `answer` hides every node carrying the answer, so a pointer — which emits
    the label of a *visible* node — cannot answer it at all, and a zero from one
    is a fact about the design. `answer_one` hides the first occurrence only.
    """
    eps, tok = frozen
    multi = [ep for ep in eps
             if len(answer_nodes(ep.graph, min(len(ep.graph), 128), ep.answer)) > 1]
    assert multi, "expected episodes whose answer appears on several nodes"
    rng = np.random.default_rng(0)
    for ep in multi:
        n = min(len(ep.graph), 128)
        roots = answer_nodes(ep.graph, n, ep.answer)
        hidden = set(int(i) for i in
                     choose_hidden(ep.graph, n, rng, mode="answer_one",
                                   answer=ep.answer))
        assert roots[0] in hidden
        assert all(r not in hidden for r in roots[1:])

    batch = collate_graph(multi, tok, max_nodes=128, mask_mode="answer_one",
                          rng=np.random.default_rng(0))
    # a visible node carries the answer, so the pointer target exists
    assert int((batch.target_source != -100).sum()) > 0


def test_the_floor_hides_exactly_what_the_batch_hides_in_answer_mode(episodes):
    """The floor is only a floor while it faces the model's masking regime.

    ``answer`` masking is deterministic, so this compares the two sets outright
    instead of comparing the rule that produces them.
    """
    _, ev, tok = episodes
    task = make_task("nodeans", mask_rate=0.15, max_nodes=128)
    batch = collate_graph(ev, tok, max_nodes=128, mask_mode="answer",
                          rng=np.random.default_rng(0))
    for b, ep in enumerate(ev):
        n = min(len(ep.graph), 128)
        from_batch = {i for i in range(n)
                      if int(batch.target_types[b, i]) != -100}
        from_floor = task._hidden(ep, n, np.random.default_rng(0))
        assert from_batch == from_floor


def test_the_answer_floor_is_restricted_and_absent_from_node_runs(episodes):
    train, ev, tok = episodes
    ans = make_task("nodeans", mask_rate=0.15, max_nodes=128).floor(ev, tok, train)
    node = make_task("node", mask_rate=0.15, max_nodes=128).floor(ev, tok, train)
    assert "ansnode_acc" not in node, (
        "a `node` run must not grow keys it never had; every published summary "
        "carrying that name would silently gain a column")
    if "ansnode_n" in ans:                     # this fixture covers some answers
        assert ans["ansnode_n"] <= ans["label_n"]


# ---------------------------------------------------------------------------
# subtree mode
# ---------------------------------------------------------------------------
def _pieces(g, n, hidden: set[int]) -> int:
    """How many separate holes: a hidden node whose parent is not hidden."""
    return sum(1 for i in hidden
               if not (0 <= g.parent[i] < n and g.parent[i] in hidden))


def test_a_subtree_draw_is_closed_downward(frozen):
    eps, _ = frozen
    rng = np.random.default_rng(11)
    checked = 0
    for ep in eps:
        g = ep.graph
        n = min(len(g), 128)
        if n < 4:
            continue
        hidden = set(int(i) for i in
                     choose_hidden(g, n, rng, mask_rate=0.35, mode="subtree"))
        for i in range(n):
            p = g.parent[i]
            if 0 <= p < n and p in hidden:
                assert i in hidden, "a hidden node has a visible child"
        checked += 1
    assert checked > 10


def test_subtree_masking_keeps_the_scattered_budget(frozen):
    """Matched budget is what makes the two regimes comparable at all."""
    eps, _ = frozen
    for rate in RATES:
        frac = {}
        for mode in ("scatter", "subtree"):
            rng = np.random.default_rng(5)
            hid = tot = 0
            for ep in eps:
                n = min(len(ep.graph), 128)
                if not n:
                    continue
                hid += len(choose_hidden(ep.graph, n, rng, mask_rate=rate,
                                         mode=mode))
                tot += n
            frac[mode] = hid / tot
        assert abs(frac["subtree"] - frac["scatter"]) < 0.03, (rate, frac)


def test_a_subtree_hole_is_much_larger_than_a_scattered_one(frozen):
    """The manipulation has to manipulate something.

    Fails on the uniform-candidate version of ``_subtree_hidden``, which reached
    only 1.37x because a uniform draw over a bushy term picks a leaf.
    """
    eps, _ = frozen
    size = {}
    for mode in ("scatter", "subtree"):
        rng = np.random.default_rng(5)
        hid = pieces = 0
        for ep in eps:
            n = min(len(ep.graph), 128)
            if not n:
                continue
            h = set(int(i) for i in
                    choose_hidden(ep.graph, n, rng, mask_rate=0.15, mode=mode))
            hid += len(h)
            pieces += _pieces(ep.graph, n, h)
        size[mode] = hid / max(pieces, 1)
    assert size["subtree"] > 1.8 * size["scatter"], size


# ---------------------------------------------------------------------------
# the fitting regime
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("task_name,rate,mode",
                         [("node", 0.60, "scatter"), ("nodesub", 0.35, "subtree"),
                          ("nodeans", 0.15, "answer"),
                          ("nodeans1", 0.15, "answer_one")])
def test_a_model_fits_under_the_regime_it_is_scored_under(episodes, task_name,
                                                          rate, mode):
    """``training_views`` promised this and delivered a hard-coded 0.15.

    Fails on the previous version for every row but the first, which is the
    point: a mask-rate curve read off models fitted at 0.15 measures transfer to
    an unseen regime and would have been reported as infilling at that rate.
    """
    train, _, tok = episodes
    task = make_task(task_name, mask_rate=rate, max_nodes=128)
    model = build("routes-001", ModelConfig(vocab_size=len(tok), max_nodes=128))
    model.fit(FitContext(episodes=train, tok=tok, tasks={task_name: task}))
    assert model.fit_mask_rate == pytest.approx(rate)
    assert model.fit_mask_mode == mode


def test_the_fitting_regime_can_be_forced_away_from_the_scoring_one(episodes):
    """The undertraining control needs a knob, and the knob must actually bite.

    `answer` masking hides about 1.2 nodes per episode where scattered masking
    at 0.15 hides about 10, so the matched regime gives a model roughly eight
    times less supervision. `extra.fit_mask_mode` fits under one regime and
    scores under another, which is what separates "cannot answer" from "was
    never shown enough to learn to".
    """
    train, _, tok = episodes
    task = make_task("nodeans", mask_rate=0.15, max_nodes=128)
    model = build("routes-001",
                  ModelConfig(vocab_size=len(tok), max_nodes=128,
                              extra={"fit_mask_mode": "scatter",
                                     "fit_mask_rate": 0.15}))
    model.fit(FitContext(episodes=train, tok=tok, tasks={"nodeans": task}))
    assert model.fit_mask_mode == "scatter"
    assert model.fit_mask_rate == pytest.approx(0.15)


def test_the_split_floor_pools_back_to_the_floor(episodes):
    """A second floor is a floor that drifts, so this one must not be a second.

    `split_floor` answers a different question — what a structure-only lookup
    gets on the copyable half and on the other — using the same rule, the same
    context ladder and the same masking draw. If it has become an independent
    implementation, its pooled number stops matching `floor()`'s, and that is
    the only cheap detector there is. It fails on any change to one and not the
    other.
    """
    train, ev, tok = episodes
    task = make_task("node", mask_rate=0.15, max_nodes=128)
    pooled = task.split_floor(ev, tok, train)
    assert pooled["floor_pooled"] == pytest.approx(
        task.floor(ev, tok, train)["label_acc"], abs=1e-12)
    assert pooled["n_copyable"] + pooled["n_not_copyable"] > 0


def test_every_graph_task_is_registered_and_named(episodes):
    assert set(GRAPH_TASKS) <= set(TASKS)
    for name in GRAPH_TASKS:
        assert make_task(name, mask_rate=0.15, max_nodes=128).name == name
