"""synthEX's class layer and the control it shipped.

The pair exists to answer one question — is a *curated* class layer worth more
than a meaningless partition of the same size — so the tests here guard the
things that would make that comparison a lie: matched cardinality, a
deterministic partition, and one differing method.
"""

from __future__ import annotations

import collections

import pytest

from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.train import TrainConfig, build_tokenizer

LESSONS = ["unification", "symbol_grounding", "center_embedding"]


@pytest.fixture(scope="module")
def fitted():
    train = list(generate(LESSONS, n=25))
    tok = build_tokenizer(TrainConfig(vocab_size=1600), train)
    cfg = ModelConfig(vocab_size=len(tok), max_len=160, max_nodes=128)
    out = {}
    for name in ("synthex_class-002", "synthex_random-002"):
        model = build(name, cfg)
        model.fit_on(train, tok)
        out[name] = model
    return out


def test_the_control_matches_the_curated_cardinality(fitted):
    """The confound that would invert the result, pinned.

    Only 6 of the curriculum's 17 node types ever land on a labelled node. A
    first version hashed into all 17, giving the control a partition three times
    finer than the thing it controls for -- it won, and the row would have read
    "random beats curated" when it meant "more classes beat fewer". synthEX's
    own control sets k from the real class count for this reason.
    """
    curated = set(fitted["synthex_class-002"].symbol_class.values())
    control = set(fitted["synthex_random-002"].symbol_class.values())
    assert len(control) == len(curated), (
        f"cardinality mismatch: curated {len(curated)}, control {len(control)}")


def test_the_two_models_differ_only_in_the_class_assignment(fitted):
    from symbolic_ai_models.models.synthex_002.model import (SynthexClassModel,
                                                             SynthexCurated,
                                                             SynthexRandom)
    assert SynthexCurated._assign_classes is not SynthexRandom._assign_classes
    for name in ("_contexts", "_label_table", "node_votes", "learn",
                 "_fit_gate", "_class_of"):
        assert getattr(SynthexCurated, name) is getattr(SynthexClassModel, name)
        assert getattr(SynthexRandom, name) is getattr(SynthexClassModel, name)


def test_the_control_partition_is_deterministic_across_processes(fitted):
    """`hash()` is salted per interpreter; sha256 is not.

    A control whose partition changed between runs would make the row
    irreproducible while looking fine in any single session.
    """
    import hashlib

    model = fitted["synthex_random-002"]
    k = len(set(model.symbol_class.values()))
    for symbol, assigned in list(model.symbol_class.items())[:50]:
        expected = int(hashlib.sha256(str(symbol).encode()).hexdigest(), 16) % k
        assert assigned == expected


def test_the_curated_ontology_is_severely_imbalanced(fitted):
    """The mechanism behind the result, asserted so it cannot quietly change.

    The curriculum's node types are semantically correct and statistically
    useless as a conditioning context: the largest class holds most of the
    symbols, so most pairs land in the same cell and the context cannot
    discriminate. The random partition is uniform by construction. That is why a
    meaningless partition outscores a ground-truth ontology here, and it is a
    fact about class *balance*, not about semantics being worthless.

    Asserted as a *relation* rather than a threshold. The first version required
    the top class to hold >0.5, which is what it holds on the twelve-lesson
    slice (0.68) and not on this three-lesson fixture (0.47). Pinning a constant
    measured on one slice into a test run on another is the mistake this repo
    keeps paying for; the imbalance itself is the invariant, its size is not.
    """
    counts = collections.Counter(
        fitted["synthex_class-002"].symbol_class.values())
    total = sum(counts.values())
    curated_top = max(counts.values()) / total
    control = collections.Counter(
        fitted["synthex_random-002"].symbol_class.values())
    control_top = max(control.values()) / sum(control.values())
    assert control_top < 0.35, "the control partition is not uniform"
    assert curated_top > 2 * control_top, (
        f"curated layer is no longer imbalanced against the control: "
        f"{curated_top:.2f} vs {control_top:.2f}")


def test_an_unknown_symbol_gets_its_own_class(fitted):
    """The unseen tail has to be reachable, which is most of what the class
    layer was ever buying -- see the module docstring's deflation table."""
    model = fitted["synthex_class-002"]
    unseen = max(model.symbol_class) + 10_000
    assert model._class_of(unseen) == model.n_classes
    assert model._class_of(None) == model.n_classes
