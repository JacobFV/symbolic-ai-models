"""A checkable derivation, and the two halves that do not cost the same."""

from __future__ import annotations

import pytest

from symbolic_ai_core.runtime.proof import (DistanceCertificate, ProofTrace,
                                            Step, VerificationError,
                                            verify_optimality, verify_witness)


def _walk() -> ProofTrace:
    return ProofTrace("3 legs under 2000 km",
                      (Step("A", "B", 100.0, 2000.0),
                       Step("B", "C", 150.0, 2000.0),
                       Step("C", "D", 900.0, 2000.0)),
                      sources=("snapshot/openflights",))


class TestWitness:
    def test_a_connected_walk_within_bounds_verifies(self):
        assert verify_witness(_walk()) == 3

    def test_a_broken_walk_is_refused(self):
        bad = ProofTrace("x", (Step("A", "B", 1.0, 10.0),
                               Step("Z", "C", 1.0, 10.0)))
        with pytest.raises(VerificationError, match="not a connected walk"):
            verify_witness(bad)

    def test_a_step_violating_its_bound_is_refused(self):
        bad = ProofTrace("x", (Step("A", "B", 9000.0, 2000.0),))
        with pytest.raises(VerificationError, match="fails <= 2000"):
            verify_witness(bad)

    def test_a_step_that_is_not_an_edge_is_refused(self):
        """Bounds alone do not make a route: the leg has to exist."""
        with pytest.raises(VerificationError, match="not adjacent"):
            verify_witness(_walk(), {"A": {"B"}, "B": {"C"}, "C": set()})

    def test_the_claimed_endpoints_are_checked(self):
        with pytest.raises(VerificationError, match="not the claimed source"):
            verify_witness(_walk(), source="Q")
        with pytest.raises(VerificationError, match="not the claimed target"):
            verify_witness(_walk(), target="Q")

    def test_verification_reads_only_the_trace(self):
        """The reason the existential half is 247x cheaper than solving: it
        never touches the rest of the graph."""
        assert verify_witness(_walk(), {"A": {"B"}, "B": {"C"}, "C": {"D"}}) == 3

    def test_a_failure_raises_rather_than_returning_false(self):
        """A bare False invites a caller to read a refutation as a missing
        value."""
        with pytest.raises(VerificationError):
            verify_witness(ProofTrace("x", (Step("A", "B", 5.0, 1.0),)))


class TestOptimality:
    def test_a_valid_labelling_certifies_the_answer(self):
        cert = DistanceCertificate("A", {"A": 0, "B": 1, "C": 2}, 2)
        assert verify_optimality(cert, {"A": ["B"], "B": ["C"]}, "C") == 2

    def test_a_source_not_at_zero_is_refused(self):
        cert = DistanceCertificate("A", {"A": 1}, 1)
        with pytest.raises(VerificationError, match="not 0"):
            verify_optimality(cert, {}, "A")

    def test_an_edge_skipping_a_level_is_refused(self):
        """The condition that costs: it quantifies over every edge, which is
        what a universal claim requires."""
        cert = DistanceCertificate("A", {"A": 0, "B": 1, "C": 3}, 3)
        with pytest.raises(VerificationError, match="skips a level"):
            verify_optimality(cert, {"A": ["B"], "B": ["C"]}, "C")

    def test_a_claim_disagreeing_with_the_labelling_is_refused(self):
        cert = DistanceCertificate("A", {"A": 0, "B": 1}, 5)
        with pytest.raises(VerificationError, match="but the claim is"):
            verify_optimality(cert, {"A": ["B"]}, "B")

    def test_an_unlevelled_node_does_not_invalidate_the_certificate(self):
        """Nodes beyond the search frontier are unconstrained; requiring them
        would make every bounded search uncertifiable."""
        cert = DistanceCertificate("A", {"A": 0, "B": 1}, 1)
        assert verify_optimality(cert, {"A": ["B"], "B": ["Z"],
                                        "Z": ["Q"]}, "B") == 1


class TestTraceShape:
    def test_a_trace_carries_where_its_facts_came_from(self):
        """A route certified from bytes under an unresolved licence is a route
        you may not be able to publish, and that travels with the answer."""
        assert _walk().sources == ("snapshot/openflights",)

    def test_endpoints_and_length_are_readable_without_verifying(self):
        assert _walk().endpoints() == ("A", "D") and _walk().length == 3

    def test_an_empty_trace_has_no_endpoints(self):
        assert ProofTrace("nothing", ()).endpoints() is None

    def test_a_trace_round_trips_to_json_shape(self):
        d = _walk().to_dict()
        assert d["steps"][0]["from"] == "A" and d["sources"] == [
            "snapshot/openflights"]
