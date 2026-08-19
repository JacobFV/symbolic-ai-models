"""A kernel may return a witness; it may not invent one.

The asymmetry these tests guard is measured, not stylistic:
`notes/findings/2026-08-18-a-witness-grows-linearly-and-its-complement-grows-with-the-ball.md`.
An existential answer has a certificate whose size grows linearly in the answer;
its universal complement's grows with the search space that has to be excluded —
2.0x apart at d=2 on the route network and 874x at d=10. So the field exists for
one of them and deliberately not for the other, and the failure mode worth
testing is a kernel filling it in anyway.
"""

from __future__ import annotations

import pytest

from symbolic_ai_kernels.abi import (ANSWERED, PROVED_IMPOSSIBLE, KernelResult,
                                     Witness)


class TestWitness:
    def test_an_empty_witness_is_refused(self):
        # It would read like a certificate at every call site that checks
        # `is not None`, and certify nothing.
        with pytest.raises(ValueError):
            Witness(kind="model", facts=())

    def test_size_is_the_number_of_facts(self):
        assert Witness(kind="path", facts=("a", "b", "c")).size == 3

    def test_it_serialises_with_how_to_check_it(self):
        d = Witness(kind="cover", facts=("f1",), claim="a cover of size 1",
                    verifies="each item is held by the named filer").to_dict()
        assert d["size"] == 1 and d["verifies"]


class TestKernelResult:
    def test_no_witness_by_default(self):
        # A kernel that has not thought about it must not claim one.
        assert KernelResult(kernel="k@1").witness is None
        assert not KernelResult(kernel="k@1").maintainable

    def test_maintainable_iff_a_witness_is_present(self):
        r = KernelResult(kernel="k@1",
                         witness=Witness(kind="model", facts=("p(a)",)))
        assert r.maintainable

    def test_a_proof_of_impossibility_is_conclusive_and_not_maintainable(self):
        # The distinction the whole finding turns on. `proved_impossible` is an
        # answer, often the most valuable one — and it has no short certificate,
        # so it can only be maintained by re-establishing it.
        r = KernelResult(kernel="k@1", outcome=PROVED_IMPOSSIBLE,
                         refused="unsatisfiable")
        assert r.conclusive and r.proved_impossible
        assert not r.maintainable

    def test_witness_survives_to_dict(self):
        r = KernelResult(kernel="k@1", outcome=ANSWERED,
                         witness=Witness(kind="model", facts=("p(a)", "q(b)")))
        assert r.to_dict()["witness"]["size"] == 2

    def test_to_dict_carries_none_rather_than_omitting_it(self):
        # A reader must be able to tell "this kernel has no witness" from
        # "this artifact predates witnesses".
        assert "witness" in KernelResult(kernel="k@1").to_dict()


