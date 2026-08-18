"""What does a query cost when the world holds 251 unresolved conflicts?

`possible_answers` prices a query at the **world's** product: 251 retained
GLEIF conflicts are 2^251 consistent worlds, so it refuses every query,
including "who ultimately owns this one company" — whose answer depends on one
of them. The module's own refuter says so.

This measures the three ways out on real filed bytes, against the same 251
mixtures the retention finding retained:

* **scoped enumeration** — hand the computation a recording assignment, learn
  which conflicts it read, enumerate exactly those. Exact, `2^(read)`.
* **additive bounds** — for a portfolio count, whose answer really does depend
  on every conflict beneath a hub, the extreme worlds are found term by term.
* **set propagation** — the cheap answer, built here as the **control that must
  fail**: carry a set of possible values per entity and take unions. It cannot
  see that two entities under one conflict must move together.

Hypotheses are in
`notes/decisions/2026-08-18-a-query-pays-for-the-conflicts-it-reads-not-the-ones-that-exist.md`,
written before any of this ran.
"""

from __future__ import annotations

import collections
import importlib.util
import itertools
import time
from pathlib import Path
from typing import Hashable, Mapping

from symbolic_ai_core.runtime.ambiguity import (Alternatives,
                                                AmbiguityExplosion,
                                                additive_bounds,
                                                possible_answers,
                                                possible_answers_scoped)
from symbolic_ai_tasks.ultimate_parent import (closure_with_cycles,
                                               load_task)

BASE = Path("data/sources/gleif/commandagi-r2-2026-08-15")

