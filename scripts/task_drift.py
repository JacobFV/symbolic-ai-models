"""What happens when the TASK changes, not the surface.

The maintenance finding showed the signature-determinacy audit predicts
robustness to surface change -- rearrangement, rewording -- and said plainly that
it says nothing about a change in the underlying task.

So: introduce a claim kind no reader has seen, and one the world **cannot
express**. A region under a **weight restriction** admits light vehicles and
refuses heavy ones -- not equivalent to flooding, which refuses everything.

A first version used a *curfew* closing a region to all traffic. That was not a
task change at all: it has the same sentence signature as a flooding report, and
elimination defaults unresolved lone regions to ``flooded``, so the reader landed
on the right semantics by accident and answered 0/16 wrong. Every check "firing"
in that run was a false alarm, not a catch.

Two questions, and the second is the point:

1. Does the answer go wrong? (A reader with no branch drops the sentence.)
2. **Does anything catch it?** Every check in this repo -- the role flag, the
   role-independent certificate, the load-bearing completeness check -- inspects
   the **read world**, and a claim kind that never entered the world is invisible
   there.

And one thing nobody has computed: the text still contains the sentence. A reader
that accounted for every **sentence**, rather than every claim it managed to
produce, would notice one it could not type.

Run: uv run python -u scripts/task_drift.py
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import replace
from pathlib import Path

from symbolic_ai_core.world import Claim, EntityRef
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.certificate import certifies_role_independent
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (read_content_roles,
                                                       read_content_roles_checked)
from symbolic_ai_generators.flood.render import (omits_load_bearing,
                                                 render_answer, ungrounded)
from symbolic_ai_generators.flood.surface import render_observation

OUT = Path("runs/task_drift.json")
N = 60
_SENT = re.compile(r"(?<=[.?])\s+")


def curfew_target(case):
    """A region on the network that is not already flooded, depot or site."""
    busy = {c.roles["where"].id for c in case.world.claims
            if c.predicate in ("flooded", "depot", "needs")}
    regions = sorted({e for c in case.world.claims if c.predicate == "link"
                      for e in c.entities()})
    return next((r for r in regions if r not in busy), None)


def unconsumed_sentences(text: str) -> int:
    """Sentences whose removal does not change the read world.

    The task-drift detector, done properly. A first version asked whether the
    ENTITIES in a sentence were known, which fails immediately: the restricted
    region appears in the link claims, so the sentence looked read while
    contributing nothing. Consumption is not familiarity.

    This is ``len(sentences)`` reads, and a read costs 0.2 ms against a 9 ms
    answer, so the whole check is cheaper than solving once.
    """
    sents = [x for x in _SENT.split(text.replace("\n\n", " ")) if x.strip()]
    # Compare like with like. Reading the paragraph-structured original and the
    # sentence-joined variants makes every world differ for an unrelated reason
    # -- read_content_roles picks its network paragraph by content -- so nothing
    # ever looks unconsumed. A first version did exactly that and reported 0.
    full = read_content_roles(" ".join(sents))
    base = {(c.predicate, tuple(sorted(c.entities()))) for c in full.claims}
    unconsumed = 0
    for i in range(len(sents)):
        without = " ".join(s for j, s in enumerate(sents) if j != i)
        try:
            w = read_content_roles(without)
        except Exception:
            continue
        got = {(c.predicate, tuple(sorted(c.entities()))) for c in w.claims}
        if got == base:
            unconsumed += 1
    return unconsumed


def main() -> None:
    wrong = caught_cert = caught_flag = caught_omits = caught_cov = 0
    n = 0
    for s in range(N):
        case = generate(s)
        target = curfew_target(case)
        if target is None:
            continue
        # Ground truth under the changed task. A weight restriction admits
        # light vehicles and refuses heavy ones, which the world cannot express
        # -- so the truth is computed outside it: drop from the answer any
        # vehicle whose laden mass exceeds the cutoff, when its route must pass
        # through the restricted region.
        base = solve(case.world)[0]
        if not base:
            continue
        masses = {c.roles["of"].id: float(c.roles["value"].value)
                  for c in case.world.claims if c.predicate == "mass"}
        demand = next((float(c.roles["value"].value) for c in case.world.claims
                       if c.predicate == "demand"), 0.0)
        laden = sorted(masses[v] + demand for v in base if v in masses)
        if len(laden) < 2:
            continue
        cutoff = laden[0] + 1            # admits the lightest, refuses others
        # every route in this generator passes through the network, so treat the
        # restriction as binding on the heavier vehicles
        want = tuple(v for v in base if masses.get(v, 0.0) + demand <= cutoff)
        if want == base:
            continue
        n += 1

        obs = render_observation(case, variants=4)
        text = obs.text + (f"\n\nWEIGHT RESTRICTION. {target} admits vehicles "
                           f"up to {cutoff:.0f} kg only.")
        world, forced = read_content_roles_checked(text)
        got, outs, _ = solve(world)
        wrong += got != want

        # A check only CAUGHT it if the answer was actually wrong. Firing on a
        # correct answer is a false alarm, and the first version of this script
        # counted those as catches.
        bad = got != want
        if not bad:
            continue
        # A check signals DRIFT only if it fires more with the drifted sentence
        # than without it. omits_load_bearing fires on every template-rendered
        # paragraph regardless -- measured 0/18 complete -- so its raw rate here
        # carries no information, and a first version of this script counted it
        # as a perfect catch.
        clean_world, clean_forced = read_content_roles_checked(obs.text)
        clean_ans, clean_outs, _ = solve(clean_world)
        base_flag = not clean_forced
        base_cert = not certifies_role_independent(obs.text, solve)
        base_omits = bool(omits_load_bearing(
            render_answer(case, clean_ans, clean_outs), case))
        base_cov = unconsumed_sentences(obs.text)

        para = render_answer(case, got, outs)
        caught_flag += (not forced) and not base_flag
        caught_cert += (not certifies_role_independent(text, solve)) \
            and not base_cert
        caught_omits += bool(omits_load_bearing(para, case)) and not base_omits
        caught_cov += unconsumed_sentences(text) > base_cov

    print(f"{n} cases where the restriction changes the answer\n")
    print(f"  answers wrong                       : {wrong}/{n} "
          f"({wrong / n:.0%})")
    print(f"\n  catches counted ONLY where the check is silent without the "
          f"drift:\n")
    print(f"  caught by role_assignment_forced    : {caught_flag}/{n}")
    print(f"  caught by the certificate           : {caught_cert}/{n}")
    print(f"  caught by omits_load_bearing        : {caught_omits}/{n}")
    print(f"  caught by UNCONSUMED SENTENCES      : {caught_cov}/{n}"
          f"   (an INCREASE over the clean count, not its presence:\n    the clean text already has distractors that contribute nothing)")

    world_checks = max(caught_flag, caught_cert, caught_omits)
    print()
    if wrong and caught_cov > world_checks:
        print(f"-> THE WORLD-LEVEL CHECKS ARE BLIND AND THE TEXT-LEVEL ONE IS "
              f"NOT. A claim kind that\n   never entered the world cannot be "
              f"seen by anything inspecting the world, which\n   is the same "
              f"lesson as `ungrounded` and the certificate -- a check that reads "
              f"part of\n   the world inherits that part's errors -- one level "
              f"up, at the task.")
        print(f"\n   Input coverage catches it {caught_cov}/{n} because the "
              f"SENTENCE is still there even\n   though the claim is not. The "
              f"reader consumed the text, so it can account for\n   what it did "
              f"not consume, and nothing in this repo was doing that.")
    elif wrong and caught_cov == 0:
        print(f"-> NOTHING CATCHES IT, including coverage. The reader is "
              f"attributing the curfew\n   sentence to entities it already "
              f"knows, so the sentence does not look unread.")
    else:
        print(f"-> answers wrong {wrong}/{n}; world checks {world_checks}/{n}; "
              f"coverage {caught_cov}/{n}.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": n, "wrong": wrong,
                               "caught_flag": caught_flag,
                               "caught_certificate": caught_cert,
                               "caught_omits": caught_omits,
                               "caught_coverage": caught_cov}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
