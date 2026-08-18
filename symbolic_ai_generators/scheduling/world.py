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


def feasible_by_search(jobs, machines) -> bool:
    """Exhaustive. 3^6 = 729 assignments, so exact rather than heuristic.

    Shares no code with the ASP projection or the kernel; a heuristic oracle that
    occasionally missed a feasible packing would be indistinguishable from a
    kernel bug, which is the failure this is guarding against.
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
