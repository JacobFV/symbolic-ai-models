"""Certification without monotonicity: a misread number instead of a lost claim.

Both certificates so far cover **deletions**, and monotonicity is what makes half
the objects free -- a vehicle that cannot qualify, an instance already
infeasible. A **misread number** has no direction: a corrupted bridge limit can
push either way, so nothing is safe for free.

This is a real failure mode. The load-limit sentence carries two numbers -- *"was
rated at OLD kg before last year's resurfacing; it is now rated for NEW kg"* --
the reader takes the last, and the audit priced the ``capacity``/``load_limit``
collision at 0.550.

The candidate certificate is **margin** rather than structure. A misreading only
matters if it moves a limit **across a vehicle's threshold**. So if every limit
and its alternative fall on the same side of every vehicle's ``mass + demand``,
no misreading changes any edge's admissibility for any vehicle, and the answer is
invariant. ``O(E x V)`` comparisons, no graph work at all.

What is being tested is whether cheap certification survives the loss of
monotonicity, or whether monotonicity was doing the real work.

Run: uv run python -u scripts/non_monotone_certificate.py
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Quantity
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/non_monotone_certificate.json")
N = 60
#: the sentence that carries a superseded rating alongside the current one
_SUPERSEDED = re.compile(r"rated at (\d+) kg before[^.]*?rated for (\d+) kg")


def alternatives(case) -> dict[float, float]:
    """current limit -> the superseded value stated beside it, if any.

    The reader can see both numbers; taking the wrong one is the perturbation.
    """
    text = render_observation(case, variants=1).text
    out = {}
    for old, new in _SUPERSEDED.findall(text):
        out[float(new)] = float(old)
    return out


def _pieces(world):
    limits, mass, capacity = {}, {}, {}
    demand = None
    for c in world.claims:
        q = c.roles.get("value")
        if c.predicate == "load_limit" and isinstance(q, Quantity):
            limits[c.roles["of"].id] = float(q.value)
        elif c.predicate == "mass" and isinstance(q, Quantity):
            mass[c.roles["of"].id] = float(q.value)
        elif c.predicate == "capacity" and isinstance(q, Quantity):
            capacity[c.roles["of"].id] = float(q.value)
        elif c.predicate == "demand" and isinstance(q, Quantity):
            demand = float(q.value)
    return limits, mass, capacity, demand


def _on_some_path(links, a, b, edge) -> bool:
    """Is ``edge`` on any depot->site path? If not, its limit cannot matter."""
    rest = [e for e in links if frozenset(e) != frozenset(edge)]
    adj: dict = {}
    for x, y in rest:
        adj.setdefault(x, []).append(y)
        adj.setdefault(y, []).append(x)

    def reach(src):
        seen, stack = {src}, [src]
        while stack:
            cur = stack.pop()
            for nxt in adj.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    from_depot, to_site = reach(a), reach(b)
    u, v = edge
    return ((u in from_depot and v in to_site)
            or (v in from_depot and u in to_site))


def margin_certificate(world, alts: dict[float, float],
                       use_relevance: bool = False) -> bool:
    """No misreading crosses any vehicle's threshold, so nothing can change."""
    limits, mass, capacity, demand = _pieces(world)
    if demand is None or not limits or not mass:
        return False
    links, bridge_pair, depot, needs = [], {}, None, None
    for c in world.claims:
        if c.predicate == "link":
            links.append(tuple(c.entities()))
        elif c.predicate == "bridge_on":
            bridge_pair[c.roles["via"].id] = (c.roles["a"].id, c.roles["b"].id)
        elif c.predicate == "depot":
            depot = c.roles["where"].id
        elif c.predicate == "needs":
            needs = c.roles["where"].id
    thresholds = [m + demand for v, m in mass.items()
                  if capacity.get(v, 0.0) >= demand]
    if not thresholds:
        return True                        # no vehicle can qualify at all
    for via, value in limits.items():
        alt = alts.get(value)
        if alt is None:
            continue
        if use_relevance and depot and needs and via in bridge_pair:
            # A limit on an edge lying on no depot->site path cannot change any
            # answer, whichever number was read.
            if not _on_some_path(links, depot, needs, bridge_pair[via]):
                continue
        for t in thresholds:
            if (value >= t) != (alt >= t):
                return False
    return True


