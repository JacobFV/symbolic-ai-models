"""Conditioning OmegaClaw on the language, and the facts that decide what it can buy.

``tests/test_omegaclaw.py`` covers the family's shared contract. What is left is
the set of claims the *language-conditioned* members make, and one claim about
the corpus that they all stand on:

**The term graph is byte-identical in every language.** ``Lesson.structured``
takes no language, so a rule that reads only the graph has the same reliability
in every pack by construction. That is why ``omegaclaw_lang-002`` is expected to
lose and ``omegaclaw_textlang-002`` is not, and it is pinned here rather than
left in a docstring — if ``structured`` ever grows a language parameter, this
file should fail loudly and the whole reading changes.
"""

from __future__ import annotations

import numpy as np
import pytest

from symbolic_ai_core.data.batch import collate_graph
from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.models.omegaclaw import (CLAWS, SURFACE_CLAWS,
                                                 TEXT_CLAWS, OmegaClaw, Scan)
from symbolic_ai_models.models.omegaclaw_const_002 import OmegaClawConstant
from symbolic_ai_models.models.omegaclaw_ctx_001 import OmegaClawContext
from symbolic_ai_models.models.omegaclaw_lang_002 import OmegaClawLanguage
from symbolic_ai_models.models.omegaclaw_text_002 import OmegaClawText
from symbolic_ai_models.models.omegaclaw_textlang_002 import OmegaClawTextLanguage
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]
#: Deliberately spans the extremes of the surface measurement: `symbols` renders
#: 0.978 of labels verbatim and `chinese` 0.285, so a test that wants to see the
#: surface claws behave differently by language has somewhere to look.
LANGUAGES = ["english", "chinese", "symbols"]


@pytest.fixture(scope="module")
def parallel():
    """The same seeds in every pack, interleaved: an exact parallel corpus."""
    drawn = [list(generate(LESSONS, n=8, language=lang)) for lang in LANGUAGES]
    episodes = [ep for row in zip(*drawn) for ep in row]
    tok = build_tokenizer(TrainConfig(vocab_size=800), episodes)
    return episodes, tok


@pytest.fixture(scope="module")
def cfg(parallel):
    _, tok = parallel
    return ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2, n_heads=4,
                       d_ff=64, dropout=0.0, max_nodes=128)


# ---------------------------------------------------------------------------
# the fact the whole experiment rests on
# ---------------------------------------------------------------------------
def test_the_graph_is_byte_identical_in_every_language():
    """So a graph-only claw cannot have a language-varying reliability.

    ``tests/test_language.py`` pins this for two lessons and three packs on the
    text side. Pinned again here because it is the premise of two registered
    models: if it ever stops holding, ``omegaclaw_lang-002``'s docstring — which
    says the model can only lose — becomes false.
    """
    base = {ep.instance_id: ep.graph.to_dict()
            for ep in generate(LESSONS, n=4, language="english")}
    for lang in LANGUAGES[1:]:
        for ep in generate(LESSONS, n=4, language=lang):
            assert ep.graph.to_dict() == base[ep.instance_id], \
                f"{lang} changed the graph; the language experiment changes with it"


def test_the_view_knows_which_language_rendered_its_prompt(parallel, cfg):
    """``perceive`` cannot condition on a field the collator does not carry."""
    episodes, tok = parallel
    model = build("omegaclaw_lang-002", cfg)
    model.fit_on(episodes[:6], tok)
    batch = collate_graph(episodes[:6], tok, rng=np.random.default_rng(0))
    seen = {model._view(batch, b).language for b in range(len(episodes[:6]))}
    assert seen == set(LANGUAGES), seen