class TestAspKernelWitness:
    """The ASP kernel held its answer set and threw it away.

    Note the shape of the first version of these tests: they passed a ``rules``
    parameter the kernel does not take, so the projection was **empty**, the
    solver returned one empty stable model, and both tests exercised the
    degenerate path rather than the one they named. That is what produced the
    ``vacuous`` flag on :class:`Witness` — a real distinction, found by a
    mistake, and the flag stays because the distinction is real.
    """

    def _kernel(self):
        pytest.importorskip("clingo")
        from symbolic_ai_kernels.asp.kernel import AspKernel
        k = AspKernel()
        ok, why = k.available()
        if not ok:                                        # pragma: no cover
            pytest.skip(why)
        return k

    def test_a_unique_completion_returns_its_answer_set(self):
        from symbolic_ai_core.world import WorldSnapshot
        from symbolic_ai_kernels.abi import KernelRequest
        k = self._kernel()
        proj = k.project(WorldSnapshot(), KernelRequest(
            params={"program": "p(a). p(b). q(X) :- p(X)."}))
        res = k.run(proj, KernelRequest())
        assert res.ok and res.diagnostics["unique"]
        assert res.maintainable
        assert res.witness.kind == "answer_set"
        assert res.witness.size > 0 and not res.witness.vacuous
        assert res.witness.verifies

    def test_an_unsatisfiable_program_returns_no_witness(self):
        from symbolic_ai_core.world import WorldSnapshot
        from symbolic_ai_kernels.abi import KernelRequest
        k = self._kernel()
        proj = k.project(WorldSnapshot(), KernelRequest(
            params={"program": "p(a).", "constraints": [":- p(a)."]}))
        res = k.run(proj, KernelRequest())
        assert res.proved_impossible
        assert res.witness is None and not res.maintainable

    def test_several_answer_sets_yield_no_witness_either(self):
        # Same reason the delta is empty for a non-unique completion: the first
        # answer set is a choice the caller never made. A witness for one of
        # three hypotheses would read as a witness for the world.
        from symbolic_ai_core.world import WorldSnapshot
        from symbolic_ai_kernels.abi import KernelRequest
        k = self._kernel()
        proj = k.project(WorldSnapshot(), KernelRequest(
            params={"program": "d(a). d(b). { p(X) } :- d(X)."}))
        res = k.run(proj, KernelRequest())
        assert res.ok and not res.diagnostics["unique"]
        assert res.witness is None

    def test_an_empty_unique_model_is_vacuous_not_missing(self):
        # The degenerate case the first version of this file hit by accident.
        from symbolic_ai_core.world import WorldSnapshot
        from symbolic_ai_kernels.abi import KernelRequest
        k = self._kernel()
        res = k.run(k.project(WorldSnapshot(), KernelRequest(params={})),
                    KernelRequest())
        if not (res.ok and res.diagnostics["unique"]):     # pragma: no cover
            pytest.skip("the empty projection did not give a unique model")
        assert res.witness is not None and res.witness.vacuous
        assert res.witness.size == 0


class TestSmtWitness:
    """The satisfying assignment was already computed and handed out unlabelled.

    Built on the fixtures the existing SMT tests use, rather than on invented
    parameter names. The first version of this file guessed the shapes and
    tested nothing; the lesson note about that is
    `2026-08-18-a-test-that-passes-an-unknown-parameter-tests-the-empty-case.md`
    and it was written by me, three hours before I did it again.
    """

    def test_sat_returns_the_model_as_a_witness(self):
        pytest.importorskip("z3")
        from tests.test_smt_kernel import K, robot, under_20kg
        from symbolic_ai_kernels.abi import KernelRequest
        req = KernelRequest(params={"constraints": under_20kg()})
        r = K.run(K.project(robot(), req), req)
        assert r.ok and r.diagnostics["satisfiable"]      # the path, not the outcome
        assert r.maintainable and r.witness.kind == "model"
        assert r.witness.size >= 1 and r.witness.verifies

    def test_unsat_returns_none_because_the_universal_half_has_no_witness(self):
        pytest.importorskip("z3")
        from tests.test_smt_kernel import K, robot, under_20kg
        from symbolic_ai_kernels.abi import KernelRequest
        req = KernelRequest(params={"constraints": under_20kg() + [
            {"op": ">=", "args": [{"var": "mass@robot"},
                                  {"q": {"value": 900, "unit": "kg"}}]}]})
        r = K.run(K.project(robot(), req), req)
        if not r.proved_impossible:                       # pragma: no cover
            pytest.skip("this fixture stayed satisfiable")
        assert r.witness is None and not r.maintainable


