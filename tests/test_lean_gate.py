"""The gating diagnostic, and whether its controls are working.

These do not pin the gate's *values* — a constant measured on one slice pinned
into a test that runs on another fixture is a mistake this repo has already
made twice (``notes/lessons/2026-08-13-slices-have-inverted-results-eight-times.md``,
final paragraph). They pin the **relations that make the number readable**, all
of which must hold on any slice:

* the ``shifted`` control must destroy gold survival while leaving the prune
  rate alone — otherwise the filter is not reading the hole;
* gold survival must beat the matched-random filter — otherwise the filter is
  not reading anything;
* ``closed`` must prune more than ``open`` — that is what the arm *is*;
* the eval seeds must not be touched.
"""

from __future__ import annotations

import numpy as np
import pytest

from symbolic_ai_core.data.curriculum import generate, lesson_ids
from symbolic_ai_lean.gate import (HELD_OUT_SEED0, arity_accepts, holes_of,
                                   mask_nodes, run_gate, truncate)


@pytest.fixture(scope="module")
def result():
    return run_gate(lessons=lesson_ids()[:24], n=1)


def test_the_diagnostic_never_touches_an_evaluation_seed():
    """Seeds >= 1,000,000 are evaluation only, and design choices are settled on
    held-out *training* episodes. This is the assertion, not the intention."""
    assert HELD_OUT_SEED0 < 1_000_000
    assert HELD_OUT_SEED0 >= 100          # clear of training's 0..n_train-1


def test_it_scored_something(result):
    assert result.n_holes > 100
    assert 0.5 < result.n_copyable / result.n_holes < 0.95
    assert result.checks > 1000


@pytest.mark.parametrize("mode", ["open", "declared", "closed", "arity"])
def test_prune_and_survival_are_proportions(result, mode):
    assert 0.0 <= result.median_prune(mode) <= 1.0
    assert 0.0 <= result.survival(mode) <= 1.0


def test_the_shifted_control_keeps_the_prune_rate_and_loses_the_gold(result):
    """Same episode, same signature, same cardinality — wrong hole. If gold
    survival did not collapse, the prune rate would be a property of the
    candidate set rather than of the question."""
    assert abs(result.median_prune("shifted")
               - result.median_prune("open")) < 0.05
    assert result.survival("shifted") < result.survival("open") - 0.3


def test_gold_survival_beats_a_filter_of_the_same_cardinality(result):
    """The instrument working: the kernel is not merely keeping enough
    candidates to keep the gold by luck."""
    for mode in ("open", "declared"):
        assert result.survival(mode) > result.matched_random(mode) + 0.2


def test_committing_harder_prunes_harder_and_costs_gold(result):
    assert result.median_prune("closed") > result.median_prune("open")
    assert result.survival("closed") < result.survival("open")


def test_the_arity_floor_is_computed_without_the_kernel():
    """A floor that quietly used the kernel would not be a floor. This one is a
    child count and nothing else, so it stands up under a permuted signature."""
    ep = next(iter(generate(lesson_ids()[:1], n=1, seed0=500)))
    from symbolic_ai_lean.elaborate import elaborate
    g = ep.graph
    e = elaborate(g, [3], mode="open")
    for label in e.candidate_labels(3)[:20]:
        want = len(e.children[3])
        expected = any(len(e.children[j]) == want
                       for j in range(len(g))
                       if g.labels[j] == label and j != 3
                       and g.types[j] not in ("list", "tuple", "record", "nil"))
        assert arity_accepts(e, 3, label) == expected


def test_the_gate_is_deterministic():
    a = run_gate(lessons=lesson_ids()[:8], n=1)
    b = run_gate(lessons=lesson_ids()[:8], n=1)
    assert a.median_prune("open") == b.median_prune("open")
    assert a.survival("declared") == b.survival("declared")


def test_masking_matches_the_collator_and_always_asks_something():
    """`collate_graph` guarantees at least one question per graph; a diagnostic
    that silently skipped small graphs would be measuring a different slice."""
    rng = np.random.default_rng(0)
    for ep in generate(lesson_ids()[:20], n=1, seed0=500):
        g = truncate(ep.graph, 128)
        assert len(mask_nodes(g, rng, 0.15)) >= 1


def test_holes_are_the_ones_the_copy_head_is_scored_on():
    ep = next(iter(generate(lesson_ids()[:1], n=1, seed0=500)))
    g = ep.graph
    hidden = list(range(len(g)))
    for i in holes_of(g, hidden):
        assert g.labels[i]
        assert g.types[i] not in ("list", "tuple", "record", "nil")


def test_truncation_keeps_a_tree():
    ep = next(iter(generate(lesson_ids()[:1], n=1, seed0=500)))
    g = truncate(ep.graph, 20)
    assert len(g) == 20
    for i, p in enumerate(g.parent):
        assert p < i                       # every parent precedes its child
