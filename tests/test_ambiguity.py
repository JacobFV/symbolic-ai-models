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
                                                additive_bounds,
                                                alternatives_from, exposure,
                                                possible_answers,
                                                possible_answers_scoped,
                                                rank_by_exposure)


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


class TestExposure:
    """How much an unresolved conflict costs, before enumerating it."""

    KIDS = {"hub": ["f0", "f1", "f2"], "f0": ["g0", "g1"]}

    def test_a_leaf_conflict_costs_one_answer(self):
        assert exposure("f2", self.KIDS) == 1

    def test_a_hub_conflict_costs_everything_beneath_it(self):
        assert exposure("hub", self.KIDS) == 6

    def test_an_unknown_node_is_a_leaf(self):
        assert exposure("nobody", self.KIDS) == 1

    def test_a_cycle_terminates(self):
        assert exposure("a", {"a": ["b"], "b": ["a"]}) == 2

    def test_a_diamond_counts_each_node_once(self):
        kids = {"a": ["b", "c"], "b": ["d"], "c": ["d"]}
        assert exposure("a", kids) == 4

    def test_ranking_puts_the_expensive_conflict_first(self):
        """The point is to see an expensive conflict BEFORE enumeration.
        `possible_answers` refuses an explosion, which is the right failure and
        a late one."""
        alts = Alternatives({("owns", ("f2",)): ("A", "B"),
                             ("owns", ("hub",)): ("C", "D")})
        ranked = rank_by_exposure(alts, self.KIDS, subject_of=lambda k: k[1][0])
        assert ranked[0][0] == ("owns", ("hub",)) and ranked[0][1] == 6
        assert ranked[-1][1] == 1

    def test_ranking_is_deterministic_on_ties(self):
        alts = Alternatives({("owns", ("f1",)): ("A", "B"),
                             ("owns", ("f2",)): ("C", "D")})
        a = rank_by_exposure(alts, self.KIDS, subject_of=lambda k: k[1][0])
        b = rank_by_exposure(alts, self.KIDS, subject_of=lambda k: k[1][0])
        assert a == b

    def test_exposure_is_not_a_property_of_the_graph_but_of_the_node(self):
        """The correction the last finding needed. The same graph gives 1 and
        6 depending only on where the conflict lands, and on GLEIF the spread
        is 1 to 3,848 inside a single relation."""
        assert exposure("f2", self.KIDS) != exposure("hub", self.KIDS)


class TestScopedEnumeration:
    """A query should pay for the conflicts it reads, not the ones that exist.

    `possible_answers` prices a query at the whole world's product, so 251
    retained GLEIF conflicts refuse *every* query -- including one whose answer
    depends on a single one of them.
    """

    @staticmethod
    def _many(n: int = 200) -> Alternatives:
        return Alternatives({f"c{i}": ("a", "b") for i in range(n)})

    def test_the_whole_world_product_refuses_what_one_conflict_decides(self):
        big = self._many()
        with pytest.raises(AmbiguityExplosion):
            possible_answers(lambda a: a["c7"], big)
        got = possible_answers_scoped(lambda a: a["c7"], big)
        assert set(got.answers) == {"a", "b"}
        assert got.worlds == 2
        assert got.read == ("c7",)

    def test_a_query_reading_two_conflicts_costs_four_worlds_not_2_pow_200(self):
        got = possible_answers_scoped(
            lambda a: (a["c1"], a["c2"]), self._many())
        assert got.worlds == 4
        assert len(got.answers) == 4
        assert set(got.read) == {"c1", "c2"}

    def test_it_agrees_with_full_enumeration_answer_for_answer(self):
        alts = Alternatives({"x": (1, 2), "y": (10, 20), "z": (100, 200)})

        def q(a):
            return a["x"] + a["y"]

        full, scoped = possible_answers(q, alts), possible_answers_scoped(q, alts)
        assert set(full.answers) == set(scoped.answers)
        assert full.worlds == 8 and scoped.worlds == 4

    def test_a_read_set_that_grows_with_the_choice_is_discovered(self):
        """The read set is not static: which conflict matters can depend on
        how an earlier one was settled, so one pass is not enough."""
        alts = Alternatives({"x": ("stop", "go"), "y": (1, 2)})

        def q(a):
            return a["x"] if a["x"] == "stop" else a["y"]

        got = possible_answers_scoped(q, alts)
        assert set(got.answers) == {"stop", 1, 2}
        assert set(got.read) == {"x", "y"}

    def test_the_defaults_pass_is_discarded_not_reported(self):
        """The first pass runs against first-alternative defaults. If its
        answers leaked into the result, `y`'s second value would be missing."""
        alts = Alternatives({"x": ("stop", "go"), "y": (1, 2)})
        got = possible_answers_scoped(
            lambda a: a["x"] if a["x"] == "stop" else a["y"], alts)
        assert got.worlds == 4
        assert sum(len(v) for v in got.answers.values()) == 4

    def test_a_genuinely_wide_query_is_still_refused_and_says_so(self):
        with pytest.raises(AmbiguityExplosion, match="reads 12 of 200"):
            possible_answers_scoped(
                lambda a: sum(a[f"c{i}"] == "a" for i in range(12)),
                self._many(), max_worlds=1024)

    def test_reading_a_settled_subject_is_a_key_error_not_a_silent_default(self):
        with pytest.raises(KeyError):
            possible_answers_scoped(lambda a: a["nope"], self._many())

    def test_iterating_the_assignment_counts_as_reading_all_of_it(self):
        """A computation that walks the whole mixture has depended on all of
        it as far as this can tell, and recording nothing there is how an
        exact method quietly becomes an approximate one."""
        alts = Alternatives({"x": (1, 2), "y": (1, 2)})
        with pytest.raises(AmbiguityExplosion):
            possible_answers_scoped(lambda a: sum(a.values()), alts,
                                    max_worlds=2)

    def test_a_query_reading_nothing_is_one_world(self):
        got = possible_answers_scoped(lambda a: 7, self._many())
        assert got.worlds == 1 and got.read == () and set(got.answers) == {7}

    def test_each_answer_carries_only_the_conflicts_it_rests_on(self):
        got = possible_answers_scoped(lambda a: a["c3"], self._many())
        for assignments in got.answers.values():
            for assignment in assignments:
                assert set(assignment) == {"c3"}


