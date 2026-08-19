"""How much ambiguity can a world carry before the bound goes vacuous?

`scripts/ambiguity_vs_guessing.py` ablated paragraph position entirely, leaving
48 consistent worlds per case. The bound over them is **sound** -- the truth is
inside it every time -- and **vacuous**: it decides 3.0% of the fleet.

A flat "carrying ambiguity does not pay" would be the wrong reading. That was a
*total* ablation, in which the depot, the flooded region and the demand can all
permute. The useful question is the **regime**: at what ambiguity level does a
bound stop being worth having?

Each group is opened or closed independently. A closed group is resolved from
the true world -- an oracle for that group only -- which isolates *how wide is
the bound with k groups open* from *can the reader close them*. Only the first
is asked here.

Run: uv run python -u scripts/ambiguity_regime.py
"""

from __future__ import annotations

import itertools
import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import signature_worlds
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/ambiguity_regime.json")
N_CASES = 40
GROUPS = ("vehicle", "region", "bare")


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truths = [solve(c.world)[0] for c in cases]
    texts = [render_observation(c, variants=4).text for c in cases]
    print(f"{N_CASES} cases at V=4; a CLOSED group is resolved from the true "
          f"world\n", flush=True)
    hdr = (f"{'open groups':<26} {'worlds':>7} {'sound':>7} {'IN':>6} "
           f"{'OUT':>6} {'open':>6} {'decided':>8}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for k in range(len(GROUPS) + 1):
        for combo in itertools.combinations(GROUPS, k):
            openg = frozenset(combo)
            sound = n = 0
            ws, ins, outs, opens = [], [], [], []
            for case, want, text in zip(cases, truths, texts):
                if not want:
                    continue
                worlds = signature_worlds(text, open_groups=openg,
                                          truth=case.world)
                if not worlds:
                    continue
                answers = []
                for w in worlds:
                    try:
                        answers.append(frozenset(solve(w)[0]))
                    except Exception:
                        answers.append(frozenset())
                fleet = sorted({v for c in case.world.claims
                                if c.predicate == "mass" for v in c.entities()})
                cin = {v for v in fleet if all(v in a for a in answers)}
                cout = {v for v in fleet if all(v not in a for a in answers)}
                und = [v for v in fleet if v not in cin and v not in cout]
                n += 1
                sound += (cin <= set(want)
                          and set(want) <= cin | set(und))
                ws.append(len(worlds))
                ins.append(len(cin))
                outs.append(len(cout))
                opens.append(len(und))
            if not n:
                continue
            fleet_mean = statistics.mean(ins) + statistics.mean(outs) + \
                statistics.mean(opens)
            decided = (statistics.mean(ins) + statistics.mean(outs)) / fleet_mean
            label = ", ".join(combo) if combo else "(none -- fully resolved)"
            rows.append({"open": list(combo), "worlds": statistics.mean(ws),
                         "sound": sound / n, "in": statistics.mean(ins),
                         "out": statistics.mean(outs),
                         "undetermined": statistics.mean(opens),
                         "decided": decided, "n": n})
            print(f"{label:<26} {statistics.mean(ws):>7.0f} {sound/n:>7.3f} "
                  f"{statistics.mean(ins):>6.2f} {statistics.mean(outs):>6.2f} "
                  f"{statistics.mean(opens):>6.2f} {decided:>7.1%}",
                  flush=True)

    print(f"\nevery row is SOUND by construction -- the question is width.\n")
    useful = [r for r in rows if r["decided"] >= 0.5 and r["open"]]
    if useful:
        worst = max(useful, key=lambda r: r["worlds"])
        print(f"-> a bound stays useful (>=50% of the fleet decided) up to "
              f"{worst['worlds']:.0f} worlds,\n   with "
              f"{', '.join(worst['open'])} left open. Beyond that it is sound "
              f"and vacuous.")
    else:
        print(f"-> NO ambiguity level above zero keeps the bound useful. "
              f"Carrying ambiguity in\n   this task is sound and never "
              f"actionable.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
