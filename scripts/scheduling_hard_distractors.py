"""Does the flood result generalise? Scheduling's distractors were defanged too.

Flood's disused track was inert only because the generator drew its endpoints
from **outside** the network. Scheduling's three distractors are inert for the
matching reason: the withdrawn machine and the cancelled job carry no capability
and no quantity, and "no machine is set up for anodising" names a capability
**outside the vocabulary**. Point one at a real entity with an in-vocabulary
word and the reader must admit it.

The two directions are **not symmetric**, and the asymmetry was found before the
run rather than after: each job needs exactly one capability, so a spurious
``needs_capability`` violates arity and is catchable by the mechanism built for
flood this morning. A machine holds any number, so a spurious ``has_capability``
is not. **And the uncatchable one is the unsound one** -- an extra machine
capability makes an infeasible instance read as feasible.

Reports accuracy by arm, the direction of every error, and the arity fire rate.

Run: uv run python -u scripts/scheduling_hard_distractors.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.scheduling.surface import render_observation

sys.path.insert(0, str(Path(__file__).parent))
from hard_regime_milestone import solve_world  # noqa: E402

OUT = Path("runs/scheduling_hard_distractors.json")
N = 200


def arity_violations(world) -> int:
    """Jobs claiming more than one capability. The domain allows exactly one."""
    per: Counter = Counter()
    for c in world.claims:
        if c.predicate == "needs_capability":
            per[c.roles["job"].id] += 1
    return sum(1 for v in per.values() if v > 1)


def run(hard) -> dict:
    rows = []
    for s in range(N):
        case = generate(s)
        text = render_observation(case, variants=4,
                                  hard_distractors=hard).text
        world = read_signature(text)
        got = solve_world(world)[0]
        rows.append({"seed": s, "truth": case.feasible, "got": got,
                     "arity": arity_violations(world)})
    n = len(rows)
    wrong = [r for r in rows if r["got"] != r["truth"]]
    return {
        "n": n,
        "accuracy": 1 - len(wrong) / n,
        "false_feasible": sum(1 for r in wrong if r["got"] and not r["truth"]),
        "false_infeasible": sum(1 for r in wrong
                                if not r["got"] and r["truth"]),
        "arity_fires": sum(1 for r in rows if r["arity"]) / n,
        "arity_catches": (sum(1 for r in wrong if r["arity"]) / len(wrong)
                          if wrong else float("nan")),
    }


def main() -> None:
    arms = {
        "default distractors (published)": False,
        "hard: machine only (spurious has_capability)": "machine",
        "hard: job only (spurious needs_capability)": "job",
        "hard: both": True,
    }
    out = {}
    print(f"{'arm':<46} {'acc':>7} {'false feas':>11} {'false inf':>10} "
          f"{'arity':>7}")
    print("-" * 86)
    for name, hard in arms.items():
        r = run(hard)
        out[name] = r
        print(f"{name:<46} {r['accuracy']:>7.3f} {r['false_feasible']:>11d} "
              f"{r['false_infeasible']:>10d} {r['arity_fires']:>7.3f}")

    print(f"\n{N} cases at the default regime (6 jobs, 3 machines, slack 0.15).")
    print("A FALSE FEASIBLE is an unsound answer: the reader admitted a "
          "capability\nthe floor does not have. Arity is the check built for "
          "flood this morning.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
