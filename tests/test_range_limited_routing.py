"""The first powered composition: geo decides the edges, the graph searches."""

from __future__ import annotations

import random

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_adapters import load_airports, load_routes
from symbolic_ai_kernels.geo import haversine_km
from symbolic_ai_tasks.range_limited_routing import (RangeNetwork,
                                                     build_network,
                                                     compare_from_sources,
                                                     hop_table, min_hops)


def _toy() -> RangeNetwork:
    # Collinear: A-B and B-C are ~100 km each, so the direct A-C hop is ~200.
    # A limit between the two is what makes the composition bite.
    pos = {"A": (0.0, 0.0), "B": (0.0, 0.9), "C": (0.0, 1.8),
           "Z": (0.0, 45.0)}
    edges = [("A", "B"), ("B", "C"), ("A", "C"), ("A", "Z")]
    return build_network(pos, edges)


class TestNetwork:
    def test_short_legs_survive_a_tight_limit(self):
        net = _toy()
        assert "B" in net.within(200.0)["A"]

    def test_a_long_leg_is_removed(self):
        net = _toy()
        assert "Z" not in net.within(200.0).get("A", frozenset())

    def test_the_limit_changes_the_hop_count_not_just_reachability(self):
        """A->C is one hop unconstrained and two when the direct leg is too
        long. This is the whole task in one assertion."""
        net = _toy()
        assert min_hops(net.adjacency, "A", "C") == 1
        assert min_hops(net.within(150.0), "A", "C") == 2

    def test_an_endpoint_without_a_position_is_dropped(self):
        net = build_network({"A": (0.0, 0.0)}, [("A", "ghost")])
        assert net.length_km == {}


class TestHops:
    def test_a_node_reaches_itself_in_zero(self):
        assert min_hops({"A": frozenset()}, "A", "A") == 0

    def test_unreachable_within_the_cap_is_none(self):
        chain = {c: frozenset([n]) for c, n in zip("abcdefghij", "bcdefghijk")}
        assert min_hops(chain, "a", "k", cap=3) is None
        assert min_hops(chain, "a", "k", cap=12) == 10

    def test_the_table_agrees_with_the_pairwise_search(self):
        net = _toy()
        table = hop_table(net.adjacency, "A")
        for t in ("B", "C", "Z"):
            assert table.get(t) == min_hops(net.adjacency, "A", t)

    def test_comparing_identical_structures_finds_no_difference(self):
        net = _toy()
        r = compare_from_sources(net.adjacency, net.adjacency,
                                 ["A"], list(net.nodes))
        assert r["differ"] == 0 and r["pairs"] > 0


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstTheRealNetwork:
    @staticmethod
    @pytest.fixture(scope="class")
    def nets():
        base = next(s for s in SourceRegistry().snapshots().values()
                    if s.source == "openflights").resolve(data_root())
        air = load_airports(base)
        edges, _ = load_routes(base, known=air.world.entities)
        pos = {i: (e.facets["geo.place"].values["lat"],
                   e.facets["geo.place"].values["lon"])
               for i, e in air.world.entities.items()}
        return (build_network(pos, edges),
                build_network(pos, edges, metric=haversine_km))

    def test_the_range_limit_removes_a_real_share_of_the_network(self, nets):
        exact, _ = nets
        within = sum(1 for d in exact.length_km.values() if d <= 2000)
        assert within / len(exact.length_km) == pytest.approx(0.736, abs=0.01)

    def test_the_graph_only_answer_is_usually_wrong(self, nets):
        """0.1437 agreement over 810,000 pairs. The single-kernel answer is
        not a near-miss heuristic, which is what makes the composition
        load-bearing rather than ceremonial."""
        exact, _ = nets
        srcs = random.Random(31).sample(exact.nodes, 40)
        r = compare_from_sources(exact.adjacency, exact.within(2000),
                                 srcs, list(exact.nodes))
        assert r["same"] / r["pairs"] < 0.20

    def test_the_spherical_approximation_stays_inside_its_stated_error(self, nets):
        """The geo kernel claims the spherical answer is 0.5% out. Measured
        over 37,042 real legs: p99 0.504%, max 0.559%."""
        exact, approx = nets
        rel = sorted(abs(approx.length_km[e] - d) / d
                     for e, d in exact.length_km.items() if d > 0)
        assert rel[int(0.99 * len(rel))] < 0.0055
        assert rel[-1] < 0.006

    def test_a_tiny_metric_error_is_amplified_by_the_graph(self, nets):
        """19 legs of 37,042 flip the 2,000 km threshold (0.051%) and 0.427%
        of answers change. The composition amplifies its inputs' error, and
        that is the number a two-kernel design has to know."""
        exact, approx = nets
        flipped = sum(1 for e, d in exact.length_km.items()
                      if (d <= 2000) != (approx.length_km[e] <= 2000))
        assert flipped == 19
        srcs = random.Random(31).sample(exact.nodes, 40)
        r = compare_from_sources(exact.within(2000), approx.within(2000),
                                 srcs, list(exact.nodes))
        assert r["differ_rate"] > flipped / len(exact.length_km)