def main() -> None:
    rows = []
    for s in range(N):
        case = generate(s)
        base = solve(case.world)[0]
        if not base:
            continue
        alts = alternatives(case)
        idx = [i for i, c in enumerate(case.world.claims)
               if c.predicate == "load_limit"
               and isinstance(c.roles.get("value"), Quantity)
               and float(c.roles["value"].value) in alts]
        if not idx:
            continue
        answers = {base}
        for i in idx:
            c = case.world.claims[i]
            old = alts[float(c.roles["value"].value)]
            swapped = replace(c, roles={**c.roles,
                                        "value": Quantity(old, "kg")})
            answers.add(solve(replace(case.world, claims=tuple(
                swapped if j == i else x
                for j, x in enumerate(case.world.claims))))[0])
        rows.append({"decided": len(answers) == 1, "n": len(idx) + 1,
                     "cert": margin_certificate(case.world, alts),
                     "cert2": margin_certificate(case.world, alts, True)})

    n = len(rows)
    dec = sum(r["decided"] for r in rows)
    fires = sum(r["cert"] for r in rows)
    unsound = sum(r["cert"] and not r["decided"] for r in rows)
    missed = sum(r["decided"] and not r["cert"] for r in rows)
    enum = statistics.mean(r["n"] for r in rows)
    cert = statistics.mean(1 if r["cert"] else r["n"] for r in rows)

    print(f"{n} non-empty cases with a superseded rating, "
          f"perturbation = read the OLD number\n")
    print(f"  decided by enumeration      : {dec}/{n}")
    print(f"  margin certificate fires    : {fires}")
    print(f"  UNSOUND (fired, not decided): {unsound}")
    print(f"  missed (decided, not fired) : {missed}")
    fires2 = sum(r["cert2"] for r in rows)
    unsound2 = sum(r["cert2"] and not r["decided"] for r in rows)
    missed2 = sum(r["decided"] and not r["cert2"] for r in rows)
    cert2 = statistics.mean(1 if r["cert2"] else r["n"] for r in rows)
    print(f"\n  + relevance (ignore edges on no depot->site path):")
    print(f"      fires {fires2}   unsound {unsound2}   missed {missed2}")
    print(f"\n  mean solves, enumeration      : {enum:.1f}")
    print(f"  mean solves, margin only      : {cert:.1f}  "
          f"({1 - cert / enum:.0%} saving)")
    print(f"  mean solves, margin + relevance: {cert2:.1f}  "
          f"({1 - cert2 / enum:.0%} saving)")

    print()
    if unsound:
        print(f"-> UNSOUND on {unsound} case(s), so margin does NOT substitute "
              f"for direction as built.")
    elif fires and missed == 0:
        print(f"-> MARGIN SUBSTITUTES FOR DIRECTION. The certificate is sound "
              f"and complete here:\n   it fires on every decided case and no "
              f"undecided one, using only O(E x V)\n   comparisons and no graph "
              f"work. Monotonicity was NOT doing the essential work --\n   the "
              f"requirement is a CHEAP INVARIANT OF ANY SHAPE, and a threshold "
              f"argument serves\n   where a structural one is unavailable.")
    elif fires and unsound2 == 0 and missed2 < missed:
        print(f"-> THE TWO INGREDIENTS COMPOSE. Margin alone is sound and "
              f"misses {missed} decided cases;\n   adding RELEVANCE -- ignore "
              f"limits on edges lying on no depot->site path -- gives\n   "
              f"{fires2} fires, {missed2} missed, still 0 unsound. Margin "
              f"handles the LOSS OF DIRECTION,\n   structure handles WHICH "
              f"CLAIMS CAN MATTER; orthogonal, and they stack.")
        print(f"\n   So the requirement is not monotonicity but A CHEAP "
              f"INVARIANT OF ANY SHAPE. The free\n   half is still gone -- "
              f"nothing is safe by direction -- but checking is arithmetic\n"
              f"   and reachability rather than search.")
    elif fires:
        print(f"-> MARGIN WORKS BUT IS INCOMPLETE: sound on all {fires}, and it "
              f"misses {missed} decided\n   cases where the answer survives "
              f"even though a limit does cross a threshold --\n   crossing a "
              f"threshold on an edge that no qualifying route uses changes "
              f"nothing.\n   The free half really is gone: with no direction, "
              f"every vehicle must be checked,\n   though checking is "
              f"arithmetic rather than search.")
    else:
        print(f"-> the certificate never fires; margin does not substitute for "
              f"direction.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": n, "decided": dec, "fires": fires,
                               "unsound": unsound, "missed": missed,
                               "fires_relevance": fires2,
                               "unsound_relevance": unsound2,
                               "missed_relevance": missed2,
                               "mean_enum": enum, "mean_cert": cert,
                               "mean_cert_relevance": cert2},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
