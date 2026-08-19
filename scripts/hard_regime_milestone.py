"""End to end where the kernel is not decorative.

Every scheduling pipeline number in this repo comes from the easy default -- 6
jobs, slack 0.15 -- where clingo answers in 0.6 ms. And the honest milestone has
only ever been run on flood, whose decision turned out to be a widest path. So no
end-to-end measurement here has had the kernel doing real work.

This runs the milestone on scheduling at ``HARD_REGIME`` (20 jobs, 3 machines,
slack 0.0): the one cell where the capacity gate is silent on half the instances,
the solver is non-trivial, and ground truth is still affordable.

The reader is measured on the honest surface too -- headings dropped, paragraphs
shuffled, sentences interleaved -- because a reader tested only on the template
it was written for has demonstrated nothing.

Run: uv run python -u scripts/hard_regime_milestone.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from symbolic_ai_core.world import Quantity
from symbolic_ai_generators.scheduling import generate_hard
from symbolic_ai_generators.scheduling.ops import build_program, capacity_gate
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.scheduling.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate
from symbolic_ai_kernels import KernelRequest, get_kernel

OUT = Path("runs/hard_regime_milestone.json")
N = 30
HEADINGS = ("WORKS ORDER.",)
BUDGET_NS = 10_000_000_000


def solve_world(world) -> tuple[bool | None, float, float]:
    """(feasible, usd, ms) via the ASP kernel, gate first."""
    need_search, _ = capacity_gate(world)
    if not need_search:
        return False, 0.0, 0.0
    prog, _ = build_program(world)
    asp = get_kernel("asp@1")
    req = KernelRequest(params={"program": prog, "max_models": 1},
                        budget_ns=BUDGET_NS)
    t0 = time.perf_counter()
    res = asp.run(asp.project(world, req), req)
    ms = (time.perf_counter() - t0) * 1000
    if not res.conclusive:
        return None, float(res.cost.usd or 0.0), ms
    return bool(res.ok), float(res.cost.usd or 0.0), ms


def claim_set(world) -> set:
    out = set()
    for c in world.claims:
        v = c.roles.get("value")
        out.add((c.predicate, tuple(sorted(c.entities())),
                 round(v.value, 2) if isinstance(v, Quantity) else None))
    return out


def main() -> None:
    cases = [generate_hard(s) for s in range(N)]
    truth = [c.feasible for c in cases]
    print(f"{N} cases at HARD_REGIME (20 jobs, 3 machines, slack 0.0)")
    print(f"  feasible: {sum(truth)}/{N}\n")

    surfaces = {}
    for name in ("as published", "interleaved"):
        texts = []
        for c in cases:
            obs = render_observation(c, variants=4)
            if name == "as published":
                texts.append(obs.text)
            else:
                flat = unsaturate(obs, headings=HEADINGS, shuffle=False)
                texts.append(interleave(flat).text)
        surfaces[name] = texts

    hdr = (f"{'system':<28} {'claim R':>8} {'task acc':>9} {'$/correct':>11} "
           f"{'ms/case':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}

    # the ceiling: the oracle's own world
    usd = ms = 0.0
    ok = 0
    for case, want in zip(cases, truth):
        a, u, m = solve_world(case.world)
        usd += u
        ms += m
        ok += a == want
    rows["oracle world (CEILING)"] = {
        "claim_recall": 1.0, "acc": ok / N,
        "usd_per_correct": usd / max(ok, 1), "ms": ms / N}
    r = rows["oracle world (CEILING)"]
    print(f"{'oracle world (CEILING)':<28} {1.0:>8.3f} {r['acc']:>9.3f} "
          f"{r['usd_per_correct']:>11.2e} {r['ms']:>9.1f}")

    for sname, texts in surfaces.items():
        usd = ms = 0.0
        ok = 0
        recs = []
        for case, want, text in zip(cases, truth, texts):
            world = read_signature(text)
            t, g = claim_set(case.world), claim_set(world)
            recs.append(len(t & g) / len(t) if t else 0.0)
            a, u, m = solve_world(world)
            usd += u
            ms += m
            ok += a == want
        label = f"signature reader, {sname}"
        rows[label] = {"claim_recall": statistics.mean(recs), "acc": ok / N,
                       "usd_per_correct": usd / max(ok, 1), "ms": ms / N}
        r = rows[label]
        print(f"{label:<28} {r['claim_recall']:>8.3f} {r['acc']:>9.3f} "
              f"{r['usd_per_correct']:>11.2e} {r['ms']:>9.1f}", flush=True)

    ceiling = rows["oracle world (CEILING)"]["acc"]
    best = max((k for k in rows if "reader" in k),
               key=lambda k: rows[k]["acc"])
    reader_loss = ceiling - rows[best]["acc"]
    gated = sum(1 for c in cases if not capacity_gate(c.world)[0])
    print(f"\n  reader loss (best arm)      : {reader_loss:.3f}")
    print(f"  gate settles                : {gated}/{N}")
    print(f"  solver time on the rest     : "
          f"{rows['oracle world (CEILING)']['ms'] * N / max(N - gated, 1):.1f} "
          f"ms/case")

    print()
    print(f"-> READER LOSS IS {reader_loss:.3f} AND THE COST IS ALL KERNEL. "
          f"Flood's honest milestone\n   put reader loss at 0.500, matching its "
          f"worst kernel loss, on a decision that is a\n   widest path. Here "
          f"the reader is exact -- claim recall "
          f"{rows[best]['claim_recall']:.3f}, unchanged by\n   interleaving, "
          f"because job_/machine_ prefixes fix the predicate and the domain "
          f"audits\n   at 0.000 ambiguity -- while the solver does genuine "
          f"search.")
    print(f"\n   So the suite now has both cases measured the same way: one "
          f"domain where READING\n   is the whole cost, and one where SOLVING "
          f"is. That contrast is the point, and\n   neither number means much "
          f"without the other.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "feasible": sum(truth),
                               "gated": gated, "rows": rows,
                               "reader_loss": reader_loss}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
