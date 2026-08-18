"""The aggregate that reads every conflict, and is answerable anyway.

Scoped enumeration prices a query at the conflicts it reads. That is a cure for
a *local* query over a wide mixture and no cure at all for a global one: "how
many of the SEC filers we aligned to GLEIF are US-domiciled" reads every
ambiguous alignment there is, so `2^k` is not an artefact of enumerating too
much — it is the true size of the answer's dependency.

It is still answerable. The count is a sum of independent per-filer terms, so
the world that minimises it minimises every term, found filer by filer in
linear time, and each bound is **attained** by the assignment returned with it.

The mixture is the one the alignment work already measured and never consumed:
`kg:sec:cik:*` and `kg:lei:*` share no identifier, so the join runs through
canonical names and 14.7% of matched filers get more than one GLEIF candidate.
Country comes from GLEIF's own `body` column.
"""

from __future__ import annotations

import collections
import time
from pathlib import Path

import pyarrow.parquet as pq

from symbolic_ai_core.runtime.ambiguity import (Alternatives,
                                                AmbiguityExplosion,
                                                additive_bounds,
                                                possible_answers,
                                                possible_answers_scoped)
from symbolic_ai_tasks.company_key import (fit_strip_set, load_task,
                                           predict_fitted, slugify)
from symbolic_ai_tasks.cross_source_alignment import (Candidate,
                                                      AlignmentResult,
                                                      ambiguity_report)

SEC = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15")
GLEIF = Path("data/sources/gleif/commandagi-r2-2026-08-15/gleif/"
             "lei2_entities_p0.parquet")
PREDICATE = "core.aligned_entity"


def key_with(strip: frozenset[str], name: str) -> str:
    """The fitted canonical key, applied to a raw name from either source."""
    parts = slugify(name).split("-")
    kept = [p for j, p in enumerate(parts) if j == 0 or p not in strip]
    return "-".join(kept) if kept else "-".join(parts)


def gleif_candidates(strip: frozenset[str], wanted: set[str]
                     ) -> dict[str, list[Candidate]]:
    """GLEIF entities whose canonical name is one a filer asked for.

    Filtered to ``wanted`` rather than indexing all 3.35M entities: the
    alignment only ever asks about 8,021 keys, and the unfiltered index is a
    gigabyte of dictionary to answer the same questions.
    """
    index: dict[str, list[Candidate]] = collections.defaultdict(list)
    pf = pq.ParquetFile(GLEIF)
    for batch in pf.iter_batches(columns=["id", "label", "body"]):
        for row in batch.to_pylist():
            k = key_with(strip, row["label"] or "")
            if k in wanted:
                index[k].append(Candidate(entity=row["id"],
                                          country=(row["body"] or "")))
    return dict(index)


def main() -> None:
    t0 = time.perf_counter()
    task = load_task(SEC)
    strip = fit_strip_set(task, task.ids)
    keys = predict_fitted(task, strip)
    index = gleif_candidates(strip, set(keys.values()))
    print(f"{len(task.ids):,} SEC filers, {len(index):,} canonical keys matched "
          f"in GLEIF, in {time.perf_counter()-t0:.1f}s")

    results = {f: AlignmentResult(filer=f, key=k, candidates=tuple(index[k]))
               for f, k in keys.items() if k in index}
    print("  " + str(ambiguity_report(results)))

    ambiguous = {f: r for f, r in results.items() if r.ambiguous}
    settled = {f: r for f, r in results.items() if not r.ambiguous}
    alts = Alternatives({(PREDICATE, f): tuple(c.entity for c in r.candidates)
                         for f, r in ambiguous.items()})
    country = {c.entity: c.country for r in results.values()
               for c in r.candidates}
    print(f"  mixture: {len(alts.choices):,} ambiguous alignments, "
          f"2^{len(alts.choices):,} worlds at 2 candidates each and more above")

    base = sum(1 for r in settled.values()
               if r.candidates[0].country == "US")
    print(f"\n=== 'how many aligned filers are US-domiciled?' ===")
    print(f"  filers whose alignment is unambiguous: {len(settled):,} "
          f"({base:,} of them US)")
    for name, fn in (("full enumeration", possible_answers),
                     ("scoped enumeration", possible_answers_scoped)):
        try:
            fn(lambda a: sum(country[v] == "US" for v in a.values()), alts)
            print(f"  {name}: DID NOT REFUSE -- unexpected")
        except AmbiguityExplosion as exc:
            named = (f"naming the {len(exc.read):,} conflicts the query "
                     "depends on" if exc.read else
                     "on the whole world's product, which names nothing")
            print(f"  {name}: refused, {named}")

    t1 = time.perf_counter()
    b = additive_bounds(alts, lambda s, v: float(country[v] == "US"),
                        base=float(base))
    wall = time.perf_counter() - t1
    print(f"  additive bounds: [{b.low:.0f}, {b.high:.0f}], width "
          f"{b.width:.0f}, in {wall*1000:.1f}ms")
    print(f"  ambiguous alignments that move the answer at all: "
          f"{len(b.width_by_subject):,} of {len(alts.choices):,}")

    print("\n=== the anchor: bounds against enumeration where it can run ===")
    for k in (8, 12):
        small = Alternatives(dict(sorted(alts.choices.items(), key=repr)[:k]))
        full = possible_answers(
            lambda a: sum(country[v] == "US" for v in a.values()), small,
            max_worlds=2 ** 16)
        sb = additive_bounds(small, lambda s, v: float(country[v] == "US"))
        print(f"  {k} conflicts, {full.worlds:,} worlds: enumerated "
              f"[{min(full.answers)}, {max(full.answers)}] vs bounds "
              f"[{sb.low:.0f}, {sb.high:.0f}] -- "
              f"{'exact' if (sb.low, sb.high) == (min(full.answers), max(full.answers)) else 'DISAGREE'}")

    print("\n=== the per-filer query, which scoping does answer ===")
    t2 = time.perf_counter()
    undetermined = 0
    for f in results:
        got = possible_answers_scoped(
            lambda a, f=f: country[a[(PREDICATE, f)]]
            if (PREDICATE, f) in a else results[f].candidates[0].country, alts)
        undetermined += got.ambiguous
    wall = time.perf_counter() - t2
    print(f"  'which country is this filer's entity in?' over {len(results):,} "
          f"filers in {wall:.1f}s: {undetermined:,} undetermined "
          f"({undetermined/len(results)*100:.1f}%)")
    print(f"  -- against {len(ambiguous):,} ambiguous alignments: the gap is "
          f"the filers whose candidates all agree on a country")


if __name__ == "__main__":
    main()
