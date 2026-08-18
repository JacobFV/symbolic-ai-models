"""The `005` round trip, asserted over the curriculum rather than over a fixture.

``test_encoding_is_lossless`` existed in this repo, passed, and missed that the
tokenizer was deleting underscores — because the fixture it drew happened to
contain no underscore. That is the fifth-costliest mistake in this repo's
history and the test below is the same shape, so it is written the way
``notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-
property.md`` says to write it:

* it covers **every graph of all 179 lessons**, not a sample of them;
* it asserts on the **alphabet** — every node type, and the label characters
  that a naive s-expression printer would silently eat — rather than trusting
  that the corpus happened to contain them;
* the coverage assertions are separate tests, so a corpus that shrank would fail
  *loudly* instead of making the round-trip test vacuous.

The whole corpus is built once, module-scoped. Two seeds per lesson rather than
one because the generator draws structure per seed and a single draw per lesson
would be a fixture again, just a large one.
"""

from __future__ import annotations

import collections

import pytest

from symbolic_ai_atomspace import (AtomSpace, DERIVED_RULES, E, G, S, V,
                                   atomspace_to_graph, chain, graph_to_atomspace,
                                   match_atom, occurrence, parse_atom,
                                   parse_atoms, print_atom, term_atom, unify,
                                   view_to_atomspace)
from symbolic_ai_core.data import curriculum as C
from symbolic_ai_core.data.term_graph import NODE_TYPES

#: Types the collator writes and the generator never does.
COLLATOR_ONLY = {"pad", "mask", "text"}

#: **Dead types.** Measured, not assumed: over 179 lessons x 8 seeds — 1,432
#: episodes, 100,000-odd nodes — these five never occur once. So the graph type
#: alphabet the whole repo is defined over is seventeen names of which **nine**
#: are live, and ``STRUCTURAL`` (five names) is really ``{list, record}``.
#:
#: Pinned here rather than merely observed, because it cuts both ways. If a
#: generator change starts emitting ``rel``, this test fails and says the round
#: trip has never been exercised on it — which is precisely the guard the
#: tokenizer's underscore fixture did not have.
NEVER_GENERATED = {"nil", "tuple", "app", "rel", "node"}

#: Five seeds per lesson. Generation is ~1 s for the whole grid, so there is no
#: reason to take a sample of a corpus that costs nothing to cover.
SEEDS_PER_LESSON = 5


@pytest.fixture(scope="module")
def corpus():
    """Every implemented lesson, twice. Training seeds only."""
    lessons = C.lesson_ids()
    assert len(lessons) >= 179, f"the curriculum shrank to {len(lessons)} lessons"
    return list(C.generate(lessons, n=SEEDS_PER_LESSON, seed0=0,
                           on_error="skip"))


def test_the_corpus_is_the_whole_curriculum(corpus):
    """A fixture that quietly stopped generating would make every test below
    pass on nothing. Assert the size before asserting anything about it."""
    lessons = {ep.lesson_id for ep in corpus}
    assert len(lessons) >= 179, f"only {len(lessons)} lessons generated"
    assert len(corpus) >= 179 * SEEDS_PER_LESSON - 10


def test_the_round_trip_is_the_identity_on_every_graph_of_all_179_lessons(corpus):
    """``TermGraph -> atomspace -> TermGraph``, on every graph, on every field.

    ``to_dict`` is compared rather than the object, so ``depth`` is included —
    and ``depth`` is *recomputed* by the decoder rather than stored, which makes
    this strictly stronger than comparing what was written down.
    """
    bad: list[str] = []
    for ep in corpus:
        got = atomspace_to_graph(graph_to_atomspace(ep.graph))
        if got.to_dict() != ep.graph.to_dict():
            bad.append(f"{ep.lesson_id} seed={ep.seed}")
    assert not bad, (f"{len(bad)} of {len(corpus)} graphs did not survive the "
                     f"round trip; first few: {bad[:5]}")