# The 251 are *defined* by the mid-chain test in `gleif_fund_exposure`, and this
# repo has already been bitten once by two scripts holding two definitions of
# "conflict" (251 vs 4,992). Imported rather than re-typed, so the two cannot
# drift apart.
_spec = importlib.util.spec_from_file_location(
    "gleif_fund_exposure", Path(__file__).with_name("gleif_fund_exposure.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)                                # type: ignore[union-attr]
real_conflicts = _mod.real_conflicts
_direct_chain = _mod._direct_chain

PREDICATE = "core.ultimate_parent"


def key_of(entity: str) -> tuple[str, str]:
    return (PREDICATE, entity)


def build_mixture(task) -> tuple[Alternatives, list[str]]:
    """The 251 entities, each with the two ultimate owners GLEIF's own filings
    support: the one it filed directly, and the root of the direct chain it
    also filed. Neither is derived from the other and both are `measured`,
    which is why `prefer_measured` refuses to settle them."""
    conflicts = real_conflicts(task)
    choices = {}
    for e in conflicts:
        chain = _direct_chain(task.direct, e)
        choices[key_of(e)] = (task.truth[e], chain[-1])
    return Alternatives(choices), conflicts


def ultimate(entity: str, direct: Mapping[str, str],
             assignment: Mapping[Hashable, str]) -> str | None:
    """Who ultimately owns ``entity``, under one assignment.

    Reads the **first conflicted ancestor** and stops: the disagreement is
    about that ancestor's ultimate owner, and an entity's ultimate owner is its
    ancestor's. Walking past it would read conflicts the answer does not
    depend on, and the whole point of scoping is that the read set is the
    dependency.

    ``None`` on an ownership cycle — six are real in this data — rather than a
    hang or a silently broken loop.
    """
    seen = {entity}
    cur = entity
    while True:
        k = key_of(cur)
        if k in assignment:
            return assignment[k]
        nxt = direct.get(cur)
        if nxt is None:
            return cur
        if nxt in seen:
            return None
        seen.add(nxt)
        cur = nxt


def summarize(label: str, values: list[int]) -> None:
    s = sorted(values)
    n = len(s)
    print(f"  {label}: n={n} sum={sum(s)} mean={sum(s)/n:.3f} "
          f"p50={s[n//2]} p99={s[min(n-1, int(n*0.99))]} max={s[-1]}")


# --------------------------------------------------------------------------
# Arm 1: the point query. Who ultimately owns X?
# --------------------------------------------------------------------------
def arm_point_query(task, alts: Alternatives) -> None:
    print("\n=== Arm 1: the point query, over every scored entity ===")
    print(f"mixture: {len(alts.choices)} unresolved conflicts, "
          f"world_count = 2^{len(alts.choices)}")

    try:
        possible_answers(lambda a: ultimate(task.ids[0], task.direct, a), alts)
        print("  full enumeration: DID NOT REFUSE -- unexpected")
    except AmbiguityExplosion:
        print("  full enumeration: refused, as it must (the bound is the "
              "world's product, not the query's)")

    reads, ambiguous, t0 = [], 0, time.perf_counter()
    for e in task.ids:
        got = possible_answers_scoped(
            lambda a, e=e: ultimate(e, task.direct, a), alts)
        reads.append(len(got.read))
        if got.ambiguous:
            ambiguous += 1
    wall = time.perf_counter() - t0

    print(f"  scoped: {len(task.ids):,} queries answered in {wall:.1f}s "
          f"({wall/len(task.ids)*1e6:.1f} us each)")
    summarize("conflicts read per query", reads)
    print(f"  queries whose answer is undetermined: {ambiguous} "
          f"({ambiguous/len(task.ids)*100:.3f}%)")
    print(f"  queries reading 0 conflicts: {sum(1 for r in reads if r == 0):,}")

    # What retention actually costs. The comparison is not against enumerating
    # the world -- that is refused -- but against the thing a caller does when
    # it gives up: collapse the mixture and answer once.
    t1 = time.perf_counter()
    for e in task.ids:
        ultimate(e, task.direct, {})
    collapsed = time.perf_counter() - t1
    usd_per_core_second = 0.02 / 3600.0            # cost.py's price sheet
    print(f"  collapsed (one world, no mixture): {collapsed:.2f}s "
          f"-- retention costs {wall/collapsed:.1f}x, "
          f"${wall*usd_per_core_second/len(task.ids):.2e} per answered query "
          f"against ${collapsed*usd_per_core_second/len(task.ids):.2e}")
    anchor_against_full_enumeration(task, alts)



def anchor_against_full_enumeration(task, alts: Alternatives, *, k: int = 8,
                                    sample: int = 400) -> None:
    """The check that says scoping is exact rather than merely cheap.

    Full enumeration cannot run on 251 conflicts, so the anchor takes the first
    ``k`` of them as a mixture in their own right — 2^8 = 256 worlds, which
    `possible_answers` will enumerate — and demands the *same answer set* for
    every entity, not a subset and not a superset.
    """
    small = Alternatives(dict(sorted(alts.choices.items(), key=repr)[:k]))
    conflicted = {c[1] for c in small.choices}
    every = task.ids                    # a property that sorts 117k ids: once
    ids = [e for e in every
           if any(x in conflicted for x in _direct_chain(task.direct, e))]
    step = max(1, len(every) // sample)
    ids += [e for i, e in enumerate(every) if i % step == 0]
    same = 0
    for e in dict.fromkeys(ids):
        full = possible_answers(
            lambda a, e=e: ultimate(e, task.direct, a), small, max_worlds=2 ** k)
        scoped = possible_answers_scoped(
            lambda a, e=e: ultimate(e, task.direct, a), small)
        same += set(full.answers) == set(scoped.answers)
    print(f"  anchor: over a {k}-conflict sub-mixture ({2**k} worlds), scoped "
          f"and full enumeration return the same answer set on "
          f"{same}/{len(dict.fromkeys(ids))} entities")


# --------------------------------------------------------------------------
# Arm 2: the control. Set propagation, and the pairs it gets wrong.
# --------------------------------------------------------------------------
def possible_set(entity: str, direct: Mapping[str, str],
                 alts: Alternatives) -> tuple[str | None, ...]:
    """The cheap method: the set of owners this entity could have."""
    k = key_of(entity)
    if k in alts.choices:
        return alts.choices[k]
    seen = {entity}
    cur = entity
    while True:
        nxt = direct.get(cur)
        if nxt is None:
            return (cur,)
        if nxt in seen:
            return (None,)
        seen.add(nxt)
        cur = nxt
        if key_of(cur) in alts.choices:
            return alts.choices[key_of(cur)]


def arm_correlated_pairs(task, alts: Alternatives, conflicts: list[str]
                         ) -> None:
    print("\n=== Arm 2: two entities under one conflict (the control) ===")
    children: dict[str, list[str]] = collections.defaultdict(list)
    for child, parent in task.direct.items():
        children[parent].append(child)

    # Entities whose first conflicted ancestor is c, for each conflict c.
    under: dict[str, list[str]] = collections.defaultdict(list)
    conflict_set = {key_of(c) for c in conflicts}
    for e in task.ids:
        seen, cur = {e}, e
        while True:
            if key_of(cur) in conflict_set:
                under[cur].append(e)
                break
            nxt = direct_next = task.direct.get(cur)
            if nxt is None or nxt in seen:
                break
            seen.add(nxt)
            cur = nxt

    pairs = [(a, b) for c, members in under.items()
             for a, b in itertools.combinations(sorted(members), 2)]
    print(f"  entities sharing a first conflicted ancestor: "
          f"{sum(len(v) for v in under.values()):,} over "
          f"{len(under):,} conflicts")
    print(f"  pairs both of whose answers turn on the *same* conflict: "
          f"{len(pairs):,}")

    scoped_wrong = prop_wrong = 0
    for a, b in pairs:
        got = possible_answers_scoped(
            lambda asg, a=a, b=b: (ultimate(a, task.direct, asg)
                                   == ultimate(b, task.direct, asg)), alts)
        truth = set(got.answers)                    # exact, by construction
        sa, sb = possible_set(a, task.direct, alts), possible_set(b, task.direct, alts)
        propagated = {x == y for x in sa for y in sb}
        if truth != propagated:
            prop_wrong += 1
        if len(truth) != 1:
            scoped_wrong += 1                       # not wrong, just reported
    print(f"  'do X and Y have the same ultimate owner?'")
    print(f"    scoped enumeration returns one answer on {len(pairs)-scoped_wrong}"
          f"/{len(pairs)} pairs (the conflict cancels)")
    print(f"    set propagation disagrees with it on {prop_wrong}/{len(pairs)} "
          f"pairs ({prop_wrong/max(1,len(pairs))*100:.1f}%)")


# --------------------------------------------------------------------------
# Arm 3: the portfolio query, where the read set is genuinely wide.
# --------------------------------------------------------------------------
def _first_conflict(entity: str, direct: Mapping[str, str],
                    conflict_set: set) -> Hashable | None:
    """The one conflict a point query about ``entity`` turns on, or None."""
    seen, cur = {entity}, entity
    while True:
        if key_of(cur) in conflict_set:
            return key_of(cur)
        nxt = direct.get(cur)
        if nxt is None or nxt in seen:
            return None
        seen.add(nxt)
        cur = nxt


def arm_portfolio(task, alts: Alternatives, conflicts: list[str]) -> None:
    print("\n=== Arm 3: the portfolio query, and where scoping stops ===")
    children: dict[str, list[str]] = collections.defaultdict(list)
    for child, parent in task.direct.items():
        children[parent].append(child)
    conflict_set = {key_of(c) for c in conflicts}

    nodes = set(task.direct) | set(task.direct.values())
    first = {e: _first_conflict(e, task.direct, conflict_set) for e in nodes}

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

    sub = {h: subtree(h) for h in children}
    hubs = [h for h in sub if len(sub[h]) > 1]
    keys_of_hub = {h: {first[e] for e in sub[h]} - {None} for h in hubs}
    reads = {h: len(keys_of_hub[h]) for h in hubs}
    summarize("conflicts a hub's portfolio query reads", [reads[h] for h in hubs])
    live = [h for h in hubs if reads[h]]
    print(f"  hubs whose portfolio query reads >= 1 conflict: "
          f"{len(live):,}/{len(hubs):,}")
    wide = sorted(live, key=lambda h: (-reads[h], h))
    print(f"  widest: {wide[0]} reads {reads[wide[0]]} conflicts over "
          f"{len(sub[wide[0]]):,} entities -- 2^{reads[wide[0]]} = "
          f"{2**reads[wide[0]]:,} worlds")

    def bounds_for(h: str):
        """How many entities beneath ``h`` are ultimately owned by the party
        ``h``'s own chain names? A sum of independent per-conflict terms: each
        member's answer turns on exactly one conflict, so the extremes are
        found term by term and are attained."""
        members = sub[h]
        target = ultimate(h, task.direct, {})
        local = Alternatives({k: alts.choices[k] for k in sorted(keys_of_hub[h])})
        routed: dict[Hashable, int] = collections.Counter(
            first[e] for e in members if first[e] is not None)
        base = sum(1 for e in members
                   if first[e] is None and ultimate(e, task.direct, {}) == target)
        return local, target, members, additive_bounds(
            local, lambda s, v, routed=routed, target=target:
                routed[s] if v == target else 0, base=float(base))

    checked = agree = read_agree = 0
    for h in live:
        local, target, members, b = bounds_for(h)
        if local.world_count() > 1024:
            continue
        full = possible_answers(
            lambda a, members=members, target=target: sum(
                ultimate(e, task.direct, a) == target for e in members),
            local, max_worlds=1024)
        scoped = possible_answers_scoped(
            lambda a, members=members, target=target: sum(
                ultimate(e, task.direct, a) == target for e in members),
            local, max_worlds=1024)
        checked += 1
        agree += (b.low == min(full.answers) and b.high == max(full.answers))
        read_agree += (set(scoped.read) == set(local.choices)
                       or set(scoped.read) <= set(local.choices))
    print(f"  additive bounds == enumerated extremes: {agree}/{checked} hubs")
    print(f"  the recorder's read set stayed inside the analytic one: "
          f"{read_agree}/{checked}")

    h = wide[0]
    local, target, members, b = bounds_for(h)
    print(f"  widest hub: {len(members):,} entities, {local.world_count():,} "
          f"worlds; entities ultimately owned by {target}: "
          f"[{b.low:.0f}, {b.high:.0f}], width {b.width:.0f}")
    try:
        possible_answers_scoped(
            lambda a: sum(ultimate(e, task.direct, a) == target
                          for e in members), local, max_worlds=1024)
        print("  scoped enumeration on the widest hub: DID NOT REFUSE")
    except AmbiguityExplosion as exc:
        print(f"  scoped enumeration on the widest hub: refused, naming "
              f"{len(exc.read)} conflicts and {exc.worlds:,} worlds")
    print(f"  widest conflict contributes {b.width_by_subject[0][1]:.0f} of the "
          f"width; top 3 of {len(b.width_by_subject)}: "
          f"{[(k[1][-8:], w) for k, w in b.width_by_subject[:3]]}")



def build_closure_mixture(task) -> tuple[Alternatives, list[str]]:
    """The other conflict set: the closure of the filed *direct* edges against
    the filed *ultimate* edge, 4,992 of them.

    This is the mixture you are left holding if you do **not** have
    derivation-aware fusion — the population `prefer_measured` settles by
    ranking a filing above an inference, and the one last-writer-wins rewrote
    on load order. It is twenty times larger than the 251 and it is the honest
    place to look for correlated queries, because the 251 turned out to have
    almost none.
    """
    choices, conflicts = {}, []
    for e in task.ids:
        root, cycled = closure_with_cycles(task.direct, e)
        if root is None or root == task.truth[e]:
            continue
        choices[key_of(e)] = (task.truth[e], root)
        conflicts.append(e)
    return Alternatives(choices), conflicts


def main() -> None:
    t0 = time.perf_counter()
    task = load_task(BASE)
    alts, conflicts = build_mixture(task)
    print(f"loaded {len(task.direct):,} direct and {len(task.truth):,} "
          f"ultimate filings, {len(task.ids):,} scored entities, in "
          f"{time.perf_counter()-t0:.1f}s")
    arm_point_query(task, alts)
    arm_correlated_pairs(task, alts, conflicts)
    arm_portfolio(task, alts, conflicts)

    print("\n########## the same three arms on the 4,992-conflict mixture, "
          "which is what a world without derivation-aware fusion holds")
    alts2, conflicts2 = build_closure_mixture(task)
    arm_point_query(task, alts2)
    arm_correlated_pairs(task, alts2, conflicts2)
    arm_portfolio(task, alts2, conflicts2)


if __name__ == "__main__":
    main()
