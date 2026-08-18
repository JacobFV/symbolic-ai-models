"""Rigid body: the first specialised world kernel, and the fusion gate it opens.

The physics is deliberately small. What matters is that a domain engine sits
behind the same narrow contract as datalog and Lean, declares a clock, and
returns claims with **honest error bars** — because a prediction whose stderr is
missing would dominate an inverse-variance fusion completely while looking like
a very good prediction.
"""

from __future__ import annotations

import math
import random
from dataclasses import replace

import pytest

from symbolic_ai_core.artifact import Provenance
from symbolic_ai_core.runtime import fuse, inverse_variance
from symbolic_ai_core.runtime.fusion import FusionError
from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.rigid import project_world

K = get_kernel("rigid@1")


def world(*, frame="world", stderr=0.5, pos=(0.0, 10.0), vel=(1.0, 0.0)):
    return WorldSnapshot(entities={
        "ball": Entity("ball", types=("body",), facets={
            "scene.body": Facet("scene.body", {"mass_kg": 2.0}),
            "scene.pose": Facet("scene.pose", {
                "position": list(pos), "velocity": list(vel),
                "frame": frame, "stderr_m": stderr})}),
        "field": Entity("field", facets={
            "scene.field": Facet("scene.field", {"acceleration": [0.0, -9.81]})}),
    })


def run(w, dt=0.1):
    return K.run(K.project(w, KernelRequest()), KernelRequest(params={"dt_s": dt}))


# --- the step -------------------------------------------------------------
def test_semi_implicit_euler_uses_the_new_velocity():
    """Explicit Euler would put the ball at y=10.0; semi-implicit at y<10."""
    after = run(world()).delta.apply(world()).entity("ball").facet("scene.pose")
    assert after.values["velocity"][1] == pytest.approx(-0.981)
    assert after.values["position"][1] == pytest.approx(10.0 - 0.0981)


def test_the_step_grows_the_uncertainty():
    before, after = 0.5, run(world()).claims[0].roles["value"].stderr
    assert after > before, "a prediction that got no less certain over time"
    assert after == pytest.approx(math.sqrt(0.5 ** 2 + (0.5 * 0.1) ** 2))


def test_the_assumption_behind_that_growth_is_in_the_provenance():
    method = run(world()).claims[0].provenance.method
    assert "stated assumption" in method and "not a derivation" in method


# --- refusals -------------------------------------------------------------
def test_a_missing_dt_is_refused_rather_than_defaulted():
    out = K.run(K.project(world(), KernelRequest()), KernelRequest())
    assert not out.ok and "invent a clock" in out.refused


def test_a_step_past_the_declared_tolerance_is_refused():
    out = run(world(), dt=5.0)
    assert not out.ok and "tolerance" in out.refused
    assert K.manifest.tolerances["dt_s"] == 1.0


def test_a_body_with_no_frame_is_discarded_not_defaulted():
    p = project_world(world(frame=""))
    assert p.covered_entities == frozenset({"field"}) or "ball" not in p.covered_entities
    assert any("position in nothing" in d.why for d in p.discarded)


def test_two_frames_in_one_world_are_refused():
    w = world()
    ents = dict(w.entities)
    ents["ball2"] = Entity("ball2", facets={
        "scene.body": Facet("scene.body", {"mass_kg": 1.0}),
        "scene.pose": Facet("scene.pose", {"position": [0.0, 0.0],
                                           "velocity": [0.0, 0.0],
                                           "frame": "camera",
                                           "stderr_m": 0.1})})
    with pytest.raises(ValueError, match="no transform here on purpose"):
        project_world(WorldSnapshot(entities=ents, claims=w.claims))


def test_a_pose_without_an_error_bar_is_projected_and_the_absence_recorded():
    p = project_world(world(stderr=None))
    assert "ball" in p.covered_entities
    assert any(d.kind == "uncertainty" and "dominate the fusion" in d.why
               for d in p.discarded)


def test_an_empty_world_is_a_refusal_not_a_pass():
    out = K.run(K.project(WorldSnapshot(), KernelRequest()),
                KernelRequest(params={"dt_s": 0.1}))
    assert not out.ok and "true and empty" in out.refused


def test_the_manifest_declares_a_clock_and_only_proposes():
    m = K.manifest
    assert m.clocks == "fixed_dt"
    assert m.authority["pose"] == "propose", (
        "a prediction must not be able to override an observation")


