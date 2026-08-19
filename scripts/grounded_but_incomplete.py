"""Grounding certifies what is said. It cannot see what is left out.

Every renderer in this repo formats a **fixed template**, so nothing is ever
omitted by choice and the grounding check has never had to face omission. A
renderer that must **select** what to say -- the case the stage-accounting
finding flagged as not transferring -- makes omission possible for the first
time.

`ungrounded()` verifies that everything *asserted* is supported: tokens appear in
the world or the flow's outputs, route hops are real edges, the paragraph does
not contradict the structured answer. Every one of those is a property of what is
**present**.

So this renders under a **citation budget** and measures two things separately:

- **grounded** -- the existing check;
- **decision-complete** -- can a reader of the paragraph *alone* reconstruct the
  answer? Rebuild a world from only the cited facts, re-solve, and compare.

Run: uv run python -u scripts/grounded_but_incomplete.py
"""

from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Quantity, WorldSnapshot
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.render import ungrounded

OUT = Path("runs/grounded_but_incomplete.json")
N = 60
BUDGETS = (0, 2, 4, 8, 16, 999)


def supporting_claims(case, answer) -> list[int]:
    """Indices of the claims a complete explanation would have to cite.

    Ordered as a selecting renderer plausibly would: the query first, then the
    network, then the constraints that bind. The budget cuts from the tail, which
    is where the binding facts sit -- that is exactly the failure mode.
    """
    order = {"needs": 0, "demand": 1, "depot": 2, "mass": 3, "capacity": 4,
             "link": 5, "bridge_on": 6, "flooded": 7, "load_limit": 8}
    idx = [(order.get(c.predicate, 9), i)
           for i, c in enumerate(case.world.claims)]
    return [i for _, i in sorted(idx)]


def _selected_paragraph(case, answer, cited: list[int]):
    """A real paragraph citing only ``cited``, for the real grounding check.

    Deliberately minimal: the verdict sentence the template always emits, then
    one clause per cited claim. Every token it contains comes from a claim or
    from the flow's outputs, which is what makes the grounding result meaningful
    rather than an artefact of inventing prose.
    """
    from symbolic_ai_generators.flood.render import Answer

    parts = []
    if answer:
        parts.append(f"{len(answer)} vehicles can make the delivery: "
                     f"{', '.join(answer)}.")
    else:
        parts.append("No vehicle can make the delivery.")
    for i in cited:
        c = case.world.claims[i]
        ents = " ".join(c.entities())
        q = c.roles.get("value")
        if isinstance(q, Quantity):
            parts.append(f"{ents} {float(q.value):.0f} kg.")
        elif ents:
            parts.append(f"{ents}.")
    return Answer(structured=tuple(answer), text=" ".join(parts),
                  citations=())


def cited_world(case, cited: list[int]) -> WorldSnapshot:
    """The world a reader could rebuild from the cited facts alone."""
    return replace(case.world,
                   claims=tuple(case.world.claims[i] for i in sorted(cited)))


def main() -> None:
    cases = [generate(s) for s in range(N)]
    truth = [solve(c.world)[0] for c in cases]
    ne = [i for i, t in enumerate(truth) if t]
    print(f"{N} cases, {len(ne)} with a non-empty answer\n")

    print(f"{'budget':>8} {'cited':>7} {'grounded':>10} {'decision-complete':>19}")
    print("-" * 48)
    rows = {}
    for budget in BUDGETS:
        grounded, complete, cited_n = [], [], []
        for i in ne:
            case, want = cases[i], truth[i]
            picks = supporting_claims(case, want)[:budget]
            cited_n.append(len(picks))
            # Grounding is MEASURED, not argued. An earlier version of this
            # asserted grounded=True on the reasoning that a subset of true
            # claims asserts nothing false -- which is correct and is still not
            # a measurement. Build the paragraph and run the real check.
            answer, outs, _ = solve(case.world)
            para = _selected_paragraph(case, answer, picks)
            grounded.append(not ungrounded(para, case, outs))
            try:
                got = solve(cited_world(case, picks))[0]
            except Exception:
                got = ()
            complete.append(got == want)
        rows[budget] = {"cited": statistics.mean(cited_n),
                        "grounded": statistics.mean(grounded),
                        "complete": statistics.mean(complete)}
        r = rows[budget]
        print(f"{budget if budget < 999 else 'all':>8} {r['cited']:>7.1f} "
              f"{r['grounded']:>10.3f} {r['complete']:>19.3f}")

    small = rows[4]
    full = rows[999]
    print(f"\n  at a budget of 4 facts: grounded {small['grounded']:.3f}, "
          f"decision-complete {small['complete']:.3f}")
    print(f"  with everything cited : grounded {full['grounded']:.3f}, "
          f"decision-complete {full['complete']:.3f}")

    print()
    if small["grounded"] == 1.0 and small["complete"] < 0.5:
        print(f"-> GROUNDED AND USELESS. Every paragraph is grounded at every "
              f"budget, because a\n   paragraph that cites a SUBSET of true "
              f"claims asserts nothing false -- and at a\n   budget of 4 a "
              f"reader of the paragraph alone reconstructs the answer "
              f"{small['complete']:.0%} of the\n   time.")
        print(f"\n   The two are independent by construction: `ungrounded` "
              f"inspects what is PRESENT\n   -- tokens, route hops, "
              f"contradiction with the structured answer -- and omission is\n"
              f"   a property of what is ABSENT. No amount of grounding can "
              f"reach it.")
        print(f"\n   That matters because the pipeline's argument is that its "
              f"reasoning is\n   INSPECTABLE. A paragraph that is fully "
              f"grounded and materially incomplete is\n   inspectable in the "
              f"letter and not in substance.")
    else:
        print(f"-> completeness tracks grounding more closely than expected; "
              f"the existing check may\n   already imply it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": len(ne), "rows": {str(k): v
                                                      for k, v in rows.items()}},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
