"""Where the knowledge graph came from, as data a test can assert against.

Same rules as ``symbolic_ai_data/_vendor.py``: the content is somebody else's,
the provenance lives in a module rather than a README so it is checkable, and
nothing here reaches the network at import or at generation time.

The one difference from that precedent is worth stating plainly rather than
glossing. ``symbolic_ai_data`` is a **verbatim file-for-file copy**; this is a
**deterministic projection** of a verbatim upstream artefact. Two hashes carry
the claim instead of one:

* :data:`UPSTREAM_SHA256` pins the bytes ``scripts/build_wordnet_kg.py``
  downloads and refuses to parse anything else;
* :data:`GRAPH_SHA256` pins the bytes that script wrote, which are the ones
  committed here.

``tests/test_kg_vendor.py`` checks the second on every run and the first only
when the zip happens to be on the machine, because a test that needs the network
is a test that fails for reasons unrelated to its subject — see
``notes/lessons/2026-08-14-a-sandboxed-test-reports-environment-faults-under-its-own-name.md``.

Why not vendor the zip itself: 10.8 MB, of which the projection keeps under 3%,
and the rest is glosses and sense keys nothing here reads. Why not download at
runtime: a curriculum that cannot generate offline is not reproducible, and
``symbolic_ai_core/data/langdb.py`` records what happens when a data path can go
inert without saying so — 58 languages were unreachable and every published
number was measured on seven because a file was absent rather than because seven
was the design.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["ROOT", "DATA", "UPSTREAM_URL", "UPSTREAM_SHA256", "GRAPH_PATH",
           "GRAPH_SHA256", "LICENSE_PATH", "SELECTION", "RELEASE", "LICENSE_NAME"]

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

RELEASE = "WordNet 3.0"
LICENSE_NAME = "WordNet 3.0 License (Princeton University)"

#: Princeton WordNet 3.0 as redistributed by the NLTK project. The NLTK
#: redistribution is used rather than princeton.edu because it is a single
#: immutable file under a stable URL with the license inside it.
UPSTREAM_URL = ("https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/"
                "packages/corpora/wordnet.zip")

#: sha256 of that zip, 10,775,600 bytes, taken 2026-08-14.
UPSTREAM_SHA256 = "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"

GRAPH_PATH = DATA / "wordnet30-physical.json.gz"
LICENSE_PATH = DATA / "LICENSE.wordnet"

#: sha256 of the committed projection. Filled in by the builder; asserted by
#: ``tests/test_kg_vendor.py``.
GRAPH_SHA256 = "8b456c5de1275195cd0e1b90f7adc9dd740616eec1eb78b05cdf5fecc967a99a"

#: The selection rule, in one string, so it travels inside the artefact.
SELECTION = (
    "nouns in the ten physical lexicographer files with a single-word lowercase "
    "lemma and SemCor tag count >= 1; verbs in the seven physical lexicographer "
    "files under the same rule, with their sentence frames; adjectives carrying "
    "an attribute pointer plus one hop of similar-to and antonym; the noun side "
    "of every attribute pointer; all of it closed under hypernymy"
)
