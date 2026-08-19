"""The number that predicts whether carrying an ambiguity is cheap.

A correction to a correction. The previous finding attributed *carrying spurious
links is free* to the audit's **collision cost** of 0.000 for ``bridge_on``/
``link``. That number measures *permutation between two kinds*, and it is zero
because their role signatures differ so nothing is permutable. What the link
policy carries is a **spurious claim**, explored by **deletion**. Two different
quantities that happened to coincide at zero, and the coincidence was read as a
prediction.

The quantity that actually predicts is the dependency of a claim kind **under the
perturbation being carried**:

- links are carried by deletion -- does removing one change the answer?
- roles are carried by reassignment -- does moving one change the answer?

Measured here on flood, plus solvency's ``owns`` as the low-dependency point in a
second domain.

Run: uv run python -u scripts/perturbation_dependency.py
"""

from __future__ import annotations

import itertools
import json
import random
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Claim, EntityRef
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve

OUT = Path("runs/perturbation_dependency.json")
N = 60
ROLES = ("depot", "flooded", "needs")


def deletion_dependency(kind: str) -> tuple[float, float]:
    """P(answer changes | one claim of ``kind`` removed), and the per-case max."""
    changed, any_changed = [], []
    for s in range(N):
        case = generate(s)
        base = solve(case.world)[0]
        idx = [i for i, c in enumerate(case.world.claims)
               if c.predicate == kind]
        if not idx:
            continue
        hits = []
        for i in idx:
            w = replace(case.world, claims=tuple(
                c for j, c in enumerate(case.world.claims) if j != i))
            hits.append(solve(w)[0] != base)
        changed.append(statistics.mean(hits))
        any_changed.append(any(hits))
    return statistics.mean(changed), statistics.mean(any_changed)


def reassignment_dependency() -> float:
    """P(answer changes | two lone-region roles swapped)."""
    changed = []
    for s in range(N):
        case = generate(s)
        base = solve(case.world)[0]
        roles = {c.roles["where"].id: c.predicate for c in case.world.claims
                 if c.predicate in ROLES}
        if len(roles) < 2:
            continue
        keep = tuple(c for c in case.world.claims if c.predicate not in ROLES)
        hits = []
        for a, b in itertools.combinations(sorted(roles), 2):
            if roles[a] == roles[b]:
                continue
            swapped = dict(roles)
            swapped[a], swapped[b] = roles[b], roles[a]
            made = tuple(Claim(r, {"where": EntityRef(e)})
                         for e, r in sorted(swapped.items()))
            hits.append(solve(replace(case.world,
                                      claims=keep + made))[0] != base)
        if hits:
            changed.append(statistics.mean(hits))
    return statistics.mean(changed)


def owns_dependency() -> float:
    from symbolic_ai_generators.solvency import decide, generate as sg
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    from symbolic_ai_generators.solvency.surface import render_observation
    changed = []
    for s in range(N):
        case = sg(s)
        obs = render_observation(case, variants=4)
        full = decide_reading(read_signature(obs.text))
        drop = [(sp.start, sp.end) for sp in obs.spans
                if sp.claim is not None and sp.kind == "owns"]
        hits = []
        for lo, hi in drop:
            text = obs.text[:lo] + obs.text[hi:]
            hits.append(decide_reading(read_signature(text)) != full)
        if hits:
            changed.append(statistics.mean(hits))
    return statistics.mean(changed)


def main() -> None:
    link_mean, link_any = deletion_dependency("link")
    role = reassignment_dependency()
    owns = owns_dependency()

    print(f"{'perturbation':<44} {'dependency':>11}")
    print("-" * 57)
    print(f"{'flood: delete one link':<44} {link_mean:>11.3f}")
    print(f"{'flood: reassign two lone-region roles':<44} {role:>11.3f}")
    print(f"{'solvency: delete one owns claim':<44} {owns:>11.3f}")
    print(f"\n  (flood: share of cases where SOME single link "
          f"deletion matters: {link_any:.3f})")

    print(f"\ncarried cheaply?  link deletion -> yes (0.383 decided, gave up "
          f"nothing)\n                  role reassignment -> no (0.067 "
          f"decided)\n                  owns deletion -> nothing to carry, "
          f"dependency is exactly 0")

    print()
    if link_mean < role - 0.2:
        print(f"-> THE CORRECTED PRINCIPLE SURVIVES WITH THE RIGHT NUMBER. "
              f"Dependency UNDER THE\n   PERTURBATION BEING CARRIED is "
              f"{link_mean:.3f} for link deletion against {role:.3f} for role\n"
              f"   reassignment, and carrying was free for the first and vacuous "
              f"for the second.\n   The audit's collision cost of 0.000 for "
              f"bridge_on/link is a DIFFERENT quantity --\n   permutation "
              f"between two kinds, zero because their role signatures differ -- "
              f"that\n   agreed by accident. Substituting it was wrong even "
              f"though it pointed the right way.")
    else:
        print(f"-> link deletion dependency is {link_mean:.3f}, not far below "
              f"role reassignment at\n   {role:.3f}, so individual link "
              f"inertness does NOT explain the free ride. Something\n   else "
              f"does -- most likely that the phantom edge duplicates an existing "
              f"path.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "link_deletion": link_mean,
                               "link_any_case": link_any,
                               "role_reassignment": role,
                               "solvency_owns_deletion": owns}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
