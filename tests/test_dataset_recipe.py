"""A dataset recipe: how examples exist, not where a jsonl happens to be.

The failure this replaces: a "dataset" was a directory with train.jsonl in it,
which makes two things unanswerable — which source version produced it, and what
would happen if you asked for more.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.data.key import SampleKey
from symbolic_ai_core.data.recipe import (DatasetRecipe, RecipeError,
                                          load_recipe, recipes)
from symbolic_ai_core.source.manifest import load_yaml


def test_every_recipe_loads_and_builds():
    got = recipes()
    assert got, "no recipes under manifests/datasets/"
    for rid, r in got.items():
        assert r.id == rid
        ds = r.dataset()
        assert ds.block("train") > 0


def test_a_recipe_hash_covers_its_content():
    a = load_recipe("kg_essays_wordnet_v1")
    b = load_recipe("kg_essays_cskg_v1")
    assert a.hash != b.hash, "two different recipes hashed the same"
    assert a.hash == load_recipe("kg_essays_wordnet_v1").hash


def test_a_recipe_cannot_name_an_arbitrary_importable():
    """A recipe is data. Data that can name any importable is a recipe that can
    execute anything."""
    r = DatasetRecipe(id="x", raw={"id": "x", "generator": {"id": "os.system"}})
    with pytest.raises(RecipeError, match="not registered"):
        r.dataset()


def test_the_splits_keep_train_and_eval_apart_by_seed_range():
    ds = load_recipe("formal_curriculum_v1").dataset()
    train = {ds.address("train", i)[1] for i in range(2000)}
    ev = {ds.address("eval", i)[1] for i in range(ds.block("eval"))}
    assert train.isdisjoint(ev)
    assert min(ev) >= 1_000_000


def test_an_eval_split_refuses_a_second_epoch():
    ds = load_recipe("kg_essays_wordnet_v1").dataset()
    with pytest.raises(ValueError, match="finite"):
        next(ds.keys("eval", epoch=1))


# --- the coverage a recipe carries ---------------------------------------
def test_the_essay_dataset_carries_what_its_source_cannot_do():
    ds = load_recipe("kg_essays_wordnet_v1").dataset()
    assert set(ds.dead_sections()) == {"qualities", "behaviour"}
    case = ds.get(SampleKey(ds.dataset_id, "train", 0, 3))
    assert set(case.meta["dead_sections"]) == {"qualities", "behaviour"}, (
        "a sample did not carry the fact that its corpus is missing two of "
        "eight rhetorical sections")


def test_the_two_essay_recipes_are_complementary_not_alternatives():
    wn = load_recipe("kg_essays_wordnet_v1").dataset()
    ck = load_recipe("kg_essays_cskg_v1").dataset()
    assert "qualities" in wn.dead_sections()
    assert "qualities" not in ck.dead_sections()
    assert wn.coverage["composition"] > ck.coverage["composition"]


def test_the_recipe_records_the_coverage_the_dataset_measures():
    """The manifest's `coverage.dead_sections` must not drift from the source."""
    for rid in ("kg_essays_wordnet_v1", "kg_essays_cskg_v1"):
        r = load_recipe(rid)
        declared = set((r.raw.get("coverage") or {}).get("dead_sections") or [])
        measured = set(r.dataset().dead_sections())
        assert declared <= measured, (
            f"{rid} declares {declared - measured} dead, and the source "
            f"populates them")


# --- addressing -----------------------------------------------------------
def test_essay_addressing_is_topic_minor():
    """Any prefix covers the topic pool rather than being many seeds of one."""
    ds = load_recipe("kg_essays_wordnet_v1").dataset()
    topics = [ds.address("train", i)[0] for i in range(ds.n_topics)]
    assert len(set(topics)) == ds.n_topics
    assert ds.address("train", 0)[1] == ds.address("train", 1)[1]
    assert ds.address("train", ds.n_topics)[1] == 1


def test_an_essay_sample_replays_exactly():
    ds = load_recipe("kg_essays_wordnet_v1").dataset()
    k = SampleKey(ds.dataset_id, "train", 0, 77)
    assert ds.get(k).to_dict() == ds.get(k).to_dict()
    assert ds.essay(k).text == ds.essay(k).text


def test_an_essay_case_carries_text_and_its_alignment():
    ds = load_recipe("kg_essays_wordnet_v1").dataset()
    case = ds.get(SampleKey(ds.dataset_id, "train", 0, 11))
    assert case.observations["text"].value
    spans = case.observations["mentions"].value
    assert spans and all({"start", "end", "node"} <= set(m) for m in spans)


# --- the YAML trap --------------------------------------------------------
def test_yaml_implicit_typing_is_refused(tmp_path):
    """An unquoted 2026-08-18 is a `date`, an unquoted `no` is `False`. The
    authored-YAML/canonical-JSON contract rests on the parse being
    JSON-compatible, and this is what noticed."""
    p = tmp_path / "bad.yaml"
    p.write_text("id: x\nmeasured: 2026-08-18\n", encoding="utf-8")
    with pytest.raises(ValueError, match="implicit typing"):
        load_yaml(p)

    ok = tmp_path / "good.yaml"
    ok.write_text("id: x\nmeasured: '2026-08-18'\n", encoding="utf-8")
    assert load_yaml(ok)["measured"] == "2026-08-18"


def test_every_tracked_manifest_parses_to_json_compatible_types():
    from pathlib import Path

    from symbolic_ai_core.source.registry import repo_root

    root = repo_root()
    seen = 0
    for d in ("catalog", "manifests", "ontology"):
        for p in sorted((root / d).rglob("*.yaml")):
            load_yaml(p)                       # raises on an implicit type
            seen += 1
    assert seen > 20, f"only {seen} manifests checked"
