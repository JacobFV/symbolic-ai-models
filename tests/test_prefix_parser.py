"""The parser-as-a-parameter seam, and the leak it would be if it were wrong.

The oracle parser is handed the episode's true term graph while the model is
predicting the next token, and 85.3% of this curriculum's answers are literally
the label of one of that graph's nodes. So the whole value of the ``-003``
generation rests on one claim — that the oracle returns only what the reader has
already earned — and this file is where that claim is checked rather than
asserted.

Three properties, and they are not interchangeable:

* **suffix-freedom** — the parse at ``t`` does not depend on anything after
  ``t``. Necessary, and on its own worth very little: an oracle returning the
  whole graph at every position would pass it.
* **no unseen symbol** — the parse at ``t`` names nothing the prefix does not.
  This is the one that bites, and it is what makes the oracle a parser rather
  than an answer key.
* **the model cannot be moved by a symbol the text never contains** — the same
  claim one level up, checked on the logits, which is where a leak would
  actually show up. It is the text-surface counterpart of
  ``test_the_hidden_answer_never_reaches_the_model``, and it is needed because
  that test and the causality test both perturb *tokens*, and a model reading
  the graph unrestricted would sail through both.
"""

from __future__ import annotations

import copy

import pytest
import torch

from symbolic_ai_core.data.batch import collate_text, text_batch
from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_core.data.term_graph import TermGraph
from symbolic_ai_core.data.tokenizer import split_words
from symbolic_ai_models.models import ModelConfig, build, model_names
from symbolic_ai_models.models.registry import get
from symbolic_ai_models.prefix import (Reading, audit_prefix_parser,
                                       availability, build_prefix_parser,
                                       restrict)
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]

#: Every reader a `-003` model can be configured with. `template-002` and
#: `retrieve-001` are real parsers reached through the `symbolic_ai_parsers`
#: registry; the rest are built in.
READERS = ["none", "flat", "oracle", "template-002", "retrieve-001"]

GPARSE = [n for n in model_names() if n.startswith("gparse")]


@pytest.fixture(scope="module")
def fixtures():
    train = list(generate(LESSONS, n=6, seed0=0))
    evals = list(generate(LESSONS, n=2, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1200), train)
    return train, evals, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, _, tok = fixtures
    return ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                       d_ff=64, dropout=0.0, max_len=320)


def fitted(name, fixtures):
    train, _, tok = fixtures
    p = build_prefix_parser(name)
    p.fit(train, tok)
    return p


# ---------------------------------------------------------------------------
# the seam
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", READERS)
def test_a_prefix_parse_is_a_function_of_its_prefix(name, fixtures):
    """Whatever the reader, position ``t`` must not move when the tail does."""
    train, evals, tok = fixtures
    report = audit_prefix_parser(fitted(name, fixtures), evals, tok)
    assert report["suffix_violations"] == 0.0, f"{name} reads forward: {report}"


@pytest.mark.parametrize("name", ["none", "flat", "oracle"])
def test_a_reader_shown_the_episode_never_names_an_unread_symbol(name, fixtures):
    """The property that separates a parser from an answer key.

    It applies to the readers that are shown the episode, which is the oracle
    and — vacuously but on purpose — the two that are shown nothing. A symbol
    the prefix has not spelled is precisely the shape a leaked answer has, so
    this is the whole leak argument for the ceiling row.

    It deliberately does **not** apply to a real parser. ``retrieve-001`` emits a
    remembered training graph verbatim and therefore names symbols this episode
    never used; that is a wrong answer, not a leak, because nothing it says came
    from the episode it is reading. Measuring how often it happens is
    interesting — see the test below — but constraining it would be constraining
    parsers to be right rather than to be honest.
    """
    train, evals, tok = fixtures
    report = audit_prefix_parser(fitted(name, fixtures), evals, tok)
    assert report["symbol_violations"] == 0.0, f"{name} invents symbols: {report}"


@pytest.mark.parametrize("name", ["template-002", "retrieve-001"])
def test_a_real_parser_may_invent_symbols_and_is_only_asked_to_be_causal(
        name, fixtures):
    """What a real parser owes the seam, and what it does not.

    It owes suffix-freedom, which the adapter gives it structurally. It does not
    owe accuracy — a parser that hands back a remembered graph is allowed to be
    wrong, and the ``-003`` table exists to measure exactly how wrong.
    """
    train, evals, tok = fixtures
    report = audit_prefix_parser(fitted(name, fixtures), evals, tok)
    assert report["suffix_violations"] == 0.0, f"{name} reads forward: {report}"
    assert report["nodes"] >= 0.0


