"""What a generator needs from a knowledge source, checked rather than assumed.

The failure this exists to stop is not a crash. A source missing an accessor
produces essays with one fewer rhetorical section, and a corpus quietly
two-thirds the intended richness reads exactly like one that is exactly right.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data.essay import (REQUIRED, SECTIONS, generate,
                                         sections_available)
from symbolic_ai_core.data.knowledge_source import (CAPABILITIES,
                                                    CapabilityError,
                                                    capabilities_of,
                                                    require_capabilities)


class Thin:
    """Has the minimum and nothing else."""

    pos = ["n", "n", "n"]

    def __len__(self):
        return 3

    def word(self, n):
        return f"w{n}"


class Declared:
    """Declares everything and populates nothing — the case detection catches."""

    pos = ["n", "n", "n"]

    def __len__(self):
        return 3

    def word(self, n):
        return f"w{n}"

    def __getattr__(self, name):
        if name in CAPABILITIES:
            return lambda n: ()
        raise AttributeError(name)


@pytest.fixture(scope="module")
def wordnet():
    return pytest.importorskip("symbolic_ai_kg").load("wordnet")


# --- detection, not declaration ------------------------------------------
def test_declaring_a_capability_is_not_having_it():
    """An accessor that exists and returns empty everywhere is the capability
    in name only, and that is the live case: WordNet exposes properties_of and
    carries zero property assertions."""
    r = capabilities_of(Declared(), name="declared")
    assert "properties_of" in r.present
    assert "properties_of" not in r.populated
    assert r.coverage["properties_of"] == 0.0


def test_a_missing_accessor_is_neither_present_nor_populated():
    r = capabilities_of(Thin(), name="thin")
    assert "hypernyms" not in r.present and "hypernyms" not in r.populated
    assert "word" in r.populated


def test_detection_is_deterministic(wordnet):
    a = capabilities_of(wordnet, name="wordnet")
    b = capabilities_of(wordnet, name="wordnet")
    assert a.coverage == b.coverage


# --- refusal --------------------------------------------------------------
def test_a_missing_capability_is_refused_by_name_with_what_it_costs():
    r = capabilities_of(Thin(), name="thin")
    with pytest.raises(CapabilityError) as e:
        require_capabilities(r, REQUIRED, who="the essay generator")
    msg = str(e.value)
    assert "hypernyms" in msg and "essay generator" in msg
    assert "placement" in msg or "kind of" in msg, (
        "the refusal did not say what is lost, only what is absent")


def test_the_generator_refuses_before_generating_anything():
    with pytest.raises(CapabilityError):
        list(generate(Thin(), n=1, source="thin"))


def test_a_populated_source_still_generates(wordnet):
    essays = list(generate(wordnet, n=3, source="wordnet"))
    assert essays


# --- the audit that changed what we thought ------------------------------
def test_wordnet_can_never_fill_two_of_the_eight_sections(wordnet):
    """Not an edge case: every essay corpus this repo has generated is missing
    the qualities and behaviour sections, and nothing said so."""
    avail = sections_available(wordnet, name="wordnet")
    assert set(avail) == set(SECTIONS)
    assert avail["qualities"] == 0.0
    assert avail["behaviour"] == 0.0
    assert avail["placement"] > 0.5, "the audit is not just reporting zeros"


def test_cskg_fills_exactly_the_sections_wordnet_cannot():
    """The two sources are complementary, not interchangeable."""
    kg = pytest.importorskip("symbolic_ai_kg").load("cskg")
    avail = sections_available(kg, name="cskg")
    assert avail["qualities"] > 0.0 and avail["behaviour"] > 0.0


def test_membership_is_dead_in_every_registered_source():
    """A section reachable nowhere is a template nobody has ever seen fire."""
    kgmod = pytest.importorskip("symbolic_ai_kg")
    for name in kgmod.KG_NAMES:
        assert sections_available(kgmod.load(name), name=name)["membership"] < 0.05
