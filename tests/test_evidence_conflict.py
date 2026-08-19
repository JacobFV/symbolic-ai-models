"""Two independent signals for one role, and the disagreement was discarded.

The reader finds the needs site two ways -- a lexical anchor, and positional
adjacency to the bare demand quantity -- and consults the second only when the
first stayed silent. `evidence_conflict` recovers the discarded disagreement,
which is the **only** signal measured that sees a *misfire*.

Three forms, each the unique coverer of one misfire direction, none of them a
stronger check than the others -- each reads a **different fact**. Tests below
pin both the catches and the reason each form cannot cover the others.
"""

from __future__ import annotations

import sys
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood import surface as S
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import evidence_conflict
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from misfiring_vocabulary import MISFIRING  # noqa: E402

SEEDS = 60


def _fire_rate(variants) -> tuple[int, int]:
    original = dict(S._VARIANTS)
    if variants:
        for role, forms in variants.items():
            S._VARIANTS[role] = forms
    try:
        fired = n = 0
        for s in range(SEEDS):
            case = generate(s)
            if not solve(case.world)[0]:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            n += 1
            fired += bool(evidence_conflict(interleave(flat).text))
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    return fired, n


def test_silent_on_the_published_surface():
    """Zero false alarms in normal operation: 0 of 252 at 400 seeds."""
    fired, n = _fire_rate(None)
    assert fired == 0, f"{fired} false alarms in {n} clean cases"


def test_catches_a_misfire_that_steals_the_needs_slot():
    fired, n = _fire_rate({"depot": MISFIRING["depot"]})
    assert fired > n * 0.5, f"only {fired}/{n}"


def test_catches_the_worst_misfire_which_steals_no_slot():
    """A needs sentence tripping the flooding vocabulary marks the destination
    impassable -- accuracy 0.151, the worst measured -- and does not take the
    needs slot, so only the `reassigned` form can see it."""
    original = dict(S._VARIANTS)
    S._VARIANTS["needs"] = MISFIRING["needs"]
    try:
        forms = set()
        for s in range(SEEDS):
            case = generate(s)
            if not solve(case.world)[0]:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            forms |= set(evidence_conflict(interleave(flat).text))
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    assert "reassigned" in forms, forms




def test_arity_closes_the_depot_blind_spot():
    """Two regions claiming one single-valued role needs no second signal at
    all, only the domain's arity -- and it is what sees a misfire onto depot,
    the direction adjacency cannot reach. 0.833 at 400 seeds."""
    original = dict(S._VARIANTS)
    S._VARIANTS["flooded"] = MISFIRING["flooded"]
    try:
        fired = n = 0
        for s in range(SEEDS):
            case = generate(s)
            if not solve(case.world)[0]:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            n += 1
            fired += "arity" in evidence_conflict(interleave(flat).text)
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    assert fired > n * 0.5, f"only {fired}/{n}"


def test_arity_is_silent_where_the_role_is_multi_valued():
    """`flooded` holds any number of regions, so a needs sentence tripping the
    flooding vocabulary violates no arity. That is why `reassigned` exists."""
    original = dict(S._VARIANTS)
    S._VARIANTS["needs"] = MISFIRING["needs"]
    try:
        fired = 0
        for s in range(SEEDS):
            case = generate(s)
            if not solve(case.world)[0]:
                continue
            obs = S.render_observation(case, variants=4)
            flat = unsaturate(obs, drop_headings=True, shuffle=False)
            fired += "arity" in evidence_conflict(interleave(flat).text)
    finally:
        S._VARIANTS.clear()
        S._VARIANTS.update(original)
    assert fired == 0, f"arity fired {fired} times on a multi-valued role"
