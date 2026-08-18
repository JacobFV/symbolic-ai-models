"""Every registered kernel states what it does about each ABI contract.

Three fields in this substrate have now been found documented and never
exercised: ``add_facts``' delta-proportional cost (false by three orders of
magnitude), ``cost_estimator`` (absent from every kernel), and ``budget_ns``
(read nowhere). Three is a pattern rather than three accidents -- a field added
while designing gets exercised by the design discussion and then never again.

This file is the guard. It enumerates the registered kernels against an explicit
table, so a kernel cannot be added, and a contract cannot be introduced, without
somebody writing down what the kernel does about it. **There is no silent
default**: a kernel either honours a contract, or declines it with a reason that
a reader can disagree with.
"""

from __future__ import annotations

import inspect

import pytest

from symbolic_ai_kernels import get_kernel, kernel_ids
from symbolic_ai_kernels.abi import (ANSWERED, EXHAUSTED, OUTCOMES,
                                     PROVED_IMPOSSIBLE, REFUSED)

#: Why a kernel does not honour ``budget_ns``. A reason, never a bare False,
#: because "no" and "nobody has done it yet" are different states and only one
#: of them is a design decision.
NO_BUDGET_NEEDED = ("terminates in time proportional to its input with no "
                    "search, so a budget could only cut off a computation that "
                    "was going to finish anyway")
NOT_YET = "NOT YET IMPLEMENTED -- this is a known gap, not a decision"

#: kernel -> (honours budget_ns, why not, sets a typed outcome)
CONFORMANCE: dict[str, tuple[bool, str, bool]] = {
    "asp@1":      (True,  "", True),
    "smt@1":      (True,  "", True),
    "datalog@1":  (False, NO_BUDGET_NEEDED, False),
    "geo@1":      (False, NO_BUDGET_NEEDED, False),
    "rigid@1":    (False, NO_BUDGET_NEEDED, False),
    "economy@1":  (False, NO_BUDGET_NEEDED, False),
    "lean@1":     (False, NOT_YET, False),
    "egraph@1":   (False, NOT_YET, False),
}


def test_every_registered_kernel_appears_in_the_table():
    """The guard that makes the rest of this file impossible to bypass: a new
    kernel fails here until somebody states what it does."""
    assert set(kernel_ids()) == set(CONFORMANCE), (
        "a kernel was registered or removed without declaring its conformance")


@pytest.mark.parametrize("kid", sorted(CONFORMANCE))
def test_a_declined_contract_carries_a_reason(kid):
    honours, why, _ = CONFORMANCE[kid]
    assert honours or why, f"{kid} declines budget_ns with no reason given"


@pytest.mark.parametrize("kid", sorted(CONFORMANCE))
def test_the_table_matches_what_the_kernel_actually_does(kid):
    """Declaring conformance is not conforming. This reads the source."""
    honours, _, sets_outcome = CONFORMANCE[kid]
    src = inspect.getsource(type(get_kernel(kid)))
    assert ("budget_ns" in src) == honours, (
        f"{kid}: the table says budget honoured={honours}, the source "
        f"{'does' if 'budget_ns' in src else 'does not'} read budget_ns")
    assert ("outcome=" in src) == sets_outcome, (
        f"{kid}: the table says outcome={sets_outcome}, the source disagrees")


@pytest.mark.parametrize("kid", sorted(CONFORMANCE))
def test_every_kernel_answers_availability_without_raising(kid):
    """Roadmap item 5: refuse loudly, never degrade silently. A kernel whose
    toolchain is missing must *say so*, not throw an import error at the
    caller."""
    ok, why = get_kernel(kid).available()
    assert isinstance(ok, bool)
    assert ok or why, f"{kid} is unavailable and will not say why"


@pytest.mark.parametrize("kid", sorted(CONFORMANCE))
def test_an_external_kernel_names_its_dependency(kid):
    m = get_kernel(kid).manifest
    if m.runtime == "external":
        assert m.dependencies, (
            f"{kid} says it is external and names no dependency, so a missing "
            "toolchain cannot be diagnosed from the manifest")


class TestOutcomeVocabulary:
    def test_the_vocabulary_is_closed(self):
        assert set(OUTCOMES) == {ANSWERED, PROVED_IMPOSSIBLE, EXHAUSTED,
                                 REFUSED}

    def test_the_solver_kernels_are_the_ones_that_need_it(self):
        """Only a kernel that can run out of time needs to distinguish
        exhaustion from impossibility; the others cannot be exhausted."""
        needs = {k for k, (b, _, _) in CONFORMANCE.items() if b}
        assert needs == {"asp@1", "smt@1"}
        assert all(CONFORMANCE[k][2] for k in needs)


class TestKnownGaps:
    def test_the_gaps_are_listed_rather_than_forgotten(self):
        """`lean@1` and `egraph@1` both search and neither takes a budget.
        Naming them here is the difference between a known gap and an
        oversight -- and this test fails the day the list is emptied by
        implementation rather than by deletion."""
        gaps = {k for k, (_, why, _) in CONFORMANCE.items() if why == NOT_YET}
        assert gaps == {"lean@1", "egraph@1"}
