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
