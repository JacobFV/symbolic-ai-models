"""Two claims in one sentence, which is the granularity real prose has.

Measured false on 168 Wikipedia articles: the one-claim-per-sentence assumption
is baked into the audit's spans, `unconsumed`, `evidence_conflict` and
`filter_stale`. The ``packed`` surface option is the constructive response.

The theorem the tests exist to pin: a signature is a function of the **sentence**,
so a sentence realising two claim kinds is ambiguous *by definition* --
`ambiguity_mass` is bounded below by the share of multi-claim sentences, and no
signature reader can be packing-robust. Flood's reader survives packing only
because at that point it is not signature-based: it merges crossings into links.
"""

from __future__ import annotations

import sys
from pathlib import Path

from symbolic_ai_generators.audit import audit_surface
from symbolic_ai_generators.scheduling import generate as sched_generate
from symbolic_ai_generators.scheduling import surface as SS
from symbolic_ai_generators.scheduling.read_surface import read_signature as sr
from symbolic_ai_generators.solvency import decide
from symbolic_ai_generators.solvency import generate as solv_generate
from symbolic_ai_generators.solvency import surface as VS
from symbolic_ai_generators.solvency.read_surface import (decide_reading,
                                                          read_signature)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

SEEDS = 40


def test_a_packed_sentence_carries_two_spans_over_the_same_text():
    obs = VS.render_observation(solv_generate(0), variants=4, packed=True)
    ranges = {}
    for span in obs.spans:
        if span.claim is None:
            continue
        ranges.setdefault((span.start, span.end), set()).add(span.kind)
    shared = [k for k, v in ranges.items() if len(v) > 1]
    assert shared, "no range realises two claim kinds"


def test_the_audit_sees_packing_offline():
    """A signature is a function of the sentence, so two kinds in one sentence
    is ambiguity by definition -- and the audit reports it before any reader."""
    for gen, surf, reg, ent in ((solv_generate, VS, None,
                                 r"\bsub_\d+\b|\bgroup\b"),
                                (sched_generate, SS, None, None)):
        cases = [gen(s) for s in range(SEEDS)]
        worlds = [c.world for c in cases]
        plain = audit_surface([surf.render_observation(c, variants=4)
                               for c in cases], reg, ent, worlds)
        packed = audit_surface([surf.render_observation(c, variants=4,
                                                        packed=True)
                                for c in cases], reg, ent, worlds)
        assert plain.ambiguity_mass == 0.0
        assert packed.ambiguity_mass > 0.2, packed.ambiguity_mass


def test_packing_collapses_the_solvency_reader_to_its_floor():
    truth = [decide(solv_generate(s), as_of=solv_generate(s).decision_date)[0]
             for s in range(SEEDS)]
    got = []
    for s in range(SEEDS):
        case = solv_generate(s)
        text = VS.render_observation(case, variants=4, packed=True).text
        got.append(decide_reading(read_signature(text)))
    assert len(set(got)) == 1, "expected a degenerate answer, not a mixed one"
    acc = sum(g == t for g, t in zip(got, truth)) / len(truth)
    floor = max(sum(truth), len(truth) - sum(truth)) / len(truth)
    assert abs(acc - floor) < 0.02, (acc, floor)


def _caps(world):
    return {(c.roles["machine"].id, c.roles["capability"])
            for c in world.claims if c.predicate == "has_capability"}


def test_packing_silently_drops_the_packed_capability():
    """The exact mechanism: `read_signature` branches on shape with an ``elif``
    chain, so a packed sentence matches the capacity branch and the capability
    branch never runs. Seed 0 loses (machine_0, cut) and (machine_1, cut) --
    half the floor's capabilities, in the UNSOUND direction."""
    lost = 0
    for s in range(SEEDS):
        case = sched_generate(s)
        plain = _caps(sr(SS.render_observation(case, variants=4).text))
        packed = _caps(sr(SS.render_observation(case, variants=4,
                                                packed=True).text))
        assert packed < plain or packed == plain
        lost += len(plain - packed)
    assert lost >= SEEDS, f"only {lost} capabilities lost over {SEEDS} cases"


def test_flood_is_the_control_because_its_reader_merges():
    """One sentence carrying a road AND its limit, read whole -- because
    `read_content_roles` folds crossings into links rather than branching."""
    from symbolic_ai_generators.flood.read_surface import read_content_roles
    text = ("Depot operations are run out of region_0, which is where every "
            "vehicle starts the day. A request has come in from region_3. It "
            "is for 1400 kg of supplies.\n\n"
            "region_0 and region_3 are joined by a surfaced road rated for "
            "3000 kg.\n\n"
            "truck_0 weighs 1200 kg empty. The vehicle listed as truck_0 can "
            "take a further 2500 kg.")
    kinds = {c.predicate for c in read_content_roles(text).claims}
    assert {"link", "load_limit"} <= kinds, kinds