# --- the fusion gate ------------------------------------------------------
def test_inverse_variance_beats_both_inputs():
    """The standard result, and the reason a predictor and a sensor are worth
    having together. Also a calibration check: the reported stderr must match
    the error actually achieved."""
    rng = random.Random(7)
    TRUE, SP, SO, N = 10.0, 0.50, 0.20, 4000
    ep = eo = ef = 0.0
    stderr = None
    for _ in range(N):
        pred, obs = rng.gauss(TRUE, SP), rng.gauss(TRUE, SO)
        out = fuse([
            Claim("pose", {"of": EntityRef("b"),
                           "value": Quantity(pred, "m", SP)},
                  provenance=Provenance(producer="rigid@1")),
            Claim("pose", {"of": EntityRef("b"),
                           "value": Quantity(obs, "m", SO)},
                  provenance=Provenance(producer="sensor")),
        ], rules={"pose": inverse_variance})
        q = out.resolved[0].roles["value"]
        stderr = q.stderr
        ep += (pred - TRUE) ** 2
        eo += (obs - TRUE) ** 2
        ef += (q.value - TRUE) ** 2

    rms = lambda e: math.sqrt(e / N)
    theory = SP * SO / math.sqrt(SP ** 2 + SO ** 2)
    assert rms(ef) < min(rms(ep), rms(eo)), "fusion was worse than an input"
    assert rms(ef) == pytest.approx(theory, rel=0.1)
    assert stderr == pytest.approx(theory, rel=1e-6)
    assert rms(ef) == pytest.approx(stderr, rel=0.1), (
        "the claimed uncertainty does not match the error achieved")


def test_a_claim_with_no_error_bar_is_refused_not_given_infinite_weight():
    with pytest.raises(FusionError, match="no error bar"):
        inverse_variance(_group(Quantity(1.0, "m", 0.1), Quantity(2.0, "m")))


def test_a_zero_error_bar_is_refused():
    with pytest.raises(FusionError, match="infinite precision"):
        inverse_variance(_group(Quantity(1.0, "m", 0.0), Quantity(2.0, "m", 0.1)))


def test_the_prediction_and_the_observation_coexist_without_last_writer_wins():
    """The phase-11 gate. Two kernels claim one property; with no rule declared
    the mixture is kept, and with a rule declared it is combined -- neither is
    ever silently overwritten."""
    claims = [
        Claim("pose", {"of": EntityRef("b"), "value": Quantity(9.0, "m", 0.5)},
              provenance=Provenance(producer="rigid@1")),
        Claim("pose", {"of": EntityRef("b"), "value": Quantity(10.0, "m", 0.2)},
              provenance=Provenance(producer="sensor")),
    ]
    unresolved = fuse(claims)
    assert unresolved.resolved == () and len(unresolved.unresolved) == 1

    resolved = fuse(claims, rules={"pose": inverse_variance})
    v = resolved.resolved[0].roles["value"].value
    assert 9.0 < v < 10.0, "the fused estimate sits outside both readings"
    assert v > 9.8, "the more precise reading did not dominate"


def _group(*quantities):
    from symbolic_ai_core.runtime import ClaimGroup
    return ClaimGroup("pose", ("b",), tuple(
        Claim("pose", {"of": EntityRef("b"), "value": q},
              provenance=Provenance(producer=f"k{i}"))
        for i, q in enumerate(quantities)))


# --- the time is part of the type ----------------------------------------
def test_two_horizons_do_not_fuse_into_a_position_at_no_time():
    """Measured before the fix: poses for t+0.1s and t+0.9s fused by inverse
    variance into 0.387 m, silently, because from fusion's point of view that is
    its job. They are two states, not two readings of one."""
    K.project(world(), KernelRequest())
    t0 = "2026-08-18T12:00:00"
    a = run_at(0.1, t0).claims[0]
    b = run_at(0.9, t0).claims[0]
    assert a.valid_time.start != b.valid_time.start

    out = fuse([a, b], rules={"pose": inverse_variance})
    assert len(out.resolved) == 2, "two moments were merged into one"
    kept = sorted(c.roles["value"].value for c in out.resolved)
    assert kept == sorted([a.roles["value"].value, b.roles["value"].value]), (
        "the values were combined rather than kept apart")
    # and the thing that would have happened without the split
    merged = fuse([a, replace(b, valid_time=a.valid_time)],
                  rules={"pose": inverse_variance})
    assert len(merged.resolved) == 1
    assert min(kept) < merged.resolved[0].roles["value"].value < max(kept), (
        "same-time claims did not combine, so the split is not what separated "
        "the two horizons")


def test_two_estimates_of_the_SAME_moment_do_fuse():
    """The split must not break the case fusion is for."""
    t0 = "2026-08-18T12:00:00"
    pred = run_at(0.5, t0).claims[0]
    sensor = Claim("pose", {"of": EntityRef("ball"),
                            "value": Quantity(pred.roles["value"].value + 0.2,
                                              "m", 0.05)},
                   valid_time=pred.valid_time,
                   provenance=Provenance(producer="sensor"))
    out = fuse([pred, sensor], rules={"pose": inverse_variance})
    assert len(out.resolved) == 1


def test_an_untimed_prediction_says_so_rather_than_pretending():
    out = run(world())
    assert out.diagnostics["timed"] is False
    assert "at no time at all" in out.diagnostics["untimed_warning"]

    timed_out = run_at(0.1, "2026-08-18T12:00:00")
    assert timed_out.diagnostics["timed"] is True
    assert timed_out.diagnostics["untimed_warning"] == ""


def test_an_unparseable_epoch_does_not_become_a_fabricated_time():
    out = run_at(0.1, "next tuesday")
    assert out.diagnostics["timed"] is False
    assert out.claims[0].valid_time.unbounded


def run_at(dt, t0):
    return K.run(K.project(world(), KernelRequest()),
                 KernelRequest(params={"dt_s": dt, "t0": t0}))
