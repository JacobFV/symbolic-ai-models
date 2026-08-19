"""Scheduling's distractors were defanged the same way flood's were.

The withdrawn machine and the cancelled job carry no capability and no quantity,
and "no machine is set up for anodising" names a capability **outside the
vocabulary** -- so the capability list rejects all three for free. Point one at a
real entity with an in-vocabulary word and the reader must admit it.

The two sides are not symmetric and the asymmetry is the finding: each job needs
exactly one capability, so a spurious ``needs_capability`` violates arity and is
catchable; a machine holds any number, so a spurious ``has_capability`` is not.
**The uncatchable one is the unsound one** -- 0.790 accuracy with all 42 errors
false-FEASIBLE, against 0.965 and arity firing on every case.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from symbolic_ai_generators.scheduling import generate
from symbolic_ai_generators.scheduling.read_surface import read_signature
from symbolic_ai_generators.scheduling.surface import render_observation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from hard_regime_milestone import solve_world  # noqa: E402

SEEDS = 60


def _arity(world) -> int:
    per: Counter = Counter()
    for c in world.claims:
        if c.predicate == "needs_capability":
            per[c.roles["job"].id] += 1
    return sum(1 for v in per.values() if v > 1)


def _arm(hard):
    for s in range(SEEDS):
        case = generate(s)
        text = render_observation(case, variants=4, hard_distractors=hard).text
        world = read_signature(text)
        yield case.feasible, solve_world(world)[0], _arity(world)


def test_the_default_distractors_are_inert():
    """They must stay inert, or every published scheduling number moves."""
    wrong = [1 for t, g, _ in _arm(False) if t != g]
    assert not wrong, f"{len(wrong)} errors on the default surface"


def test_the_machine_side_is_admitted_and_unsound():
    rows = list(_arm("machine"))
    wrong = [(t, g) for t, g, _ in rows if t != g]
    assert len(wrong) > SEEDS * 0.05, f"only {len(wrong)} errors"
    assert all(g and not t for t, g in wrong), (
        "every error should be false-FEASIBLE: an admitted capability the floor "
        f"does not have. Got {wrong[:5]}")


def test_arity_sees_the_job_side_and_not_the_machine_side():
    """The check built for flood ports unchanged -- onto the harmless channel."""
    assert all(a for _, _, a in _arm("job")), "arity missed the job distractor"
    assert not any(a for _, _, a in _arm("machine")), (
        "arity fired on the machine side, where a machine may hold any number "
        "of capabilities -- if this now fires the arity of has_capability has "
        "changed and the finding's asymmetry is stale")
