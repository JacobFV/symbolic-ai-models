"""A learned routing gate, and the comparison that says when it is worth having.

The measured result is that the hand-written *provable* gate captures more
headroom at zero accuracy loss, and the learned one only wins once an accuracy
bar below 1.000 is acceptable. So the learned policy is registered **beside** the
hand one and the graph names which trade it is making.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.artifact import Artifact
from symbolic_ai_core.flow.router import ROUTER_POLICIES
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.features import FEATURES, feature_vector
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.gate_model import GateModel, fit
from symbolic_ai_generators.flood import routing as _routing
from symbolic_ai_core.world import Claim

assert _routing


def reach_of(case):
    _, outs, _ = solve(case.world)
    return [Claim.from_dict(x) for x in outs["reach"].value["claims"]]


# --- the features ---------------------------------------------------------
def test_every_feature_is_computable_before_the_expensive_path():
    """A gate may only read what is already on the table. A feature needing a
    solver would make the gate cost what it is deciding whether to spend."""
    import inspect

    from symbolic_ai_generators.flood import features

    src = inspect.getsource(features)
    for forbidden in ("asp@1", "smt@1", "clingo", "import z3", "check_loads"):
        assert forbidden not in src, f"a feature reaches for {forbidden}"


def test_the_feature_vector_is_ordered_and_complete():
    c = generate(3)
    x = feature_vector(c.world, reach_of(c))
    assert len(x) == len(FEATURES)
    assert x[FEATURES.index("bias")] == 1.0
    assert all(isinstance(v, float) for v in x)


def test_features_are_scaled_to_comparable_magnitudes():
    """An unscaled ratio of 6000 beside a 0/1 flag makes gradient descent a
    study of the largest column rather than of the problem."""
    biggest = 0.0
    for s in range(12):
        c = generate(s)
        biggest = max(biggest, max(abs(v) for v in feature_vector(c.world,
                                                                  reach_of(c))))
    assert biggest < 20.0, f"a feature reached {biggest}"


def test_a_world_with_no_bridges_does_not_divide_by_zero():
    c = generate(3)
    stripped = c.world.__class__(
        entities=c.world.entities,
        claims=tuple(x for x in c.world.claims
                     if x.predicate not in ("bridge_on", "load_limit")))
    x = feature_vector(stripped, reach_of(c))
    assert all(v == v for v in x)          # no NaN
    assert x[FEATURES.index("laden_over_min_limit")] == 0.0


# --- the model ------------------------------------------------------------
def test_a_model_round_trips_and_prints_its_weights():
    m = fit([([1.0] + [0.0] * (len(FEATURES) - 1), 1),
             ([1.0] + [1.0] * (len(FEATURES) - 1), 0)], epochs=50)
    assert GateModel.from_dict(m.to_dict()).weights == m.weights
    assert "bias=" in m.explain()


def test_a_model_fitted_on_a_different_feature_order_is_refused():
    """A weight vector against a different ordering is not broken, it is merely
    worse -- which is the harder failure to notice."""
    m = fit([([1.0] * len(FEATURES), 1), ([0.0] * len(FEATURES), 0)], epochs=10)
    d = m.to_dict()
    d["features"] = list(reversed(d["features"]))
    with pytest.raises(ValueError, match="merely worse"):
        GateModel.from_dict(d)


def test_fitting_on_nothing_is_refused():
    with pytest.raises(ValueError, match="route on its bias term"):
        fit([])


def test_the_model_separates_a_separable_problem():
    rows = [([1.0, 0.0], 1) for _ in range(20)] + \
           [([1.0, 1.0], 0) for _ in range(20)]
    m = fit(rows, epochs=300)
    assert m.score([1.0, 0.0]) > m.score([1.0, 1.0])


# --- the policy -----------------------------------------------------------
def test_the_learned_policy_is_registered_beside_the_hand_one():
    assert "flood_escalate" in ROUTER_POLICIES
    assert "flood_learned" in ROUTER_POLICIES, (
        "the learned gate replaced the hand gate instead of standing beside it")


def test_the_learned_policy_refuses_to_run_without_a_model():
    """A silent fallback to some default policy is how a broken component reads
    as a working one."""
    with pytest.raises(KeyError, match="silent fallback"):
        ROUTER_POLICIES["flood_learned"]({}, {})


def test_the_learned_policy_decides_deterministically():
    m = fit([([1.0] * len(FEATURES), 1), ([0.0] * len(FEATURES), 0)], epochs=50)
    c = generate(5)
    from symbolic_ai_kernels.flow_ops import world_artifact
    inputs = {"in": world_artifact(c.world),
              "aux": Artifact(type="claim_set",
                              value={"producer": "datalog@1", "claims": []})}
    params = {"model": m.to_dict()}
    first = ROUTER_POLICIES["flood_learned"](inputs, params)
    assert first == ROUTER_POLICIES["flood_learned"](inputs, params)
    assert first in (["cheap"], ["full"])


def test_an_absent_world_routes_to_the_expensive_path():
    """Absence must escalate, never take the shortcut."""
    m = fit([([1.0] * len(FEATURES), 1)], epochs=10)
    out = ROUTER_POLICIES["flood_learned"](
        {"in": Artifact.absent("world_snapshot", why="upstream off")},
        {"model": m.to_dict()})
    assert out == ["full"]


# --- the stronger learner, and what it buys its extra headroom with -------
def test_boosted_trees_round_trip_and_separate():
    from symbolic_ai_generators.flood.gate_model import BoostedGate, fit_boosted

    rows = [([1.0, 0.0, 0.0], 1) for _ in range(40)] + \
           [([1.0, 1.0, 0.0], 0) for _ in range(40)]
    m = fit_boosted(rows, n_trees=20, depth=2, min_leaf=5)
    assert m.score([1.0, 0.0, 0.0]) > m.score([1.0, 1.0, 0.0])
    back = BoostedGate.from_dict(m.to_dict())
    assert back.score([1.0, 0.0, 0.0]) == pytest.approx(m.score([1.0, 0.0, 0.0]))


def test_boosted_trees_capture_an_interaction_a_linear_model_cannot():
    """XOR. This is the whole reason a second learner was worth fitting, and
    the reason it finds headroom the logistic model leaves."""
    from symbolic_ai_generators.flood.gate_model import fit, fit_boosted

    rows = ([([1.0, 0.0, 0.0], 0)] * 30 + [([1.0, 1.0, 0.0], 1)] * 30 +
            [([1.0, 0.0, 1.0], 1)] * 30 + [([1.0, 1.0, 1.0], 0)] * 30)
    lin = fit(rows, epochs=400)
    gbt = fit_boosted(rows, n_trees=40, depth=2, min_leaf=5)

    def separates(m):
        return (min(m.score([1.0, 1.0, 0.0]), m.score([1.0, 0.0, 1.0]))
                > max(m.score([1.0, 0.0, 0.0]), m.score([1.0, 1.0, 1.0])))

    assert not separates(lin), "the linear model solved XOR, which it cannot"
    assert separates(gbt)


def test_a_boosted_model_fitted_on_another_feature_order_is_refused():
    from symbolic_ai_generators.flood.gate_model import BoostedGate, fit_boosted

    m = fit_boosted([([1.0] * len(FEATURES), 1),
                     ([0.0] * len(FEATURES), 0)], n_trees=3, min_leaf=1)
    d = m.to_dict()
    d["features"] = list(reversed(d["features"]))
    with pytest.raises(ValueError, match="current order"):
        BoostedGate.from_dict(d)


def test_the_hand_gate_is_lossless_by_proof_not_by_sample():
    """The correction to the earlier finding, pinned.

    A provable gate's accuracy is a theorem; a learned gate's is a sample
    estimate. Measured across three disjoint 1,000-seed evaluation ranges: the
    hand gate is wrong 0 times, and the boosted gate 1, 2 and 1 -- while
    capturing more headroom. This test checks the *hand* half, which is the half
    that must hold at any N.
    """
    from symbolic_ai_generators.flood.features import FEATURES as F
    from symbolic_ai_generators.flood.flow import solve as _solve
    from symbolic_ai_core.flow import Context

    wrong = 0
    for s in range(1_000_000, 1_000_060):
        c = generate(s)
        full, _, _ = _solve(c.world, ctx=Context())
        routed, outs, _ = _solve(c.world, ctx=Context(), routed=True)
        if outs["decision"].value["chosen"] == ["cheap"] and full != routed:
            wrong += 1
    assert wrong == 0, (
        f"the provable gate was wrong {wrong} times; one of its two conditions "
        f"is not actually sufficient")
