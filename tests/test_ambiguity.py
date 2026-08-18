"""Computing with a mixture instead of resolving it.

`fuse` retains a disagreement it cannot settle, and since the serialisation fix
the mixture survives leaving the process. Nothing read one -- and a retained
alternative no consumer can act on is a data structure, not a capability, with
the pressure to collapse it returning the moment a caller needs an answer.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.runtime.ambiguity import (Alternatives,
                                                AmbiguityExplosion,
                                                PossibleAnswers,
                                                alternatives_from,
                                                possible_answers)


class TestAlternatives:
    def test_a_settled_subject_does_not_belong_in_a_mixture(self):
        with pytest.raises(ValueError, match="is settled"):
            Alternatives({"x": ("only",)})

    def test_a_subject_with_no_values_is_a_hole_not_a_choice(self):
        with pytest.raises(ValueError, match="hole rather than a choice"):
            Alternatives({"x": ()})

    def test_worlds_multiply(self):
        a = Alternatives({"x": (1, 2), "y": (1, 2, 3)})
        assert a.world_count() == 6

    def test_no_choices_is_one_world(self):
        assert Alternatives({}).world_count() == 1


class TestPossibleAnswers:
    def test_an_irrelevant_conflict_gives_one_answer(self):
        """1,024 worlds that all give the same number is not an ambiguous
        result, it is an irrelevant conflict -- and that distinction is the
        whole point of computing rather than collapsing."""
        a = Alternatives({"x": (1, 2), "y": (3, 4)})
        r = possible_answers(lambda asg: "constant", a)
        assert not r.ambiguous and r.settled == "constant" and r.worlds == 4

    def test_a_relevant_conflict_gives_every_answer(self):
        a = Alternatives({"x": ("P1", "P2")})
        r = possible_answers(lambda asg: asg["x"], a)
        assert r.ambiguous and set(r.answers) == {"P1", "P2"}

    def test_each_answer_carries_the_choices_that_produce_it(self):
        a = Alternatives({"x": (1, 2), "y": (10, 20)})
        r = possible_answers(lambda asg: asg["x"] + asg["y"], a)
        assert r.answers[11] == ({"x": 1, "y": 10},)
        assert sum(len(v) for v in r.answers.values()) == 4

    def test_taking_the_single_answer_refuses_when_there_is_not_one(self):
        r = possible_answers(lambda asg: asg["x"], Alternatives({"x": (1, 2)}))
        with pytest.raises(ValueError, match="no single one to take"):
            r.settled

    def test_the_explosion_is_refused_and_never_truncated(self):
        """Truncating would return an answer set that looks complete and is
        not, which is worse than refusing."""
        big = Alternatives({i: ("a", "b") for i in range(20)})
        with pytest.raises(AmbiguityExplosion, match="1,048,576"):
            possible_answers(lambda asg: 1, big)

    def test_the_bound_is_a_parameter_not_a_constant(self):
        a = Alternatives({i: ("a", "b") for i in range(4)})
        with pytest.raises(AmbiguityExplosion):
            possible_answers(lambda asg: 1, a, max_worlds=8)
        assert possible_answers(lambda asg: 1, a, max_worlds=16).worlds == 16


class TestReadingAFusionResult:
    def test_it_reads_unresolved_groups_into_choices(self):
        from symbolic_ai_core.artifact.value import Provenance
        from symbolic_ai_core.runtime.fusion import (fuse, prefer_measured,
                                                     register_subject_roles)
        from symbolic_ai_core.world import Claim, EntityRef

        register_subject_roles("owns", ("of",))

        def c(parent, producer):
            return Claim("owns", {"of": EntityRef("x"),
                                  "parent": EntityRef(parent)},
                         provenance=Provenance(producer=producer,
                                               derivation="measured"))

        res = fuse([c("P1", "a"), c("P2", "b")],
                   rules={"owns": prefer_measured})
        alts = alternatives_from(res.unresolved,
                                 value=lambda cl: cl.roles["parent"].id)
        assert list(alts.choices.values()) == [("P1", "P2")]

    def test_a_group_whose_claims_agree_contributes_no_choice(self):
        class _G:
            predicate = "p"
            subject = ("x",)
            claims = ("same", "same")
        assert alternatives_from([_G()], value=lambda c: c).choices == {}

    def test_duplicate_values_collapse_to_one_option(self):
        class _G:
            predicate = "p"
            subject = ("x",)
            claims = ("A", "B", "A")
        alts = alternatives_from([_G()], value=lambda c: c)
        assert list(alts.choices.values()) == [("A", "B")]
