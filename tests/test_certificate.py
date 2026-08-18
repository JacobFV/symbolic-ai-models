"""What a dependency certificate must never do: certify an answer that moved.

The soundness tests here are the cheap half of the guard. The expensive half is
in `scripts/cert_maintenance_13f.py`, which anchors every certificate against a
full recomputation on the real second snapshot — because a unit fixture cannot
tell you that a *query* reaches around the store, and that is the one failure
mode this mechanism has.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.runtime.certificate import (
    MISSING, Certificate, FullScan, RecordingStore, certify, changed_keys,
    digest_all, revalidate)


def _holders_store(edges):
    """cusip -> frozenset(filers), the shape the 13F experiment uses."""
    out: dict = {}
    for filer, sec in edges:
        out.setdefault(("holders", sec), set()).add(filer)
    return {k: frozenset(v) for k, v in out.items()}


OLD = _holders_store([("f1", "a"), ("f2", "a"), ("f1", "b")])
NEW = _holders_store([("f1", "a"), ("f2", "a"), ("f3", "b")])


def count_a(store):
    return len(store.get(("holders", "a"), frozenset()))


def count_b(store):
    return len(store.get(("holders", "b"), frozenset()))


def count_missing(store):
    return len(store.get(("holders", "zz"), frozenset()))


class TestReadSet:
    def test_records_only_what_was_read(self):
        cert = certify(count_a, OLD)
        assert cert.answer == 2
        assert cert.keys == (("holders", "a"),)

    def test_a_key_that_was_not_there_is_still_a_read(self):
        # The addition case. A certificate that records only hits cannot notice
        # a fact appearing where the answer relied on its absence.
        cert = certify(count_missing, OLD)
        assert cert.answer == 0
        assert cert.digests[("holders", "zz")] is MISSING

    def test_iterating_the_store_is_refused_by_default(self):
        with pytest.raises(FullScan):
            certify(lambda s: sum(len(v) for v in s.values()), OLD)

    def test_a_full_scan_is_allowed_when_asked_for_and_says_so(self):
        cert = certify(lambda s: len(list(s)), OLD, allow_full_scan=True)
        assert cert.full_scan
        assert cert.size == len(OLD)

    def test_reading_the_same_key_twice_records_it_once(self):
        cert = certify(lambda s: count_a(s) + count_a(s), OLD)
        assert cert.answer == 4
        assert cert.size == 1


class TestRevalidation:
    def test_an_untouched_answer_is_certified_without_recomputing(self):
        cert = certify(count_a, OLD)
        r = revalidate(cert, digest_all(NEW))
        assert r.valid and r.changed == ()
        assert count_a(NEW) == cert.answer          # the anchor

    def test_a_touched_answer_is_refused_even_when_its_value_is_unchanged(self):
        # b's holder set changed f1 -> f3, so the *count* is still 1. The
        # certificate must invalidate anyway: it certifies the reads, and it is
        # not entitled to guess that a changed input left the answer alone.
        cert = certify(count_b, OLD)
        r = revalidate(cert, digest_all(NEW))
        assert not r.valid
        assert r.changed == (("holders", "b"),)
        assert count_b(NEW) == cert.answer          # sound, and conservative

    def test_a_deleted_key_invalidates(self):
        cert = certify(count_a, OLD)
        r = revalidate(cert, {k: v for k, v in digest_all(NEW).items()
                              if k != ("holders", "a")})
        assert not r.valid

    def test_a_key_appearing_where_absence_was_read_invalidates(self):
        cert = certify(count_missing, OLD)
        grown = dict(NEW) | {("holders", "zz"): frozenset({"f9"})}
        assert not revalidate(cert, digest_all(grown)).valid

    def test_a_set_that_lost_and_regained_a_member_digests_equal(self):
        cert = certify(count_a, OLD)
        churned = dict(OLD) | {("holders", "a"): frozenset({"f2", "f1"})}
        assert revalidate(cert, digest_all(churned)).valid


class TestChangedKeys:
    def test_the_delta_is_symmetric_over_additions_and_deletions(self):
        assert changed_keys(OLD, NEW) == {("holders", "b")}
        assert changed_keys(NEW, OLD) == {("holders", "b")}

    def test_an_added_key_is_in_the_delta(self):
        grown = dict(OLD) | {("holders", "c"): frozenset({"f1"})}
        assert changed_keys(OLD, grown) == {("holders", "c")}


class TestWorth:
    def test_a_certificate_carries_the_cost_of_the_thing_it_replaces(self):
        # Without compute_ns the certificate cannot be priced, and an unpriced
        # certificate reads as a saving whatever it cost.
        cert = certify(count_a, OLD)
        assert cert.compute_ns > 0
        r = revalidate(cert, digest_all(NEW))
        assert r.speedup_over(cert.compute_ns) >= 0.0

    def test_size_and_keys_agree(self):
        cert = certify(lambda s: count_a(s) + count_b(s), OLD)
        assert cert.size == 2 == len(cert.keys)

    def test_a_certificate_serialises_without_the_values(self):
        d = Certificate(answer=7, digests={("holders", "a"): 1}).to_dict()
        assert d["answer"] == 7 and d["size"] == 1
        assert d["keys"] == ["('holders', 'a')"]


class TestRecordingStore:
    def test_contains_is_a_read(self):
        rec = RecordingStore(OLD)
        assert ("holders", "a") in rec
        assert ("holders", "zz") not in rec
        assert set(rec.read) == {("holders", "a"), ("holders", "zz")}

    def test_getitem_raises_for_a_miss_and_still_records_it(self):
        rec = RecordingStore(OLD)
        with pytest.raises(KeyError):
            rec[("holders", "zz")]
        assert rec.read[("holders", "zz")] is MISSING