def test_the_round_trip_corpus_covers_the_whole_node_type_alphabet(corpus):
    """The guard the tokenizer's fixture did not have.

    A round trip asserted over graphs that happen to contain four of the twelve
    generatable node types is a round trip over four node types. Name the
    alphabet and assert the corpus exhausts it.
    """
    seen = {t for ep in corpus for t in ep.graph.types}
    expected = set(NODE_TYPES) - COLLATOR_ONLY - NEVER_GENERATED
    assert seen >= expected, f"never exercised: {sorted(expected - seen)}"
    assert not (seen - set(NODE_TYPES)), f"unknown types: {sorted(seen - set(NODE_TYPES))}"
    # The other half of the guard: if a type on the dead list starts being
    # generated, the round trip above has never seen it and this must fail.
    assert not (seen & NEVER_GENERATED), (
        f"{sorted(seen & NEVER_GENERATED)} used to be dead on this curriculum "
        f"and now is not -- the round trip has never been exercised on it")


def test_the_round_trip_corpus_covers_the_labels_that_break_a_naive_printer(corpus):
    """The characters an s-expression printer eats if nobody quotes them.

    ``context_free_language`` renders bracket strings, so ``(`` and ``)`` are
    genuine one-character labels here; prose words carry underscores; and the
    empty label is on every structural node. Each of these would round-trip
    wrongly under a printer that assumed identifiers, and each would do it
    silently. This test is what makes the round trip above mean something.
    """
    labels = {l for ep in corpus for l in ep.graph.labels}
    checks = {
        "an empty label": lambda s: s == "",
        "an underscore": lambda s: "_" in s,
        "an open paren": lambda s: "(" in s,
        "a close paren": lambda s: ")" in s,
        "whitespace": lambda s: any(c in s for c in " \t\n"),
        "a digit-only label": lambda s: s.isdigit(),
    }
    missing = [name for name, ok in checks.items()
               if not any(ok(l) for l in labels)]
    assert not missing, (
        f"the corpus never contained {missing} -- the round trip is not "
        f"exercising the escaping it claims to")


def test_the_metta_source_reparses_into_the_same_space(corpus):
    """Print the space, read it back, and require the same set of atoms.

    This is the property the out-of-band ``hyperon`` conformance oracle depends
    on: it is handed source, not objects. A printer that lost a character would
    make every conformance result meaningless in the flattering direction.
    """
    bad: list[str] = []
    for ep in corpus:
        space = graph_to_atomspace(ep.graph)
        if AtomSpace.from_metta(space.to_metta()) != space:
            bad.append(f"{ep.lesson_id} seed={ep.seed}")
    assert not bad, f"{len(bad)} spaces did not survive print/parse: {bad[:5]}"


def test_the_round_trip_survives_the_source_as_well_as_the_objects(corpus):
    """TermGraph -> space -> MeTTa text -> space -> TermGraph, on the whole corpus."""
    bad: list[str] = []
    for ep in corpus:
        text = graph_to_atomspace(ep.graph).to_metta()
        if atomspace_to_graph(AtomSpace.from_metta(text)).to_dict() != \
                ep.graph.to_dict():
            bad.append(f"{ep.lesson_id} seed={ep.seed}")
    assert not bad, f"{len(bad)} graphs did not survive the source trip: {bad[:5]}"


def test_content_addressing_would_collapse_occurrences(corpus):
    """The measurement behind the encoder's design, not an assertion of taste.

    An atomspace stores each atom once. Encode a term as its own nested
    expression — the map the pre-registration proposed — and two occurrences
    with equal content become one atom, so the arity of their parent is no
    longer recoverable. This test says the collapse is real on *this* corpus and
    prints how much of it there is, so the encoder's extra machinery is
    justified by a number rather than by an argument.
    """
    collapsed = graphs = 0
    for ep in corpus:
        contents = [term_atom(ep.graph, i) for i in range(len(ep.graph))]
        distinct = len(set(contents))
        if distinct < len(contents):
            graphs += 1
            collapsed += len(contents) - distinct
    assert graphs > 0, (
        "no graph in the whole curriculum has two content-equal occurrences, "
        "which would make the naive encoding lossless and this encoder's "
        "occurrence naming unnecessary -- re-read the module docstring")
    print(f"\ncontent addressing would merge {collapsed} occurrences "
          f"across {graphs}/{len(corpus)} graphs")


# ---------------------------------------------------------------------------
# the language, unit-sized
# ---------------------------------------------------------------------------
def test_unification_binds_both_ways_and_composes():
    assert unify(parse_atom("(f $x b)"), parse_atom("(f a $y)")) == {
        "x": S("a"), "y": S("b")}
    assert unify(parse_atom("(f $x $x)"), parse_atom("(f a b)")) is None
    assert unify(parse_atom("(f a)"), parse_atom("(f a b)")) is None


