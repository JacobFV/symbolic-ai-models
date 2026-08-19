"""The defect the prose scan found, with its mask taken off.

`audit_surface(prose=True)` flagged that flood's *"A disused track once ran from
X to Z"* carries exactly the ``link`` signature, and the reader admits one
spurious link in every one of 20 cases. It is harmless today only because the
generator draws that sentence's endpoints from ``_OUTSIDE`` -- regions that
appear nowhere else -- so the phantom edge connects nothing.

That is a **generator choice masking a reader defect**. A real report could
describe a disused track between two real places. This points the distractor at
two real, currently-unlinked regions and re-measures.

Nothing else changes: same claims, same answer, same phrasings. Only the two
region ids inside one distractor sentence.

Run: uv run python -u scripts/adversarial_distractor.py
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.scramble import interleave, unsaturate

OUT = Path("runs/adversarial_distractor.json")
N = 60
HEADINGS = ("SITUATION REPORT.", "ROAD NETWORK.", "OVERNIGHT.",
            "LOADING AND LIMITS.", "TASKING.")
_TRACK = re.compile(r"A disused track once ran from (region_\d+) to "
                    r"(region_\d+); it has not carried traffic for years\.")


def phantom_pair(case) -> tuple[str, str] | None:
    """Two real regions with no road between them, preferring a useful one.

    A phantom edge only matters if it could change the answer, so this prefers
    a pair joining the depot's side of the network to the demand site.
    """
    world = case.world
    regions = sorted({e for c in world.claims if c.predicate == "link"
                      for e in c.entities()})
    links = {frozenset(c.entities()) for c in world.claims
             if c.predicate == "link"}
    depot = next((c.roles["where"].id for c in world.claims
                  if c.predicate == "depot"), None)
    needs = next((c.roles["where"].id for c in world.claims
                  if c.predicate == "needs"), None)
    if depot and needs and frozenset({depot, needs}) not in links:
        return depot, needs                       # the maximally useful phantom
    for a in regions:
        for b in regions:
            if a < b and frozenset({a, b}) not in links:
                return a, b
    return None


def rewrite(text: str, pair: tuple[str, str]) -> str:
    a, b = pair
    return _TRACK.sub(f"A disused track once ran from {a} to {b}; it has not "
                      f"carried traffic for years.", text)


def score(adversarial: bool, interleaved: bool) -> tuple[float, float]:
    """(answer accuracy, spurious links admitted per case)."""
    ok, spurious = [], []
    for s in range(N):
        case = generate(s)
        want = solve(case.world)[0]
        obs = render_observation(case, variants=4)
        if interleaved:
            flat = unsaturate(obs, headings=HEADINGS, shuffle=False)
            text = interleave(flat).text
        else:
            text = unsaturate(obs, headings=HEADINGS).text
        if adversarial:
            pair = phantom_pair(case)
            if pair:
                text = rewrite(text, pair)
        world = read_content_roles(text)
        ok.append(solve(world)[0] == want)
        true_links = {frozenset(c.entities()) for c in case.world.claims
                      if c.predicate == "link"}
        got_links = {frozenset(c.entities()) for c in world.claims
                     if c.predicate == "link"}
        spurious.append(len(got_links - true_links))
    return statistics.mean(ok), statistics.mean(spurious)


def main() -> None:
    print(f"{'distractor':<26} {'surface':<13} {'accuracy':>9} "
          f"{'spurious links/case':>21}")
    print("-" * 72)
    rows = {}
    for adv in (False, True):
        for il in (False, True):
            a, sp = score(adv, il)
            label = "adversarial (real ids)" if adv else "as published (_OUTSIDE)"
            rows[f"{'adv' if adv else 'pub'}|{'inter' if il else 'grouped'}"] = {
                "accuracy": a, "spurious": sp}
            print(f"{label:<26} {'interleaved' if il else 'grouped':<13} "
                  f"{a:>9.3f} {sp:>21.2f}", flush=True)
        print()

    base = rows["pub|grouped"]["accuracy"]
    hard = rows["adv|grouped"]["accuracy"]
    print(f"-> pointing one distractor sentence at two REAL regions costs "
          f"{hard - base:+.3f}.")
    if hard < base - 0.1:
        print(f"   THE DEFECT IS REAL AND WAS MASKED BY THE GENERATOR. The "
              f"phantom edge creates\n   routes that do not exist, and the "
              f"reader has no way to reject it: the sentence\n   carries "
              f"EXACTLY the link signature, so by the audit's own logic no "
              f"content-free\n   observable separates it from a real road. "
              f"Distractor rejection is the same\n   closure result as role "
              f"assignment, not a separate problem -- which is also why\n   "
              f"scheduling's capability vocabulary works as a distractor "
              f"filter: it is CONTENT.")
    elif abs(hard - base) < 0.05:
        print(f"   THE FLOW ABSORBS IT. A phantom edge only adds candidate "
              f"routes, and every route\n   is re-checked against flooding and "
              f"bridge limits, so the wrong claim does not\n   survive to the "
              f"answer. That is a robustness property of the FLOW rather than "
              f"the\n   reader, and it means a false link is cheaper than a "
              f"false role.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"n": N, "rows": rows}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
