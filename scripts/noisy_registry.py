"""What the value registry was worth, and what its absence does to the marker.

`render.uncorroborated` flagged **88 of 88** false citations on the honest
surface. The limit was stated in the same breath: recall is 1.000 only because no
reader error there lands on a **value**, and what stops that is flood's
``VALUE_REGISTRY`` -- whose own docstring says the sets are *"the generator's own
draw sets, unusually clean; a real registry would be noisier and would overlap"*.

So overlap them, as a real vocabulary would, and re-measure. Two things come out
that had never been measured: what the registry is worth end to end on the honest
surface, and whether the marker's perfect recall survives without it.

Run: uv run python -u scripts/noisy_registry.py
"""

from __future__ import annotations

import collections
import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (
    VALUE_REGISTRY, read_content_roles_checked)
from symbolic_ai_generators.flood.render import render_complete, uncorroborated
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/noisy_registry.json")
N = 300

#: A registry that overlaps, which is what a real one does. Every capacity value
#: is also listed as a possible mass -- the vocabularies stop being disjoint
#: exactly where the reader relies on them being disjoint.
NOISY = {"mass": frozenset(VALUE_REGISTRY["mass"] | VALUE_REGISTRY["capacity"]),
         "capacity": VALUE_REGISTRY["capacity"],
         "demand": VALUE_REGISTRY["demand"]}

#: And one with no value knowledge at all, for the floor.
EMPTY = {"mass": frozenset(), "capacity": frozenset(), "demand": frozenset()}


def key(claim) -> tuple:
    roles = []
    for name in sorted(claim.roles):
        r = claim.roles[name]
        roles.append((name, r.id if hasattr(r, "id")
                      else (float(r.value) if hasattr(r, "value") else str(r))))
    return (claim.predicate, tuple(roles))


def run(registry) -> dict:
    ok, cites, false, flagged, caught = [], 0, 0, 0, 0
    by_pred: collections.Counter = collections.Counter()
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=True)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        try:
            world, forced = read_content_roles_checked(text, registry=registry)
            got, outputs, _ = solve(world)
        except Exception:
            continue
        ok.append(got == want)
        answer = render_complete(replace(case, world=world), got, outputs)
        true_keys = {key(c) for c in case.world.claims}
        marks = set(uncorroborated(answer, world, forced=forced))
        for c in answer.citations:
            if not c.source.startswith("claim:"):
                continue
            ref = c.source.split(":", 1)[1]
            cited = answer.text[c.start:c.end]
            if ref.isdigit() and 0 <= int(ref) < len(world.claims):
                claim = world.claims[int(ref)]
                bad = key(claim) not in true_keys
                pred = claim.predicate
            elif ref in ("needs", "flooded"):
                bad = (ref, (("where", cited),)) not in true_keys
                pred = ref
            else:
                continue
            cites += 1
            flagged += cited in marks
            if bad:
                false += 1
                by_pred[pred] += 1
                caught += cited in marks
    return {"n": len(ok), "accuracy": statistics.mean(ok),
            "citations": cites, "false": false,
            "flagged_share": flagged / max(cites, 1),
            "marker_recall": caught / false if false else float("nan"),
            "false_by_predicate": dict(by_pred)}


def main() -> None:
    out = {}
    print(f"{'registry':<22} {'accuracy':>9} {'citations':>10} {'false':>7} "
          f"{'flagged':>8} {'marker recall':>14}")
    print("-" * 76)
    for name, reg in (("clean (published)", None), ("overlapping", NOISY),
                      ("none", EMPTY)):
        r = run(reg)
        out[name] = r
        print(f"{name:<22} {r['accuracy']:>9.3f} {r['citations']:>10} "
              f"{r['false']:>7} {r['flagged_share']:>8.3f} "
              f"{r['marker_recall']:>14.3f}")
        preds = ", ".join(f"{k} {v}" for k, v in
                          sorted(r["false_by_predicate"].items(),
                                 key=lambda kv: -kv[1]))
        print(f"{'':<22} false by predicate: {preds}")

    print("\nThe marker flags `link` always and depot/flooded when the role")
    print("assignment was not forced. It cannot flag a MASS or a CAPACITY,")
    print("because on the published registry those are never wrong -- which is")
    print("a property of the registry and not of the reader.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
