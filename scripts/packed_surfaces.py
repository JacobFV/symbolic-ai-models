"""Two claims in one sentence -- the granularity real prose actually has.

`notes/findings/2026-08-19-on-real-prose-the-sentence-is-the-wrong-unit.md`
measured the one-claim-per-sentence assumption **false** on 168 Wikipedia
articles, and that assumption is baked into the audit's spans, `unconsumed`,
`evidence_conflict` and `filter_stale`. This is the constructive response: give
the generators a ``packed`` option and see which mechanisms survive.

A packed sentence carries **two spans over the same text**, one per claim kind,
so the audit sees exactly what it is built to count -- one signature realising two
kinds.

The question the run is for: **does the audit predict the damage?** It has had a
run of things it cannot predict -- which channels are erroneous, vocabulary
fragility, real-prose determinacy. Packing is the case where it should come out
ahead, offline and before any reader runs.

Run: uv run python -u scripts/packed_surfaces.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from symbolic_ai_generators.audit import audit_surface

OUT = Path("runs/packed_surfaces.json")
sys.path.insert(0, str(Path(__file__).parent))
N = 120


def solvency(packed: bool):
    from symbolic_ai_generators.solvency import decide, generate
    from symbolic_ai_generators.solvency import surface as S
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    obs, worlds, ok = [], [], []
    for s in range(N):
        case = generate(s)
        o = S.render_observation(case, variants=4, packed=packed)
        obs.append(o)
        worlds.append(case.world)
        want = decide(case, as_of=case.decision_date)[0]
        ok.append(decide_reading(read_signature(o.text)) == want)
    truth = [decide(generate(s), as_of=generate(s).decision_date)[0]
             for s in range(N)]
    floor = max(sum(truth), N - sum(truth)) / N
    return obs, worlds, statistics.mean(ok), floor, None, None


def scheduling(packed: bool):
    from hard_regime_milestone import solve_world
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling import surface as S
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    obs, worlds, ok = [], [], []
    truth = []
    for s in range(N):
        case = generate(s)
        o = S.render_observation(case, variants=4, packed=packed)
        obs.append(o)
        worlds.append(case.world)
        truth.append(case.feasible)
        ok.append(solve_world(read_signature(o.text))[0] == case.feasible)
    floor = max(sum(truth), N - sum(truth)) / N
    return obs, worlds, statistics.mean(ok), floor, None, None


def main() -> None:
    from symbolic_ai_generators.flood.read_surface import VALUE_REGISTRY

    out = {}
    print(f"{'domain':<14} {'packed':>7} {'ambiguity mass':>15} "
          f"{'accuracy':>10} {'floor':>7}")
    print("-" * 60)
    for name, fn, reg, ent in (("solvency", solvency, None, r"\bsub_\d+\b|\bgroup\b"),
                               ("scheduling", scheduling, None, None)):
        row = {}
        for packed in (False, True):
            obs, worlds, acc, floor, _, _ = fn(packed)
            a = audit_surface(obs, reg, ent, worlds)
            row[packed] = {"mass": a.ambiguity_mass, "accuracy": acc,
                           "floor": floor, "spans": a.spans}
            print(f"{name:<14} {str(packed):>7} {a.ambiguity_mass:>15.3f} "
                  f"{acc:>10.3f} {floor:>7.3f}")
        d_mass = row[True]["mass"] - row[False]["mass"]
        d_acc = row[True]["accuracy"] - row[False]["accuracy"]
        print(f"{'':<14} {'delta':>7} {d_mass:>+15.3f} {d_acc:>+10.3f}")
        out[name] = {"unpacked": row[False], "packed": row[True],
                     "d_mass": d_mass, "d_accuracy": d_acc}
        print()

    # Flood is the control and it needs no surface change: its reader MERGES
    # crossings into links, so a sentence carrying both a road and its limit is
    # already handled. Checked directly rather than by reading the code.
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    packed_text = (
        "Depot operations are run out of region_0, which is where every "
        "vehicle starts the day. A request has come in from region_3. It is "
        "for 1400 kg of supplies.\n\n"
        "region_0 and region_3 are joined by a surfaced road rated for "
        "3000 kg.\n\n"
        "truck_0 weighs 1200 kg empty. The vehicle listed as truck_0 can take "
        "a further 2500 kg.")
    w = read_content_roles(packed_text)
    kinds = sorted({c.predicate for c in w.claims})
    print("FLOOD CONTROL -- one sentence carrying a road AND its limit:")
    print(f"   claim kinds recovered: {kinds}")
    print("   read_content_roles merges crossings into links, so packing those "
          "two\n   kinds is harmless there. No surface option needed; the "
          "reader already\n   handles the packed shape, which is why flood is "
          "the control.")
    out["flood_control_kinds"] = kinds

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
