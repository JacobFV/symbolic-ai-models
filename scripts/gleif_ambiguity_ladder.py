"""One statistic, and the two ends of it need different machinery.

`notes/findings/2026-08-18-a-query-pays-for-the-conflicts-it-reads-and-4992-of-them-cost-one.md`
left a hole it named: scoped enumeration is exact when the query reads few
conflicts, `additive_bounds` is exact when the answer is a sum of independent
terms, and a query that is **neither** — a wide read set and a non-additive
answer — stays refused, with "that is a solver's job" as an assertion nobody
had tested.

So test it, on a question the mixture makes genuinely hard. Beneath a hub, under
GLEIF's 4,992 unresolved ownership conflicts:

    concentration(world) = the largest number of the hub's entities that any
                           single party ultimately owns

* the **maximum** over worlds is closed-form and linear: conflicts are
  independent, so every conflict that *can* name owner `o` may name it at once.
* the **minimum** is makespan minimisation with restricted assignment. Each
  conflict must place its weight on one of two owners and the objective is the
  maximum load. That is the classical NP-hard shape, and it is where a solver
  earns its rung on the ladder.

Rungs measured here: collapse (one world, no idea it was a mixture), scoped
enumeration (exact, dies above ~10 conflicts), the closed form, the cheap
lower bound, and clingo with `#minimize`.
"""

from __future__ import annotations

import collections
import importlib.util
import math
import time
from pathlib import Path
from typing import Hashable, Mapping, Sequence

from symbolic_ai_core.runtime.ambiguity import (Alternatives,
                                                possible_answers)
from symbolic_ai_tasks.ultimate_parent import closure_with_cycles, load_task

BASE = Path("data/sources/gleif/commandagi-r2-2026-08-15")

