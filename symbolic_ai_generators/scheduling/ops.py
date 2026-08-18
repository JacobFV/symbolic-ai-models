"""Assignment search as ASP, and the honest note about where the numbers enter.

The relational projection **discards** every claim whose role is a ``Quantity``
— that is what makes datalog and ASP unit-safe, and it is measured working on
the flood task. Here it means the durations and capacities this problem is
entirely about do not reach the solver through the projection at all.

So they enter through the **supplied program text**, as integers scaled by 100.
That is legitimate — a caller's ASP is a caller's ASP — and it has a real cost
worth stating rather than hiding: **numbers that arrive this way are not
unit-checked.** A duration in minutes and a capacity in hours would produce a
perfectly well-formed answer to the wrong question, and neither the projection
nor the solver would notice. The scaling is done in one function, here, and the
unit is asserted before it happens.
"""

from __future__ import annotations

from typing import Any, Mapping

from symbolic_ai_core.artifact.value import Artifact, Provenance
from symbolic_ai_core.flow.port import Port
from symbolic_ai_core.flow.registry import OpDef, register_op
from symbolic_ai_core.world import Claim, EntityRef, Quantity, WorldSnapshot
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.flow_ops import claims_artifact, read_world

__all__ = ["ASSIGN_PROGRAM", "build_program", "SOLVE", "GATE", "capacity_gate"]

#: Scale factor from hours to the integers ASP counts in. 100 keeps two decimal
#: places, which is the precision the generator emits.
SCALE = 100

#: One machine per job, capability respected, no machine over its budget.
ASSIGN_PROGRAM = """
1 { assign(J, M) : machine(M) } 1 :- job(J).
:- assign(J, M), needs(J, C), not has(M, C).
:- capacity(M, Cap), #sum { D,J : assign(J, M), duration(J, D) } > Cap.
#show assign/2.
"""


def build_program(world: WorldSnapshot) -> tuple[str, list[str]]:
    """The ASP text for one instance, and what had to be smuggled past P_asp.

    Returns ``(program, notes)`` where ``notes`` names every numeric fact that
    entered outside the projection and is therefore unchecked.
    """
    jobs: dict[str, int] = {}
    needs: dict[str, str] = {}
    machines: dict[str, int] = {}
    has: list[tuple[str, str]] = []
    notes: list[str] = []

    for c in world.claims:
        if c.predicate in ("duration", "capacity"):
            q = c.roles.get("value")
            if not isinstance(q, Quantity):
                continue
            if q.unit != "h":
                raise ValueError(
                    f"{c.predicate} of {c.roles['of'].id} is in {q.unit!r}, not "
                    f"hours. This value bypasses the projection's unit check, "
                    f"so the assertion has to happen here or not at all.")
            target = jobs if c.predicate == "duration" else machines
            target[c.roles["of"].id] = int(round(q.value * SCALE))
            notes.append(f"{c.predicate}({c.roles['of'].id})")
        elif c.predicate == "needs_capability":
            needs[c.roles["job"].id] = str(c.roles["capability"])
        elif c.predicate == "has_capability":
            has.append((c.roles["machine"].id, str(c.roles["capability"])))

    lines = [f'job("{j}").' for j in sorted(jobs)]
    lines += [f'machine("{m}").' for m in sorted(machines)]
    lines += [f'duration("{j}", {d}).' for j, d in sorted(jobs.items())]
    lines += [f'capacity("{m}", {c}).' for m, c in sorted(machines.items())]
    lines += [f'needs("{j}", "{c}").' for j, c in sorted(needs.items())]
    lines += [f'has("{m}", "{c}").' for m, c in sorted(has)]
    # A job with no duration claim is not a job here; a job with a duration and
    # no capability requirement can go anywhere, which is the right reading.
    return "\n".join(lines) + "\n" + ASSIGN_PROGRAM, notes


def capacity_gate(world: WorldSnapshot) -> tuple[bool, str]:
    """Whether the search can still change the answer. Provably sufficient.

    Total demand above total capacity is infeasible whatever the assignment, and
    is arithmetic over facts already on the table. The converse is **not** a
    sufficient condition -- capacity to spare says nothing about whether the
    capabilities line up -- so there is only one gate here, not two.
    """
    demand = capacity = 0.0
    for c in world.claims:
        q = c.roles.get("value")
        if not isinstance(q, Quantity):
            continue
        if c.predicate == "duration":
            demand += q.value
        elif c.predicate == "capacity":
            capacity += q.value
    if demand > capacity:
        return False, (f"total demand {demand:.2f}h exceeds total capacity "
                       f"{capacity:.2f}h, so no assignment can fit whatever the "
                       f"capabilities are")
    return True, ""


def _solve(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
           ctx) -> dict[str, Artifact]:
    """Ask ASP whether a feasible assignment exists."""
    world = read_world(inputs["world"])
    program, notes = build_program(world)
    asp = get_kernel("asp@1")
    request = KernelRequest(
        params={"program": program, "max_models": 1},
        budget_ns=params.get("budget_ns"))
    projection = asp.project(world, request)
    result = asp.run(projection, request)
    ctx.cost_usd = result.cost.usd
    feasible = result.ok

    # An unfinished search is not a negative answer. Before this, `not
    # result.ok` became `polarity="negative", modality="asserted"` -- so a
    # solver that ran out of time would have entered "this schedule is NOT
    # feasible" into the world as a fact it had never established. Latent while
    # nothing passed a budget, exactly as the ASP unsat/exhausted conflation
    # was latent until something could interrupt the search.
    claims = ()
    if result.conclusive:
        claims = (Claim("feasible_schedule", {"of": EntityRef("plan")},
                        polarity="positive" if feasible else "negative",
                        modality="asserted",
                        provenance=Provenance(
                            producer="scheduling.solve@1", inputs=("asp@1",),
                            method="answer set search over one machine per job; "
                                   "durations and capacities entered through the "
                                   "supplied program as centihours and are NOT "
                                   "unit-checked by the projection")),)
    return {
        "claims": claims_artifact(claims, "scheduling.solve@1"),
        "report": Artifact(type="json", value={
            "feasible": feasible, "refused": result.refused,
            "outcome": result.classification,
            "settled": result.conclusive,
            "unchecked_numeric_facts": len(notes),
            "projection_discarded": len(projection.discarded),
            "diagnostics": dict(result.diagnostics)}),
    }


def _gate(inputs: Mapping[str, Artifact], params: Mapping[str, Any],
          ctx) -> dict[str, Artifact]:
    """The cheap arm: refuse on the capacity bound alone, without searching."""
    world = read_world(inputs["world"])
    need, why = capacity_gate(world)
    claim = Claim("feasible_schedule", {"of": EntityRef("plan")},
                  polarity="negative", modality="asserted",
                  provenance=Provenance(producer="scheduling.gate@1",
                                        method=why or "capacity bound"))
    return {"claims": claims_artifact(() if need else (claim,),
                                      "scheduling.gate@1"),
            "report": Artifact(type="json", value={"needs_search": need,
                                                   "why": why})}


SOLVE = register_op(OpDef(
    id="scheduling.solve@1", fn=_solve, family="kernel",
    inputs=(Port("world", "world_snapshot"),),
    outputs=(Port("claims", "claim_set"), Port("report", "json")),
    doc="Answer set search for a feasible machine assignment."))

GATE = register_op(OpDef(
    id="scheduling.gate@1", fn=_gate, family="router",
    inputs=(Port("world", "world_snapshot"),),
    outputs=(Port("claims", "claim_set"), Port("report", "json")),
    doc="The provable capacity bound, without searching."))
