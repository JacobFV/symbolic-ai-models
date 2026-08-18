"""Ownership consolidation: the closure task with independently filed labels."""

from __future__ import annotations

import random

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_tasks.ultimate_parent import (UltimateParentTask,
                                               closure_with_cycles, evaluate,
                                               load_task, predict_closure,
                                               predict_direct, predict_fused)


def _chain() -> UltimateParentTask:
    # a -> b -> c -> d(root);  x -> y(root)
    direct = {"a": "b", "b": "c", "c": "d", "x": "y"}
    truth = {"a": "d", "b": "d", "c": "d", "x": "y"}
    return UltimateParentTask(direct=direct, truth=truth)


class TestMechanics:
    def test_only_entities_with_both_relations_are_scored(self):
        """An entity with an ultimate parent and no direct parent is a hole in
        the input, not a reasoning failure, and scoring it would price a data
        gap as an error."""
        t = UltimateParentTask(direct={"a": "b"}, truth={"a": "b", "z": "q"})
        assert t.ids == ("a",)

    def test_the_floor_assumes_depth_one(self):
        t = _chain()
        assert t.floor() == pytest.approx(0.5)   # c and x are depth 1
        assert predict_direct(t)["a"] == "b"

    def test_closure_walks_to_the_root(self):
        assert predict_closure(_chain())["a"] == "d"

    def test_a_cycle_is_reported_not_truncated(self):
        """"A is ultimately owned by A" and "we gave up after 64 hops" are
        different claims; a method that cannot tell them apart reports
        neither."""
        root, cyc = closure_with_cycles({"a": "b", "b": "a"}, "a")
        assert root is None and cyc is True

    def test_a_clean_chain_reports_no_cycle(self):
        root, cyc = closure_with_cycles({"a": "b", "b": "c"}, "a")
        assert root == "c" and cyc is False


class TestFusionDiscipline:
    def test_fusion_continues_past_a_broken_chain(self):
        """b's chain stops at c; c filed an ultimate parent, so use it."""
        t = UltimateParentTask(direct={"b": "c"},
                               truth={"b": "top", "c": "top"})
        assert predict_fused(t)["b"] == "top"

    def test_fusion_never_reads_the_label_of_the_entity_it_predicts(self):
        """The one way this method could cheat. `a` has no direct parent, so
        the walk stops immediately rather than reading a's own filed answer."""
        t = UltimateParentTask(direct={"a": "a"}, truth={"a": "secret"})
        assert predict_fused(t)["a"] != "secret"

    def test_fusion_leaves_a_complete_chain_alone(self):
        assert predict_fused(_chain())["a"] == "d"


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheFiledData:
    @staticmethod
    @pytest.fixture(scope="class")
    def task():
        base = next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "gleif").resolve(data_root())
        return load_task(base)

    def test_the_task_is_the_size_it_should_be(self, task):
        assert len(task.ids) == 117129

    def test_the_naive_floor_is_already_strong(self, task):
        """75% of entities are consolidated directly by their ultimate parent,
        so "assume depth one" is a real answer and not a strawman."""
        assert task.floor() == pytest.approx(0.7503, abs=5e-4)

    def test_the_swept_floor_is_much_stronger_than_the_naive_one(self, task):
        """Depth-2 truncated closure -- a crude version of the same
        capability, which is the floor that can actually embarrass it."""
        two = {e: task.direct.get(task.direct.get(e, e), task.direct.get(e))
               for e in task.ids}
        assert evaluate(task, two) == pytest.approx(0.9005, abs=2e-3)

    def test_closure_beats_the_swept_floor(self, task):
        assert evaluate(task, predict_closure(task)) == pytest.approx(
            0.9573, abs=2e-3)

    def test_fusing_the_two_relations_beats_either(self, task):
        """Two relations disagreeing on 4.27% of entities are not a
        contradiction to resolve by picking a winner."""
        assert evaluate(task, predict_fused(task)) == pytest.approx(
            0.9785, abs=2e-3)

    def test_ownership_cycles_exist_and_are_few(self, task):
        n = sum(1 for e in task.ids
                if closure_with_cycles(task.direct, e)[1])
        assert n == 6

    def test_shuffling_the_edges_destroys_it(self, task):
        rng = random.Random(5)
        tgt = list(task.direct.values())
        rng.shuffle(tgt)
        broken = UltimateParentTask(
            direct=dict(zip(task.direct.keys(), tgt)), truth=task.truth)
        assert evaluate(broken, predict_closure(broken)) < 0.01
