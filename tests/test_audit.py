"""The signature-determinacy audit, against the domains whose answers are known.

The instrument's claim is that it predicts where a reader will break **from the
surface alone**, before a reader exists. That is only worth anything if it
reproduces the two domains already measured, so those are pinned here.
"""

from __future__ import annotations

from symbolic_ai_generators.audit import audit_surface, signature_of

SOLVENCY_ENTITY = r"\b(sub)_\d+\b|\b(group)\b"


def _flood(n: int = 12):
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.surface import render_observation
    return [render_observation(generate(s), variants=4) for s in range(n)]


def _scheduling(n: int = 12):
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling.surface import render_observation
    return [render_observation(generate(s), variants=4) for s in range(n)]


def _solvency(n: int = 12):
    from symbolic_ai_generators.solvency import generate
    from symbolic_ai_generators.solvency.surface import render_observation
    return [render_observation(generate(s), variants=4) for s in range(n)]


def test_flood_collides_on_exactly_the_known_residual() -> None:
    """depot / flooded / needs is the group the closure finding proved
    unreachable without content. The audit must find it from the surface."""
    from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
    a = audit_surface(_flood(), registries=VALUE_REGISTRY)
    groups = [frozenset(k) for k in a.collisions.values()]
    assert frozenset({"depot", "flooded", "needs"}) in groups, groups
    assert a.ambiguity_mass > 0.1


def test_scheduling_has_no_collision_at_all() -> None:
    """Its job_/machine_ prefixes fix the predicate, and it is measured immune
    to interleaving."""
    a = audit_surface(_scheduling())
    assert a.collisions == {}, a.collisions
    assert a.ambiguity_mass == 0.0


def test_solvency_has_no_collision() -> None:
    a = audit_surface(_solvency(), entity=SOLVENCY_ENTITY)
    assert a.collisions == {}, a.collisions
    assert a.ambiguity_mass == 0.0


def test_the_registry_removes_collisions_it_can_settle() -> None:
    """Declared value knowledge is part of what the reader sees, so supplying it
    must reduce the measured ambiguity rather than leave it untouched."""
    from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
    raw = audit_surface(_flood())
    with_reg = audit_surface(_flood(), registries=VALUE_REGISTRY)
    assert with_reg.ambiguity_mass < raw.ambiguity_mass


def test_both_date_styles_are_recognised() -> None:
    """Solvency renders half its corpus as "1 June 2026". A date read as two
    bare numbers would silently change every signature in that half."""
    iso = signature_of("group filed 10.00 USD dated 2026-06-01")
    long = signature_of("group filed 10.00 USD dated 1 June 2026")
    assert iso.dates == 1 and long.dates == 1
    assert iso.numbers == long.numbers == 1


def test_an_entity_off_the_naming_convention_is_still_counted() -> None:
    """Solvency's parent is ``group``, with no number. The generic pattern
    misses it, which would audit the domain with an entity invisible."""
    generic = signature_of("group owns sub_1 outright")
    given = signature_of("group owns sub_1 outright", entity=SOLVENCY_ENTITY)
    assert sum(n for _, n in generic.entities) == 1
    assert sum(n for _, n in given.entities) == 2


# --- from ordinal to cardinal: which collisions are real, and what they cost ---

def _flood_cases(n: int = 12):
    from symbolic_ai_generators.flood import generate
    return [generate(s) for s in range(n)]


def test_roles_separate_the_collision_that_costs_nothing() -> None:
    """``link`` (a, b) and ``bridge_on`` (a, b, via) are flood's LARGEST
    collision by span mass and cost nothing, because a reader that recovers the
    roles already has them apart. Span mass is the wrong weight."""
    from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
    a = audit_surface(_flood(), registries=VALUE_REGISTRY,
                      worlds=[c.world for c in _flood_cases()])
    real = {frozenset(k) for k in a.real_collisions.values()}
    assert frozenset({"bridge_on", "link"}) not in real
    assert frozenset({"depot", "flooded", "needs"}) in real
    assert a.real_ambiguity_mass < a.ambiguity_mass


def test_real_mass_still_separates_the_domains() -> None:
    from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
    flood = audit_surface(_flood(), registries=VALUE_REGISTRY,
                          worlds=[c.world for c in _flood_cases()])
    from symbolic_ai_generators.scheduling import generate as sg
    sched = audit_surface(_scheduling(),
                          worlds=[sg(s).world for s in range(12)])
    assert flood.real_ambiguity_mass > 0.05
    assert sched.real_ambiguity_mass == 0.0


def test_the_costly_collision_is_the_one_that_breaks() -> None:
    """The permutation is done in the TRUE world, so no reader is involved --
    which is what lets the audit speak before a reader exists."""
    from symbolic_ai_generators.audit import collision_cost
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
    cases = _flood_cases(10)
    costs = collision_cost(cases, _flood(10), solve, registries=VALUE_REGISTRY)
    residual = costs[frozenset({"depot", "flooded", "needs"})]
    assert residual["cost"] > 0.3, residual
    assert residual["n"] == 10, residual
    # nothing to permute where the roles differ, so this is structural rather
    # than a measured zero -- and the count is what says so
    harmless = costs[frozenset({"bridge_on", "link"})]
    assert harmless["permutable"] == 0, harmless
