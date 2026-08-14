"""The readout seam, and the two things it must not have broken.

Three questions are asked here and each of them could have gone the other way.

**Is it behaviour-preserving?** Every published number in this repo carrying
``label_acc`` or ``copy_acc`` came out of
:meth:`~symbolic_ai_models.tasks.masked_node.MaskedNode.compute`. The ``symbol``
and ``node`` readouts recompute the same quantities through the new protocol, so
they must agree **exactly**. A readout that computed something nearly the same
would silently redefine all of them, which is the failure this file exists to
prevent.

**Is the site target really free of the answer?** The causality test in
``tests/test_models.py`` perturbs *tokens*, and the graph does not move when
tokens do, so it could never catch a graph-side leak. The guard that works is
:func:`test_a_graph_node_the_text_never_names_cannot_move_a_logit`: adding nodes
labelled with symbols the rendering does not contain must leave every logit
bit-identical.

**Does the target agree with itself?** ``gsite-oracle`` is handed the very
object the target is derived from, so it must score 1.000. That is not a result
and it is deliberately not reported as one — it is the assertion that the target
and the prefix restriction have not come apart, and it caught two real bugs
while this was being written: a scored position defined by character count
rather than by the reader's own rule, and a target keyed on a single word at a
position where one token finishes two.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
import torch

from symbolic_ai_core.data.batch import collate_graph, collate_text
from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_core.floors import Totals
from symbolic_ai_core.readout import CHANNELS, REGISTRY, SITE, readout_names
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.prefix import Reading
from symbolic_ai_models.readouts.site import (ROOT, position_of_word,
                                              site_targets, words_at_position,
                                              words_read)
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]
SITE_MODELS = ["gsite-001", "gsite-flat", "gsite-retrieve", "gsite-oracle"]


@pytest.fixture(scope="module")
def fixtures():
    train = list(generate(LESSONS, n=6))
    ev = list(generate(LESSONS, n=3, seed0=1_000_000))
    tok = build_tokenizer(TrainConfig(vocab_size=1200), train)
    return train, ev, tok


@pytest.fixture(scope="module")
def cfg(fixtures):
    _, _, tok = fixtures
    return ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                       max_len=320, max_nodes=128)


def fitted(name, fixtures, cfg):
    train, _, tok = fixtures
    model = build(name, cfg)
    model.fit_on(train, tok)
    return model.eval()


# ---------------------------------------------------------------------------
# the protocol
# ---------------------------------------------------------------------------
def test_every_registered_readout_names_a_real_channel():
    assert readout_names(), "no readouts registered"
    for name in readout_names():
        cls = REGISTRY.get(name)
        assert cls.channel in CHANNELS, f"{name} reads unknown channel {cls.channel!r}"
        assert cls.prefix, f"{name} reports under no prefix"


def test_source_logits_and_the_node_channel_are_the_same_object(fixtures, cfg):
    """The seam was generalised, not duplicated.

    ``source_logits`` is eight files old and carries a published copy number, so
    it stays a named field — but a model that fills one and a readout that reads
    the other must never be looking at two different tensors.
    """
    _, ev, tok = fixtures
    model = fitted("corefer", fixtures, cfg)
    batch = collate_graph(ev[:2], tok, rng=np.random.default_rng(0))
    out = model(batch)
    assert out.source_logits is not None
    assert out.channels["node"] is out.source_logits
    assert out.channels["symbol"] is out.symbol_logits


# ---------------------------------------------------------------------------
# behaviour preservation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["corefer", "ngram", "ilp"])
def test_the_symbol_readout_reproduces_label_acc_exactly(name, fixtures, cfg):
    """Not "close to". The same count, from the same logits, to the last unit."""
    _, ev, tok = fixtures
    model = fitted(name, fixtures, cfg)
    task = make_task("node", max_nodes=128)
    task.rng = np.random.default_rng(12345)
    totals = Totals()
    for i in range(0, len(ev), 4):
        batch = task.collate(ev[i:i + 4], tok)
        totals.add(task.compute(model(batch), batch).counts)
    assert totals["rsymbol_n"] == totals["label_n"]
    assert totals["rsymbol_correct"] == totals["label_correct"]
    assert totals["rsymbol_nll"] == pytest.approx(totals["label_nll"], rel=1e-9)


def test_the_node_readout_reproduces_copy_acc_exactly(fixtures, cfg):
    _, ev, tok = fixtures
    model = fitted("corefer", fixtures, cfg)
    task = make_task("node", max_nodes=128)
    task.rng = np.random.default_rng(12345)
    totals = Totals()
    for i in range(0, len(ev), 4):
        batch = task.collate(ev[i:i + 4], tok)
        totals.add(task.compute(model(batch), batch).counts)
    assert totals["rnode_n"] == totals["copy_n"]
    assert totals["rnode_correct"] == totals["copy_correct"]


def test_a_model_without_a_pointer_is_unscored_rather_than_scored_zero(fixtures, cfg):
    """"Cannot point" and "points badly" are different facts."""
    _, ev, tok = fixtures
    model = fitted("ngram", fixtures, cfg)
    task = make_task("node", max_nodes=128)
    batch = task.collate(ev[:2], tok)
    counts = task.compute(model(batch), batch).counts
    assert model(batch).channels.get("node") is None
    assert "rnode_n" not in counts


# ---------------------------------------------------------------------------
# the site target
# ---------------------------------------------------------------------------
def test_the_site_target_never_points_forward(fixtures):
    """A site is always a position the reader has already passed.

    The property that makes the readout a question rather than a lookup. It is
    checked on real episodes rather than argued from the construction, because
    the construction went through three versions and two of them were wrong.
    """
    _, ev, tok = fixtures
    for ep in ev:
        ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer, eos=True)
        reading = Reading(ids[-320:], tok)
        for t, (site, _) in site_targets(ep.graph, reading).items():
            assert 0 <= site < t, f"{ep.lesson_id}: site {site} is not before {t}"


def test_the_site_target_names_a_word_the_reader_has_read(fixtures):
    """The leak surface, stated as the thing that would be a leak.

    A target naming a word that has not been read would be unanswerable, and a
    reader that scored above the floor on it would be reading forward.
    """
    _, ev, tok = fixtures
    for ep in ev:
        ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer, eos=True)
        reading = Reading(ids[-320:], tok)
        read = words_read(reading)
        for t, (site, key) in site_targets(ep.graph, reading).items():
            if key == ROOT:
                assert site == 0
                continue
            assert key in words_at_position(reading, site, read)
            assert key in {w.lower() for w in reading.words[:read[t]]}


def test_the_oracle_row_agrees_with_the_target_it_was_handed(fixtures, cfg):
    """A consistency check, and deliberately not a result.

    ``gsite-oracle`` is handed the object the target is derived from, so
    agreeing with it is not evidence about attachment. A *dis*agreement is
    evidence — that the target and the prefix restriction have come apart — and
    that is what this pins. It caught two real bugs: a scored position defined
    by character count rather than by the reader's own rule, and a target keyed
    on a single word at a position where one token finishes two.

    The bar is 0.99 rather than 1.0, and the gap is understood rather than
    tolerated. On the full curriculum this row is **0.9979**, and the residual
    0.2% is multi-word labels: the target requires the head to have been read
    before the phrase *began*, while the restricted parse reveals a head that
    becomes available part-way through it, so the two walk to different
    ancestors. Every lesson in this fixture labels in single words, so the
    fixture itself sits at 1.000 — asserting that exactly would pin a property
    of the fixture rather than of the code.
    """
    _, ev, tok = fixtures
    model = fitted("gsite-oracle", fixtures, cfg)
    task = make_task("lm", max_len=320)
    totals = Totals()
    for i in range(0, len(ev), 4):
        batch = task.collate(ev[i:i + 4], tok)
        totals.add(task.compute(model(batch), batch).counts)
    metrics = task.summarize(totals)
    assert metrics["site_n"] > 0
    assert metrics["site_acc"] >= 0.99, (
        "the site target and the prefix restriction disagree; one of them is "
        f"wrong (got {metrics['site_acc']:.4f})")


@pytest.mark.parametrize("name", SITE_MODELS)
def test_a_site_pointer_never_names_a_later_position(name, fixtures, cfg):
    """Closed structurally in ``_pointer_logits``, checked here on real output."""
    _, ev, tok = fixtures
    model = fitted(name, fixtures, cfg)
    batch = collate_text(ev[:3], tok, max_len=320)
    logits = model(batch).channels.get(SITE)
    assert logits is not None, f"{name} emitted no site channel"
    L = logits.shape[1]
    future = torch.ones((L, L), dtype=torch.bool).triu(1)
    assert bool((logits[:, future] <= -1e8).all()), \
        f"{name} can point at a position it has not read"


def test_the_site_floor_is_measured_and_says_which_rule_won(fixtures):
    train, ev, tok = fixtures
    floor = make_task("lm", max_len=320).floor(ev, tok, train)
    assert floor["site_n"] > 0
    assert 0.0 < floor["site_acc"] < 1.0
    assert floor["site_floor_by"] in {"previous", "start", "offset"}


# ---------------------------------------------------------------------------
# THE leak guard
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", SITE_MODELS)
def test_a_graph_node_the_text_never_names_cannot_move_a_logit(name, fixtures, cfg):
    """The guard the causality test cannot be.

    ``test_causal_task_cannot_see_the_future`` perturbs tokens, and on the text
    task the graph does not move when tokens do — so a model reading the answer
    key out of ``meta["graphs"]`` would sail through it. The guard that bites is
    this one: bolt extra nodes onto the episode's term, label them with symbols
    the rendering does not contain, and require every logit on every channel to
    be **bit-identical**.

    It has real force here because the oracle prefix parser genuinely is handed
    that graph. What makes it pass is the restriction — a node whose symbol the
    reader has not read is never revealed — and this is what says the
    restriction is doing its job on the ``site`` channel too, which is new
    surface that the existing guard never covered.
    """
    _, ev, tok = fixtures
    model = fitted(name, fixtures, cfg)
    original = ev[:2]
    bolted = copy.deepcopy(original)
    for ep in bolted:
        g = ep.graph
        root = next((i for i, p in enumerate(g.parent) if p < 0), 0)
        for k in range(4):
            g.add(f"qqzz{k}", "ident", root, 7)

    with torch.no_grad():
        a = model(collate_text(original, tok, max_len=320))
        b = model(collate_text(bolted, tok, max_len=320))
    for channel in sorted(set(a.channels) | set(b.channels)):
        left, right = a.channels.get(channel), b.channels.get(channel)
        assert (left is None) == (right is None), f"{name}/{channel} appeared"
        if left is None:
            continue
        assert torch.equal(left, right), (
            f"{name}: an unnameable graph node moved the {channel} channel")


def test_the_bolted_symbols_really_are_absent_from_the_text(fixtures):
    """The control on the control: a guard whose perturbation is invisible
    because it changed nothing would pass while checking nothing."""
    _, ev, tok = fixtures
    for ep in ev[:2]:
        assert "qqzz" not in ep.text.lower()


# ---------------------------------------------------------------------------
# the reading geometry the target rests on
# ---------------------------------------------------------------------------
def test_position_of_word_is_the_readers_rule_and_not_a_character_count(fixtures):
    """The bug that made every row score as abstention.

    A prefix ending in an alphanumeric character does not count its final word,
    so the position at which a word's last byte arrives is one before the
    position at which the reader has *read* it. Scoring at the former put every
    question one token ahead of the parse meant to answer it.
    """
    _, ev, tok = fixtures
    ep = ev[0]
    ids = tok.encode(ep.prompt + "\n", bos=True) + tok.encode(ep.answer, eos=True)
    reading = Reading(ids[-320:], tok)
    read = words_read(reading)
    at = position_of_word(reading, read)
    for w, t in enumerate(at):
        if t < 0:
            continue
        assert read[t] > w, "the reader has not read the word at its own position"
        assert t == 0 or read[t - 1] <= w