# ---------------------------------------------------------------------------
# what each new member is allowed to differ in
# ---------------------------------------------------------------------------
def test_each_variant_differs_in_exactly_what_it_claims_to():
    """The family's readability rule, extended to the four new rows.

    ``lang`` may change ``perceive`` and nothing else; ``text`` may change
    ``claws`` and nothing else; ``textlang`` changes both, which is why it is
    read against ``text`` rather than against ``ctx``.
    """
    for cls in (OmegaClawLanguage, OmegaClawConstant):
        assert cls.claws is OmegaClaw.claws
        assert cls.perceive is not OmegaClaw.perceive
        assert cls.commit is OmegaClaw.commit
    for cls in (OmegaClawText, OmegaClawTextLanguage):
        assert cls.claws is not OmegaClaw.claws
        assert cls.commit is OmegaClaw.commit
    assert OmegaClawText.perceive is OmegaClaw.perceive
    assert OmegaClawTextLanguage.perceive is not OmegaClaw.perceive


def test_the_text_models_keep_every_claw_the_others_have():
    """A wider reach, not a different one — otherwise the contrast is unreadable."""
    assert set(TEXT_CLAWS) == set(CLAWS) | set(SURFACE_CLAWS)
    for name, claw in CLAWS.items():
        assert TEXT_CLAWS[name] is claw
    # Insertion order is part of the model: ties in a winner-take-all commit
    # break towards the earlier claw, so the base claws must still come first.
    assert list(TEXT_CLAWS)[:len(CLAWS)] == list(CLAWS)


# ---------------------------------------------------------------------------
# the control: a constant where the language goes must change nothing
# ---------------------------------------------------------------------------
def test_a_constant_context_field_changes_nothing(parallel, cfg):
    """``omegaclaw_const-002`` must be ``omegaclaw_ctx-001``, exactly.

    Appending a constant to a tuple key is a bijection on contexts, so every
    cell keeps its counts and every prediction is unchanged. This is the check
    that the plumbing — the new ``GraphView.language`` field, the widened key,
    the iteration order — costs nothing on its own, which is what licenses
    reading any ``lang`` versus ``ctx`` difference as the language partition.
    """
    episodes, tok = parallel
    ctx_model = build("omegaclaw_ctx-001", cfg)
    const_model = build("omegaclaw_const-002", cfg)
    ctx_model.fit_on(episodes, tok)
    const_model.fit_on(episodes, tok)

    assert len(const_model.claw_evidence) == len(ctx_model.claw_evidence)
    assert const_model.claw_totals == ctx_model.claw_totals

    checked = 0
    for view, targets in ctx_model.training_views(episodes[:24], tok, repeats=1,
                                                  max_nodes=cfg.max_nodes):
        scan = Scan(view)
        for node in targets:
            a = ctx_model._decide(view, scan, node)
            b = const_model._decide(view, scan, node)
            assert (a is None) == (b is None)
            if a is None:
                continue
            assert a[0] == b[0], "the constant control changed the distribution"
            assert a[1] == pytest.approx(b[1]), "it changed the raw score"
            checked += 1
    assert checked > 20, "the test did not actually exercise the decision path"


def test_the_language_partition_really_partitions(parallel, cfg):
    """``lang`` must key on the language; otherwise it is ``ctx`` with a longer key."""
    episodes, tok = parallel
    model = build("omegaclaw_lang-002", cfg)
    model.fit_on(episodes, tok)
    languages = {key[0] for key, _ in model.claw_evidence}
    assert languages == set(LANGUAGES), languages


# ---------------------------------------------------------------------------
# what the surface claws are allowed to do
# ---------------------------------------------------------------------------
def test_every_surface_claw_points_at_a_visible_node(parallel, cfg):
    """Pointer-valued, so the family's renaming equivariance survives the prose.

    A claw that returned a symbol read out of the text rather than off a node
    would be remembering vocabulary, and the whole family's equivariance claim
    would stop being true of the models that use it.
    """
    episodes, tok = parallel
    model = build("omegaclaw_text-002", cfg)
    model.fit_on(episodes[:6], tok)
    fired = 0
    for view, targets in list(model.training_views(episodes, tok, repeats=1,
                                                   max_nodes=cfg.max_nodes))[:12]:
        scan = Scan(view)
        for node in targets:
            for name, claw in SURFACE_CLAWS.items():
                claim = claw(scan, node)
                if claim is None:
                    continue
                fired += 1
                assert 0 <= claim.source < len(view), f"{name} pointed nowhere"
                assert claim.source != node, f"{name} pointed at the hidden node"
                assert view.labels[claim.source] == claim.symbol, \
                    f"{name} invented a symbol"
    assert fired > 20


