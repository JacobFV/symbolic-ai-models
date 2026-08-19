"""When does carrying the ambiguity beat choosing one interpretation?

The programme's critical invariant:

> Do not collapse ambiguity merely to obtain a single world. If the reader
> produces "entity may be A or B", the world should be able to carry that, and
> downstream kernels may resolve it, branch over it, bound over it, or refuse.

`read_signature` resolves its type-signature ambiguities using **paragraph
position**, which is a property of this generator's five-paragraph template.
Ablate position and the ambiguity is real:

```
(1 vehicle, 1 quantity)  ->  mass OR capacity
(1 region,  0 quantity)  ->  flooded OR depot OR needs
(0 entities, 1 quantity) ->  the pronoun capacity OR the demand
```

`link` vs `bridge_on` still resolves **structurally** -- a bridge is a pair
carrying a limit -- so what remains is bounded and enumerable: about 96 worlds.

Two policies on the same reading:

**collapse** picks one world and answers. It may be wrong and cannot say so.

**bound** enumerates every consistent world, runs the kernels on each, and
reports three sets: vehicles in *every* world (certainly in), vehicles in *no*
world (certainly out), and the rest (undetermined). That answer is never wrong;
the question is whether it is narrow enough to be worth having.

Run: uv run python -u scripts/ambiguity_vs_guessing.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import signature_worlds
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/ambiguity_vs_guessing.json")
N_CASES = 40
VARIANTS = 4


def main() -> None:
    cases = [generate(s) for s in range(N_CASES)]
    truths = [solve(c.world)[0] for c in cases]
    print(f"{N_CASES} cases at V={VARIANTS}; position ABLATED so the signature "
          f"ambiguities are real\n", flush=True)

    rows = []
    collapse_hits = collapse_n = 0
    sound = bound_n = 0
    widths, ins, outs = [], [], []
    refusals = 0
    for case, want in zip(cases, truths):
        text = render_observation(case, variants=VARIANTS).text
        worlds = signature_worlds(text)
        if not worlds:
            refusals += 1
            continue
        answers = []
        for w in worlds:
            try:
                answers.append(frozenset(solve(w)[0]))
            except Exception:
                answers.append(frozenset())
        fleet = sorted({v for c in case.world.claims
                        if c.predicate == "mass" for v in c.entities()})
        certainly_in = {v for v in fleet if all(v in a for a in answers)}
        certainly_out = {v for v in fleet if all(v not in a for a in answers)}
        undetermined = [v for v in fleet
                        if v not in certainly_in and v not in certainly_out]

        # collapse: take the first consistent world, which is a guess
        collapse_n += 1
        collapse_hits += (tuple(sorted(answers[0])) == want)

        if want:                      # report on cases with a real answer
            bound_n += 1
            ok = (certainly_in <= set(want)
                  and set(want) <= certainly_in | set(undetermined))
            sound += ok
            widths.append(len(undetermined))
            ins.append(len(certainly_in))
            outs.append(len(certainly_out))
            rows.append({"seed": case.seed, "worlds": len(worlds),
                         "fleet": len(fleet), "certainly_in": len(certainly_in),
                         "certainly_out": len(certainly_out),
                         "undetermined": len(undetermined), "sound": ok})

    print(f"refusals (ambiguity too large to name): {refusals}\n")
    print(f"COLLAPSE -- pick one consistent world and answer")
    print(f"  exact-set accuracy, all cases: "
          f"{collapse_hits/max(1,collapse_n):.3f}\n")
    print(f"BOUND -- every consistent world, three-valued answer "
          f"(non-empty cases, n={bound_n})")
    print(f"  sound (truth inside the bound):        "
          f"{sound/max(1,bound_n):.3f}")
    print(f"  fleet size:                            "
          f"{statistics.mean(r['fleet'] for r in rows):.2f}")
    print(f"  certainly IN per case:                 "
          f"{statistics.mean(ins):.2f}")
    print(f"  certainly OUT per case:                "
          f"{statistics.mean(outs):.2f}")
    print(f"  UNDETERMINED per case:                 "
          f"{statistics.mean(widths):.2f}")
    decided = statistics.mean(ins) + statistics.mean(outs)
    fleet_mean = statistics.mean(r["fleet"] for r in rows)
    print(f"\n  the bound decides {decided/fleet_mean:.1%} of the fleet and "
          f"leaves {1-decided/fleet_mean:.1%} open")
    print(f"  worlds enumerated per case: "
          f"{statistics.mean(r['worlds'] for r in rows):.0f}")

    if sound < bound_n:
        print(f"\n!! UNSOUND on {bound_n-sound} cases -- the truth fell outside "
              f"the enumeration. That is a\n   reader bug, not a finding, and it "
              f"invalidates the comparison.")
    elif decided / fleet_mean > 0.5:
        print(f"\n-> CARRYING THE AMBIGUITY BEATS GUESSING HERE. Collapsing is "
              f"right "
              f"{collapse_hits/max(1,collapse_n):.1%} of the time and cannot "
              f"say when;\n   the bound is right every time and still decides "
              f"{decided/fleet_mean:.0%} of the fleet.")
    else:
        print(f"\n-> THE BOUND IS TOO WIDE TO BE USEFUL at this ambiguity "
              f"level. It is never wrong\n   and leaves "
              f"{1-decided/fleet_mean:.0%} of the fleet open, which a caller "
              f"cannot act on.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n_cases": N_CASES, "variants": VARIANTS, "refusals": refusals,
         "collapse_accuracy": collapse_hits / max(1, collapse_n),
         "bound_soundness": sound / max(1, bound_n),
         "mean_undetermined": statistics.mean(widths) if widths else None,
         "mean_certainly_in": statistics.mean(ins) if ins else None,
         "mean_certainly_out": statistics.mean(outs) if outs else None,
         "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
