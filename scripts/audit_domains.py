"""Run the signature-determinacy audit on every domain that has a surface.

Validated on the two whose answers are already measured -- flood collapses under
interleaving, scheduling does not -- and then applied to solvency, which has no
committed reader at all. The point of an instrument is to say where the reader
will break **before** the reader exists.

Run: uv run python -u scripts/audit_domains.py
"""

from __future__ import annotations

import json
from pathlib import Path

from symbolic_ai_generators.audit import audit_surface

OUT = Path("runs/audit_domains.json")
N = 40


def _cases(domain: str):
    if domain == "flood":
        from symbolic_ai_generators.flood import generate
    elif domain == "scheduling":
        from symbolic_ai_generators.scheduling import generate
    else:
        from symbolic_ai_generators.solvency import generate
    return [generate(s) for s in range(N)]


def corpus(domain: str, V: int = 4):
    if domain == "flood":
        from symbolic_ai_generators.flood import generate
        from symbolic_ai_generators.flood.surface import render_observation
    elif domain == "scheduling":
        from symbolic_ai_generators.scheduling import generate
        from symbolic_ai_generators.scheduling.surface import render_observation
    else:
        from symbolic_ai_generators.solvency import generate
        from symbolic_ai_generators.solvency.surface import render_observation
    return [render_observation(generate(s), variants=V) for s in range(N)]


KNOWN = {
    "flood": "collapses under interleaving (1.000 -> 0.000)",
    "scheduling": "immune to interleaving (1.000 -> 1.000)",
    "solvency": "UNKNOWN -- no committed reader",
}


def main() -> None:
    results = {}
    for domain in ("flood", "scheduling", "solvency"):
        # The reader's declared value knowledge is part of what it sees, so the
        # audit is run WITH it. Without it flood reads 0.860, most of which are
        # collisions its value registry already settles.
        reg = None
        if domain == "flood":
            from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY
            reg = VALUE_REGISTRY
        ent = r"\b(sub)_\d+\b|\b(group)\b" if domain == "solvency" else None
        obs = corpus(domain)
        a = audit_surface(obs, registries=reg, entity=ent,
                          worlds=[c.world for c in _cases(domain)])
        results[domain] = {"spans": a.spans,
                           "ambiguity_mass": a.ambiguity_mass,
                           "real_ambiguity_mass": a.real_ambiguity_mass,
                           "kinds": sorted(a.by_kind),
                           "collisions": {str(s): sorted(k)
                                          for s, k in a.collisions.items()}}
        print(f"=== {domain} ===  (measured: {KNOWN[domain]})")
        print(a.report())
        print()

    print(f"{'domain':<12} {'kinds':>6} {'spans':>7} {'raw mass':>10} "
          f"{'real mass':>10} {'predicts':>26}")
    print("-" * 72)
    for domain, r in results.items():
        m = r["real_ambiguity_mass"]
        pred = ("arrangement load-bearing" if m > 0.05
                else "signature suffices")
        print(f"{domain:<12} {len(r['kinds']):>6} {r['spans']:>7} "
              f"{r['ambiguity_mass']:>10.3f} {m:>10.3f} {pred:>26}")

    f, s = results["flood"], results["scheduling"]
    if f["real_ambiguity_mass"] > 0.05 and s["real_ambiguity_mass"] < 0.05:
        print(f"\n-> the instrument reproduces both measured answers, which is "
              f"what licenses its\n   use on the third. flood's collision is "
              f"exactly the group the closure finding\n   proved unreachable "
              f"without content; scheduling has none.")
    v = results["solvency"]["real_ambiguity_mass"]
    print(f"\n-> PREDICTION for solvency, before any reader exists: ambiguity "
          f"mass {v:.3f}, so a\n   signature reader should "
          f"{'NOT ' if v > 0.05 else ''}need arrangement, and interleaving "
          f"should {'break' if v > 0.05 else 'not break'} it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
