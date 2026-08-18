"""ASP: defaults with exceptions, world completion, and alternatives kept apart.

The test that carries the design is
``test_a_non_unique_completion_asserts_nothing``. A world completion with three
admissible answer sets is a world with three hypotheses, and a kernel that
returns the first one has made a choice the caller never made and cannot see.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)
from symbolic_ai_kernels import KernelRequest, get_kernel
from symbolic_ai_kernels.asp import Mangler, project_world, quote

clingo = pytest.importorskip("clingo")

K = get_kernel("asp@1")


def birds() -> WorldSnapshot:
    return WorldSnapshot(
        entities={n: Entity(n, types=("bird",))
                  for n in ("tweety", "pingu", "opus")},
        claims=(Claim("penguin", {"who": EntityRef("pingu")}),))


# --- the name bijection ---------------------------------------------------
def test_mangling_is_injective_where_a_regex_would_collide():
    m = Mangler()
    a = m.to_solver("cites-precedent")
    b = m.to_solver("cites_precedent")
    assert a != b, "two relations collapsed onto one solver name"
    assert m.from_solver(a) == "cites-precedent"
    assert m.from_solver(b) == "cites_precedent"


def test_a_leading_digit_or_empty_name_still_yields_an_identifier():
    m = Mangler()
    assert m.to_solver("2020_census")[0].isalpha()
    assert m.to_solver("::")[0].isalpha()


def test_constants_are_quoted_not_mangled():
    assert quote("wn:dog.n.01") == '"wn:dog.n.01"'
    assert quote('he said "hi"') == '"he said \\"hi\\""'


def test_a_program_invented_predicate_reads_back_verbatim():
    m = Mangler()
    m.to_solver("parent")
    assert m.read("flies") == "flies"
    with pytest.raises(KeyError, match="never emitted"):
        m.from_solver("flies")


# --- defaults and exceptions ---------------------------------------------
def test_defaults_with_exceptions():
    p = K.project(birds(), KernelRequest(params={"program": """
        abnormal(X) :- penguin(X).
        flies(X) :- type(X, "bird"), not abnormal(X).
    """}))
    r = K.run(p, KernelRequest())
    assert r.ok and r.diagnostics["unique"]
    flies = {c.roles["arg0"] for c in r.claims if c.predicate == "flies"}
    assert {getattr(f, "id", f) for f in flies} == {"tweety", "opus"}


def test_the_projection_reuses_the_relational_judgement_calls():
    """ASP drops what datalog drops, for the same reasons -- and says so."""
    w = WorldSnapshot(
        entities={"a": Entity("a"), "b": Entity("b")},
        claims=(Claim("believes", {"who": EntityRef("a"),
                                   "what": Claim("p", {"x": EntityRef("b")})}),
                Claim("mass", {"of": EntityRef("a"),
                               "value": Quantity(1.0, "kg")})))
    p = project_world(w)
    why = " ".join(d.why for d in p.discarded)
    assert "nested proposition" in why and "Quantity" in why


# --- world completion -----------------------------------------------------
def test_a_unique_completion_is_asserted():
    """One admissible answer set: the kernel may assert its delta."""
    p = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "grounded", "over": ["entity"]}],
        "constraints": [
            '% every bird is grounded iff it is a penguin',
            ':- grounded(X), not penguin(X).',
            ':- penguin(X), not grounded(X).',
        ]}))
    r = K.run(p, KernelRequest())
    assert r.ok and r.diagnostics["unique"]
    assert not r.delta.is_empty()
    assert all(c.modality == "asserted" for c in r.claims)


def test_a_non_unique_completion_asserts_nothing():
    """Three admissible completions are three hypotheses, not an answer."""
    p = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "chosen", "over": ["entity"]}],
        "constraints": [':- #count { X : chosen(X) } != 1.']}))
    r = K.run(p, KernelRequest())
    assert r.ok
    assert r.diagnostics["n_models"] == 3
    assert not r.diagnostics["unique"]
    assert r.delta.is_empty(), "the solver's first answer set became the world"
    assert all(c.modality == "possible" for c in r.claims)
    assert len(r.artifacts["models"]) == 3, "the alternatives were collapsed"


def test_the_open_predicates_are_reported():
    p = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "chosen", "over": ["entity"]}]}))
    assert p.program.open_predicates == ("chosen",)
    assert K.run(p, KernelRequest()).diagnostics["open_predicates"] == ["chosen"]


def test_a_choice_rule_with_no_domain_is_discarded_not_run():
    p = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "anything", "over": []}]}))
    assert any(d.kind == "choice" and "finite meaning" in d.why
               for d in p.discarded)
    assert p.program.open_predicates == ()


def test_model_enumeration_reports_truncation():
    p = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "chosen", "over": ["entity"]}]}))
    r = K.run(p, KernelRequest(params={"max_models": 2}))
    assert r.diagnostics["truncated"], (
        "a truncated model set read as 'these are the possibilities'")


# --- refusals -------------------------------------------------------------
def test_unsatisfiable_says_it_is_about_the_projection():
    p = K.project(birds(), KernelRequest(params={
        "constraints": [':- type(X, "bird").']}))
    r = K.run(p, KernelRequest())
    assert not r.ok
    assert "unsatisfiable" in r.refused and "PROJECTION" in r.refused
    assert r.diagnostics["satisfiable"] is False


def test_a_syntax_error_is_a_refusal_not_a_crash():
    p = K.project(birds(), KernelRequest(params={"program": "this is not asp"}))
    r = K.run(p, KernelRequest())
    assert not r.ok and "rejected the program" in r.refused


def test_the_manifest_declares_an_external_dependency():
    m = K.manifest
    assert m.runtime == "external" and m.dependencies == ("clingo>=5.7",)
    assert set(m.semantics) == {"closed_world", "non_monotonic", "defeasible"}
    assert m.authority["admissible_completion"] == "propose"


def test_a_higher_arity_domain_must_say_which_column_it_means():
    """Guessing the first column produces a well-formed model of the wrong
    question, which is the failure that has no symptom."""
    p = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "picked",
                     "over": [{"pred": "type", "arity": 2, "arg": 1}]}]}))
    assert p.program.open_predicates == ("picked",)
    r = K.run(p, KernelRequest())
    picked = {getattr(c.roles["arg0"], "id", c.roles["arg0"])
              for c in r.claims if c.predicate == "picked"}
    assert picked <= {"bird"}, "the domain ranged over entities, not kinds"

    bad = K.project(birds(), KernelRequest(params={
        "choices": [{"predicate": "picked", "over": [{"pred": "type",
                                                      "arity": 2, "arg": 5}]}]}))
    assert any(d.kind == "choice" for d in bad.discarded)
    assert bad.program.open_predicates == ()


def test_every_entity_gets_a_unary_domain_predicate():
    p = project_world(birds())
    assert 'entity("opus").' in p.program.text
