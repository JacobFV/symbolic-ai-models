"""Geo: geodesic distance on a stated datum, and the coordinate errors it catches.

Anchored on published distances rather than on itself. A geodesy implementation
that agrees with its own previous output is a regression test, not a correctness
one, and this repo's standing rule is that an evaluation needs a ground-truth
anchor.
"""

from __future__ import annotations

import math

import pytest

from symbolic_ai_core.world import Entity, Facet, WorldSnapshot
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.geo import (SUPPORTED_CRS, distance_km, haversine_km,
                                     project_world, vincenty_km)

K = get_kernel("geo@1")

CITIES = {"london": (51.5074, -0.1278), "paris": (48.8566, 2.3522),
          "berlin": (52.5200, 13.4050), "madrid": (40.4168, -3.7038),
          "newyork": (40.7128, -74.0060), "sydney": (-33.8688, 151.2093)}


def world(cities=None, crs="EPSG:4326", **overrides):
    cities = cities or CITIES
    ents = {}
    for n, (la, lo) in cities.items():
        vals = {"lat": la, "lon": lo}
        if crs:
            vals["crs"] = crs
        vals.update(overrides.get(n, {}))
        ents[n] = Entity(n, types=("city",),
                         facets={"geo.place": Facet("geo.place", vals)})
    return WorldSnapshot(entities=ents)


# --- ground truth ---------------------------------------------------------
@pytest.mark.parametrize("a,b,published_km", [
    ("london", "paris", 343.9),
    ("london", "newyork", 5585.2),
    ("london", "berlin", 933.4),
    ("paris", "madrid", 1053.0),
])
def test_geodesics_match_published_distances(a, b, published_km):
    la1, lo1 = CITIES[a]
    la2, lo2 = CITIES[b]
    got = vincenty_km(la1, lo1, la2, lo2)
    assert got == pytest.approx(published_km, rel=0.003), (
        f"{a}-{b}: {got:.1f} km against a published {published_km} km")


def test_the_sphere_is_out_by_the_amount_that_makes_it_the_wrong_default():
    """Fine for 'which is nearer', not fine for a fuel budget -- and the whole
    point of reporting which method ran."""
    la1, lo1 = CITIES["london"]
    la2, lo2 = CITIES["newyork"]
    ell, sph = vincenty_km(la1, lo1, la2, lo2), haversine_km(la1, lo1, la2, lo2)
    assert abs(sph - ell) > 10.0, "the two methods agreed, so one is not running"
    assert abs(sph - ell) / ell < 0.01


def test_distance_is_symmetric_and_obeys_the_triangle_inequality():
    d = lambda a, b: distance_km(*CITIES[a], *CITIES[b])
    assert d("london", "berlin") == pytest.approx(d("berlin", "london"))
    assert d("london", "berlin") <= d("london", "paris") + d("paris", "berlin")


def test_the_antipodal_case_returns_nan_rather_than_the_spherical_answer():
    """A silent substitution would return a plausible number computed by a
    different method than the one the caller asked for."""
    assert math.isnan(vincenty_km(0.0, 0.0, 0.5, 179.7))
    assert not math.isnan(haversine_km(0.0, 0.0, 0.5, 179.7))


# --- what the projection refuses -----------------------------------------
def test_a_coordinate_without_a_crs_is_discarded_by_name():
    p = project_world(world(crs=""))
    assert p.covered_entities == frozenset()
    assert any("not a location" in d.why for d in p.discarded)


def test_an_unsupported_crs_is_discarded_rather_than_measured_wrong():
    p = project_world(world(crs="EPSG:27700"))
    assert p.covered_entities == frozenset()
    assert any("EPSG:27700" in d.why and "reproject" in d.why
               for d in p.discarded)
    assert SUPPORTED_CRS == ("EPSG:4326",)


def test_two_crss_in_one_world_are_refused():
    ents = dict(world().entities)
    ents["odd"] = Entity("odd", facets={"geo.place": Facet("geo.place", {
        "lat": 0.0, "lon": 0.0, "crs": "EPSG:3857"})})
    with pytest.raises(ValueError, match="no reprojection here on purpose"):
        project_world(WorldSnapshot(entities=ents))


def test_a_facet_that_does_not_name_its_fields_is_discarded():
    w = WorldSnapshot(entities={"x": Entity("x", facets={
        "geo.place": Facet("geo.place", {"coords": [51.5, -0.13],
                                         "crs": "EPSG:4326"})})})
    p = project_world(w)
    assert any("NAME its fields" in d.why for d in p.discarded)
    assert any("latitude-first" in d.why for d in p.discarded)


# --- the swap the range check catches, and the one it cannot -------------
def test_a_swapped_coordinate_is_caught_when_the_longitude_exceeds_90():
    la, lo = CITIES["sydney"]
    p = project_world(world({"sydney": (lo, la)}))          # swapped
    assert p.covered_entities == frozenset()
    assert any("longitude in the latitude field" in d.why for d in p.discarded)


