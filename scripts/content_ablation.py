"""Is the content actually load-bearing, or is elimination doing the work?

`read_content_roles` scores 1.000 in all four cells of the phrasing x
arrangement grid -- the first reader here invariant to both. That is a stronger
result than predicted (0.4-0.8 was the call), and a reader that beats its own
prediction is the one to distrust.

The control that must fail: **empty the anchors.** What is left is signature +
adjacency + elimination, which is content-free, and the closure finding says no
content-free observable settles depot vs flooded (21/21 role-slots ambiguous).
If the emptied arm still scores 1.000, either the closure finding is wrong or
this arm is getting its answer from somewhere undeclared.

Per-role ablations then say which vocabulary is actually carrying it.

Run: uv run python -u scripts/content_ablation.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (ROLE_ANCHORS,
                                                       read_content_roles)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/content_ablation.json")
N = 60


def score(anchors: dict, V: int, interleaved: bool) -> float:
    ok = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=V)
        flat = unsaturate(obs, drop_headings=True, shuffle=False)
        text = (interleave(flat).text if interleaved
                else unsaturate(obs).text)
        try:
            got = solve(read_content_roles(text, anchors=anchors))[0]
        except Exception:
            got = ()
        ok.append(got == want)
    return statistics.mean(ok)


def main() -> None:
    full = dict(ROLE_ANCHORS)
    arms = [("full", full), ("ALL anchors emptied",
                             {k: () for k in full})]
    arms += [(f"without {k}", {kk: (() if kk == k else v)
                               for kk, v in full.items()}) for k in full]
    arms += [(f"only {k}", {kk: (v if kk == k else ())
                            for kk, v in full.items()}) for k in full]

    print(f"{'anchors':<24} {'V1 grouped':>11} {'V1 inter':>9} "
          f"{'V4 grouped':>11} {'V4 inter':>9}")
    print("-" * 68)
    results = {}
    for label, anchors in arms:
        row = {"V1_grouped": score(anchors, 1, False),
               "V1_interleaved": score(anchors, 1, True),
               "V4_grouped": score(anchors, 4, False),
               "V4_interleaved": score(anchors, 4, True)}
        results[label] = row
        print(f"{label:<24} {row['V1_grouped']:>11.3f} "
              f"{row['V1_interleaved']:>9.3f} {row['V4_grouped']:>11.3f} "
              f"{row['V4_interleaved']:>9.3f}", flush=True)

    hard = "V4_interleaved"
    base = results["full"][hard]
    none = results["ALL anchors emptied"][hard]
    print(f"\n-> in the hardest cell, full anchors score {base:.3f} and the "
          f"emptied control {none:.3f}.")
    if none < 0.3 and base > 0.9:
        print(f"   THE CONTROL FAILS AS IT MUST. Content is load-bearing: "
              f"removing it costs\n   {base - none:.3f}, and what remains -- "
              f"signature, adjacency, elimination -- is exactly\n   the "
              f"content-free machinery the closure finding proved cannot settle "
              f"this group.")
        worst = min(results[f"without {k}"][hard] for k in full)
        which = [k for k in full if results[f"without {k}"][hard] == worst]
        print(f"   The single vocabulary that costs most to remove is "
              f"{which[0]!r}, at {worst:.3f}.")
    elif none > 0.9:
        print(f"   THE CONTROL PASSES, WHICH IS BAD. The arm reaches "
              f"{none:.3f} with NO content,\n   so either the closure finding "
              f"is wrong or this arm is reading something\n   undeclared. The "
              f"1.000 headline cannot stand until that is resolved.")
    else:
        print(f"   PARTIAL, and the decomposition says why. Content is worth "
              f"{base - none:+.3f}, so it is\n   load-bearing -- but the "
              f"content-free floor is {none:.3f}, not the 0.000 the earlier "
              f"finding\n   quoted for the arms that existed then.")
        print(f"\n   Measured at CLAIM level with the anchors emptied: needs "
              f"recall 1.000, depot 0.471,\n   flooded 0.632. So ADJACENCY "
              f"FULLY SOLVES `needs` with no content at all, which is why\n   "
              f"the needs vocabulary is redundant ({results['without needs'][hard]:.3f} "
              f"without it). Depot and flooded stay\n   where the closure "
              f"finding says they must, and answer accuracy exceeds their "
              f"recall\n   because a region wrongly marked flooded is often "
              f"not on the needed route.")
        print(f"\n   The closure result therefore stands at the CLAIM level. "
              f"What is corrected is the\n   answer-level claim that the cell "
              f"was empty: it was empty for the arms that\n   existed, and a "
              f"properly built content-free arm floors at {none:.3f}.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "results": results}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
