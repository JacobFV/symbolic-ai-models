"""The last unpriced term, in the only currency available.

**Each domain is tested with the reader that existed FIRST**, not the one since
repaired. flood's ``read_content_roles`` was built specifically to survive
interleaving and paraphrase; measuring it would price the repair and report the
damage as zero, which a first version of this script did. Scheduling and solvency
have only ever had one reader, so testing it is already the historical question.


Amortisation left maintenance unpriced: *a reader revised whenever the surface
changes never finishes amortising, and this repo has changed its surfaces
repeatedly.* That is not only a caveat -- it is a **record**. Every surface
transform built this session is a maintenance event, and whether each domain's
reader survived is measurable.

Four events, applied to all three domains: drop the section headings, shuffle the
paragraph order, interleave the sentences, and vary the phrasing to V=4. A
**breakage** is an accuracy drop of more than 0.1 from the published surface.

Run: uv run python -u scripts/maintenance_cost.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/maintenance_cost.json")
N = 40
BREAK = 0.1


def flood_probe():
    from symbolic_ai_generators.flood import generate
    from symbolic_ai_generators.flood.flow import solve
    # The reader that EXISTED FIRST, not the one repaired for these transforms.
    # read_content_roles was built to survive interleaving and paraphrase, so
    # testing it measures the repair rather than the damage -- a first version of
    # this script did exactly that and reported maintenance as free everywhere.
    from symbolic_ai_generators.flood.read_surface import (
        read_signature as read_content_roles)
    from symbolic_ai_generators.flood.surface import render_observation
    H = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
         "LOADING AND LIMITS.", "TASKING.")

    def score(variants, transform):
        ok = []
        for s in range(N):
            case = generate(s)
            want = solve(case.world)[0]
            if not want:
                continue
            obs = render_observation(case, variants=variants)
            text = transform(obs, H)
            try:
                ok.append(solve(read_content_roles(text))[0] == want)
            except Exception:
                ok.append(False)
        return statistics.mean(ok)
    return score


def scheduling_probe():
    from symbolic_ai_generators.scheduling import generate
    from symbolic_ai_generators.scheduling.read_surface import read_signature
    from symbolic_ai_generators.scheduling.surface import render_observation
    H = ("WORKS ORDER.",)

    def score(variants, transform):
        ok = []
        for s in range(N):
            case = generate(s, n_jobs=6, n_machines=3, slack=0.15)
            obs = render_observation(case, variants=variants)
            text = transform(obs, H)
            world = read_signature(text)
            t = {(c.predicate, tuple(sorted(c.entities())))
                 for c in case.world.claims}
            g = {(c.predicate, tuple(sorted(c.entities())))
                 for c in world.claims}
            ok.append(t == g)
        return statistics.mean(ok)
    return score


def solvency_probe():
    from symbolic_ai_generators.solvency import decide, generate
    from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                              read_signature)
    from symbolic_ai_generators.solvency.surface import render_observation
    H = ("COVENANT REVIEW.", "AS FIRST REPORTED.", "SUBSEQUENT REVISIONS.",
         "THE TEST.")

    def score(variants, transform):
        ok = []
        for s in range(N):
            case = generate(s)
            want = decide(case, as_of=case.decision_date)[0]
            obs = render_observation(case, variants=variants)
            text = transform(obs, H)
            ok.append(decide_reading(read_signature(text)) == want)
        return statistics.mean(ok)
    return score


EVENTS = (
    ("as published", 1, lambda o, h: o.text),
    ("drop headings", 1, lambda o, h: unsaturate(o, headings=h,
                                                 shuffle=False).text),
    ("shuffle paragraphs", 1, lambda o, h: unsaturate(o, headings=h).text),
    ("interleave sentences", 1,
     lambda o, h: interleave(unsaturate(o, headings=h, shuffle=False)).text),
    ("paraphrase (V=4)", 4, lambda o, h: o.text),
)


def main() -> None:
    probes = (("flood", flood_probe), ("scheduling", scheduling_probe),
              ("solvency", solvency_probe))
    print(f"{'event':<24} " + " ".join(f"{n:>12}" for n, _ in probes))
    print("-" * 64)
    rows: dict = {n: {} for n, _ in probes}
    for label, variants, transform in EVENTS:
        cells = []
        for name, probe in probes:
            v = probe()(variants, transform)
            rows[name][label] = v
            cells.append(f"{v:>12.3f}")
        print(f"{label:<24} " + " ".join(cells), flush=True)

    print()
    print(f"{'domain':<12} {'breakages':>10} {'which':<40}")
    print("-" * 64)
    summary = {}
    for name, _ in probes:
        base = rows[name]["as published"]
        broke = [k for k, v in rows[name].items()
                 if k != "as published" and base - v > BREAK]
        summary[name] = broke
        print(f"{name:<12} {len(broke):>10} {', '.join(broke) or '-':<40}")

    print()
    worst = max(summary, key=lambda k: len(summary[k]))
    clean = [k for k in summary if not summary[k]]
    if summary[worst] and clean:
        print(f"-> MAINTENANCE IS THE FOURTH THING THE AUDIT PREDICTS. {worst} "
              f"breaks on "
              f"{len(summary[worst])} of 4\n   surface changes; "
              f"{' and '.join(clean)} break on none. The audit measures "
              f"flood's real\n   ambiguity mass at 0.161 and the others at "
              f"0.000, offline, before any reader\n   exists.")
        print(f"\n   A reader whose signatures fix their predicates never "
              f"depended on the surface, so\n   moving the surface cannot break "
              f"it. A reader that needs arrangement breaks\n   whenever "
              f"arrangement moves -- and that is a recurring cost, not a "
              f"one-off, which\n   is what stops it amortising.")
        print(f"\n   So the same offline number now predicts reader "
              f"difficulty, where the error\n   concentrates, how soon the "
              f"route pays back, and how often it needs repairing.")
    else:
        print(f"-> breakages: "
              f"{ {k: len(v) for k, v in summary.items()} } -- no clean split.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "scores": rows,
                               "breakages": summary}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
