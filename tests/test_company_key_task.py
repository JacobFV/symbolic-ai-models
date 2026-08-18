"""Name normalisation: the low-context task, chosen to embarrass the rules."""

from __future__ import annotations

import random

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_tasks.company_key import (LEGAL_SUFFIXES, CompanyKeyTask,
                                           evaluate, fit_strip_set, load_task,
                                           predict_fitted, predict_interior,
                                           predict_slug, predict_stripped,
                                           slugify)


def _toy() -> CompanyKeyTask:
    labels = {"1": "Apple Inc.", "2": "WATERS CORP /DE/",
              "3": "Four Corners Property Trust, Inc.", "4": "Co-operative Bank"}
    truth = {"1": "apple", "2": "waters-de", "3": "four-corners-property-trust",
             "4": "co-operative-bank"}
    return CompanyKeyTask(labels=labels, truth=truth)


class TestSlug:
    def test_punctuation_becomes_separators(self):
        assert slugify("Four Corners Property Trust, Inc.") == \
            "four-corners-property-trust-inc"

    def test_ampersand_separates_rather_than_expanding(self):
        """The filed keys show `Lindt & Spruengli` as `lindt-spruengli`, so
        expanding & to "and" would be a guess dressed as normalisation."""
        assert slugify("Lindt & Spruengli AG") == "lindt-spruengli-ag"


class TestRules:
    def test_trailing_strip_misses_a_medial_legal_form(self):
        """`WATERS CORP /DE/` is why the trailing rule left 68.9% of its
        residual on one pattern."""
        assert predict_stripped(_toy())["2"] == "waters-corp-de"

    def test_interior_strip_catches_it(self):
        assert predict_interior(_toy())["2"] == "waters-de"

    def test_the_head_token_is_never_stripped(self):
        """Stripping the suffix set everywhere would turn `Co-operative Bank`
        into `operative-bank`."""
        assert predict_interior(_toy())["4"].startswith("co-")

    def test_the_floor_strips_nothing(self):
        assert predict_slug(_toy())["1"] == "apple-inc"


class TestFitting:
    def test_a_token_seen_once_is_not_a_rule(self):
        """min_count is the guard against fitting the split."""
        t = CompanyKeyTask(labels={"1": "Acme Zzz"}, truth={"1": "acme"})
        assert "zzz" not in fit_strip_set(t, t.ids, min_count=3)

    def test_a_consistently_dropped_token_is_learned(self):
        labels = {str(i): f"Name{i} Inc" for i in range(5)}
        truth = {str(i): f"name{i}" for i in range(5)}
        t = CompanyKeyTask(labels=labels, truth=truth)
        assert "inc" in fit_strip_set(t, t.ids)

    def test_a_consistently_kept_token_is_not_learned(self):
        labels = {str(i): f"Name{i} Trust" for i in range(5)}
        truth = {str(i): f"name{i}-trust" for i in range(5)}
        t = CompanyKeyTask(labels=labels, truth=truth)
        assert "trust" not in fit_strip_set(t, t.ids)


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheFiledBridges:
    @staticmethod
    @pytest.fixture(scope="class")
    def task():
        base = next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "sec-edgar").resolve(data_root())
        return load_task(base)

    def test_the_task_is_the_size_it_should_be(self, task):
        assert len(task.ids) == 8021

    def test_the_floor_is_low(self, task):
        assert evaluate(task, predict_slug(task)) == pytest.approx(
            0.1046, abs=2e-3)

    def test_my_first_hand_written_rule(self, task):
        assert evaluate(task, predict_stripped(task, k=18)) == pytest.approx(
            0.8870, abs=2e-3)

    def test_my_second_hand_written_rule(self, task):
        assert evaluate(task, predict_interior(task, k=18)) == pytest.approx(
            0.9479, abs=2e-3)

    def test_the_fitted_rule_reaches_the_ceiling_held_out(self, task):
        """0.9998 on data never used to fit. The 0.05 gap between my second
        hand-written list and this was effort, not a capability boundary."""
        ids = list(task.ids)
        random.Random(17).shuffle(ids)
        cut = len(ids) // 2
        strip = fit_strip_set(task, ids[:cut])
        pred = predict_fitted(task, strip, ids[cut:])
        acc = sum(pred[i] == task.truth[i] for i in ids[cut:]) / len(ids[cut:])
        assert acc > 0.999

    def test_every_legal_token_is_treated_consistently(self, task):
        """The measurement that killed my "the residual needs world knowledge"
        hypothesis. If any token were ambiguous the ceiling would be below 1.0
        for a language model too."""
        kept: dict[str, int] = {}
        dropped: dict[str, int] = {}
        for i in task.ids:
            parts = slugify(task.labels[i]).split("-")
            gold = set(task.truth[i].split("-"))
            for j, tok in enumerate(parts):
                if j == 0 or tok not in set(LEGAL_SUFFIXES):
                    continue
                tgt = kept if tok in gold else dropped
                tgt[tok] = tgt.get(tok, 0) + 1
        for tok in set(kept) | set(dropped):
            k, d = kept.get(tok, 0), dropped.get(tok, 0)
            if k + d >= 20:
                assert k == 0 or d == 0, f"{tok} is treated both ways"
