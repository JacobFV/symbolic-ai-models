"""The reader that replaces paragraph INDEX with paragraph CO-OCCURRENCE.

`read_signature` branches on ``pi == 0..3`` and therefore knows the generator's
five-paragraph template by position. `read_signature_roles` keeps only the fact
that survives a reorder -- which sentences share a paragraph -- and must match it
on the published surface while surviving a shuffle that destroys it.
"""

from __future__ import annotations

import pytest

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.flow import solve
from symbolic_ai_generators.flood.read_surface import (VALUE_REGISTRY,
                                                       read_signature,
                                                       read_signature_roles)
from symbolic_ai_generators.flood.surface import render_observation
from symbolic_ai_generators.flood.unsaturate import unsaturate


def _texts(seed: int):
    obs = render_observation(generate(seed))
    return obs.text, unsaturate(obs).text


def test_matches_the_index_reader_on_the_published_surface() -> None:
    """Replacing the mechanism must not cost anything where both apply."""
    for seed in range(20):
        ordered, _ = _texts(seed)
        assert solve(read_signature_roles(ordered))[0] == \
            solve(read_signature(ordered))[0], seed


def test_reaches_the_oracle_on_the_published_surface() -> None:
    for seed in range(20):
        case = generate(seed)
        ordered, _ = _texts(seed)
        assert solve(read_signature_roles(ordered))[0] == solve(case.world)[0]


def test_survives_the_shuffle_that_breaks_the_index_reader() -> None:
    """The whole point. Both halves are asserted, so neither can drift.

    Scored on cases with a **non-empty** answer only. The index reader returns
    the empty set once its ``pi ==`` branches stop matching, which is
    accidentally right wherever the truth is also empty -- pooling the two
    populations would credit it for a collapse.
    """
    broke = held = n = 0
    for seed in range(20):
        case = generate(seed)
        want = solve(case.world)[0]
        if not want:
            continue
        n += 1
        _, scrambled = _texts(seed)
        broke += solve(read_signature(scrambled))[0] != want
        held += solve(read_signature_roles(scrambled))[0] == want
    assert n >= 8, n
    assert held == n, (held, n)
    assert broke == n, (broke, n)


def _links(world) -> set:
    return {tuple(sorted(c.entities())) for c in world.claims
            if c.predicate == "link"}


def test_the_network_paragraph_is_found_by_content() -> None:
    """"Districts X and Y lie outside the affected area" is a region pair with
    no number, exactly like a road. Only the paragraph richest in such pairs is
    read as the network, which is what keeps that one out.

    Parity with the index reader is the bar: the same links, admitted from a
    shuffled document as from the template it was written for. One extra pair
    does survive in both -- the disused track, which sits *inside* the network
    paragraph -- so this asserts sameness rather than purity.
    """
    for seed in range(10):
        case = generate(seed)
        ordered, scrambled = _texts(seed)
        got = _links(read_signature_roles(scrambled))
        assert _links(case.world) <= got, seed
        assert got == _links(read_signature(ordered)), seed


@pytest.mark.parametrize("kind", ["mass", "capacity", "demand"])
def test_the_value_registry_is_load_bearing(kind: str) -> None:
    """The registry is declared external knowledge, so it must actually be used.

    Corrupting one vocabulary has to damage the reading, or the arm is getting
    its answer from somewhere undeclared.
    """
    saved = VALUE_REGISTRY[kind]
    VALUE_REGISTRY[kind] = frozenset()
    try:
        damaged = sum(solve(read_signature_roles(_texts(s)[1]))[0]
                      != solve(generate(s).world)[0] for s in range(10))
    finally:
        VALUE_REGISTRY[kind] = saved
    assert damaged > 0, f"emptying {kind} changed nothing"


def test_no_content_word_is_consulted() -> None:
    """The arm's claim about itself, checked against its source.

    Only **string literals** count: those are what could be matched against the
    document. Identifiers like ``depot`` name the slot being filled, not a word
    being looked for, and an earlier version of this test failed on exactly that
    confusion -- pinning names rather than behaviour.
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(read_signature_roles)))
    fn = tree.body[0]
    # The docstring is prose ABOUT the reader and necessarily names the claim
    # kinds; excluding it by node is exact, where matching its text is not --
    # ``ast.get_docstring`` returns a cleaned copy that no longer equals the
    # literal it came from, which is how the first version of this test failed.
    doc = fn.body[0].value if (isinstance(fn.body[0], ast.Expr) and
                               isinstance(fn.body[0].value, ast.Constant)) else None
    literals = {n.value.lower() for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n is not doc}
    for word in ("rated", "flood", "water", "carry", "weigh", "supplies",
                 "road", "bridge", "district", "lightest", "rose"):
        assert not any(word in lit for lit in literals), (word, literals)