class TestDatalogWitness:
    """Opt-in, because recording derivations changes `evaluate`'s cost profile."""

    def test_no_witness_by_default_and_the_diagnostics_say_why(self):
        from tests.test_datalog_kernel import ANCESTRY, world
        from symbolic_ai_kernels.abi import KernelRequest
        from symbolic_ai_kernels.datalog.kernel import DATALOG as k
        req = KernelRequest(params={"rules": ANCESTRY})
        r = k.run(k.project(world(), req), req)
        assert r.ok and r.diagnostics["derived"] > 0      # the path was real
        assert r.witness is None
        assert "witness_for" in r.diagnostics["witness"]

    def test_a_requested_goal_returns_its_derivation(self):
        from tests.test_datalog_kernel import ANCESTRY, world
        from symbolic_ai_kernels.abi import KernelRequest
        from symbolic_ai_kernels.datalog.kernel import DATALOG as k
        base = k.run(k.project(world(), KernelRequest(params={"rules": ANCESTRY})),
                     KernelRequest())
        goal = sorted(base.claims, key=lambda c: repr(c.roles))[0]
        # roles hold EntityRef, whose repr is "EntityRef(id='b')" — str() here
        # produces a constant that matches nothing and the goal reads as
        # underivable. The fact's constants are the bare ids.
        args = [getattr(v, "id", v) for v in goal.roles.values()]
        req = KernelRequest(params={
            "rules": ANCESTRY,
            "witness_for": {"predicate": goal.predicate, "args": args}})
        r = k.run(k.project(world(), req), req)
        assert r.ok
        assert r.witness is not None, (
            f"{goal.predicate}{args} was derived by the default path, so it "
            "must have a derivation")
        assert r.witness.kind == "derivation"
        assert r.witness.size >= 1 and r.witness.verifies
        assert r.diagnostics["witness_nodes"] >= 1

    def test_an_underivable_goal_gets_no_tree_and_says_so(self):
        from tests.test_datalog_kernel import ANCESTRY, world
        from symbolic_ai_kernels.abi import KernelRequest
        from symbolic_ai_kernels.datalog.kernel import DATALOG as k
        req = KernelRequest(params={
            "rules": ANCESTRY,
            "witness_for": {"predicate": "ancestor",
                            "args": ["nobody", "nowhere"]}})
        r = k.run(k.project(world(), req), req)
        assert r.witness is None
        assert "not derivable" in r.diagnostics["witness"]


class TestWitnessCoverage:
    """Where the witness contract stands, in three categories rather than two.

    `Witness`'s contract says a kernel with no witness must leave the field
    ``None`` rather than invent one, so a kernel in the second or third group is
    **conforming**. The point of this test is that the groups are a deliberate,
    checked classification instead of an accident, and that a new kernel must
    join one of them explicitly.

    The three-way split is the honest one, and the difference between the second
    and third groups is where the remaining work is:

    * **CARRIES** — the answer is existential and the kernel returns the object
      that makes it checkable.
    * **COULD, DOES NOT** — the answer is existential and the witness exists in
      principle but is not recorded. `egraph@1` claims ``equivalent_form``,
      whose witness is the rewrite sequence; `SaturationReport` counts rule
      applications but keeps no ordered path, so there is nothing to hand back.
      This is the group worth emptying.
    * **NONE TO HAVE** — the answer is a computed *value*, not an existential
      claim. A pose, a geodesic distance, a consolidated total: there is no
      "here is why" shorter than the computation, because the computation is a
      function evaluation rather than a search.
    """

    CARRIES = {"asp@1", "smt@1", "lean@1", "datalog@1"}
    COULD_BUT_DOES_NOT = {"egraph@1"}
    NONE_TO_HAVE = {"rigid@1", "geo@1", "economy@1"}

    def test_every_kernel_is_classified(self):
        from symbolic_ai_kernels.abi import kernel_ids
        known = self.CARRIES | self.COULD_BUT_DOES_NOT | self.NONE_TO_HAVE
        missing = set(kernel_ids()) - known
        assert not missing, (
            f"{sorted(missing)} are unclassified. A new kernel must say whether "
            "its answer is existential and whether it returns the witness.")

    def test_the_groups_do_not_overlap(self):
        assert not (self.CARRIES & self.COULD_BUT_DOES_NOT)
        assert not (self.CARRIES & self.NONE_TO_HAVE)
        assert not (self.COULD_BUT_DOES_NOT & self.NONE_TO_HAVE)

    def test_the_carriers_construct_one(self):
        import importlib
        from symbolic_ai_kernels.abi import KERNEL_MODULES
        for kid in sorted(self.CARRIES):
            mod = importlib.import_module(KERNEL_MODULES[kid] + ".kernel")
            assert "Witness(" in open(mod.__file__).read(), (
                f"{kid} is listed as carrying a witness and never builds one")

    def test_the_others_do_not_quietly_construct_one(self):
        # The failure this guards: a kernel joining the contract without being
        # reclassified, so the map above silently stops describing the code.
        import importlib
        from symbolic_ai_kernels.abi import KERNEL_MODULES
        for kid in sorted(self.COULD_BUT_DOES_NOT | self.NONE_TO_HAVE):
            mod = importlib.import_module(KERNEL_MODULES[kid] + ".kernel")
            assert "Witness(" not in open(mod.__file__).read(), (
                f"{kid} now builds a witness — move it to CARRIES")
