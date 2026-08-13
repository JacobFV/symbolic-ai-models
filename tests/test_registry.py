"""The versioned-name rule, tested once and pinned to one implementation.

`test_models.py` and `test_graph_parsers.py` each check the rule through their
own registry, which is right — those are the surfaces people use. What they
cannot check is that there is still only *one* rule. There used to be two: the
fix that stopped `ptrgen` resolving to the `ptrgen-argmax` control was written
for models and then hand-carried into the parsers package, and a second copy of a
rule whose whole job is keeping published names honest is a drift waiting to
happen.

So this file tests `symbolic_ai_core.registry` directly, on a throwaway registry
that cannot be perturbed by what happens to be registered, and then asserts that
both real registries are instances of it rather than lookalikes.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.registry import VersionedRegistry, base_name


class Thing:
    name = ""


def _registry(*names: str) -> VersionedRegistry[Thing]:
    reg: VersionedRegistry[Thing] = VersionedRegistry("thing")
    for n in names:
        reg.add(n, type("T", (Thing,), {"name": n}))
    return reg


def test_a_bare_name_resolves_over_numbers_and_never_over_words():
    """The `ptrgen-argmax` failure, in the abstract. A string sort puts every
    word above every number, so a scheme that encourages naming a variant for
    what it changed will silently promote the ablation."""
    reg = _registry("t-001", "t-002", "t-argmax", "t-noprose")
    assert reg.get("t").name == "t-002"
    assert reg.get("t-argmax").name == "t-argmax"


def test_numbers_compare_as_numbers():
    """`-010` is above `-009`; a lexical sort disagrees at ten variants."""
    assert _registry("t-009", "t-010").get("t").name == "t-010"


def test_an_exact_name_beats_resolution():
    """Something literally registered as `foo` must win, or a later `foo-002`
    hijacks a name someone pinned to a published number."""
    assert _registry("t", "t-002").get("t").name == "t"


def test_an_unnumbered_family_refuses_rather_than_guessing():
    reg = _registry("t-alpha", "t-beta")
    with pytest.raises(KeyError, match="no numbered version"):
        reg.get("t")
    with pytest.raises(KeyError, match="unknown thing"):
        reg.get("nothing")


def test_a_duplicate_name_is_an_error_not_an_overwrite():
    """An overwrite is how a published row gets redefined in silence."""
    reg = _registry("t-001")
    with pytest.raises(ValueError, match="already registered"):
        reg.add("t-001", Thing)


def test_base_name_strips_only_a_version_suffix():
    assert base_name("corefer-001") == "corefer"
    assert base_name("corefer-noprose") == "corefer"
    assert base_name("corefer") == "corefer"


def test_both_registries_are_the_shared_one_rather_than_copies():
    """The point of the move. If either package grows its own resolution again,
    this fails before the two can drift."""
    from symbolic_ai_models.models import registry as models_registry
    from symbolic_ai_parsers import base as parsers_base

    for module in (models_registry, parsers_base):
        assert isinstance(module._REGISTRY, VersionedRegistry), module.__name__
        # REGISTRY is the live dict, not a snapshot taken at import time.
        assert module.REGISTRY is module._REGISTRY.entries, module.__name__
        assert module.base_name is base_name, module.__name__
