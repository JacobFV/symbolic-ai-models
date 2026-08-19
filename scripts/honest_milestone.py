"""The milestone table with every prop removed.

`scripts/milestone_end_to_end.py` is the programme's north-star measurement --
$ per solved episode with the reader in front -- and it is measured on a surface
that has since been shown to be doing much of the work:

- it reads with ``read_signature``, whose 1.000 is **hard-coded paragraph
  indices** (2026-08-19);
- on **grouped** paragraphs with **section headings**, both removable and both
  now known to be removable at no cost to a properly built reader;
- against a distractor whose phantom edge joins regions appearing nowhere else,
  worth **-0.633** once armed.

This re-runs it with all three props off, and with the readers that now exist.
The old script is left alone: its numbers are published and changing it in place
would silently redefine them.

The number wanted here is not the accuracy but the **decomposition**. The
published table concludes that kernel losses dominate and reader loss is zero.
If that inverts, the programme's marginal effort belongs somewhere else.

Run: uv run python -u scripts/honest_milestone.py
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (read_content_roles,
                                                       read_lexical,
                                                       read_signature,
                                                       read_signature_roles,
                                                       read_surface)
from symbolic_ai_generators.flood.render import render_answer, ungrounded
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/honest_milestone.json")
N = 40
V = 4
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")


def cost_of(outputs) -> float:
    total = 0.0
    for artifact in (outputs or {}).values():
        value = getattr(artifact, "value", None)
        if not isinstance(value, dict):
            continue
        c = value.get("cost")
        if isinstance(c, dict) and "usd" in c:
            total += float(c["usd"] or 0.0)
        elif "usd" in value:
            total += float(value["usd"] or 0.0)
    return total


def run(cases, truths, texts, reader, ablations) -> dict:
    usd = 0.0
    hits_ne = n_ne = 0
    rendered = grounded = 0
    recs = []
    for case, want in zip(cases, truths):
        try:
            world = reader(case)
            answer, outs, _ = solve(world, **ablations)
            usd += cost_of(outs)
        except Exception:
            world, answer, outs = None, (), None
        if world is not None:
            t = {(c.predicate, tuple(sorted(c.entities())))
                 for c in case.world.claims}
            g = {(c.predicate, tuple(sorted(c.entities())))
                 for c in world.claims}
            recs.append(len(t & g) / len(t) if t else 0.0)
        if want:
            n_ne += 1
            hits_ne += answer == want
        if outs is not None and world is not None:
            try:
                para = render_answer(case, answer, outs)
                rendered += 1
                grounded += not ungrounded(para, case, outs)
            except Exception:
                pass
    return {"claim_recall": statistics.mean(recs) if recs else 0.0,
            "acc_non_empty": hits_ne / max(1, n_ne),
            "usd_per_correct": (usd / hits_ne) if hits_ne else float("inf"),
            "grounded": (grounded / rendered) if rendered else float("nan")}


def main() -> None:
    cases = [generate(s) for s in range(N)]
    truths = [solve(c.world)[0] for c in cases]
    texts = {}
    for c in cases:
        obs = render_observation(c, variants=V, hard_distractors=True)
        flat = unsaturate(obs, headings=HEADINGS, shuffle=False)
        texts[c.seed] = interleave(flat).text
    empty = sum(1 for t in truths if not t)
    print(f"{N} cases, V={V}, interleaved, hard_distractors=True. "
          f"{empty} have an empty answer\n({empty/N:.0%}) and are excluded from "
          f"the headline column.\n")

    def on_text(fn):
        return lambda c: fn(texts[c.seed])

    readers = (
        ("oracle world (CEILING)", lambda c: c.world, {}),
        ("signature+content", on_text(read_content_roles), {}),
        ("signature/roles", on_text(read_signature_roles), {}),
        ("signature/index (published)", on_text(read_signature), {}),
        ("rules", on_text(read_surface), {}),
        ("lexical cue routing", on_text(read_lexical), {}),
    )
    ablations = (
        ("oracle, no datalog reachability", lambda c: c.world,
         {"ignore_flooding": True}),
        ("oracle, no SMT load check", lambda c: c.world,
         {"ignore_bridge_limits": True}),
        ("oracle, no ASP route search", lambda c: c.world,
         {"first_route_only": True}),
    )

    hdr = (f"{'system':<32} {'claim R':>8} {'task acc':>9} {'$/correct':>11} "
           f"{'grounded':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = {}
    for label, reader, abl in list(readers) + list(ablations):
        if label.startswith("oracle,"):
            print()
        r = run(cases, truths, texts, reader, abl)
        rows[label] = r
        print(f"{label:<32} {r['claim_recall']:>8.3f} "
              f"{r['acc_non_empty']:>9.3f} {r['usd_per_correct']:>11.2e} "
              f"{r['grounded']:>9.3f}", flush=True)

    ceiling = rows["oracle world (CEILING)"]["acc_non_empty"]
    best = max((k for k in rows if not k.startswith("oracle")),
               key=lambda k: rows[k]["acc_non_empty"])
    reader_loss = ceiling - rows[best]["acc_non_empty"]
    kernel_losses = {k.split(", ")[1]: ceiling - rows[k]["acc_non_empty"]
                     for k in rows if k.startswith("oracle,")}
    print(f"\ndecomposition against the oracle ceiling of {ceiling:.3f}:\n")
    print(f"  reader loss ({best:<24}) {reader_loss:>7.3f}")
    for k, v in sorted(kernel_losses.items(), key=lambda kv: -kv[1]):
        print(f"  kernel loss ({k:<24}) {v:>7.3f}")

    worst_kernel = max(kernel_losses.values())
    print()
    if reader_loss >= worst_kernel:
        print(f"-> READER LOSS NOW MATCHES OR EXCEEDS EVERY KERNEL LOSS: "
              f"{reader_loss:.3f} against a worst\n   kernel loss of "
              f"{worst_kernel:.3f}. The published table concludes the opposite "
              f"-- reader loss\n   0.000, kernel losses up to 0.500 -- and it "
              f"reaches that on a surface whose headings,\n   grouping and "
              f"distractor were all doing work.")
    else:
        print(f"-> reader loss {reader_loss:.3f} still sits below the worst "
              f"kernel loss {worst_kernel:.3f}.")

    best_row = rows[best]
    print(f"\n-> CLAIM RECALL IS THE WRONG READER COLUMN. {best} scores "
          f"{best_row['claim_recall']:.3f} recall\n   and "
          f"{best_row['acc_non_empty']:.3f} accuracy: its failure is a claim it "
          f"ADDS, and recall cannot see a\n   false positive. The published "
          f"table reports recall as its reader-quality column.")

    print(f"\n-> $/correct for the best reader is "
          f"{best_row['usd_per_correct']:.2e}, "
          f"{best_row['usd_per_correct'] / rows['oracle world (CEILING)']['usd_per_correct']:.1f}x "
          f"the oracle's\n   "
          f"{rows['oracle world (CEILING)']['usd_per_correct']:.2e}. The spend "
          f"is nearly identical; what changes is how many\n   correct answers "
          f"it buys.")

    print(f"\n-> GROUNDING READS {best_row['grounded']:.3f} AND MEANS LESS "
          f"THAN IT APPEARS. ungrounded() builds its\n   admissible edges from "
          f"the routes the flow computed FROM THE READ WORLD, so a route over\n"
          f"   a phantom edge is self-consistent and passes. Demonstrated: a "
          f"case whose true answer\n   is EMPTY renders as \"truck_0 runs "
          f"region_0 to region_3\" -- a road that does not exist --\n   with "
          f"ungrounded() returning []. The check certifies INTERNAL CONSISTENCY "
          f"WITH THE READ\n   WORLD, not truth: it catches renderer errors and "
          f"cannot, by construction, catch\n   reader errors.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "variants": V, "rows": rows,
                               "reader_loss": reader_loss,
                               "kernel_losses": kernel_losses}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