def test_a_swapped_coordinate_is_NOT_caught_when_it_cannot_be():
    """The honest limit, asserted so nobody reads the check as complete.

    London is 51.5N, 0.13W. Swapped it is 0.13N, 51.5E -- a valid point in
    Somalia. No range check can see that, which is exactly why the facet must
    name its fields rather than carry a pair.
    """
    la, lo = CITIES["london"]
    p = project_world(world({"london": (lo, la)}))
    assert "london" in p.covered_entities
    assert not any(d.kind == "entity" and "london" in d.ref
                   for d in p.discarded)


# --- the kernel -----------------------------------------------------------
def test_distances_come_back_as_quantities_with_units_and_an_error_bar():
    r = K.run(K.project(world(), KernelRequest()),
              KernelRequest(params={"from": "london"}))
    assert r.ok
    assert all(c.predicate == "geodesic_distance" for c in r.claims)
    q = next(c.roles["value"] for c in r.claims if c.roles["to"].id == "paris")
    assert q.unit == "km"
    assert q.value == pytest.approx(343.9, rel=0.003)
    assert q.stderr is not None and q.stderr > 0, (
        "a computed geodesic with no error bar would dominate any fusion "
        "against a surveyed distance")


def test_the_modelling_assumption_is_in_the_provenance():
    r = K.run(K.project(world(), KernelRequest()),
              KernelRequest(params={"from": "london"}))
    m = r.claims[0].provenance.method
    assert "stated assumption" in m and "EPSG:4326" in m


def test_a_budget_excludes_what_is_outside_it():
    r = K.run(K.project(world(), KernelRequest()),
              KernelRequest(params={"from": "london", "within_km": 1000}))
    reached = {c.roles["to"].id for c in r.claims}
    assert "paris" in reached and "berlin" in reached
    assert "madrid" not in reached and "sydney" not in reached


def test_fewer_than_two_places_is_a_refusal():
    r = K.run(K.project(world({"london": CITIES["london"]}), KernelRequest()),
              KernelRequest())
    assert not r.ok and "a distance needs two" in r.refused


def test_an_unknown_origin_is_refused_by_name():
    r = K.run(K.project(world(), KernelRequest()),
              KernelRequest(params={"from": "atlantis"}))
    assert not r.ok and "atlantis" in r.refused


def test_the_manifest_only_proposes():
    assert K.manifest.authority["geodesic_distance"] == "propose", (
        "the ellipsoid is not the terrain; a surveyed road length beats it")
    assert K.manifest.runtime == "native" and K.manifest.dependencies == ()


def test_a_geodesic_does_not_fuse_with_a_road_survey():
    """The predicate is the type, and this is why.

    London to Paris is 344 km across the ellipsoid and 459 km by road. They are
    different PROPERTIES of the same pair, not two measurements of one -- and
    the fusion registry groups by predicate, so a kernel that emitted a generic
    `distance` would let inverse-variance weighting average them into 381 km,
    which is neither. Naming the claim `geodesic_distance` makes the category
    error unrepresentable rather than merely discouraged.
    """
    from symbolic_ai_core.artifact import Provenance
    from symbolic_ai_core.runtime import fuse, inverse_variance
    from symbolic_ai_core.world import Claim, EntityRef, Quantity

    r = K.run(K.project(world(), KernelRequest()),
              KernelRequest(params={"from": "london"}))
    computed = next(c for c in r.claims if c.roles["to"].id == "paris")
    surveyed = Claim("road_distance",
                     {"from": EntityRef("london"), "to": EntityRef("paris"),
                      "value": Quantity(459.0, "km", 0.5)},
                     provenance=Provenance(producer="road_survey"))
    out = fuse([computed, surveyed],
               rules={"geodesic_distance": inverse_variance,
                      "road_distance": inverse_variance})
    values = sorted(c.roles["value"].value for c in out.resolved)
    assert len(out.resolved) == 2, "two properties were merged into one"
    assert values[0] == pytest.approx(343.9, rel=0.003)
    assert values[1] == pytest.approx(459.0)


def test_two_geodesic_estimates_do_fuse():
    """The case fusion IS for: same property, two sources, different precision."""
    from symbolic_ai_core.artifact import Provenance
    from symbolic_ai_core.runtime import fuse, inverse_variance
    from symbolic_ai_core.world import Claim, EntityRef, Quantity

    r = K.run(K.project(world(), KernelRequest()),
              KernelRequest(params={"from": "london"}))
    computed = next(c for c in r.claims if c.roles["to"].id == "paris")
    gps = Claim("geodesic_distance",
                {"from": EntityRef("london"), "to": EntityRef("paris"),
                 "value": Quantity(344.6, "km", 0.05)},
                provenance=Provenance(producer="gps_trace"))
    out = fuse([computed, gps], rules={"geodesic_distance": inverse_variance})
    v = out.resolved[0].roles["value"]
    assert v.value == pytest.approx(344.6, abs=0.2), (
        "the tighter estimate did not dominate")
    assert v.stderr < 0.05
