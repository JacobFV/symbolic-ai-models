"""The first real-data task with a floor a method can fail to beat."""

from __future__ import annotations

import random

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_tasks import (AirportCountryTask, evaluate, load_task,
                               predict_anchor, predict_knn, predict_modal)
from symbolic_ai_tasks.airport_country import (STRONGEST_FLOOR,
                                               STRONGEST_FLOOR_DEG,
                                               predict_grid)


def _toy() -> AirportCountryTask:
    # Two tight clusters, one country each, plus a lone outlier.
    pos = {"a1": (0.0, 0.0), "a2": (0.1, 0.1), "a3": (0.2, 0.0),
           "b1": (50.0, 50.0), "b2": (50.1, 50.1), "b3": (50.2, 50.0)}
    truth = {k: ("X" if k[0] == "a" else "Y") for k in pos}
    return AirportCountryTask(pos=pos, truth=truth,
                              body_country={k: truth[k] for k in pos})


class TestTaskMechanics:
    def test_the_floor_is_the_modal_country(self):
        t = AirportCountryTask(pos={"a": (0.0, 0.0), "b": (1.0, 1.0),
                                    "c": (2.0, 2.0)},
                               truth={"a": "X", "b": "X", "c": "Y"},
                               body_country={})
        assert t.floor() == pytest.approx(2 / 3)

    def test_knn_leaves_the_point_out(self):
        """An airport is its own nearest neighbour; including it would score
        the labels against themselves and read 1.0 for any labelling."""
        t = _toy()
        scrambled = AirportCountryTask(
            pos=t.pos, truth={**t.truth, "a1": "Y"}, body_country={})
        assert predict_knn(scrambled, 1)["a1"] == "X"

    def test_spatial_contiguity_is_learnable(self):
        assert evaluate(_toy(), predict_knn(_toy(), 1)) == 1.0

    def test_the_modal_baseline_scores_the_floor(self):
        t = _toy()
        assert evaluate(t, predict_modal(t)) == pytest.approx(t.floor())


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheRealTask:
    @staticmethod
    @pytest.fixture(scope="class")
    def task():
        base = next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "openflights").resolve(data_root())
        return load_task(base)

    def test_the_task_is_the_size_it_should_be(self, task):
        assert len(task.ids) == 5995
        assert len(set(task.truth.values())) == 222

    def test_the_floor_is_real_and_beatable(self, task):
        assert task.floor() == pytest.approx(0.2087, abs=5e-4)

    def test_the_ground_truth_anchor_is_exact(self, task):
        """The anchor reads the leak and must score 1.0. It scored 0.9715 and
        the missing 2.85% was a parser bug of mine -- `country=United States`
        truncated to `United` -- not a flaw in the data. An anchor that is
        allowed to be approximately right catches nothing."""
        assert evaluate(task, predict_anchor(task)) == 1.0

    def test_coordinates_alone_beat_the_floor_by_a_wide_margin(self, task):
        assert evaluate(task, predict_knn(task, 1)) == pytest.approx(
            0.9078, abs=2e-3)

    def test_shuffling_the_labels_destroys_it(self, task):
        """The control that must fail. It lands *below* the floor, which is
        right: 1-NN copies a random neighbour's random label, and that is
        worse than always guessing the commonest country."""
        rng = random.Random(11)
        ids = list(task.ids)
        shuf = ids[:]
        rng.shuffle(shuf)
        broken = AirportCountryTask(
            pos=task.pos, truth={a: task.truth[b] for a, b in zip(ids, shuf)},
            body_country={})
        assert evaluate(broken, predict_knn(broken, 1)) < broken.floor()

    def test_shuffling_the_coordinates_destroys_it_too(self, task):
        rng = random.Random(11)
        ids = list(task.ids)
        shuf = ids[:]
        rng.shuffle(shuf)
        moved = {a: task.pos[b] for a, b in zip(ids, shuf)}
        assert evaluate(task, predict_knn(task, 1, pos=moved)) < task.floor()


class TestTheFloorAudit:
    def test_a_cell_with_neighbours_votes(self):
        pos = {f"a{i}": (0.1 * i, 0.1 * i) for i in range(4)}
        truth = {"a0": "X", "a1": "X", "a2": "X", "a3": "Y"}
        t = AirportCountryTask(pos=pos, truth=truth, body_country={})
        assert predict_grid(t, 5.0)["a3"] == "X"

    def test_an_emptied_cell_falls_back_to_the_global_mode(self):
        """Leave-one-out on a singleton cell leaves nothing to vote."""
        pos = {"a": (0.0, 0.0), "b": (0.1, 0.1), "far": (80.0, 170.0)}
        truth = {"a": "X", "b": "X", "far": "Y"}
        t = AirportCountryTask(pos=pos, truth=truth, body_country={})
        assert predict_grid(t, 1.0)["far"] == "X"


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestTheFloorAgainstRealData:
    @staticmethod
    @pytest.fixture(scope="class")
    def task():
        base = next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "openflights").resolve(data_root())
        return load_task(base)

    def test_the_strong_floor_is_far_above_the_modal_one(self, task):
        """0.7888 against 0.2087. Quoting a lift against the modal floor
        overstates it by 5.9x."""
        assert evaluate(task, predict_grid(task, STRONGEST_FLOOR_DEG)) == \
            pytest.approx(STRONGEST_FLOOR, abs=2e-3)

    def test_the_method_still_beats_the_strong_floor(self, task):
        assert evaluate(task, predict_knn(task, 1)) > STRONGEST_FLOOR

    def test_the_floor_is_not_monotone_in_resolution(self, task):
        """The finding worth keeping: a finer grid is a *sparser* floor, not a
        sharper one, because leave-one-out empties singleton cells. If this
        ever becomes monotone the sweep was wrong somewhere."""
        five = evaluate(task, predict_grid(task, 5.0))
        one = evaluate(task, predict_grid(task, 1.0))
        assert one < five