_spec = importlib.util.spec_from_file_location(
    "gleif_scoped_ambiguity", Path(__file__).with_name("gleif_scoped_ambiguity.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)                                # type: ignore[union-attr]
key_of, ultimate = _mod.key_of, _mod.ultimate
build_closure_mixture = _mod.build_closure_mixture
_first_conflict = _mod._first_conflict


def concentration(counts: Mapping[str, int]) -> int:
    return max(counts.values()) if counts else 0


def closed_form_max(fixed: Mapping[str, int],
                    options: Sequence[tuple[int, tuple[str, ...]]]) -> int:
    """The largest concentration any consistent world can show.

    Every conflict is free of every other, so for a candidate owner ``o`` the
    world that maximises ``o``'s load is the one where **every** conflict
    offering ``o`` names it. Taking the best such owner is therefore exact, not
    a bound — which is worth stating, because the minimum of the same statistic
    is NP-hard and the asymmetry is the finding.
    """
    load = collections.Counter(fixed)
    best = 0
    owners = set(fixed) | {o for _, opts in options for o in opts}
    for o in owners:
        total = fixed.get(o, 0) + sum(w for w, opts in options if o in opts)
        best = max(best, total)
    return max(best, max(load.values(), default=0))


def cheap_min(fixed: Mapping[str, int],
              options: Sequence[tuple[int, tuple[str, ...]]]) -> int:
    """A lower bound anyone would write: no world can beat the heaviest single
    conflict, the heaviest fixed owner, or a perfectly even spread."""
    owners = set(fixed) | {o for _, opts in options for o in opts}
    total = sum(fixed.values()) + sum(w for w, _ in options)
    return max([max(fixed.values(), default=0),
                max((w for w, _ in options), default=0),
                math.ceil(total / len(owners)) if owners else 0])


def _feasible(fixed: Mapping[str, int],
              options: Sequence[tuple[int, tuple[str, ...]]],
              bound: int) -> bool:
    """Is there a consistent world whose concentration is at most ``bound``?"""
    import clingo

    names: dict[str, str] = {}

    def sym(o: str) -> str:
        return names.setdefault(o, f"o{len(names)}")

    lines = []
    for i, (w, opts) in enumerate(options):
        lines.append(f"conflict(c{i}). weight(c{i},{w}).")
        for o in opts:
            lines.append(f"opt(c{i},{sym(o)}).")
    lines.append("1 { choose(C,O) : opt(C,O) } 1 :- conflict(C).")
    owners = set(fixed) | {o for _, opts in options for o in opts}
    for o in owners:
        room = bound - fixed.get(o, 0)
        if room < 0:
            return False
        lines.append(f":- #sum{{ W,C : choose(C,{sym(o)}), weight(C,W) }} > {room}.")
    ctl = clingo.Control(["--warn=none"])
    ctl.add("base", [], "\n".join(lines))
    ctl.ground([("base", [])])
    return bool(ctl.solve().satisfiable)


def solve_min(fixed: Mapping[str, int],
              options: Sequence[tuple[int, tuple[str, ...]]],
              *, lo: int, hi: int) -> tuple[int, int]:
    """Exact minimum concentration, by binary search on the bound.

    A `#minimize` over `#max` grounds a sum per owner *and* a max over those
    sums, and clingo spends the run grounding rather than searching — measured,
    after the direct encoding failed to finish 3,044 hubs in thirteen minutes.
    The decision problem "is there a world with concentration <= B" is one
    integrity constraint per owner, and log2 of the bracket answers the
    optimisation. Returns the optimum and how many solver calls it cost.
    """
    calls = 0
    while lo < hi:
        mid = (lo + hi) // 2
        calls += 1
        if _feasible(fixed, options, mid):
            hi = mid
        else:
            lo = mid + 1
    return lo, calls


def main() -> None:
    t0 = time.perf_counter()
    task = load_task(BASE)
    alts, conflicts = build_closure_mixture(task)
    conflict_set = set(alts.choices)
    print(f"{len(task.ids):,} entities, {len(alts.choices):,} unresolved "
          f"conflicts, loaded in {time.perf_counter()-t0:.1f}s")

    children: dict[str, list[str]] = collections.defaultdict(list)
    for child, parent in task.direct.items():
        children[parent].append(child)
    nodes = set(task.direct) | set(task.direct.values())
    first = {e: _first_conflict(e, task.direct, conflict_set) for e in nodes}
    root = {e: closure_with_cycles(task.direct, e)[0] for e in nodes}

    def subtree(h: str) -> list[str]:
        out, stack, seen = [], [h], {h}
        while stack:
            x = stack.pop()
            out.append(x)
            for c in children.get(x, ()):
                if c not in seen:
                    seen.add(c)
                    stack.append(c)
        return out

    hubs = []
    for h in children:
        members = subtree(h)
        if len(members) < 2:
            continue
        ks = {first[e] for e in members} - {None}
        if ks:
            hubs.append((h, members, sorted(ks, key=repr)))
    print(f"{len(hubs):,} hubs whose concentration depends on the mixture")

    rows = []
    t_solver = t_enum = 0.0
    solver_calls = 0
    for i, (h, members, ks) in enumerate(hubs):
        if i and i % 250 == 0:
            print(f"    ... {i:,}/{len(hubs):,} hubs, "
                  f"{t_solver:.1f}s in the solver", flush=True)
        fixed = collections.Counter(root[e] for e in members
                                    if first[e] is None)
        weights = collections.Counter(first[e] for e in members
                                      if first[e] is not None)
        options = [(weights[k], alts.choices[k]) for k in ks]

        cf_max = closed_form_max(fixed, options)
        lb = cheap_min(fixed, options)
        t = time.perf_counter()
        exact_min, calls = solve_min(fixed, options, lo=lb, hi=cf_max)
        t_solver += time.perf_counter() - t
        solver_calls += calls
        proved = True                  # the search closes the bracket itself

        collapsed = concentration(collections.Counter(
            ultimate(e, task.direct, {}) for e in members))

        enum_min = enum_max = None
        if len(ks) <= 10:
            local = Alternatives({k: alts.choices[k] for k in ks})
            t = time.perf_counter()
            full = possible_answers(
                lambda a, members=members: concentration(collections.Counter(
                    ultimate(e, task.direct, a) for e in members)),
                local, max_worlds=1024)
            t_enum += time.perf_counter() - t
            enum_min, enum_max = min(full.answers), max(full.answers)
        rows.append(dict(hub=h, k=len(ks), n=len(members), cf_max=cf_max,
                         lb=lb, exact_min=exact_min, proved=proved,
                         collapsed=collapsed, enum_min=enum_min,
                         enum_max=enum_max))

    enumerable = [r for r in rows if r["enum_min"] is not None]
    print(f"\n=== the anchor, on {len(enumerable):,} hubs enumeration can reach "
          f"===")
    print(f"  closed-form max == enumerated max: "
          f"{sum(r['cf_max'] == r['enum_max'] for r in enumerable)}"
          f"/{len(enumerable)}")
    print(f"  solver min == enumerated min:      "
          f"{sum(r['exact_min'] == r['enum_min'] for r in enumerable)}"
          f"/{len(enumerable)}")
    print(f"  cheap lower bound == enumerated min: "
          f"{sum(r['lb'] == r['enum_min'] for r in enumerable)}"
          f"/{len(enumerable)}")

    print(f"\n=== over all {len(rows):,} hubs ===")
    tight = sum(r["lb"] == r["exact_min"] for r in rows)
    print(f"  cheap lower bound is already exact: {tight:,}/{len(rows):,} "
          f"({tight/len(rows)*100:.1f}%)")
    gaps = [r["exact_min"] - r["lb"] for r in rows if r["exact_min"] > r["lb"]]
    if gaps:
        print(f"  where it is not, the gap is {min(gaps)}..{max(gaps)} "
              f"(mean {sum(gaps)/len(gaps):.2f}) over {len(gaps):,} hubs")
    print(f"  optimality proved by the solver: "
          f"{sum(r['proved'] for r in rows):,}/{len(rows):,}")
    undetermined = sum(r["exact_min"] != r["cf_max"] for r in rows)
    print(f"  hubs whose concentration is undetermined "
          f"(min != max): {undetermined:,} ({undetermined/len(rows)*100:.1f}%)")
    outside = sum(1 for r in rows
                  if not r["exact_min"] <= r["collapsed"] <= r["cf_max"])
    print(f"  collapsing the mixture lands outside [min,max]: {outside} "
          f"(it must be 0 -- the collapsed world is one of them)")
    widest = max(rows, key=lambda r: r["cf_max"] - r["exact_min"])
    print(f"  widest: {widest['hub']} -- {widest['n']:,} entities, "
          f"{widest['k']} conflicts (2^{widest['k']} worlds), concentration in "
          f"[{widest['exact_min']}, {widest['cf_max']}], collapsed says "
          f"{widest['collapsed']}")

    print(f"\n=== cost ===")
    print(f"  solver: {t_solver:.1f}s over {len(rows):,} hubs "
          f"({t_solver/len(rows)*1000:.2f} ms each), {solver_calls:,} clingo "
          f"calls ({solver_calls/len(rows):.2f} per hub)")
    print(f"  enumeration: {t_enum:.1f}s over {len(enumerable):,} hubs "
          f"({t_enum/max(1,len(enumerable))*1000:.2f} ms each), and impossible "
          f"on the other {len(rows)-len(enumerable):,}")
    big = max(rows, key=lambda r: r["k"])
    print(f"  the largest mixture solved exactly: {big['k']} conflicts = "
          f"2^{big['k']} worlds, {big['n']:,} entities")


if __name__ == "__main__":
    main()