class TestAdditiveBounds:
    """The case scoping does not cover: a query that really does read all of
    them. A count over every ambiguous alignment is not enumerable and is not
    therefore unanswerable."""

    def test_the_bounds_are_the_enumerated_extremes_exactly(self):
        alts = Alternatives({f"c{i}": (0, 1, 3) for i in range(6)})
        contribution = lambda s, v: v
        full = possible_answers(lambda a: sum(a.values()), alts,
                                max_worlds=10_000)
        b = additive_bounds(alts, contribution)
        assert b.low == min(full.answers) and b.high == max(full.answers)

    def test_each_bound_is_attained_by_the_assignment_it_returns(self):
        alts = Alternatives({"a": (1, 5), "b": (2, -2)})
        b = additive_bounds(alts, lambda s, v: v, base=100.0)
        assert sum(b.low_choice.values()) + 100.0 == b.low
        assert sum(b.high_choice.values()) + 100.0 == b.high

    def test_a_conflict_whose_alternatives_score_alike_adds_no_width(self):
        alts = Alternatives({"same": ("gb", "gb2"), "differs": ("gb", "us")})
        b = additive_bounds(alts, lambda s, v: float(v.startswith("gb")))
        assert b.width == 1.0
        assert [s for s, _ in b.width_by_subject] == ["differs"]

    def test_width_attribution_is_widest_first(self):
        alts = Alternatives({"small": (0, 1), "big": (0, 10), "mid": (0, 5)})
        b = additive_bounds(alts, lambda s, v: v)
        assert [s for s, _ in b.width_by_subject] == ["big", "mid", "small"]

    def test_an_answer_no_conflict_can_move_is_determined(self):
        alts = Alternatives({"x": ("a", "b")})
        assert additive_bounds(alts, lambda s, v: 1.0).determined
        assert not additive_bounds(alts, lambda s, v: v == "a").determined


class TestTheRefusalIsActionable:
    def test_a_scoped_refusal_names_the_conflicts_the_query_depends_on(self):
        alts = Alternatives({f"c{i}": ("a", "b") for i in range(50)})
        with pytest.raises(AmbiguityExplosion) as exc:
            possible_answers_scoped(
                lambda a: tuple(a[f"c{i}"] for i in range(15)), alts,
                max_worlds=64)
        assert set(exc.value.read) == {f"c{i}" for i in range(15)}
        assert exc.value.worlds == 2 ** 15

    def test_a_whole_world_refusal_names_nothing_rather_than_lying(self):
        """`possible_answers` has no query-specific read set to report, and an
        empty tuple says so; inventing one would be worse than none."""
        alts = Alternatives({f"c{i}": ("a", "b") for i in range(50)})
        with pytest.raises(AmbiguityExplosion) as exc:
            possible_answers(lambda a: a["c0"], alts)
        assert exc.value.read == ()
