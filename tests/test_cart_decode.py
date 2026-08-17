"""The CART arms' contract: the controls have to be controls.

Every reading of ``notes/findings/2026-08-16-infilling-errors-clump-but-do-not-cascade-and-cart-is-a-null.md``
rests on two structural facts about these three models, and neither is visible in
a score:

* ``cart-noop`` runs ``cart-001``'s *entire* code path — domains fitted, the
  assertion consulted at every candidate, the backtracker armed — with an
  assertion that cannot fail. So it must predict exactly what ``cart-order``
  predicts. On ``runs/full179`` the two agree to four decimals on all three
  metrics, and this test is why that is a check rather than a coincidence: a
  later edit that made the machinery change predictions by itself would make the
  whole table unreadable, and would show up here first.
* The decoder commits its **own predictions** and never the answer. A sequential
  decoder is the easiest place in this repo to leak, because it is the only model
  that writes into the view it is reading.

``tests/test_models.py`` already parameterises the leak and distribution
contracts over the registry, so these three are covered there. What is here is
what is specific to them.
"""

from __future__ import annotations

import numpy as np
import pytest

from symbolic_ai_core.data.batch import collate_graph
from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, RuleBasedModel, build
from symbolic_ai_models.models.cart_001.model import commit
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]


@pytest.fixture(scope="module")
def fixtures():
    episodes = list(generate(LESSONS, n=4))
    tok = build_tokenizer(TrainConfig(vocab_size=600), episodes)
    cfg = ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                      d_ff=64, dropout=0.0)
    return episodes, tok, cfg


def _fit(name, fixtures):
    episodes, tok, cfg = fixtures
    model = build(name, cfg)
    assert isinstance(model, RuleBasedModel)
    model.fit_on(episodes, tok)
    return model.eval()


def _views(model, fixtures):
    episodes, tok, cfg = fixtures
    batch = collate_graph(episodes, tok, max_nodes=cfg.max_nodes,
                          mask_rate=0.3, rng=np.random.default_rng(5))
    return [model._view(batch, b) for b in range(len(episodes))]


def test_the_noop_assertion_changes_nothing(fixtures):
    """``cart-noop`` must predict exactly what ``cart-order`` predicts.

    Same order, same commits, same votes — the only difference is that
    ``cart-noop`` computes and consults a domain that permits everything. If this
    ever fails, the backtracking machinery is moving predictions on its own and
    ``cart-001``'s row stops being about constraint logic.
    """
    order = _fit("cart-order", fixtures)
    noop = _fit("cart-noop", fixtures)
    seen = 0
    for va, vb in zip(_views(order, fixtures), _views(noop, fixtures)):
        a, b = order.node_votes(va), noop.node_votes(vb)
        assert set(a) == set(b)
        for node in a:
            seen += 1
            assert dict(a[node][0][0]) == dict(b[node][0][0]), node
            assert a[node][0][1] == pytest.approx(b[node][0][1]), node
    assert seen > 0, "no hidden nodes were compared; the fixture masks nothing"


def test_the_treatment_actually_fitted_some_assertions(fixtures):
    """A null is only a null if the thing that failed was present.

    ``cart-001`` scoring level with its own control would be uninteresting if the
    constraint tables were empty — that would be a null about a bug. On
    ``runs/full179`` it fits 909 slot domains and 5,220 arity entries; here the
    corpus is three lessons, so the assertion is merely that they are non-empty.
    """
    model = _fit("cart-001", fixtures)
    assert model.arity_of, "no arities were learned"
    assert model.types_of, "no label/type compatibilities were learned"
    assert model.known_labels, "no labels were recorded as known"


def test_the_decoder_never_writes_the_answer_into_the_view(fixtures):
    """``commit`` may only make visible what was passed to it.

    The leak this guards is specific to a sequential decoder: it is the one model
    family here that writes into the view it is reading, so "the hidden answer
    never reaches the model" has a second way to fail that the registry-wide test
    does not exercise.
    """
    model = _fit("cart-001", fixtures)
    view = _views(model, fixtures)[0]
    node = view.hidden[0]
    after = commit(view, node, 7, None)
    assert after.labels[node] == 7
    assert after.types[node] is None, "an abstained type must stay unknown"
    assert node not in after.hidden
    assert view.labels[node] is None, "commit must not mutate its input"
    assert node in view.hidden
    # Everything else is untouched, including the relations: the collator
    # withheld the coreference edges of hidden nodes and this decoder has no
    # way to restore them, so a commit must not invent one.
    assert after.rel is view.rel
    others = [i for i in range(len(view)) if i != node]
    assert [after.labels[i] for i in others] == [view.labels[i] for i in others]


def test_all_three_arms_answer_every_hole(fixtures):
    """A decoder that runs out of budget must still emit a vote per hole.

    The backtracker is bounded, and the bounded path is the one where a hole can
    silently go unanswered — which would not fail any score, it would quietly
    move that hole onto the back-off and flatter the arm that abstained most.
    """
    for name in ("cart-001", "cart-order", "cart-noop"):
        model = _fit(name, fixtures)
        for view in _views(model, fixtures):
            got = model.node_votes(view)
            assert set(got) == set(view.hidden), name
