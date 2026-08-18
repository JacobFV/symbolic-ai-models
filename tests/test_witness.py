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