def test_no_surface_claw_fires_when_the_whole_graph_is_hidden(parallel, cfg):
    """With every label gone there is nothing to point at, prose or no prose.

    The prompt is still there and still full of words. A surface claw that fired
    anyway would be reading a symbol out of the text instead of off a node.
    """
    episodes, tok = parallel
    model = build("omegaclaw_text-002", cfg)
    model.fit_on(episodes[:6], tok)
    batch = collate_graph(episodes[:3], tok, mask_all=True)
    view = model._view(batch, 0)
    assert view.text, "the fixture lost the prompt, so this proves nothing"
    scan = Scan(view)
    for node in view.hidden:
        for name, claw in SURFACE_CLAWS.items():
            assert claw(scan, node) is None, f"{name} fired on a fully masked graph"


def test_the_surface_claws_behave_differently_by_language(parallel, cfg):
    """The one channel the language moves, measured rather than assumed.

    The same seeds, the same graphs, different prose. If the surface claws fired
    at the same rate in Chinese as in an s-expression notation, there would be
    no per-language reliability for ``weigh`` to learn and
    ``omegaclaw_textlang-002`` could not differ from ``omegaclaw_text-002`` for
    any reason but noise.
    """
    episodes, tok = parallel
    model = build("omegaclaw_text-002", cfg)
    model.fit_on(episodes[:6], tok)
    fired = {lang: 0 for lang in LANGUAGES}
    asked = {lang: 0 for lang in LANGUAGES}
    for view, targets in model.training_views(episodes, tok, repeats=1, seed=3,
                                              max_nodes=cfg.max_nodes):
        scan = Scan(view)
        for node in targets:
            asked[view.language] += 1
            fired[view.language] += sum(claw(scan, node) is not None
                                        for claw in SURFACE_CLAWS.values())
    rate = {lang: fired[lang] / max(asked[lang], 1) for lang in LANGUAGES}
    assert all(asked[lang] > 30 for lang in LANGUAGES), asked
    assert rate["symbols"] > rate["chinese"], rate
    assert rate["english"] > rate["chinese"], rate


def test_the_graph_claws_do_not(parallel, cfg):
    """The other half of the same fact, and the reason ``lang`` cannot win.

    Identical graphs mean identical firing, exactly — not approximately. Each
    pack is walked as its own list rather than sliced out of the interleaved
    fixture, because the collator's masking RNG advances with position: in the
    interleaved order the same episode sits at a different index in each pack
    and gets a different mask, which would make this compare two different
    questions about one tree and fail for a reason that is not the one being
    tested.
    """
    _, tok = parallel
    model = build("omegaclaw_ctx-001", cfg)
    fired: dict[str, list] = {}
    for lang in LANGUAGES:
        drawn = list(generate(LESSONS, n=8, language=lang))
        fired[lang] = [
            [tuple(sorted(name for name, claw in CLAWS.items()
                          if claw(Scan(view), node) is not None))
             for node in sorted(targets)]
            for view, targets in model.training_views(
                drawn, tok, repeats=1, seed=3, max_nodes=cfg.max_nodes)]
    reference = fired[LANGUAGES[0]]
    assert sum(len(v) for v in reference) > 30
    for lang in LANGUAGES[1:]:
        assert fired[lang] == reference, \
            f"{lang}: a graph-only claw noticed the language, which it cannot see"
