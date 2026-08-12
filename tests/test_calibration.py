"""Confidence against outcome.

An accuracy without a floor is not a result; a confidence that does not track
correctness is the same kind of empty number, and worse, because it invites a
caller to trust the wrong answers.
"""

from __future__ import annotations

import numpy as np
import pytest

from symbolic_ai_models.calibration import calibrate, calibrate_model
from symbolic_ai_models.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import TrainConfig, build_tokenizer


def test_a_perfectly_calibrated_model_scores_zero():
    """Say 0.7, be right 70% of the time, in every bucket."""
    rng = np.random.default_rng(0)
    confidence = rng.uniform(0.05, 0.95, size=20_000)
    correct = rng.uniform(size=20_000) < confidence
    report = calibrate(confidence, correct)
    assert report.ece < 0.02
    assert abs(report.overconfidence) < 0.02


def test_confident_and_wrong_is_caught():
    """The failure the metric exists for: certainty that does not deliver."""
    report = calibrate(np.full(1000, 1.0), np.array([i % 2 == 0 for i in range(1000)]))
    assert report.ece == pytest.approx(0.5, abs=0.01)
    assert report.overconfidence == pytest.approx(0.5, abs=0.01)


def test_underconfidence_has_the_opposite_sign():
    """Being too shy is miscalibration too, but it is not the dangerous kind."""
    report = calibrate(np.full(1000, 0.1), np.ones(1000))
    assert report.overconfidence == pytest.approx(-0.9, abs=0.01)


def test_a_confidence_of_exactly_one_is_counted():
    """Half-open bins would drop it, and it is the bucket that matters most."""
    report = calibrate(np.ones(10), np.ones(10))
    assert report.n == 10
    assert sum(b.n for b in report.buckets) == 10


def test_empty_input_is_safe():
    assert calibrate(np.array([]), np.array([])).n == 0


def test_a_real_model_reports_a_usable_curve():
    train = list(generate(["symbol_grounding", "unification"], n=20))
    evaluation = list(generate(["symbol_grounding", "unification"], n=6,
                               seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=900), train)
    model = build("ngram", ModelConfig(vocab_size=len(tok), max_len=64))
    model.fit_on(train, tok)
    report = calibrate_model(model, make_task("node", max_nodes=64),
                             evaluation, tok)
    assert report.n > 0
    assert 0.0 <= report.ece <= 1.0
    assert 0.0 <= report.accuracy <= 1.0
    assert "ECE" in report.table()


def test_the_isotonic_map_is_monotone_and_the_right_length():
    """A higher internal score must never map to a lower stated accuracy."""
    from symbolic_ai_models.calibration import ScoreCalibrator, _pava

    assert _pava([0.4, 0.1, 0.9], [1.0, 1.0, 1.0]) == pytest.approx(
        [0.25, 0.25, 0.9])
    assert len(_pava([0.5] * 7, [1.0] * 7)) == 7

    rng = np.random.default_rng(1)
    scores = rng.uniform(size=2000)
    calibrator = ScoreCalibrator().fit(scores, rng.uniform(size=2000) < scores)
    assert calibrator.fitted
    assert all(a <= b + 1e-9 for a, b in zip(calibrator.values,
                                             calibrator.values[1:]))
    assert calibrator(0.01) < calibrator(0.99)


def test_the_map_never_promises_certainty():
    """A confidence of 1.0 would let the mixture stake everything on one symbol."""
    from symbolic_ai_models.calibration import ScoreCalibrator

    calibrator = ScoreCalibrator().fit(np.linspace(0, 1, 200), np.ones(200, bool))
    assert calibrator(1.0) <= 0.95


def test_too_little_data_leaves_the_map_unfitted():
    """And the model must then fall back rather than trust three examples."""
    from symbolic_ai_models.calibration import ScoreCalibrator

    assert not ScoreCalibrator().fit([0.1, 0.9], [False, True]).fitted


@pytest.mark.parametrize("name", ["analogy", "workspace"])
def test_the_fitted_confidence_beats_the_formula_it_replaced(name):
    """These two derived confidence from how much structure they found.

    Finding structure and being right are different things, and measured, the
    gap was the worst in the repo: `analogy` stated 0.586 against 0.219
    delivered. The map is fitted on held-out outcomes, so this asserts the
    result, not the mechanism.
    """
    train = list(generate(["symbol_grounding", "unification"], n=30))
    evaluation = list(generate(["symbol_grounding", "unification"], n=8,
                               seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1200), train)
    model = build(name, ModelConfig(vocab_size=len(tok), max_len=96))
    model.fit_on(train, tok)
    assert model.confidence_map.fitted, f"{name} did not calibrate"
    report = calibrate_model(model, make_task("node", max_nodes=96),
                             evaluation, tok)
    # Overconfidence is the property worth guarding: a model that says more
    # than it delivers misleads whatever reads it, and that is what the fitted
    # map was introduced to stop.
    assert report.overconfidence < 0.15, f"{name} says more than it delivers"

    # The distribution must also be *properly scaled*, which is the stronger
    # claim and the one that survived investigation. ECE sits around 0.22 for
    # these two, which looks like a regression from ~0.09 and is not: the
    # models are under-confident on their top-1 only, and the temperature that
    # minimises negative log-likelihood — the proper scoring rule this repo
    # actually reports — comes out at 1.0. Sharpening to flatter the ECE would
    # trade a proper score for a diagnostic, so it is not done, and the
    # assertion here is on the quantity that is not gameable that way.
    assert 0.7 <= model.temperature <= 1.4, (
        f"{name} distribution is mis-scaled (T={model.temperature})")


