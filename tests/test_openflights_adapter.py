"""The first adapter over bytes this repo did not author."""

from __future__ import annotations

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_adapters import (OPENFLIGHTS_CRS, load_airports, load_routes,
                                  parse_body)
from symbolic_ai_adapters.openflights import CRS_BASIS, ROUTE_KIND


class TestBodyParse:
    def test_the_shadow_schema_becomes_explicit(self):
        kv = parse_body("city=Goroka country=Papua lat=-6.08 lon=145.39")
        assert kv["lat"] == "-6.08" and kv["city"] == "Goroka"

    def test_an_empty_value_is_absent_not_present(self):
        """This corpus writes `iata=` for "no IATA code". A parser that
        returned "" would turn missing into present."""
        assert "iata" not in parse_body("icao=GNL iata= callsign=GENERAL")

    def test_no_body_is_no_keys(self):
        assert parse_body(None) == {} and parse_body("") == {}

    def test_values_stay_strings(self):
        """Coercion is the caller's call, because the caller knows what a
        missing value looks like in its own domain."""
        assert parse_body("pop=0")["pop"] == "0"


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheRealBytes:
    @staticmethod
    @pytest.fixture(scope="class")
    def loaded():
        base = next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "openflights").resolve(data_root())
        air = load_airports(base)
        edges, routes = load_routes(base, known=air.world.entities)
        return air, edges, routes

    def test_every_airport_row_yields_a_located_entity(self, loaded):
        air, _, _ = loaded
        assert air.rows == air.admitted == 6072 and air.loss_rate == 0.0

    def test_the_crs_is_asserted_with_its_basis_not_defaulted(self, loaded):
        """The geo kernel refuses a place with no CRS, and the bytes state
        none. An assumption a reader cannot see is indistinguishable from a
        fact, so the citation rides on the facet."""
        air, _, _ = loaded
        facet = next(iter(air.world.entities.values())).facets["geo.place"]
        assert facet.values["crs"] == OPENFLIGHTS_CRS
        assert "no field in the held bytes states a datum" in \
            facet.values["crs_basis"]
        assert facet.values["crs_basis"] == CRS_BASIS

    def test_unconsumed_body_keys_are_dropped_by_name(self, loaded):
        air, _, _ = loaded
        assert air.dropped_keys == {"icao": 6072}

    def test_a_different_relation_is_never_folded_into_the_network(self, loaded):
        """Route files carry `in-country` edges to jurisdictions. Reachability
        over a graph mixing "you can fly there" with "same country" answers
        neither question."""
        _, edges, routes = loaded
        assert routes.discarded == {"kind=in-country": 5995}
        assert routes.admitted == len(edges) == 37042

    def test_route_endpoints_are_all_located(self, loaded):
        air, edges, _ = loaded
        ids = set(air.world.entities)
        assert all(s in ids and t in ids for s, t in edges)

    def test_the_network_is_a_minority_of_the_gazetteer(self, loaded):
        """3,257 of 6,072 airports have any scheduled route at all -- so a
        floor that assumes every located airport is reachable is wrong."""
        _, edges, _ = loaded
        assert len({x for p in edges for x in p}) == 3257


class TestRouteKind:
    def test_the_relation_is_named_not_guessed(self):
        assert ROUTE_KIND == "flies-to"
