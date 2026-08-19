"""The reader seam: same claims, more reported, and a flow op beside the kernels.

`kernel.run@1` made kernel selection configuration rather than control flow.
`reader.run@1` is the same seam on the other side of the world. The migration
requirement is that behaviour does not change -- flood's reader decides exactly
what it decided before -- while everything it could not settle becomes a port
rather than a private guess.
"""

from __future__ import annotations

from symbolic_ai_core.flow.registry import get_op
from symbolic_ai_core.reader import ReadResult, get_reader, list_readers
from symbolic_ai_core.world import WorldSnapshot
from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood import reader as _reader  # noqa: F401
from symbolic_ai_generators.flood.read_surface import read_content_roles
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import interleave, unsaturate

SEEDS = 40


def _texts(hard: bool):
    for s in range(SEEDS):
        obs = render_observation(generate(s), variants=4,
                                 hard_distractors=hard)
        yield interleave(unsaturate(obs, drop_headings=True,
                                    shuffle=False)).text


def test_the_reader_is_registered_and_the_op_exists():
    assert "flood.content@1" in list_readers()
    assert get_op("reader.run@1").family == "parse"


def test_migration_changes_no_decision():
    """The acceptance criterion. The reader now returns a candidate POOL, so the
    comparison is against what it collapses to -- and that must be exactly what
    the direct call decided, on every document, on both surfaces."""
    reader = get_reader("flood.content@1")
    for hard in (False, True):
        for text in _texts(hard):
            direct = read_content_roles(text)
            got = reader.run(text).delta()
            assert [c.to_dict() for c in got.claims] == \
                   [c.to_dict() for c in direct.claims]


def test_what_was_not_settled_is_reported_rather_than_guessed():
    """The reason for the seam. On the honest surface the role assignment is
    unforced on most cases, and the old contract returned a guessed world with
    no way to see it."""
    reader = get_reader("flood.content@1")
    open_cases = [r for r in (reader.run(t) for t in _texts(True))
                  if not r.settled()]
    assert open_cases, "expected unsettled readings on the honest surface"
    with_alts = [r for r in open_cases if r.factors]
    assert with_alts
    for r in with_alts:
        f = r.factors[0]
        assert f.kind == "xor" and f.exclusive   # exactly one region is the depot
        assert len(f.claims) > 1
        # a belief over the alternatives, not an enumeration of worlds
        assert all(0.0 < r.confidence_of(i) < 1.0 for i in f.claims)


def test_the_flow_op_carries_the_unresolved_port():
    from symbolic_ai_core.artifact.value import Artifact
    op = get_op("reader.run@1")
    text = next(_texts(True))
    out = op.fn({"text": Artifact(type="json", value=text)},
                {"reader": "flood.content@1"}, None)
    assert set(out) == {"delta", "claims", "unresolved", "report"}
    assert out["claims"].value["producer"] == "flood.content@1"
    assert out["report"].value["cost_s"] > 0
    world = WorldSnapshot(entities={}, claims=())
    assert len(out["delta"].value["claims"]) == len(out["claims"].value["claims"])
    assert world is not None


def test_a_read_result_is_neither_a_world_nor_one_delta():
    """A snapshot hides every guess; a single delta still forces one reading.
    The representation is a pool, a belief and constraints -- `A: 0.62,
    B: 0.38, A XOR B` without materialising two worlds."""
    from symbolic_ai_core.reader import Factor
    from symbolic_ai_core.world import Claim, EntityRef
    assert not hasattr(ReadResult(), "entities")
    r = ReadResult(claims=(Claim("depot", {"where": EntityRef("region_0")}),
                           Claim("depot", {"where": EntityRef("region_3")})),
                   belief={0: 0.62, 1: 0.38}, factors=(Factor("xor", (0, 1)),))
    assert not r.settled()
    assert len(r.delta().claims) == 1        # collapsing is an explicit decision
