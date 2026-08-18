"""Fusion: property-specific, never last-writer-wins.

The default is the interesting case. A property with no registered rule produces
an **unresolved mixture**, not a winner, because last-writer-wins is
indistinguishable from a correct answer at the point where it is read — and that
is exactly the shape of failure this repo has the longest history with.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.artifact import Provenance
from symbolic_ai_core.runtime import (ClaimGroup, fuse, group_claims,
                                      independent_odds, intersect_intervals,
                                      log_opinion_pool, register_fusion,
                                      sum_quantities)
from symbolic_ai_core.runtime.fusion import FUSION_RULES, FusionError
from symbolic_ai_core.world import Claim, EntityRef, Quantity


def claim(pred, producer, value=None, unit="m", *, stderr=None, conf=None,
          polarity="positive", subject="r"):
    roles = {"of": EntityRef(subject)}
    if value is not None:
        roles["value"] = Quantity(value, unit, stderr)
    return Claim(pred, roles, polarity=polarity, confidence=conf,
                 provenance=Provenance(producer=producer))


# --- the default ----------------------------------------------------------
def test_disagreement_with_no_rule_is_kept_as_a_mixture():
    r = fuse([claim("pose", "rigid", 1.0), claim("pose", "vision", 9.0)])
    assert r.resolved == ()
    assert len(r.unresolved) == 1
    assert r.unresolved[0].producers() == ("rigid", "vision")
    assert "arrival order" in " ".join(r.notes)
    assert not r.settled


def test_nothing_averages_two_arbitrary_state_vectors():
    """Plausibility is what makes this dangerous; there is no default rule."""
    assert "pose" not in FUSION_RULES
    assert "state" not in FUSION_RULES


def test_agreeing_claims_resolve_to_one():
    r = fuse([claim("mass", "a", 3.0, "kg"), claim("mass", "b", 3.0, "kg")])
    assert len(r.resolved) == 1 and r.settled


def test_a_lone_claim_passes_through():
    r = fuse([claim("mass", "a", 3.0, "kg")])
    assert len(r.resolved) == 1


def test_claims_about_different_subjects_are_not_a_disagreement():
    r = fuse([claim("mass", "a", 3.0, "kg", subject="r1"),
              claim("mass", "b", 9.0, "kg", subject="r2")])
    assert len(r.resolved) == 2 and r.settled


# --- the rules ------------------------------------------------------------
def test_forces_sum_and_errors_add_in_quadrature():
    r = fuse([claim("force", "a", 3.0, "N", stderr=0.3),
              claim("force", "b", 4.0, "N", stderr=0.4)],
             rules={"force": sum_quantities})
    q = r.resolved[0].roles["value"]
    assert q.value == pytest.approx(7.0)
    assert q.stderr == pytest.approx(math.hypot(0.3, 0.4))


def test_a_missing_stderr_makes_the_total_unknown_not_optimistic():
    r = fuse([claim("force", "a", 3.0, "N", stderr=0.3),
              claim("force", "b", 4.0, "N")],
             rules={"force": sum_quantities})
    assert r.resolved[0].roles["value"].stderr is None


def _pool(*confs):
    cs = tuple(Claim("raining", {"of": EntityRef("sf")}, confidence=c,
                     provenance=Provenance(producer=f"src{i}"))
               for i, c in enumerate(confs))
    return ClaimGroup("raining", ("sf",), cs)


def test_a_consensus_pool_does_not_reinforce():
    """Two sources at 0.9 pool to 0.9. Two thermometers reading 20 degrees do
    not imply 25, and a pool that reinforced would say they did."""
    assert log_opinion_pool(_pool(0.9, 0.9)).confidence == pytest.approx(0.9)


def test_a_consensus_pool_lets_an_impossibility_veto():
    assert log_opinion_pool(_pool(0.99, 0.0)).confidence == pytest.approx(0.0,
                                                                         abs=1e-5)


def test_reinforcement_is_a_separate_rule_with_a_stated_prior():
    """This is the operator people usually mean by 'combining evidence', and it
    is not the default because its independence assumption fails silently and
    always in the confident direction."""
    assert independent_odds(_pool(0.9, 0.9)).confidence > 0.98
    assert independent_odds(_pool(0.9), prior=0.5).confidence == pytest.approx(0.9)


def test_the_prior_changes_how_much_each_report_is_worth():
    """Counterintuitive and worth pinning: a source reporting 0.9 against a
    prior of 0.01 has supplied enormous evidence, while the same 0.9 against a
    prior of 0.9 has supplied none. So a LOWER prior gives a HIGHER posterior
    for the same reports -- which is why the prior is a required argument with
    no defensible default, and why 0.5 is stated ignorance rather than a fact."""
    same_reports = (0.9, 0.9)
    assert (independent_odds(_pool(*same_reports), prior=0.01).confidence
            > independent_odds(_pool(*same_reports), prior=0.5).confidence
            > independent_odds(_pool(*same_reports), prior=0.9).confidence)
    assert independent_odds(_pool(0.9, 0.9), prior=0.9).confidence == \
        pytest.approx(0.9), "against a matching prior, each report adds nothing"


def test_not_stated_confidence_is_not_certainty():
    g = ClaimGroup("raining", ("sf",),
                   (Claim("raining", {"of": EntityRef("sf")}),
                    Claim("raining", {"of": EntityRef("sf")})))
    with pytest.raises(FusionError, match="manufacture certainty"):
        log_opinion_pool(g)


def test_disjoint_intervals_are_a_contradiction_not_a_midpoint():
    r = fuse([claim("length", "a", 1.0, "m", stderr=0.1),
              claim("length", "b", 5.0, "m", stderr=0.1)],
             rules={"length": intersect_intervals})
    assert r.resolved == ()
    assert "disjoint" in " ".join(r.notes)
    assert len(r.unresolved) == 1


def test_overlapping_intervals_intersect():
    r = fuse([claim("length", "a", 2.0, "m", stderr=1.0),
              claim("length", "b", 3.0, "m", stderr=1.0)],
             rules={"length": intersect_intervals})
    q = r.resolved[0].roles["value"]
    assert q.value == pytest.approx(2.5) and q.stderr == pytest.approx(0.5)


def test_incompatible_units_do_not_fuse():
    r = fuse([claim("mass", "a", 3.0, "kg"), claim("mass", "b", 6.6, "lb")],
             rules={"mass": sum_quantities})
    assert r.resolved == ()
    assert "different units" in " ".join(r.notes)


# --- authority ------------------------------------------------------------
def test_a_veto_beats_a_majority():
    """An exact solver saying a configuration is infeasible is not one vote."""
    proposals = [claim("feasible", "planner_a", polarity="positive"),
                 claim("feasible", "planner_b", polarity="positive"),
                 claim("feasible", "planner_c", polarity="positive")]
    veto = claim("feasible", "smt@1", polarity="negative")
    r = fuse(proposals + [veto],
             authority={"smt@1": {"feasible": "veto"}})
    assert len(r.vetoed) == 3
    assert [c.provenance.producer for c in r.resolved] == ["smt@1"]


def test_a_negative_claim_without_authority_is_only_a_disagreement():
    r = fuse([claim("feasible", "planner", polarity="positive"),
              claim("feasible", "guesser", polarity="negative")],
             authority={"guesser": {"feasible": "propose"}})
    assert r.vetoed == ()
    assert len(r.unresolved) == 1, "an unauthorised veto silently won"


# --- registration ---------------------------------------------------------
def test_a_fusion_rule_cannot_be_silently_replaced():
    register_fusion("test_property_xyz", sum_quantities)
    try:
        with pytest.raises(ValueError, match="already registered"):
            register_fusion("test_property_xyz", intersect_intervals)
    finally:
        FUSION_RULES.pop("test_property_xyz", None)


def test_grouping_is_by_predicate_and_subject():
    gs = group_claims([claim("mass", "a", 1.0, subject="r1"),
                       claim("mass", "b", 2.0, subject="r1"),
                       claim("mass", "c", 3.0, subject="r2")])
    assert [(g.predicate, g.subject, len(g.claims)) for g in gs] == [
        ("mass", ("r1",), 2), ("mass", ("r2",), 1)]


# --- identity-valued claims, and the invariant that had no claim-layer form -
from symbolic_ai_core.artifact.value import Provenance as _Prov
from symbolic_ai_core.runtime.fusion import (DERIVATION_RANK, SUBJECT_ROLES,
                                             prefer_measured,
                                             register_subject_roles)


def _owner(entity: str, parent: str, derivation: str, producer: str = "p"):
    return Claim("ultimate_parent",
                 {"of": EntityRef(entity), "parent": EntityRef(parent)},
                 provenance=_Prov(producer=producer, derivation=derivation))


class TestSubjectRoles:
    def test_by_default_the_value_entity_lands_in_the_key(self):
        """The structural problem: with the value in the key, two sources
        naming two different parents produce two groups and the conflict is
        invisible -- not a missing fuser, an ungroupable disagreement."""
        SUBJECT_ROLES.pop("owns_default_demo", None)
        a = Claim("owns_default_demo", {"of": EntityRef("x"),
                                        "parent": EntityRef("p1")})
        b = Claim("owns_default_demo", {"of": EntityRef("x"),
                                        "parent": EntityRef("p2")})
        assert len(group_claims([a, b])) == 2

    def test_declaring_the_subject_makes_the_conflict_visible(self):
        register_subject_roles("ultimate_parent", ("of",))
        groups = group_claims([_owner("x", "p1", "derived"),
                               _owner("x", "p2", "measured")])
        assert len(groups) == 1 and len(groups[0].claims) == 2

    def test_a_subject_with_no_roles_is_refused(self):
        with pytest.raises(FusionError, match="at least one role"):
            register_subject_roles("nonsense", ())

    def test_numeric_claims_keep_the_old_key(self):
        """Registering one predicate must not change how any other groups."""
        a = Claim("mass", {"of": EntityRef("r"), "value": Quantity(1.0, "kg")})
        b = Claim("mass", {"of": EntityRef("r"), "value": Quantity(2.0, "kg")})
        assert len(group_claims([a, b])) == 1


class TestPreferMeasured:
    def test_a_measurement_outranks_an_inference(self):
        register_subject_roles("ultimate_parent", ("of",))
        g = group_claims([_owner("x", "guess", "derived"),
                          _owner("x", "filed", "measured")])[0]
        assert prefer_measured(g).roles["parent"].id == "filed"

    def test_the_order_the_claims_arrive_in_does_not_matter(self):
        """Which is the whole point: last-writer-wins rewrote 4,992 measured
        facts on the real filings depending on which source loaded second."""
        register_subject_roles("ultimate_parent", ("of",))
        one = [_owner("x", "guess", "derived"), _owner("x", "filed", "measured")]
        assert (prefer_measured(group_claims(one)[0]).roles["parent"].id ==
                prefer_measured(group_claims(one[::-1])[0]).roles["parent"].id)

    def test_the_result_keeps_the_derivation_it_preferred(self):
        """Otherwise "derived can never become measured" fails at the last
        step, having been enforced everywhere upstream."""
        register_subject_roles("ultimate_parent", ("of",))
        g = group_claims([_owner("x", "guess", "derived"),
                          _owner("x", "filed", "measured")])[0]
        assert prefer_measured(g).provenance.derivation == "measured"

    def test_fusing_two_inferences_does_not_promote_them(self):
        register_subject_roles("ultimate_parent", ("of",))
        g = group_claims([_owner("x", "same", "derived", "a"),
                          _owner("x", "same", "derived", "b")])[0]
        assert prefer_measured(g).provenance.derivation == "derived"

    def test_two_measurements_that_disagree_are_refused_not_resolved(self):
        """A real conflict between sources. Picking by arrival order is the
        failure this registry exists to prevent."""
        register_subject_roles("ultimate_parent", ("of",))
        g = group_claims([_owner("x", "p1", "measured", "gleif"),
                          _owner("x", "p2", "measured", "sec")])[0]
        with pytest.raises(FusionError, match="Keep both as alternatives"):
            prefer_measured(g)

    def test_an_unstated_derivation_ranks_with_unresolved(self):
        """A gap in the record is not evidence, but neither is it a finding
        that the provenance could not be established."""
        assert DERIVATION_RANK[""] == DERIVATION_RANK["unresolved"]
        assert DERIVATION_RANK["measured"] > DERIVATION_RANK["derived"]
        assert DERIVATION_RANK["derived"] > DERIVATION_RANK["simulated"]

    def test_agreement_at_the_top_rank_is_not_a_conflict(self):
        register_subject_roles("ultimate_parent", ("of",))
        g = group_claims([_owner("x", "same", "measured", "a"),
                          _owner("x", "same", "measured", "b")])[0]
        assert prefer_measured(g).roles["parent"].id == "same"