def test_the_occurs_check_is_on_because_a_cycle_would_hang_the_sweep():
    """``$x`` against ``(f $x)`` must fail, not build a cyclic term.

    Without the check the binding is cyclic and the next walk over it recurses
    forever. A pattern matcher inside a 179-lesson sweep must not be able to
    hang.
    """
    assert unify(V("x"), parse_atom("(f $x)")) is None


def test_a_variable_stored_in_the_space_is_data_and_not_a_wildcard():
    """One-way matching. If a stored variable were a wildcard, a single stray
    atom in a space would make every query true — and every query being true is
    a model that looks like it reasons and is answering from nothing."""
    space = AtomSpace([parse_atom("(f $anything)")])
    assert not list(space.match(parse_atom("(f a)")))
    assert match_atom(parse_atom("(f $q)"), parse_atom("(f a)")) == {"q": S("a")}


def test_the_conjunctive_query_joins_on_the_shared_variable():
    space = AtomSpace(parse_atoms("(child p 0 a) (child p 1 b) (: a pred) (: b num)"))
    found = list(space.query(parse_atom("(child p $k $c)"), parse_atom("(: $c pred)")))
    assert len(found) == 1 and found[0]["c"] == S("a") and found[0]["k"] == G(0)


def test_the_typed_slot_selected_sibling_is_one_query_not_one_branch(corpus):
    """The concrete thing this IR can express that ``CLAWS`` cannot.

    ``CLAWS`` has ``sibling0`` and ``prev_sibling`` and no way to name *which*
    sibling — which is why ``omegaclaw_reach-001`` had to add a branch to reach
    ``ilp``'s best discovered clause. Here selecting the sibling by slot *and*
    by type is a single conjunctive query over the derived relation, and this
    test asserts it actually returns something on the real curriculum rather
    than merely parsing.
    """
    from symbolic_ai_core.graphview import GraphView
    import numpy as np

    hits = 0
    for ep in corpus[:40]:
        g = ep.graph
        view = GraphView(labels=[None] * len(g), types=list(g.types),
                         parent=list(g.parent), slot=list(g.slot),
                         depth=list(g.depth), rel=np.zeros((0, 0)), hidden=[],
                         tok=None)
        space = view_to_atomspace(view)
        chain(space, DERIVED_RULES, max_rounds=1)
        # "my sibling in slot 1, and it is a `num`" -- a slot-selected,
        # type-selected sibling, in one query.
        hits += sum(1 for _ in space.query(
            parse_atom("(sibling $me $k $other 1)"),
            parse_atom("(: $other num)")))
    assert hits > 0, "the derived typed-sibling query never fired on 40 episodes"


def test_a_rule_round_trips_through_its_own_source():
    from symbolic_ai_atomspace import Rule
    for r in DERIVED_RULES:
        assert Rule.from_atom(parse_atom(print_atom(r.to_atom()))) == r


def test_chaining_stops_when_nothing_new_is_derived():
    space = AtomSpace(parse_atoms("(child p 0 a) (child p 1 b)"))
    added = chain(space, DERIVED_RULES, max_rounds=8)
    again = chain(space, DERIVED_RULES, max_rounds=8)
    assert added > 0 and again == 0


def test_the_masked_view_never_carries_the_answer(corpus):
    """A hidden node has no ``label`` atom anywhere in its space.

    :class:`GraphView` closes this structurally and so must the encoding of one;
    an IR that helpfully wrote the hidden label into a derived atom would make
    every number downstream meaningless.
    """
    from symbolic_ai_core.graphview import GraphView
    import numpy as np

    for ep in corpus[:60]:
        g = ep.graph
        hidden = list(range(0, len(g), 3))
        view = GraphView(
            labels=[None if i in hidden else i for i in range(len(g))],
            types=[None if i in hidden else t for i, t in enumerate(g.types)],
            parent=list(g.parent), slot=list(g.slot), depth=list(g.depth),
            rel=np.zeros((0, 0)), hidden=hidden, tok=None)
        space = view_to_atomspace(view)
        chain(space, DERIVED_RULES, max_rounds=1)
        for i in hidden:
            assert not list(space.query(E(S("label"), occurrence(i), V("s"))))
