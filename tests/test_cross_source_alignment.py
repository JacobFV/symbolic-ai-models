"""Crossing two sources, and keeping every candidate."""

from __future__ import annotations

import pytest

from symbolic_ai_core.source import SourceRegistry, data_root
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task, slugify)
from symbolic_ai_tasks.cross_source_alignment import (AlignmentResult,
                                                      Candidate, align_filers,
                                                      alignments_for,
                                                      ambiguity_report,
                                                      build_name_index)


def _res(*cands: Candidate) -> AlignmentResult:
    return AlignmentResult(filer="kg:sec:cik:1", key="acme", candidates=cands)


class TestResultSemantics:
    def test_one_candidate_is_not_ambiguous(self):
        r = _res(Candidate("kg:lei:A", "US"))
        assert not r.ambiguous and r.confidence() == 1.0

    def test_confidence_is_one_over_the_candidate_count(self):
        r = _res(Candidate("kg:lei:A"), Candidate("kg:lei:B"),
                 Candidate("kg:lei:C"))
        assert r.confidence() == pytest.approx(1 / 3)

    def test_candidates_in_two_countries_cross_jurisdictions(self):
        r = _res(Candidate("kg:lei:A", "GB"), Candidate("kg:lei:B", "JP"))
        assert r.crosses_jurisdictions and r.countries == {"GB", "JP"}

    def test_a_blank_country_is_not_a_jurisdiction(self):
        """Missing can never become a value."""
        r = _res(Candidate("kg:lei:A", "GB"), Candidate("kg:lei:B", ""))
        assert not r.crosses_jurisdictions


class TestAlignmentClaims:
    def test_every_candidate_becomes_its_own_claim(self):
        """The world IR has no "one of these", and that is correct: several
        possibly_same claims about one left-hand side ARE the disjunction."""
        al = alignments_for(_res(Candidate("kg:lei:A", "GB"),
                                 Candidate("kg:lei:B", "JP")))
        assert len(al) == 2
        assert {a.right for a in al} == {"kg:lei:A", "kg:lei:B"}
        assert all(a.confidence == 0.5 for a in al)

    def test_the_evidence_names_the_key_that_matched(self):
        al = alignments_for(_res(Candidate("kg:lei:A", "GB")))
        assert any("acme" in e for e in al[0].evidence)
        assert any("GB" in e for e in al[0].evidence)

    def test_a_cross_vendor_prefix_alignment_is_now_legal(self):
        """Both ids begin `kg:`; before the namespace fix this raised."""
        al = alignments_for(_res(Candidate("kg:lei:A")))
        assert al[0].left.startswith("kg:sec:")


class TestUnmatched:
    def test_an_unmatched_filer_is_absent_not_aligned_to_nothing(self):
        """Absence of evidence is not a claim, and manufacturing a null
        alignment would put something in the world no source asserted."""
        out = align_filers({"f1": "nomatch"}, {"other": [Candidate("kg:lei:A")]})
        assert out == {}

    def test_the_report_handles_an_empty_match_set(self):
        assert ambiguity_report({})["ambiguous_rate"] == 0.0


@pytest.mark.skipif(not data_root().exists(), reason="snapshots not held here")
class TestAgainstBothSources:
    @staticmethod
    @pytest.fixture(scope="class")
    def aligned():
        reg = SourceRegistry()
        sec = next(s for s in reg.snapshots().values()
                   if s.source == "sec-edgar").resolve(data_root())
        gl = next(s for s in reg.snapshots().values()
                  if s.source == "gleif").resolve(data_root())
        task = load_task(sec)
        strip = fit_strip_set(task, task.ids)

        def key(name: str) -> str:
            parts = slugify(name).split("-")
            kept = [p for j, p in enumerate(parts)
                    if j == 0 or p not in strip]
            return "-".join(kept) if kept else "-".join(parts)

        index = build_name_index(gl, key)
        return task, align_filers({i: task.truth[i] for i in task.ids}, index)

    def test_about_half_the_filers_match_something(self, aligned):
        task, res = aligned
        assert len(res) / len(task.ids) == pytest.approx(0.508, abs=0.01)

    def test_ambiguity_is_common_enough_that_merging_would_be_wrong(self, aligned):
        """14.7%. The number that decides whether alignment-not-merge is
        load-bearing or ceremony."""
        rep = ambiguity_report(aligned[1])
        assert rep["ambiguous_rate"] == pytest.approx(0.1467, abs=0.005)
        assert rep["ambiguous"] == 598

    def test_half_the_ambiguous_matches_span_jurisdictions(self, aligned):
        rep = ambiguity_report(aligned[1])
        assert rep["cross_jurisdiction"] == 307

    def test_one_name_matches_thirty_five_entities(self, aligned):
        task, res = aligned
        worst = max(res.values(), key=lambda r: len(r.candidates))
        assert len(worst.candidates) == 35
        assert "HSBC" in task.labels[worst.filer]
        assert worst.crosses_jurisdictions
