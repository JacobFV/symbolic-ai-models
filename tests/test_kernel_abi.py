"""The kernel contract: manifests, projections that declare their losses, and
claims a kernel is not entitled to make.

The single most important test here is
``test_a_kernel_may_not_claim_over_what_it_discarded``. Everything else in the
kernel layer is machinery; that one is the property that makes a *lossy*
projection safe to build on, and without it a kernel answering about a fragment
returns something indistinguishable from an answer about the world.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.world import Claim, Entity, EntityRef, Facet, WorldSnapshot
from symbolic_ai_kernels import (Discard, KernelManifest, KernelRequest,
                                 KernelResult, KernelUnavailable, Projection,
                                 check_entitlement, get_kernel, register_kernel)


def proj(covered=("a", "b"), discarded=()) -> Projection:
    return Projection(kernel="test@1", program=None,
                      semantics=("closed_world",),
                      covered_entities=frozenset(covered),
                      discarded=tuple(discarded))


# --- the manifest ---------------------------------------------------------
def test_a_kernel_id_must_be_versioned():
    with pytest.raises(ValueError, match="no version"):
        KernelManifest(id="datalog")


def test_semantics_is_a_set_and_is_checked():
    m = KernelManifest(id="k@1", semantics=("closed_world", "non_monotonic"))
    assert m.to_dict()["semantics"] == ["closed_world", "non_monotonic"]
    with pytest.raises(ValueError, match="semantics"):
        KernelManifest(id="k@1", semantics=("vibes",))
    with pytest.raises(ValueError, match="semantics"):
        KernelManifest(id="k@1", semantics=())


def test_required_profiles_must_exist():
    with pytest.raises(ValueError, match="unknown profile"):
        KernelManifest(id="k@1", requires=("scene.bodyy",))


def test_authority_is_a_closed_vocabulary():
    KernelManifest(id="k@1", authority={"proof_validity": "veto"})
    with pytest.raises(ValueError, match="authority"):
        KernelManifest(id="k@1", authority={"proof_validity": "usually"})


def test_a_kernel_cannot_be_registered_twice():
    with pytest.raises(ValueError, match="already registered"):
        register_kernel(get_kernel("datalog@1"))


# --- the entitlement rule -------------------------------------------------
def test_a_kernel_may_not_claim_over_what_it_discarded():
    p = proj(covered=("a", "b"),
             discarded=[Discard("entity", "c", "no scene.pose facet")])
    ok = [Claim("near", {"x": EntityRef("a"), "y": EntityRef("b")})]
    check_entitlement(p, ok)                     # covered: fine

    bad = [Claim("near", {"x": EntityRef("a"), "y": EntityRef("c")})]
    with pytest.raises(ValueError, match="never covered"):
        check_entitlement(p, bad)


def test_a_partially_discarded_entity_is_still_claimable():
    """A kernel is entitled to reason about the part it covered. The discard
    record is what lets a consumer decide whether that was enough."""
    p = proj(covered=("a",),
             discarded=[Discard("facet", "a.scene.shape", "mesh not projectable")])
    check_entitlement(p, [Claim("moves", {"what": EntityRef("a")})])
    assert not p.lossless


def test_a_lossless_projection_says_so():
    assert proj().lossless


# --- refusal is a first-class outcome ------------------------------------
def test_a_refusal_carries_its_reason():
    r = KernelResult(kernel="k@1", refused="clingo is not installed")
    assert not r.ok
    assert "clingo" in r.to_dict()["refused"]
    assert r.claims == () and r.delta.is_empty()


def test_an_unavailable_toolchain_raises_rather_than_returning_nothing():
    """An empty result from a missing solver is indistinguishable from a solver
    that found nothing. That ambiguity is what this exception exists to remove."""
    class Missing:
        manifest = KernelManifest(id="clingo@1", runtime="external",
                                  dependencies=("clingo>=5",))

        def available(self):
            return False, "clingo is not importable on this machine"

        def project(self, world, request):
            ok, why = self.available()
            if not ok:
                raise KernelUnavailable(f"{self.manifest.id}: {why}")
            raise AssertionError                              # pragma: no cover

        def run(self, projection, request):                   # pragma: no cover
            raise AssertionError

    k = Missing()
    assert k.available()[0] is False
    with pytest.raises(KernelUnavailable, match="not importable"):
        k.project(WorldSnapshot(), KernelRequest())


# --- cost -----------------------------------------------------------------
def test_an_unpriced_kernel_reports_none_not_zero():
    from symbolic_ai_kernels import KernelCost
    assert KernelCost().usd is None, (
        "a zero that means 'not measured' is the confusion the cost module was "
        "written after")


def test_cpu_and_wall_are_recorded_separately():
    """Money is charged for cores held; usability is decided by elapsed time. A
    kernel blocking on a subprocess is cheap and unusable at once."""
    from symbolic_ai_kernels import KernelCost
    from symbolic_ai_kernels.abi import price_cpu_ns

    c = KernelCost(cpu_ns=1_000_000, wall_ns=50_000_000)
    assert c.cpu_ns != c.wall_ns
    assert price_cpu_ns(3_600 * 10 ** 9) == pytest.approx(0.02), (
        "one core-hour should cost the price sheet's core-hour rate")


# --- the world is not mutated --------------------------------------------
def test_a_kernel_cannot_mutate_the_world_it_projects():
    w = WorldSnapshot(
        entities={"a": Entity("a", types=("thing",),
                              facets={"logic.term": Facet("logic.term", {})})},
        claims=(Claim("p", {"x": EntityRef("a")}),))
    before = w.to_dict()
    k = get_kernel("datalog@1")
    p = k.project(w, KernelRequest())
    assert w.to_dict() == before
    assert p.covers("a")
