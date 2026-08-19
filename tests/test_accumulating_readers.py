"""Accumulate, do not branch -- built deliberately, not inherited by accident.

The packing result produced one actionable rule, derived from flood being the
only reader that survived a packed sentence. A rule from one accidental case is a
hypothesis. These are the two readers that collapsed, rebuilt to obey it.

They **strictly dominate**: identical on every honest surface, 1.000 instead of
their floor on the packed one.
"""

from __future__ import annotations

import sys
from pathlib import Path

from symbolic_ai_generators.scheduling import generate as sched_generate
from symbolic_ai_generators.scheduling import surface as SS
from symbolic_ai_generators.scheduling.read_surface import (
    read_signature as s_branch, read_signature_accumulating as s_acc)
from symbolic_ai_generators.solvency import decide
from symbolic_ai_generators.solvency import generate as solv_generate
from symbolic_ai_generators.solvency import surface as VS
from symbolic_ai_generators.solvency.read_surface import (
    decide_reading, read_signature as v_branch,
    read_signature_accumulating as v_acc)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

SEEDS = 40


def _solvency(reader, packed):
    ok = []
    for s in range(SEEDS):
        case = solv_generate(s)
        want = decide(case, as_of=case.decision_date)[0]
        text = VS.render_observation(case, variants=4, packed=packed).text
        ok.append(decide_reading(reader(text)) == want)
    return sum(ok) / len(ok)


def _sched_caps(reader, packed):
    lost = 0
    for s in range(SEEDS):
        case = sched_generate(s)
        want = {(c.roles["machine"].id, c.roles["capability"])
                for c in case.world.claims if c.predicate == "has_capability"}
        got = {(c.roles["machine"].id, c.roles["capability"])
               for c in reader(SS.render_observation(
                   case, variants=4, packed=packed).text).claims
               if c.predicate == "has_capability"}
        lost += len(want - got)
    return lost


def test_packing_breaks_the_branching_readers():
    assert _solvency(v_branch, packed=True) < 0.7
    assert _sched_caps(s_branch, packed=True) >= SEEDS


def test_accumulating_readers_are_immune_to_it():
    assert _solvency(v_acc, packed=True) == 1.0
    assert _sched_caps(s_acc, packed=True) == 0


def test_they_cost_nothing_unpacked():
    """A more permissive reader could admit claims the branching one refused --
    the precision failure this repo keeps finding. Measured: it does not."""
    assert _solvency(v_acc, packed=False) == _solvency(v_branch, packed=False)
    assert _sched_caps(s_acc, packed=False) == _sched_caps(s_branch,
                                                           packed=False) == 0


def test_the_filing_binds_to_the_entity_nearest_the_money():
    """In "group owns sub_0, which reported 105.87 USD, filed 29 May 2026" the
    filer is sub_0 -- the entity beside the number, not the subject. Positional
    and content-free, the same signal flood uses for its demand."""
    r = v_acc("group owns sub_0, which reported 105.87 USD, filed 2026-05-29.")
    assert r.filings == [("sub_0", 105.87, "2026-05-29")], r.filings
    assert {"group", "sub_0"} <= r.members
