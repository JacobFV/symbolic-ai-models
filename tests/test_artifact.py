"""Artifacts are immutable, content-addressed, and cannot pretend to be present.

The properties tested here are what make the flow layer's cache honest and its
provenance meaningful. In particular: the id covers the *value* and not the
producer, so two kernels computing the same thing hit one cache entry; and
``present=False`` cannot carry a value, so a missing measurement cannot be
imputed into a real one on its way through an edge.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.artifact import (Artifact, ArtifactRef, FileStore,
                                       Interval, MemoryStore, Provenance,
                                       artifact_id, canonical_bytes)


def test_the_id_is_the_content():
    a = Artifact(type="scalar", value=[1, 2, {"b": 2, "a": 1}])
    b = Artifact(type="scalar", value=[1, 2, {"a": 1, "b": 2}])
    assert a.id == b.id, "key order changed the identity"
    c = Artifact(type="scalar", value=[1, 2, {"a": 1, "b": 3}])
    assert a.id != c.id


def test_provenance_is_not_part_of_the_identity():
    """Two kernels that computed the same thing must hit the same cache entry."""
    a = Artifact(type="scalar", value=1)
    b = a.with_provenance(Provenance(producer="someone_else", method="another way"))
    assert a.id == b.id
    assert b.provenance.producer == "someone_else"


def test_unit_frame_and_time_are_part_of_the_identity():
    base = Artifact(type="scalar", value=1.0)
    assert base.id != Artifact(type="scalar", value=1.0, unit="m").id
    assert base.id != Artifact(type="scalar", value=1.0, frame="epsg:4978").id
    assert base.id != Artifact(type="scalar", value=1.0,
                               valid_time=Interval("2020", None)).id


def test_an_absent_artifact_cannot_carry_a_value():
    with pytest.raises(ValueError, match="absent"):
        Artifact(type="scalar", value=0, present=False)
    a = Artifact.absent("scalar", why="sensor offline")
    assert a.present is False and a.value is None
    assert a.meta["absent_because"] == "sensor offline"


def test_an_artifact_is_inline_or_a_ref_never_both():
    with pytest.raises(ValueError, match="never both"):
        Artifact(type="mesh", value={"tris": []},
                 ref=ArtifactRef(uri="file:///x.glb"))


def test_big_things_are_referenced_not_inlined():
    a = Artifact(type="raster", ref=ArtifactRef(
        uri="s3://bucket/dem.tif", media_type="image/tiff", n_bytes=2 << 30))
    assert a.value is None
    assert len(canonical_bytes(a.descriptor())) < 1000, (
        "a 2 GiB raster put 2 GiB into the graph")


def test_canonical_bytes_refuses_nan():
    with pytest.raises(ValueError):
        artifact_id({"x": float("nan")})


def test_a_store_cannot_overwrite():
    s = MemoryStore()
    a = Artifact(type="scalar", value=1)
    assert s.put(a) == s.put(a) == a.id
    assert s.get(a.id).value == 1
    with pytest.raises(KeyError, match="no artifact"):
        s.get("artifact:blake2b:" + "0" * 64)


def test_a_file_store_round_trips(tmp_path):
    s = FileStore(tmp_path)
    a = Artifact(type="claim_set", value={"n": 3}, schema="sai.world@1",
                 profiles=("logic.proposition",), unit="1",
                 valid_time=Interval("2026-01-01", None),
                 provenance=Provenance(producer="k", license="CC0-1.0"))
    aid = s.put(a)
    assert s.has(aid)
    back = s.get(aid)
    assert back.id == aid
    assert back.profiles == ("logic.proposition",)
    assert back.provenance.license == "CC0-1.0"
    assert back.valid_time.start == "2026-01-01"
    assert list(s) == [aid]


def test_every_provenance_field_survives_a_round_trip():
    """`derivation` was added to `to_dict` and not to `from_dict`, so it
    serialised and came back empty -- the same add-one-side asymmetry as every
    other contract found this week, in my own change, caught by one test.

    Written over `dataclasses.fields` rather than a hand-listed set, so the
    next field added is covered without anyone remembering to cover it.
    """
    import dataclasses

    from symbolic_ai_core.world import Claim
    from symbolic_ai_core.artifact.value import Provenance

    filled = {}
    for f in dataclasses.fields(Provenance):
        filled[f.name] = (("a", "b") if f.type == "tuple[str, ...]"
                          else f"{f.name}-value")
    prov = Provenance(**filled)
    back = Claim.from_dict(Claim("p", provenance=prov).to_dict()).provenance
    for f in dataclasses.fields(Provenance):
        assert getattr(back, f.name) == getattr(prov, f.name), (
            f"Provenance.{f.name} did not survive a round trip: it is in "
            "to_dict and missing from from_dict")


def test_every_provenance_field_survives_a_world_round_trip():
    """The same asymmetry existed twice -- claim.py and snapshot.py each
    rebuild a Provenance by hand."""
    import dataclasses

    from symbolic_ai_core.world import Claim, WorldSnapshot
    from symbolic_ai_core.artifact.value import Provenance

    filled = {f.name: (("a",) if f.type == "tuple[str, ...]" else f"{f.name}-v")
              for f in dataclasses.fields(Provenance)}
    w = WorldSnapshot(claims=(Claim("p", provenance=Provenance(**filled)),))
    back = WorldSnapshot.from_dict(w.to_dict()).claims[0].provenance
    for f in dataclasses.fields(Provenance):
        assert getattr(back, f.name) == filled[f.name], (
            f"Provenance.{f.name} lost in the WorldSnapshot round trip")
