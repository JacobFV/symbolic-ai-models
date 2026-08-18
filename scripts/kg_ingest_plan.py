"""Which staged directory belongs to which source, and what its streams are.

The mapping is written down rather than inferred because **the directory names
are the pipeline's, not the upstreams'**. ``appcite/``, ``cite/``, ``cpc/``,
``inventor/``, ``assignee/`` and ``wipo/`` are six directories of one probable
upstream; ``govspend/`` is one directory of four genuinely different ones. A
scan that guessed would produce a federation whose licence closure is wrong,
which is the direction that gets something published it should not have been.

Where the upstream is not established, the source card says ``unresolved`` and
the stream carries ``upstream_confidence: hypothesis`` with the evidence for the
guess (usually an id namespace observed in the parquet). That is an honest state
and is not a defect; inventing a provenance would be.
"""

from __future__ import annotations

import re
from pathlib import Path

STAGING = Path.home() / "Downloads" / "kg"

#: Every directory in this pull came from one R2 sync on this date, recorded in
#: the staging README. The acquisition is the same for all of them, so it is the
#: snapshot slug for all of them.
SLUG = "commandagi-r2-2026-08-15"
ACQUIRED_AT = "2026-08-15"

_PART = re.compile(r"_p\d+$")


def stream_by_dir(rel: str, *, depth: int = 2) -> str:
    """Stream id from the layout, truncated to ``depth`` directory components.

    Coarse on purpose. The alternative — one stream per file prefix — gives
    ``gharchive`` three hundred streams named after dates, and a stream id is
    supposed to be a *semantic channel* that survives from source through view
    to run, not a filename.
    """
    parts = Path(rel).parts
    if len(parts) == 1:
        return _PART.sub("", Path(parts[0]).stem)
    return "/".join(parts[:min(depth, len(parts) - 1)])


def _entry(source: str, dirs: list[str], *, fmt: str, layout: str = "pipeline_native",
           notes: str = "", depth: int = 2) -> dict:
    return {
        "source": source,
        "dirs": dirs,
        "snapshot_slug": SLUG,
        "snapshot_id": f"{source}@{SLUG}",
        "acquired": {
            "from": "r2://commandagi-kg-cold (and the ingest prefixes beside it)",
            "at": ACQUIRED_AT,
            "via": "commandagi KG ingest; staged to ~/Downloads/kg by dl-kg.py",
        },
        "format": fmt,
        "layout": layout,
        "notes": notes,
        "stream_of": lambda rel, _d=depth: stream_by_dir(rel, depth=_d),
    }


PLAN: list[dict] = [
    _entry("commandagi-kg", ["graph", "__r2_data_catalog", "d1", "test",
                             "README.md::_acquisition/README.md",
                             "dl-kg.py::_acquisition/dl-kg.py",
                             "INVENTORY.tsv::_acquisition/INVENTORY.tsv"],
           fmt="mixed", layout="source_native",
           notes="Three representations of one graph: the cold-tier NDJSON/parquet "
                 "export (graph/), the same tables as Iceberg (__r2_data_catalog/) "
                 "and the hot-tier D1 SQL dump (d1/). They are not three sources; "
                 "they are one source in three storage formats, and the manifest "
                 "says so rather than letting a later reader treat agreeing "
                 "counts across them as three independent confirmations. The "
                 "staging README, INVENTORY.tsv and dl-kg.py travel with them as "
                 "the acquisition record."),
    _entry("commandagi-kg-dev", ["_dev-bucket"], fmt="mixed",
           layout="source_native",
           notes="The dev stack's cold bucket. Kept apart from production "
                 "because a near-empty dev graph pooled with the real one is a "
                 "silent dilution of every count taken over the pair."),

    _entry("openalex", ["scholar/openalex"], fmt="parquet"),
    _entry("wikidata", ["entity/wikidata"], fmt="parquet"),
    _entry("geonames", ["geo/geonames"], fmt="parquet"),
    _entry("stackexchange", ["qa/stackexchange"], fmt="parquet"),
    _entry("gutenberg", ["lit/gutenberg"], fmt="parquet"),
    _entry("openflights", ["transport/openflights"], fmt="parquet"),
    _entry("cskg", ["cskg"], fmt="parquet"),
    _entry("gdelt", ["gdelt"], fmt="parquet"),
    _entry("gleif", ["gleif"], fmt="parquet"),
    _entry("gh-archive", ["gharchive"], fmt="parquet"),

    _entry("courtlistener", ["caselaw"], fmt="parquet",
           notes="Upstream unresolved. The id namespace observed in the parquet "
                 "is `kg:clop:`, which is consistent with CourtListener opinion "
                 "ids; that is a hypothesis and the source card records it as "
                 "one."),
    _entry("patentsview", ["appcite", "cite", "cpc", "inventor", "assignee",
                           "patents", "wipo"], fmt="parquet",
           notes="Seven staged directories, one probable upstream. The id "
                 "namespaces are `kg:patent:`, `kg:assignee:` and `kg:inventor:` "
                 "throughout, and the tables (citations, CPC classification, "
                 "inventor and assignee links, WIPO fields) match PatentsView's "
                 "published shape -- but the pull did not record an upstream "
                 "release, so the card says unresolved."),
    _entry("sec-edgar", ["entity/sec", "sec13f", "sec_fin", "sec_insider",
                         "finance"], fmt="parquet",
           notes="CIK-keyed filings: 13F holdings, insider transactions and "
                 "financial reports, plus the CIK-to-name bridge. `finance/` "
                 "holds a second cut of 13F and insider over a different date "
                 "window and is kept as its own stream rather than merged, "
                 "because two overlapping windows pooled without a marker "
                 "double-count the intersection."),

    _entry("usaspending", ["govspend/usaspending"], fmt="parquet"),
    _entry("fec", ["govspend/fec"], fmt="parquet"),
    _entry("cfpb", ["govspend/cfpb"], fmt="parquet"),
    _entry("senate-lda", ["govspend/lobbying"], fmt="parquet",
           notes="Lobbying disclosures. Upstream unresolved between the Senate "
                 "LDA filings and a redistributor of them."),
]
