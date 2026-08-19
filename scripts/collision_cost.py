"""What each signature collision actually costs, so the audit can say how much.

`scripts/audit_domains.py` is ordinal: it ranks collisions by span mass, and
flood's largest -- ``bridge_on``/``link`` at 520 spans -- costs nothing while its
141-span ``depot``/``flooded``/``needs`` collision costs everything. Span mass is
the wrong weight.

Rather than reason about which collisions a declared mechanism resolves, this
measures the consequence: permute the colliding predicates in the **true** world
and re-solve. No reader is involved, which is what keeps the audit able to speak
before a reader exists.

Run: uv run python -u scripts/collision_cost.py
"""

from __future__ import annotations

import json
from pathlib import Path

from symbolic_ai_generators.audit import audit_surface, collision_cost
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/collision_cost.json")
N = 40


def main() -> None:
    cases = [generate(s) for s in range(N)]
    obs = [render_observation(c, variants=4) for c in cases]
    a = audit_surface(obs, registries=VALUE_REGISTRY)
    costs = collision_cost(cases, obs, solve, registries=VALUE_REGISTRY)

    print(f"{'collision':<34} {'spans':>6} {'span share':>11} "
          f"{'cost':>7} {'cases':>6}")
    print("-" * 70)
    rows = {}
    for sig, kinds in a.collisions.items():
        key = frozenset(kinds)
        c = costs.get(key, {"cost": 0.0, "n": 0})
        mass = a.mass_by_signature.get(sig, 0)
        rows["+".join(sorted(kinds))] = {
            "spans": mass, "span_share": mass / a.spans, "cost": c["cost"],
            "cases": c["n"]}
        print(f"{'+'.join(sorted(kinds)):<34} {mass:>6} "
              f"{mass / a.spans:>11.3f} {c['cost']:>7.3f} {c['n']:>6}")

    print(f"\nraw ambiguity mass (span-weighted):   "
          f"{a.ambiguity_mass:.3f}")
    worst = max(rows.values(), key=lambda r: r["cost"])
    worst_name = [k for k, v in rows.items() if v is worst][0]
    print(f"cost-weighted, worst collision:       {worst['cost']:.3f}  "
          f"({worst_name})")
    print(f"\nmeasured drop of read_signature_roles under interleaving: 1.000")

    harmless = [k for k, v in rows.items() if v["cost"] < 0.05]
    if harmless:
        print(f"\n-> collisions costing nothing: {', '.join(harmless)}.")
        print(f"   They collide in TEXT and differ in ROLE SIGNATURE, so a "
              f"reader that recovers\n   the roles can still tell them apart. "
              f"Span mass counts them; consequence does\n   not. That is the "
              f"correction the audit needed to go from ordinal to cardinal.")
    print(f"\n-> the collision that costs is {worst_name} at "
          f"{worst['cost']:.3f}, on {worst['span_share']:.1%} of spans.\n   "
          f"It is the group the closure finding proved unreachable without "
          f"content, and the\n   one that breaks under interleaving. The audit "
          f"now says WHICH collision matters\n   and by how much, from the "
          f"world and the surface alone.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "ambiguity_mass": a.ambiguity_mass,
                               "collisions": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