# ---------------------------------------------------------------------------
# MassCalibrator: the mixture weight, fitted as a mixture weight
# ---------------------------------------------------------------------------
def test_mass_recovers_a_known_mixture_weight():
    """The estimator's one job: given data from (1-c)b + c q, return c."""
    from symbolic_ai_models.calibration import MassCalibrator

    rng = np.random.default_rng(0)
    n = 4000
    backoff = np.full(n, 1e-4)          # a flat prior over ~10k symbols
    votes = np.full(n, 0.2)             # five candidates, gold among them
    truth = 0.6
    # Draw which component produced each observation, then report that
    # component's probability of the gold symbol -- exactly the two numbers the
    # calibrator is handed at fit time.
    from_votes = rng.uniform(size=n) < truth
    q = np.where(from_votes, votes, 0.0)
    calibrator = MassCalibrator(n_bins=1).fit(np.zeros(n), q, backoff)
    assert calibrator.fitted
    assert calibrator(0.0) == pytest.approx(truth, abs=0.05)


def test_mass_returns_zero_when_the_votes_are_worse_than_the_prior():
    """Abstention has to be reachable, or a useless model is forced to speak."""
    from symbolic_ai_models.calibration import MassCalibrator

    n = 400
    calibrator = MassCalibrator(n_bins=1).fit(
        np.zeros(n), np.zeros(n), np.full(n, 1e-3))
    assert calibrator(0.0) == 0.0


def test_mass_is_monotone_in_the_score():
    """A higher agreement score may not buy less mass; PAVA enforces it."""
    from symbolic_ai_models.calibration import MassCalibrator

    rng = np.random.default_rng(1)
    n = 4000
    scores = rng.uniform(size=n)
    backoff = np.full(n, 1e-4)
    # Mass genuinely earned rises with the score, with noise on top.
    hit = rng.uniform(size=n) < scores
    votes = np.where(hit, 0.25, 0.0)
    calibrator = MassCalibrator().fit(scores, votes, backoff)
    values = [calibrator(s) for s in np.linspace(0, 1, 25)]
    assert values == sorted(values)


def test_mass_beats_argmax_accuracy_at_the_job_the_mixture_uses_it_for():
    """The motivating case, as an assertion rather than an argument.

    A model that knows the answer is one of five and nothing more has argmax
    accuracy 0.2, so a ScoreCalibrator hands the mixture c = 0.2 and spends the
    other 0.8 on a flat prior. The likelihood-optimal weight is 1.0, and the
    difference is most of the information the model had.
    """
    from symbolic_ai_models.calibration import MassCalibrator, ScoreCalibrator

    rng = np.random.default_rng(2)
    n = 3000
    backoff = np.full(n, 1e-4)
    q_gold = np.full(n, 0.2)            # gold always inside the vote set
    argmax_right = rng.uniform(size=n) < 0.2

    by_accuracy = ScoreCalibrator(n_bins=1).fit(np.zeros(n), argmax_right)(0.0)
    by_mass = MassCalibrator(n_bins=1).fit(np.zeros(n), q_gold, backoff)(0.0)
    assert by_accuracy == pytest.approx(0.2, abs=0.05)
    assert by_mass > 0.9

    nll = lambda c: -np.mean(np.log((1 - c) * backoff + c * q_gold))
    assert nll(by_mass) < nll(by_accuracy)


def test_mass_leaves_the_ordering_of_the_votes_alone():
    """The honest limit: c scales every vote equally, so argmax cannot move."""
    from symbolic_ai_models.calibration import MassCalibrator

    calibrator = MassCalibrator(n_bins=1).fit(
        np.zeros(200), np.full(200, 0.3), np.full(200, 1e-4))
    votes = {7: 0.5, 9: 0.3, 11: 0.2}
    backoff = 1e-4
    for c in (calibrator(0.0), 0.1, 0.9):
        mixed = {s: (1 - c) * backoff + c * w for s, w in votes.items()}
        assert max(mixed, key=mixed.get) == 7


def test_backoff_prob_agrees_with_the_mixture_it_describes():
    """If these two disagree the fitted weight is between the wrong things."""
    import torch

    from symbolic_ai_models.models.symbolic import _node_context

    train = list(generate(["symbol_grounding", "unification"], n=20))
    tok = build_tokenizer(TrainConfig(vocab_size=900), train)
    model = build("ruleinduce", ModelConfig(vocab_size=len(tok), max_len=96,
                                            max_nodes=96))
    model.fit_on(train, tok)

    view, targets = next(iter(model.training_views(train, tok, max_nodes=96)))
    node = next(iter(targets))
    symbol = int(targets[node][0])
    if symbol < 0:
        pytest.skip("no scorable label in the first view")

    # What `_mix` would produce for this node with no votes at all: the pure
    # back-off path, which is what `backoff_prob` claims to report.
    entry = model.context_prior.get(_node_context(view, node))
    prior = ([0], [node], [int(entry[0])], [float(entry[1])]) if entry else None
    logits = model._mix(model.symbol_backoff, (1, len(view)),
                        np.zeros((1, len(view))), [], [], [], [], prior=prior)
    assert float(logits[0, node, symbol].exp()) == pytest.approx(
        model.backoff_prob(view, node, symbol), rel=1e-6)