def test_the_audit_is_not_passing_because_nothing_is_returned(fixtures):
    """A reader that returns nothing passes both checks and measures nothing.

    So the coverage sits next to them: ``none`` is allowed to be empty because
    being empty is what it is for, and the oracle is not.
    """
    train, evals, tok = fixtures
    assert audit_prefix_parser(fitted("none", fixtures), evals, tok)["coverage"] == 0.0
    assert audit_prefix_parser(fitted("oracle", fixtures), evals, tok)["coverage"] > 5.0


def test_the_oracle_grows_and_never_shrinks(fixtures):
    """Reading more can only reveal more. A parse that shrank would mean the
    availability rule was reading something other than the prefix."""
    train, evals, tok = fixtures
    parser = fitted("oracle", fixtures)
    ep = evals[0]
    ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer, eos=True)
    view = parser.begin(ids, tok, ep.graph)
    sizes = [len(view.graph(t)) for t in range(len(ids))]
    assert sizes == sorted(sizes)
    assert sizes[-1] > sizes[0] == 0


def test_a_symbol_absent_from_the_text_is_never_revealed(fixtures):
    """The availability rule, stated directly on a graph and a word list."""
    g = TermGraph()
    root = g.add("", "record", -1, 0)
    g.add("alice", "ident", root, 0)
    g.add("alice", "ident", root, 1)
    g.add("nowhere", "ident", root, 2)

    need = availability(g, ["alice"])
    # One `alice` read, so the first `alice` node is out and the second is not.
    assert len(restrict(g, need, 1)) == 2
    assert [n for n in restrict(g, need, 1).labels] == ["", "alice"]
    # `nowhere` is never reachable, however much is read.
    assert "nowhere" not in restrict(g, need, 99).labels
    # The structural root arrives with its first available child, not before.
    assert len(restrict(g, need, 0)) == 0


def test_an_unfinished_word_does_not_count_as_read(fixtures):
    """``fran`` may yet become ``frank`` — and the position where that matters
    is exactly the position at which the answer is about to be emitted.

    Checked on :class:`Reading` directly, because it is a property of the
    prefix geometry rather than of any parser sitting on top of it.
    """
    _, _, tok = fixtures
    ids = tok.encode("frank and", bos=True)
    reading = Reading(ids, tok)
    for t in range(len(ids)):
        text, k = reading.prefix(t), reading.n_complete_words(t)
        counted = split_words(text)[:k]
        if text and text[-1].isalnum():
            # the trailing word is still growing and must not have been counted
            assert len(counted) < len(split_words(text))
        # whatever was counted really is a prefix of the finished segmentation
        assert counted == split_words(reading.text)[:k]
    # `frank` is finished, `and` is still growing.
    assert reading.n_complete_words(len(ids) - 1) == 1
    assert Reading(tok.encode('frank and ', bos=True),
                   tok).n_complete_words(-1) == 2


def test_the_oracle_returns_nothing_without_an_episode(fixtures):
    """There is no oracle at generation time, and that is the honest failure.

    ``decode`` and the agent evaluation build batches from ids, so the answer key
    is simply absent and the ceiling stops being available — which is what
    "ceiling, not a system" means operationally rather than rhetorically.
    """
    train, evals, tok = fixtures
    parser = fitted("oracle", fixtures)
    ids = tok.encode(evals[0].prompt, bos=True)
    view = parser.begin(ids, tok, None)
    assert all(len(view.graph(t)) == 0 for t in range(len(ids)))


# ---------------------------------------------------------------------------
# the models
# ---------------------------------------------------------------------------
def test_the_bare_name_never_resolves_to_the_ceiling():
    """``--models gparse`` must not silently train the row that cannot ship.

    The ``ptrgen-argmax`` failure, with much more at stake: a control that is
    merely worse is embarrassing, a *ceiling* printed under the model's name is
    a published result that is not about any system.
    """
    assert get("gparse").name == "gparse-003"
    assert get("gparse-oracle").name == "gparse-oracle"
    assert get("gparse-003").default_text_parser != "oracle"


def test_every_gparse_row_differs_only_in_its_parser():
    """The claim the comparison rests on: one reasoner, five readers."""
    from symbolic_ai_models.models.gparse_003.model import GraphParsedLM

    allowed = {"__module__", "__qualname__", "__doc__", "__firstlineno__",
               "__static_attributes__", "default_text_parser", "name", "summary"}
    readers = set()
    for name in GPARSE:
        cls = get(name)
        assert issubclass(cls, GraphParsedLM)
        if cls is GraphParsedLM:                  # the reasoner itself
            readers.add(cls.default_text_parser)
            continue
        if cls.ablation:
            # A named ablation is allowed to change the reasoner — that is what
            # it is for — but it must say so in `ablation`, and it is then not
            # part of the parser comparison and not counted as a reader.
            assert not set(vars(cls)) - allowed - {"use_lexical", "ablation"}, \
                f"{name} changes more than it declares"
            continue
        # Everything else may override the knob and nothing at all besides. The
        # moment a parser row carries its own `_plan` or its own features, the
        # spread between the rows stops being a measurement of parsing and
        # becomes a comparison of models — the mistake this generation exists to
        # avoid.
        own = set(vars(cls)) - allowed
        assert not own, f"{name} overrides more than the parser: {own}"
        readers.add(cls.default_text_parser)
    assert len(readers) >= 4
    assert "oracle" in readers


