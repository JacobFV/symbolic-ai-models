"""Is it hypothesis SIZE that makes carried ambiguity cheap, or was that a slogan?

The last finding ended on a general claim -- *ambiguity is cheap to carry when
the hypothesis about it is small* -- resting on one comparison: unbounded role
permutation was sound and vacuous (72 worlds, 0.0% decided), bounded
at-most-one-spurious-link was sound and free. Those two differ in the claim
**kind** as well as the bound, so the variable is confounded and the claim is not
earned.

This varies only the bound. Same domain, same reader, same collision -- flood's
``depot``/``flooded``/``needs`` role assignment, the one measured vacuous -- with
candidate worlds enumerated within ``k`` role reassignments of what the reader
read, for k = 0, 1, 2, 3.

``hard_distractors`` is **off** here on purpose: the phantom-link failure would
confound a measurement about roles.

Run: uv run python -u scripts/hypothesis_size_curve.py
"""

from __future__ import annotations

import itertools
import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Claim, EntityRef
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (read_signature_roles,
                                                       signature_readings)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/hypothesis_size_curve.json")
N = 60
KS = (0, 1, 2, 3)
ROLES = ("depot", "flooded", "needs")
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def read_roles(world) -> dict:
    out = {}
    for c in world.claims:
        if c.predicate in ROLES:
            out[c.roles["where"].id] = c.predicate
    return out


def with_roles(world, assignment: dict):
    """The world with its lone-region roles replaced by ``assignment``."""
    keep = tuple(c for c in world.claims if c.predicate not in ROLES)
    made = tuple(Claim(role, {"where": EntityRef(region)})
                 for region, role in sorted(assignment.items()))
    return replace(world, claims=keep + made)


def assignments(regions, current: dict, k: int):
    """Every assignment with one depot, one needs, the rest flooded, within
    ``k`` reassignments of ``current``.

    One depot and one needs is structural in this domain and is declared
    knowledge, not a hint -- enumerating assignments that violate it would
    inflate the space with worlds the generator can never produce.
    """
    # The reader's own reading is always a candidate, so k=0 is exactly the
    # collapsing baseline. Without this k=0 yields NOTHING whenever the reader's
    # assignment is not canonical -- and on the interleaved surface it usually is
    # not, because every lone region falls into one branch.
    yield dict(current)
    for depot, needs in itertools.permutations(regions, 2):
        cand = {r: "flooded" for r in regions}
        cand[depot] = "depot"
        cand[needs] = "needs"
        if cand != current and \
                sum(cand[r] != current.get(r) for r in regions) <= k:
            yield cand


def main() -> None:
    print(f"{N} cases, V=4, interleaved, hard_distractors=False "
          f"(roles isolated)\n")
    print(f"{'k':>3} {'worlds/case':>12} {'soundness':>10} {'decided':>9} "
          f"{'right when decided':>19}")
    print("-" * 58)
    rows = {}
    for k in KS:
        sound, decided, sizes, right, drift = [], [], [], [], []
        for s in range(N):
            case = generate(s)
            want = solve(case.world)[0]
            obs = render_observation(case, variants=4)
            text = interleave(unsaturate(obs, headings=HEADINGS,
                                         shuffle=False)).text
            world = read_signature_roles(text)
            truth_roles = read_roles(case.world)
            # The lone regions the reader SAW, not the ones it kept. Collapsed,
            # this reader sends every one of them to `needs` and -- since needs
            # is single-valued -- silently drops all but the first, so its own
            # world does not carry the candidates. `signature_readings` is the
            # emit-rather-than-collapse view of the same text.
            _, open_ = signature_readings(text)
            regions = sorted(set(open_["region_roles"]))
            if len(regions) < 2:
                continue
            # its best guess: what it committed to, with the rest defaulting to
            # flooded, which is what a reader forced to commit would say.
            read = read_roles(world)
            current = {r: read.get(r, "flooded") for r in regions}
            answers = set()
            n = 0
            for cand in assignments(regions, current, k):
                n += 1
                try:
                    answers.add(solve(with_roles(world, cand))[0])
                except Exception:
                    pass
            if not n:
                continue
            sizes.append(n)
            drift.append(sum(1 for r in regions
                             if current.get(r) != truth_roles.get(r)))
            sound.append(want in answers)
            is_dec = len(answers) == 1
            decided.append(is_dec)
            if is_dec:
                right.append(next(iter(answers)) == want)
        rows[k] = {"worlds": statistics.mean(sizes),
                   "reader_role_errors": statistics.mean(drift),
                   "soundness": statistics.mean(sound),
                   "decided": statistics.mean(decided),
                   "right_when_decided": (statistics.mean(right) if right
                                          else None)}
        r = rows[k]
        rw = f"{r['right_when_decided']:.3f}" if right else "--"
        print(f"{k:>3} {r['worlds']:>12.1f} {r['soundness']:>10.3f} "
              f"{r['decided']:>9.3f} {rw:>19}", flush=True)

    usable = [k for k in KS
              if rows[k]["soundness"] > 0.95 and rows[k]["decided"] > 0.1]
    print()
    if usable:
        k = usable[0]
        print(f"-> THE PRINCIPLE HOLDS. At k={k} soundness is "
              f"{rows[k]['soundness']:.3f} with {rows[k]['decided']:.3f}\n   "
              f"decided, so bounded role ambiguity IS usable and the earlier "
              f"vacuity result was\n   a property of the UNBOUNDED enumeration "
              f"rather than of role ambiguity itself.")
    else:
        best_sound = max(KS, key=lambda k: rows[k]["soundness"])
        best_sound = max(KS, key=lambda k: rows[k]["soundness"])
        print(f"-> THE PRINCIPLE IS WRONG AS STATED. No k has both soundness "
              f"above 0.95 and decidedness\n   above 0.1: decidedness "
              f"collapses {rows[0]['decided']:.3f} -> {rows[1]['decided']:.3f} "
              f"at the FIRST step, and soundness only\n   reaches "
              f"{rows[best_sound]['soundness']:.3f} at k={best_sound} where "
              f"{rows[best_sound]['decided']:.3f} is decided. There is no "
              f"useful middle.")
        print(f"\n   Hypothesis size is not what made the link case cheap. "
              f"DEPENDENCY is. A spurious\n   LINK is often inert -- the "
              f"network has other paths -- while a misassigned ROLE is\n   "
              f"never inert: it moves the depot, the destination or the "
              f"flooding, and the answer\n   depends on every one of them.")
        print(f"\n   The audit already measured this and I did not connect it. "
              f"Its COLLISION COST is\n   0.000 for link/bridge_on (nothing "
              f"even permutable) and 0.625 for\n   depot+flooded+needs. That "
              f"number, computed offline from the world and the surface\n   "
              f"with NO READER, predicts whether emitting rather than "
              f"collapsing will be usable:\n   cheap collision -> carrying is "
              f"free; expensive collision -> carrying is vacuous.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "rows": {str(k): v
                                                for k, v in rows.items()}},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
