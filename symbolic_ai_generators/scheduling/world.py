"""Generating jobs, machines, and a slack knob that moves the decision margin.

Small on purpose — six jobs over three machines is 3^6 = 729 assignments, which
an exhaustive oracle can enumerate exactly. The oracle has to be exact rather
than heuristic, because the whole task is a feasibility boolean and a heuristic
that occasionally says "no" when the answer is "yes" would be indistinguishable
from a kernel bug.
"""

from __future__ import annotations

import hashlib
import itertools
import random
from dataclasses import dataclass, field
from typing import Any

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)

__all__ = ["SchedulingCase", "generate", "feasible_by_search", "corrupt",
           "CORRUPTIONS", "CAPABILITIES"]

CAPABILITIES = ("cut", "weld", "paint")
CORRUPTIONS = ("drop_job", "drop_capability", "misread_duration",
               "drop_capacity")


@dataclass(frozen=True)
class SchedulingCase:
    seed: int
    world: WorldSnapshot
    jobs: dict[str, tuple[float, str]]        #: job -> (hours, capability)
    machines: dict[str, tuple[float, tuple[str, ...]]]
    slack: float
    feasible: bool
    meta: dict[str, Any] = field(default_factory=dict)


def _rng(seed: int, slack: float) -> random.Random:
    h = hashlib.blake2b(f"sched|{seed}|{slack}".encode(), digest_size=8)
    return random.Random(int.from_bytes(h.digest(), "big"))


def generate(seed: int, *, n_jobs: int = 6, n_machines: int = 3,
             slack: float = 0.15) -> SchedulingCase:
    """One instance. ``slack`` is the decision margin knob.

    Capacity is set to ``demand * (1 + slack)`` split across machines, so slack
    controls how far the instance sits from the feasibility boundary. At slack 0
    every hour must be used; at slack 1 there is twice the capacity needed and
    almost nothing can make it infeasible.
    """
    r = _rng(seed, slack)
    jobs = {f"job_{i}": (round(r.uniform(1.0, 6.0), 2),
                         r.choice(CAPABILITIES))
            for i in range(n_jobs)}
    demand = sum(h for h, _ in jobs.values())

    # Every capability is held by at least one machine, or the instance is
    # infeasible for a reason that has nothing to do with the margin.
    caps: list[list[str]] = [[] for _ in range(n_machines)]
    for cap in CAPABILITIES:
        caps[r.randrange(n_machines)].append(cap)
    for i in range(n_machines):
        for cap in CAPABILITIES:
            if cap not in caps[i] and r.random() < 0.45:
                caps[i].append(cap)

    total_capacity = demand * (1.0 + slack)
    weights = [r.uniform(0.6, 1.4) for _ in range(n_machines)]
    scale = total_capacity / sum(weights)
    machines = {f"machine_{i}": (round(weights[i] * scale, 2),
                                 tuple(sorted(caps[i])))
                for i in range(n_machines)}

    ok = feasible_by_search(jobs, machines)
    ents: dict[str, Entity] = {}
    claims: list[Claim] = []
    for j, (hours, cap) in sorted(jobs.items()):
        ents[j] = Entity(j, types=("job",))
        claims.append(Claim("duration", {"of": EntityRef(j),
                                         "value": Quantity(hours, "h")}))
        claims.append(Claim("needs_capability", {"job": EntityRef(j),
                                                 "capability": cap}))
    for m, (capacity, has) in sorted(machines.items()):
        ents[m] = Entity(m, types=("machine",))
        claims.append(Claim("capacity", {"of": EntityRef(m),
                                         "value": Quantity(capacity, "h")}))
        for cap in has:
            claims.append(Claim("has_capability", {"machine": EntityRef(m),
                                                   "capability": cap}))
    return SchedulingCase(
        seed=seed, world=WorldSnapshot(entities=ents, claims=tuple(claims)),
        jobs=jobs, machines=machines, slack=slack, feasible=ok,
        meta={"demand": round(demand, 2),
              "capacity": round(sum(c for c, _ in machines.values()), 2),
              "n_assignments": len(machines) ** len(jobs)})


def feasible_by_brute_force(jobs, machines) -> bool:
    """The specification: every assignment, checked. ``n_machines ** n_jobs``.

    Kept because it is obviously correct and nothing else here is. It is the
    reference ``feasible_by_search`` is tested against, and it is far too slow to
    call from ``generate`` -- see that function for what this cost 
    """
    names = sorted(jobs)
    ms = sorted(machines)
    allowed = {j: [m for m in ms if jobs[j][1] in machines[m][1]] for j in names}
    if any(not v for v in allowed.values()):
        return False
    for combo in itertools.product(*(allowed[j] for j in names)):
        load: dict[str, float] = {}
        for j, m in zip(names, combo):
            load[m] = load.get(m, 0.0) + jobs[j][0]
        if all(load[m] <= machines[m][0] + 1e-9 for m in load):
            return True
    return False