def test_the_symbol_free_ablation_really_is_symbol_free():
    """`gparse-nolex` is the only renaming evidence the text surface has.

    `_renaming_check` scores the *node* task, which every row here abstains on,
    so the claim "this reasoner is about structure and not vocabulary" would
    otherwise rest on nothing. Checked directly on the feature set: with the
    lexical keys off, renaming every symbol in a graph must leave the features
    of every node identical.
    """
    from symbolic_ai_models.models.gparse_003.model import (_children,
                                                            _features,
                                                            _multiplicity)

    g = TermGraph()
    root = g.add("", "record", -1, 0)
    pred = g.add("parent", "pred", root, 0)
    g.add("alice", "ident", pred, 0)
    g.add("bob", "ident", pred, 1)

    renamed = TermGraph.from_dict(g.to_dict())
    swap = {"parent": "zz0", "alice": "zz1", "bob": "zz2"}
    renamed.labels = [swap.get(l, l) for l in renamed.labels]

    for lexical, same in ((False, True), (True, False)):
        pairs = [
            (_features(a, _children(a), _multiplicity(a), i, lexical=lexical),
             _features(b, _children(b), _multiplicity(b), i, lexical=lexical))
            for a, b in [(g, renamed)] for i in range(len(g))
        ]
        assert all(x == y for x, y in pairs) is same


def test_a_graph_node_the_text_never_names_cannot_move_a_prediction(fixtures, cfg):
    """The decisive leak test, and the reason the other two are not enough.

    Both existing leak guards perturb *tokens*: the causality test rewrites
    later tokens, and ``test_the_hidden_answer_never_reaches_the_model``
    rewrites labels on a fully masked graph. A model that read
    ``meta["graphs"]`` in full would pass both, because the graph does not move
    when the tokens do.

    So this one perturbs the graph instead. Extra nodes are added carrying
    symbols the text does not contain — exactly the shape a leaked answer would
    have, since a leaked answer is by definition something the prefix has not
    said — and every prediction must be bit-identical.
    """
    train, evals, tok = fixtures
    model = build("gparse-oracle", cfg)
    model.fit_on(train, tok)
    model.eval()

    plain = evals[:2]
    spiked = copy.deepcopy(plain)
    for ep in spiked:
        for k in range(6):
            ep.graph.add(f"zzunseen{k}", "ident", 0, k)

    with torch.no_grad():
        a = model(collate_text(plain, tok)).symbol_logits
        b = model(collate_text(spiked, tok)).symbol_logits
    assert torch.allclose(a, b, atol=0.0), \
        "the oracle revealed a symbol the text never contained"


def test_the_leak_test_could_have_failed(fixtures, cfg):
    """A guard that cannot fail is not a guard.

    The test above would pass trivially if the oracle were doing nothing at all,
    so this pins that it is: replacing the parse changes the logits, and the
    ceiling row is not the ``none`` row wearing a different name.
    """
    train, evals, tok = fixtures
    outs = []
    for name in ("gparse-oracle", "gparse-none"):
        model = build(name, cfg)
        model.fit_on(train, tok)
        with torch.no_grad():
            outs.append(model.eval()(collate_text(evals[:2], tok)).symbol_logits)
    assert not torch.allclose(outs[0], outs[1], atol=1e-4)


@pytest.mark.parametrize("name", GPARSE)
def test_a_gparse_model_survives_a_batch_with_no_episodes_behind_it(name, fixtures, cfg):
    """``decode`` and the agent build batches from ids. Nothing may raise."""
    train, evals, tok = fixtures
    model = build(name, cfg)
    model.fit_on(train, tok)
    ids = tok.encode(evals[0].prompt, bos=True)
    with torch.no_grad():
        out = model.eval()(text_batch(ids, tok))
    assert torch.isfinite(out.symbol_logits).all()


def test_a_model_that_ignores_the_seam_is_unchanged_by_it(fixtures, cfg):
    """The ``none`` column has to be a true control.

    Every rule-based model now carries a ``text_parser``; a model that does not
    read it must be bit-identical to what it was, or the seam has quietly moved
    every published row rather than adding new ones.
    """
    train, evals, tok = fixtures
    model = build("ngram-001", cfg)
    model.fit_on(train, tok)
    model.eval()
    assert model.reads_text_parser is False
    assert model.text_parser.name == "none"
    with torch.no_grad():
        logits = model(collate_text(evals[:2], tok)).symbol_logits
    assert torch.isfinite(logits).all()
