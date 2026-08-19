"""Does the explanation stay true when the reader does not?

Inspectability is one of the five properties `APPROACH.md` argues for, and it has
only been checked on the easy surface. `ungrounded` already carries the scope
note: it certifies consistency with the world **as read**, not truth. So on the
honest surface -- where the reader admits a phantom link on every case -- an
explanation can cite a fact that is **false** and pass every check here.

Renders each answer from the **read** world and checks every ``claim:`` citation
against the **true** one. The split that matters is by whether the answer was
right: a wrong answer with a wrong explanation is a reading failure already
counted, while **a correct answer with a fabricated justification** is a separate
thing, and it is what a symbolic pipeline is supposed to be immune to.

Run: uv run python -u scripts/honest_explanations.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.render import (render_answer,
                                                 render_complete, ungrounded)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

OUT = Path("runs/honest_explanations.json")
N = 300


def key(claim) -> tuple:
    roles = []
    for name in sorted(claim.roles):
        r = claim.roles[name]
        roles.append((name, r.id if hasattr(r, "id")
                      else (float(r.value) if hasattr(r, "value") else str(r))))
    return (claim.predicate, tuple(roles))


def run(renderer, hard: bool) -> dict:
    rows = []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        if not want:
            continue
        obs = render_observation(case, variants=4, hard_distractors=hard)
        text = interleave(unsaturate(obs, drop_headings=True,
                                     shuffle=False)).text
        try:
            world = read_content_roles(text)
            got, outputs, _ = solve(world)
        except Exception:
            continue
        shim = replace(case, world=world)
        answer = renderer(shim, got, outputs)

        true_keys = {key(c) for c in case.world.claims}
        false_cites = 0
        cites = 0
        for c in answer.citations:
            if not c.source.startswith("claim:"):
                continue
            ref = c.source.split(":", 1)[1]
            # The renderer's citation scheme is NOT uniform: some sources are a
            # claim index and some are a predicate name ("claim:needs",
            # "claim:flooded"). A checker has to resolve both, which is a small
            # defect worth recording -- a citation that cannot be resolved to a
            # claim cannot be checked against anything.
            if ref.isdigit():
                i = int(ref)
                if not (0 <= i < len(world.claims)):
                    continue
                cites += 1
                if key(world.claims[i]) not in true_keys:
                    false_cites += 1
            elif ref in ("needs", "flooded"):
                cites += 1
                where = answer.text[c.start:c.end]
                if (ref, (("where", where),)) not in true_keys:
                    false_cites += 1
        rows.append({"seed": s, "correct": got == want, "cites": cites,
                     "false_cites": false_cites,
                     "ungrounded": bool(ungrounded(answer, shim, outputs))})

    n = len(rows)
    right = [r for r in rows if r["correct"]]
    wrong = [r for r in rows if not r["correct"]]
    return {
        "n": n,
        "accuracy": len(right) / n,
        "mean_citations": statistics.mean(r["cites"] for r in rows),
        "false_per_citation": (sum(r["false_cites"] for r in rows)
                               / max(sum(r["cites"] for r in rows), 1)),
        "any_false": statistics.mean(bool(r["false_cites"]) for r in rows),
        "any_false_when_correct": (statistics.mean(bool(r["false_cites"])
                                                   for r in right)
                                   if right else float("nan")),
        "any_false_when_wrong": (statistics.mean(bool(r["false_cites"])
                                                 for r in wrong)
                                 if wrong else float("nan")),
        "ungrounded_flags": statistics.mean(r["ungrounded"] for r in rows),
    }


def main() -> None:
    out = {}
    print(f"{'renderer':<12} {'surface':<10} {'acc':>6} {'cites':>7} "
          f"{'false/cite':>11} {'any false':>10} {'| correct':>10} "
          f"{'| wrong':>9} {'ungrounded':>11}")
    print("-" * 94)
    for rname, renderer in (("template", render_answer),
                            ("complete", render_complete)):
        for sname, hard in (("clean", False), ("honest", True)):
            r = run(renderer, hard)
            out[f"{rname}/{sname}"] = r
            print(f"{rname:<12} {sname:<10} {r['accuracy']:>6.3f} "
                  f"{r['mean_citations']:>7.2f} "
                  f"{r['false_per_citation']:>11.4f} {r['any_false']:>10.3f} "
                  f"{r['any_false_when_correct']:>10.3f} "
                  f"{r['any_false_when_wrong']:>9.3f} "
                  f"{r['ungrounded_flags']:>11.3f}")

    print("\n'any false' is the share of explanations citing at least one claim")
    print("absent from the TRUE world. '| correct' is that share among answers")
    print("that were RIGHT -- a correct answer with a fabricated justification.")
    print("'ungrounded' is the repo's own check, which by construction cannot")
    print("see any of this: it certifies consistency with the world AS READ.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
