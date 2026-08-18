"""Aligning SEC filers to GLEIF legal entities, and keeping the alternatives.

The four real-data tasks before this one were each a single source. This is the
first that crosses two, which is the case the federation layer exists for, and
the question it answers is architectural rather than about accuracy:

**Does "align, never merge" earn its complexity, or would last-writer-wins have
been fine?**

The two sources share no identifier — ``kg:sec:cik:*`` and ``kg:lei:*`` are
disjoint namespaces — so the join has to go through names, which is exactly what
:class:`~symbolic_ai_core.world.claim.Alignment` calls uncertain knowledge. The
canonical key comes from the fitted normaliser in :mod:`.company_key`, which
reaches 0.9998 held out, so the ambiguity measured here is a property of the
*names*, not of a weak normaliser.

The measured answer is that ambiguity is common enough to matter: 14.7% of
matched filers have more than one GLEIF candidate, one has 35, and 51.3% of the
ambiguous ones span more than one country. A merge picks one silently.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from symbolic_ai_core.world import Alignment

__all__ = ["Candidate", "AlignmentResult", "build_name_index", "align_filers",
           "alignments_for", "ambiguity_report"]


@dataclass(frozen=True)
class Candidate:
    """One GLEIF entity a filer's name could refer to."""

    entity: str
    country: str = ""


@dataclass(frozen=True)
class AlignmentResult:
    """Every candidate, never one. The plural is the point."""

    filer: str
    key: str
    candidates: tuple[Candidate, ...]

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1

    @property
    def countries(self) -> frozenset[str]:
        return frozenset(c.country for c in self.candidates if c.country)

    @property
    def crosses_jurisdictions(self) -> bool:
        return len(self.countries) > 1

    def confidence(self) -> float:
        """One over the number of candidates.

        Deliberately crude and deliberately *not* 1.0 for a single candidate
        chain of reasoning — it encodes "this name matched n things" and
        nothing else. A better estimator would use the country, the entity
        type and the filing history; there is none of that here, and inventing
        a calibrated-looking number from a name match would be worse than an
        obviously coarse one.
        """
        return 1.0 / len(self.candidates) if self.candidates else 0.0


def build_name_index(base: Path, key_of: Callable[[str], str], *,
                     stem: str = "lei2_entities"
                     ) -> dict[str, list[Candidate]]:
    """Canonical key -> every GLEIF entity whose name normalises to it."""
    import pyarrow.parquet as pq

    index: dict[str, list[Candidate]] = collections.defaultdict(list)
    for f in sorted(base.rglob(f"{stem}*.parquet")):
        pf = pq.ParquetFile(f)
        if not {"id", "label", "body"} <= set(pf.schema_arrow.names):
            continue
        for batch in pf.iter_batches(columns=["id", "label", "body"]):
            for row in batch.to_pylist():
                index[key_of(row["label"] or "")].append(
                    Candidate(entity=row["id"], country=(row["body"] or "")))
    return dict(index)


def align_filers(keys: Mapping[str, str],
                 index: Mapping[str, Sequence[Candidate]]
                 ) -> dict[str, AlignmentResult]:
    """Match filers to candidates. Unmatched filers are simply absent.

    An unmatched filer is **not** an alignment to nothing; it is the absence of
    evidence, and manufacturing a null alignment would put a claim in the world
    that no source made.
    """
    out = {}
    for filer, key in keys.items():
        cands = index.get(key)
        if cands:
            out[filer] = AlignmentResult(filer=filer, key=key,
                                         candidates=tuple(cands))
    return out


def alignments_for(result: AlignmentResult, *, method: str = "canonical-name"
                   ) -> tuple[Alignment, ...]:
    """Every candidate as its own ``Alignment`` claim.

    The world IR has no way to say "one of these", and that is correct: several
    ``possibly_same`` claims about the same left-hand side *are* the
    disjunction, and a kernel that later learns the jurisdiction can refute the
    ones that do not fit without anything having been destroyed first.
    """
    conf = result.confidence()
    return tuple(
        Alignment(left=result.filer, right=c.entity, relation="possibly_same",
                  confidence=conf, method=method,
                  evidence=(f"canonical key {result.key!r}",)
                  + ((f"country {c.country}",) if c.country else ()))
        for c in result.candidates)


def ambiguity_report(results: Mapping[str, AlignmentResult]
                     ) -> dict[str, float | int]:
    """The numbers that decide whether alignment-not-merge is load-bearing."""
    n = len(results)
    amb = [r for r in results.values() if r.ambiguous]
    sizes = collections.Counter(len(r.candidates) for r in results.values())
    return {
        "matched": n,
        "ambiguous": len(amb),
        "ambiguous_rate": len(amb) / n if n else 0.0,
        "cross_jurisdiction": sum(1 for r in amb if r.crosses_jurisdictions),
        "max_candidates": max(sizes) if sizes else 0,
    }
