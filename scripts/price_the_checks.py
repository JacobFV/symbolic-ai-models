"""What the detection layer costs, in the repo's own currency.

A day of work moved accuracy on the **honest** surface -- the one whose
distractors can actually bite. Accuracy is an input to the north star, not the
north star: `$ / solved answer above floor`. The checks are regex passes over
sentences, so the question is whether they are cheap **relative to reading**, and
in the one domain where reading is 96% of the wall clock that is not obvious.

Three systems per domain, all on the honest surface:

- **published reader** -- what the repo shipped;
- **+ checks** -- the staleness gate, plus the consolidated reader for solvency;
- and both priced with **every stage charged**, reader included.

The floor is the majority-class rate. A system at or below it has bought nothing
and the ledger says ``inf``, which is the entry that matters here: solvency's
honest reader scores **below** its floor.

Run: uv run python -u scripts/price_the_checks.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from symbolic_ai_core.cost import Capability, System, cpu_component, ledger
from symbolic_ai_generators.staleness import (filter_stale,
                                              stale_by_cancellation)

OUT = Path("runs/price_the_checks.json")
sys.path.insert(0, str(Path(__file__).parent))


def _tokens(text: str) -> int:
    return max(1, len(text.split()))


def _time(fn, texts):
    t0 = time.perf_counter()
    out = [fn(t) for t in texts]
    return out, time.perf_counter() - t0


def flood(gated: bool):
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    from symbolic_ai_generators.flood.surface import render_observation
    from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

    texts, truth = [], []
    for s in range(200):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        flat = unsaturate(obs, drop_headings=True, shuffle=False)
        texts.append(interleave(flat).text)
        truth.append(want)

    gate_s = 0.0
    if gated:
        texts, gate_s = _time(lambda t: filter_stale(t, stale_by_cancellation),
                              texts)
    worlds, read_s = _time(read_content_roles, texts)

    t0 = time.perf_counter()
    got = []
    for w in worlds:
        try:
            got.append(solve(w)[0])
        except Exception:
            got.append(())
    solve_s = time.perf_counter() - t0

    rate = statistics.mean(g == t for g, t in zip(got, truth))
    return texts, rate, 0.0, gate_s, read_s, solve_s


def scheduling(gated: bool):
    from hard_regime_milestone import solve_world
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling.surface import render_observation

    cases = [generate(s) for s in range(200)]
    texts = [render_observation(c, variants=4,
                                hard_distractors="machine").text for c in cases]
    truth = [c.feasible for c in cases]
    gate_s = 0.0
    if gated:
        texts, gate_s = _time(lambda t: filter_stale(t, stale_by_cancellation),
                              texts)
    worlds, read_s = _time(read_signature, texts)
    t0 = time.perf_counter()
    got = [solve_world(w)[0] for w in worlds]
    solve_s = time.perf_counter() - t0
    rate = statistics.mean(g == t for g, t in zip(got, truth))
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    return texts, rate, floor, gate_s, read_s, solve_s


def solvency(gated: bool):
    from symbolic_ai_generators.solvency import decide, generate
    from symbolic_ai_generators.solvency.read_surface import (
        decide_reading, read_signature, read_signature_consolidated)
    from symbolic_ai_generators.solvency.surface import render_observation

    cases = [generate(s) for s in range(200)]
    texts = [render_observation(c, variants=4, hard_distractors=True,
                                cue="cued").text for c in cases]
    truth = [decide(c, as_of=c.decision_date)[0] for c in cases]
    gate_s = 0.0
    reader = read_signature
    if gated:
        texts, gate_s = _time(lambda t: filter_stale(t, stale_by_cancellation),
                              texts)
        reader = read_signature_consolidated
    readings, read_s = _time(reader, texts)
    t0 = time.perf_counter()
    got = [decide_reading(r) for r in readings]
    solve_s = time.perf_counter() - t0
    rate = statistics.mean(g == t for g, t in zip(got, truth))
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    return texts, rate, floor, gate_s, read_s, solve_s


def main() -> None:
    out = {}
    print(f"{'system':<34} {'acc':>6} {'floor':>6} {'gate %':>7} "
          f"{'$/correct':>13} {'$/above floor':>15}")
    print("-" * 88)
    for name, fn, floor_override in (("flood", flood, 0.0),
                                     ("scheduling", scheduling, None),
                                     ("solvency", solvency, None)):
        out[name] = {}
        for gated in (False, True):
            texts, rate, floor, gate_s, read_s, solve_s = fn(gated)
            if floor_override is not None:
                floor = floor_override
            toks = sum(_tokens(t) for t in texts)
            per = toks / len(texts)
            comps = [cpu_component(f"{name}.reader", toks / read_s,
                                   stage="read", source="measured"),
                     cpu_component(f"{name}.kernel", toks / solve_s,
                                   stage="solve", source="measured")]
            if gate_s:
                comps.insert(0, cpu_component(f"{name}.staleness",
                                              toks / gate_s, stage="read",
                                              source="measured"))
            sysm = System(name=f"{name}{' + checks' if gated else ''}",
                          components=tuple(comps))
            cap = Capability(unit="answer", rate=rate, floor=floor,
                             n=len(texts), tokens_per_attempt=per)
            row = ledger(sysm, cap)
            share = gate_s / (gate_s + read_s + solve_s) if gate_s else 0.0
            out[name][sysm.name] = {
                "accuracy": rate, "floor": floor, "gate_share": share,
                "usd_per_solved": row.usd_per_solved,
                "usd_above_floor": row.usd_per_solved_above_floor}
            print(f"{sysm.name:<34} {rate:>6.3f} {floor:>6.3f} "
                  f"{share * 100:>6.1f}% {row.usd_per_solved:>13.3e} "
                  f"{row.usd_per_solved_above_floor:>15.3e}")
        print()

    print("Honest surface (hard_distractors=True) in every row. Floors are the")
    print("majority class; flood's answer is a SET, so its floor is 0 by")
    print("construction and its above-floor column equals its $/correct.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