def feasible_by_search(jobs, machines) -> bool:
    """Exact, and pruned so the oracle is not the most expensive thing here.

    Shares no code with the ASP projection or the kernel; a heuristic oracle that
    occasionally missed a feasible packing would be indistinguishable from a
    kernel bug, which is the failure this is guarding against. So the pruning
    below is **exact** -- every branch it cuts is one that provably cannot
    complete -- and ``test_scheduling_oracle.py`` holds it against
    ``feasible_by_brute_force`` on instances small enough to enumerate.

    This replaced the brute force because the brute force *was* the cost of this
    domain. It enumerates ``n_machines ** n_jobs`` and only returns early when it
    finds a packing, so **infeasible** instances -- exactly the ones a negative
    slack is built to produce -- pay the full price. Measured before the change,
    at 3 machines: 53.1s on one 18-job instance and 5.1s on a 22-job one, against
    single-digit **milliseconds** for the ASP kernel on the same worlds. The
    ground truth cost four orders of magnitude more than the system it exists to
    check, and it, not the solver, is what had capped this domain at toy sizes.

    Three cuts, in descending order of what they save:

    - **The remaining-capacity bound.** If the jobs still to place need more
      hours than the machines still have, no completion exists. This is
      ``capacity_gate``'s argument applied at every node rather than only at the
      root, and it is what makes infeasible instances cheap.
    - **Symmetry.** Two machines with the same remaining capacity and the same
      capabilities generate isomorphic subtrees, so only one is tried.
    - **Hardest first.** Longest jobs are placed first, which fails fast rather
      than deep.

    **The one configuration this does not rescue is ``slack`` exactly 0.** There
    capacity equals demand, ``spare`` is zero at every node, the capacity bound
    never fires, and what is left is exact partition. Measured: 0.027s per case
    at 20 jobs and 1.60s at 30, against 0.0002s a half-percent either side.
    Memoising failed states was tried and bought **nothing** -- 1.5975s against
    1.5984s -- because durations are real-valued, so two partial assignments
    almost never leave the same remaining capacities and there is nothing for a
    memo table to hit. Sweeps wanting the boundary should use +/-0.005, which is
    the same regime and four orders cheaper.
    """
    names = sorted(jobs, key=lambda j: (-jobs[j][0], j))   # hardest first
    ms = sorted(machines)
    allowed = {j: [m for m in ms if jobs[j][1] in machines[m][1]] for j in names}
    if any(not v for v in allowed.values()):
        return False

    # suffix[i] is the demand of names[i:], for the remaining-capacity bound.
    suffix = [0.0] * (len(names) + 1)
    for i in range(len(names) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + jobs[names[i]][0]

    remaining = {m: machines[m][0] for m in ms}

    def place(i: int, spare: float) -> bool:
        if i == len(names):
            return True
        if suffix[i] > spare + 1e-9:
            return False
        job = names[i]
        duration = jobs[job][0]
        tried: set[tuple[float, tuple[str, ...]]] = set()
        for m in allowed[job]:
            if remaining[m] + 1e-9 < duration:
                continue
            key = (round(remaining[m], 6), machines[m][1])
            if key in tried:
                continue
            tried.add(key)
            remaining[m] -= duration
            if place(i + 1, spare - duration):
                remaining[m] += duration
                return True
            remaining[m] += duration
        return False

    return place(0, sum(remaining.values()))


def corrupt(case: SchedulingCase, *, seed: int, rate: float,
            kind: str) -> WorldSnapshot:
    """Damage one channel, leaving the others intact. Same knob as the others."""
    from dataclasses import replace as _r

    if kind not in CORRUPTIONS:
        raise ValueError(f"unknown corruption {kind!r}; have {CORRUPTIONS}")
    r = random.Random(int.from_bytes(
        hashlib.blake2b(f"sc|{seed}|{rate}|{kind}".encode(),
                        digest_size=8).digest(), "big"))
    dropped_jobs: set[str] = set()
    out: list[Claim] = []
    for c in case.world.claims:
        if kind == "drop_job" and c.predicate == "duration" and r.random() < rate:
            dropped_jobs.add(c.roles["of"].id)
            continue
        if (kind == "drop_capability" and c.predicate == "has_capability"
                and r.random() < rate):
            continue
        if (kind == "drop_capacity" and c.predicate == "capacity"
                and r.random() < rate):
            continue
        if (kind == "misread_duration" and c.predicate == "duration"
                and r.random() < rate):
            q = c.roles["value"]
            roles = dict(c.roles)
            roles["value"] = Quantity(max(0.1, round(q.value * _slip(r), 2)),
                                      q.unit, q.stderr)
            out.append(_r(c, roles=roles))
            continue
        out.append(c)
    if dropped_jobs:
        # A job with no duration is not a job. Dropping the duration and keeping
        # the capability requirement would be a different corruption -- a job
        # that must be placed and takes no time -- so both go.
        out = [c for c in out
               if not (c.predicate == "needs_capability"
                       and c.roles["job"].id in dropped_jobs)]
    return WorldSnapshot(entities=case.world.entities, claims=tuple(out),
                         alignments=case.world.alignments)


def _slip(r: random.Random) -> float:
    return r.choice((0.1, 10.0, 0.9, 1.1, 0.75, 1.25))
