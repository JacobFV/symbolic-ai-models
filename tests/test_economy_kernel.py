"""Economy: consolidated aggregates as known on a date.

The kernel exists for one clause — *using only figures whose transaction_time
precedes the as-of date* — and every test here is about that clause or about the
ways a total can be silently wrong without it.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.artifact import Interval
from symbolic_ai_core.world import (Claim, Entity, EntityRef, Quantity,
                                    WorldSnapshot)
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.economy import as_of_value, project_world

K = get_kernel("economy@1")


def obs(entity, value, period="2026Q1", known="2026-04-30", unit="USD",
        **kw):
    return Claim("revenue", {"of": EntityRef(entity),
                             "value": Quantity(value, unit)},
                 valid_time=Interval(period, period),
                 transaction_time=Interval(known, known), **kw)


def group_world(extra=()):
    return WorldSnapshot(
        entities={n: Entity(n, types=("actor",))
                  for n in ("grp", "sub_a", "sub_b")},
        claims=(Claim("owns", {"parent": EntityRef("grp"),
                               "child": EntityRef("sub_a")}),
                Claim("owns", {"parent": EntityRef("grp"),
                               "child": EntityRef("sub_b")}),
                obs("sub_a", 100.0, known="2026-04-30"),
                obs("sub_a", 120.0, known="2026-07-31"),      # revised up
                obs("sub_b", 50.0, known="2026-05-15"),
                obs("grp", 10.0, known="2026-04-30")) + tuple(extra))


def run(world, **params):
    return K.run(K.project(world, KernelRequest()), KernelRequest(params={
        "period": "2026Q1", "of": ["grp"], **params}))


# --- the clause the kernel exists for ------------------------------------
@pytest.mark.parametrize("as_of,expected,missing", [
    ("2026-05-01", 110.0, ["sub_b"]),   # sub_b has not reported yet
    ("2026-06-01", 160.0, []),          # all in, sub_a at its first vintage
    ("2026-08-01", 180.0, []),          # sub_a revised 100 -> 120
])
def test_the_same_quarter_has_three_answers_depending_on_when_you_ask(
        as_of, expected, missing):
    r = run(group_world(), as_of=as_of)
    assert r.claims[0].roles["value"].value == pytest.approx(expected)
    assert r.artifacts["coverage"][0]["missing"] == missing


def test_as_of_is_required_because_the_only_default_is_the_bug():
    r = K.run(K.project(group_world(), KernelRequest()),
              KernelRequest(params={"period": "2026Q1"}))
    assert not r.ok
    assert "look-ahead" in r.refused and "'now'" in r.refused


def test_a_period_is_required_so_a_quarter_is_not_added_to_a_year():
    r = K.run(K.project(group_world(), KernelRequest()),
              KernelRequest(params={"as_of": "2026-08-01"}))
    assert not r.ok and "adding a quarter to a year" in r.refused.replace(
        "add a quarter to a year", "adding a quarter to a year")


def test_a_figure_not_yet_published_is_absent_not_zero():
    v, known, n = as_of_value(
        project_world(group_world()).program.observations,
        "sub_b", "revenue", "2026Q1", "2026-05-01")
    assert v is None and n == 0, (
        "an unpublished figure came back as a number; a zero here would make "
        "every early total look like a collapse")


def test_the_latest_vintage_on_or_before_the_date_is_the_one_used():
    obs_ = project_world(group_world()).program.observations
    assert as_of_value(obs_, "sub_a", "revenue", "2026Q1", "2026-06-01")[0] == 100.0
    assert as_of_value(obs_, "sub_a", "revenue", "2026Q1", "2026-08-01")[0] == 120.0


def test_an_incomplete_subtree_is_counted_rather_than_smoothed_over():
    """A partial sum silently labelled complete is the second way a
    vintage-aware number goes wrong."""
    early = run(group_world(), as_of="2026-05-01")
    late = run(group_world(), as_of="2026-06-01")
    assert early.diagnostics["incomplete"] == 1
    assert late.diagnostics["incomplete"] == 0


def test_the_claim_carries_both_times():
    c = run(group_world(), as_of="2026-08-01").claims[0]
    assert c.valid_time.start == "2026Q1"
    assert c.transaction_time.start == "2026-08-01"
    assert c.valid_time.start != c.transaction_time.start


def test_two_as_of_dates_do_not_fuse_into_one_number():
    """The time is part of the type, and here both times are."""
    from symbolic_ai_core.runtime import fuse, inverse_variance

    a = run(group_world(), as_of="2026-06-01").claims[0]
    b = run(group_world(), as_of="2026-08-01").claims[0]
    out = fuse([a, b], rules={"consolidated": inverse_variance})
    # valid_time is the same quarter for both, so they group -- and disagree
    # without an error bar, which the rule refuses rather than averaging.
    assert out.resolved == () and len(out.unresolved) == 1


# --- what the projection refuses -----------------------------------------
def test_an_observation_without_a_publication_date_is_discarded_by_name():
    w = WorldSnapshot(
        entities={"a": Entity("a", types=("actor",))},
        claims=(Claim("revenue", {"of": EntityRef("a"),
                                  "value": Quantity(1.0, "USD")},
                      valid_time=Interval("2026Q1", "2026Q1")),))
    p = project_world(w)
    assert p.program.observations == []
    assert any("optimistic" in d.why for d in p.discarded)


def test_an_observation_without_a_period_is_discarded():
    w = WorldSnapshot(
        entities={"a": Entity("a", types=("actor",))},
        claims=(Claim("revenue", {"of": EntityRef("a"),
                                  "value": Quantity(1.0, "USD")},
                      transaction_time=Interval("2026-04-30", "2026-04-30")),))
    assert any("arbitrary choice of which quarter" in d.why
               for d in project_world(w).discarded)


def test_a_forecast_is_not_aggregated_into_a_total():
    w = group_world([obs("sub_a", 999.0, known="2026-04-30",
                         modality="hypothesised")])
    r = run(w, as_of="2026-08-01")
    assert r.claims[0].roles["value"].value == pytest.approx(180.0)
    assert any("hypothesis into a total" in d.why
               for d in K.project(w, KernelRequest()).discarded)


def test_a_second_parent_is_refused_rather_than_double_counted():
    w = group_world([Claim("owns", {"parent": EntityRef("sub_b"),
                                    "child": EntityRef("sub_a")})])
    p = K.project(w, KernelRequest())
    assert any("double count" in d.why for d in p.discarded)
    assert K.run(p, KernelRequest(params={
        "as_of": "2026-08-01", "period": "2026Q1",
        "of": ["grp"]})).claims[0].roles["value"].value == pytest.approx(180.0)


def test_an_ownership_cycle_is_refused():
    w = group_world([Claim("owns", {"parent": EntityRef("sub_a"),
                                    "child": EntityRef("grp")})])
    with pytest.raises(ValueError, match="once per lap"):
        project_world(w)


def test_nothing_projectable_is_a_refusal():
    r = K.run(K.project(WorldSnapshot(), KernelRequest()),
              KernelRequest(params={"as_of": "2026-08-01", "period": "2026Q1"}))
    assert not r.ok and "read as-of any moment" in r.refused


def test_the_manifest_declares_two_clocks_and_only_proposes():
    assert K.manifest.clocks == "valid_and_transaction"
    assert K.manifest.authority["consolidated"] == "propose"
    assert K.manifest.runtime == "native" and K.manifest.dependencies == ()
