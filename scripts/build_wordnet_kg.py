"""Build the vendored WordNet projection under ``symbolic_ai_kg/data/``.

This is the *only* thing in the repo that touches the network, it is never run
at import or at generation time, and its output is committed. Run it to
reproduce the vendored artefact; ``tests/test_kg_vendor.py`` asserts the
committed bytes are what this script produces.

    uv run python scripts/build_wordnet_kg.py

Provenance
----------

Upstream is Princeton WordNet 3.0 as redistributed by the NLTK project
(``nltk_data/packages/corpora/wordnet.zip``). The zip's sha256 is pinned in
:mod:`symbolic_ai_kg._vendor` and checked here before a byte of it is parsed, so
"the graph moved" cannot happen quietly. The WordNet 3.0 license permits
redistribution with the copyright notice attached; the notice is copied verbatim
into ``symbolic_ai_kg/data/LICENSE.wordnet``.

Why a projection and not the whole zip
--------------------------------------

10.8 MB compressed, 35 MB unpacked, and 90% of it is glosses, sense keys and
morphological exceptions this repo never reads. The precedent in
``symbolic_ai_data/_vendor.py`` is to leave a 22 MB build artefact out of git;
the precedent in ``symbolic_ai_core/data/langdb.py`` is that a large blob lives
outside the tree and the code path goes inert without it. Neither works here,
because a curriculum that cannot generate without an uncommitted download is not
a curriculum. So: a **deterministic projection**, small enough to commit, whose
selection rule is stated below and whose inputs and outputs both carry a pinned
sha256. The bytes are still Princeton's; what this repo chose is which subset,
and that choice is written down rather than embedded in a build.

The selection rule, and why each clause is somebody else's decision
-------------------------------------------------------------------

* **Nouns** whose lexicographer file is one of the ten *physical* ones
  (``noun.animal``, ``noun.artifact``, ``noun.body``, ``noun.food``,
  ``noun.location``, ``noun.object``, ``noun.person``, ``noun.plant``,
  ``noun.shape``, ``noun.substance``), that have at least one single-word
  lowercase lemma, and that are **attested at least once in SemCor**
  (``index.sense`` tag count >= 1). Every clause is Princeton's: the lexnames
  are theirs, the lemmas are theirs, and SemCor is their own hand-tagged corpus,
  so "common enough to be worth having" is not a judgement made here.
* **Verbs** in the seven physical lexicographer files, same lemma and attestation
  rules, carrying their **sentence frames** — which is where the selectional
  restriction lives: frame 1 is "Something ----s" and frame 2 is
  "Somebody ----s", so WordNet already says which verbs take an animate subject.
* **Adjectives** that carry an ``=`` attribute pointer, plus their ``&``
  similar-to satellites and ``!`` antonyms. The attribute pointer is what makes
  an adjective a *value of a dimension* — ``heavy`` is a value of ``weight`` —
  which is the only way a graph can say two adjectives are mutually exclusive.
* Everything above is closed under ``isa`` (hypernym, ``@`` and ``@i``) so the
  taxonomy reaches its roots. The closure is not a choice either.

The output is sorted at every level and written with a fixed JSON separator, so
re-running this script on the same zip reproduces the file byte for byte.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from symbolic_ai_kg import _vendor  # noqa: E402

PHYS_NOUN = ("noun.animal", "noun.artifact", "noun.body", "noun.food",
             "noun.location", "noun.object", "noun.person", "noun.plant",
             "noun.shape", "noun.substance")
PHYS_VERB = ("verb.body", "verb.change", "verb.consumption", "verb.contact",
             "verb.creation", "verb.motion", "verb.perception")

#: WNDB pointer symbol -> the edge name used in the projection. Direction is
#: source -> target exactly as WordNet writes it.
NOUN_PTRS = {"@": "isa", "@i": "isa", "%p": "part", "%s": "substance",
             "%m": "member"}
VERB_PTRS = {"@": "isa"}
ADJ_PTRS = {"=": "attr", "&": "similar", "!": "antonym"}


def fetch(url: str, cache: Path) -> bytes:
    if cache.exists():
        return cache.read_bytes()
    with urllib.request.urlopen(url, timeout=120) as r:      # noqa: S310
        blob = r.read()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(blob)
    return blob


def _lines(z: zipfile.ZipFile, name: str):
    for ln in z.read("wordnet/" + name).decode("utf-8", "replace").splitlines():
        if ln.startswith("  ") or not ln.strip():
            continue
        yield ln


def parse_data(z: zipfile.ZipFile, pos: str, lexnames: dict[int, str]) -> dict:
    """One WNDB data file, as ``offset -> {lex, words, ptrs, frames}``."""
    out = {}
    for ln in _lines(z, "data." + pos):
        head, _, _gloss = ln.partition(" | ")
        f = head.split()
        off, lexnum = f[0], int(f[1])
        wcnt = int(f[3], 16)
        words = [f[4 + 2 * i] for i in range(wcnt)]
        i = 4 + 2 * wcnt
        pcnt = int(f[i]); i += 1
        ptrs = []
        for _ in range(pcnt):
            ptrs.append((f[i], f[i + 1], f[i + 2])); i += 4
        frames = []
        if pos == "verb" and i < len(f):
            fcnt = int(f[i]); i += 1
            for _ in range(fcnt):
                frames.append(int(f[i + 1])); i += 3
        out[off] = {"lex": lexnames[lexnum], "words": words, "ptrs": ptrs,
                    "frames": sorted(set(frames))}
    return out


def tag_counts(z: zipfile.ZipFile) -> collections.Counter:
    """SemCor attestation per (pos-digit, offset), summed over sense keys."""
    cnt: collections.Counter = collections.Counter()
    for ln in _lines(z, "index.sense"):
        f = ln.split()
        cnt[(f[0].split("%")[1][0], f[1])] += int(f[3])
    return cnt


def single_word(words):
    return sorted({w for w in words if w.isalpha() and w.islower()})


def build(blob: bytes) -> dict:
    z = zipfile.ZipFile(__import__("io").BytesIO(blob))
    lexnames = {int(a.split("\t")[0]): a.split("\t")[1] for a in _lines(z, "lexnames")}
    N = parse_data(z, "noun", lexnames)
    V = parse_data(z, "verb", lexnames)
    A = parse_data(z, "adj", lexnames)
    cnt = tag_counts(z)

    keep: set[tuple[str, str]] = set()          # (pos, offset)
    for off, d in N.items():
        if d["lex"] in PHYS_NOUN and single_word(d["words"]) and cnt[("1", off)] >= 1:
            keep.add(("n", off))
    for off, d in V.items():
        if d["lex"] in PHYS_VERB and single_word(d["words"]) and cnt[("2", off)] >= 1:
            keep.add(("v", off))
    # adjectives: attribute-bearing heads, then one hop of similar-to and antonym
    adj_seed = {off for off, d in A.items()
                if any(p[0] == "=" for p in d["ptrs"]) and single_word(d["words"])}
    adj = set(adj_seed)
    for off in sorted(adj_seed):
        for sym, tgt, tpos in A[off]["ptrs"]:
            if sym in ("&", "!") and tpos in ("a", "s") and tgt in A \
                    and single_word(A[tgt]["words"]):
                adj.add(tgt)
    keep |= {("a", off) for off in adj}
    # the noun side of every attribute pointer, so a dimension has a name
    for off in sorted(adj):
        for sym, tgt, tpos in A[off]["ptrs"]:
            if sym == "=" and tpos == "n" and tgt in N:
                keep.add(("n", tgt))
    # the target of every meronym pointer leaving a kept noun. Without this the
    # `part` and `substance` relations are almost empty, because a beak and a
    # sheet of tin are rarely SemCor-attested while the things that have them
    # are. The attestation rule is about which *concepts* the curriculum draws;
    # a concept's parts arrive because the concept did, which is the graph's
    # decision rather than this repo's.
    for pos, off in sorted(keep):
        if pos != "n":
            continue
        for sym, tgt, tpos in N[off]["ptrs"]:
            if sym in ("%p", "%s", "%m") and tpos == "n" and tgt in N \
                    and single_word(N[tgt]["words"]):
                keep.add(("n", tgt))

    # close under isa
    tables = {"n": N, "v": V, "a": A}
    frontier = sorted(keep)
    while frontier:
        nxt = []
        for pos, off in frontier:
            for sym, tgt, tpos in tables[pos][off]["ptrs"]:
                if sym in ("@", "@i") and tpos in ("n", "v") and (tpos, tgt) not in keep:
                    keep.add((tpos, tgt)); nxt.append((tpos, tgt))
        frontier = sorted(nxt)

    ids = sorted(f"{p}{o}" for p, o in keep)
    index = {k: i for i, k in enumerate(ids)}
    nodes = []
    for k in ids:
        pos, off = k[0], k[1:]
        d = tables[pos][off]
        # Selection required a single-word lemma; the hypernym closure does not,
        # so `physical_entity` and `bird_of_prey` arrive with none. Their raw
        # lemmas are kept rather than dropped: a node with no name cannot be
        # printed, and an unnamed hole in the middle of a taxonomy is worse than
        # an underscore.
        w = single_word(d["words"]) or sorted({x.lower() for x in d["words"]})
        nodes.append({"i": k, "p": pos, "x": d["lex"], "w": w})

    ptr_map = {"n": NOUN_PTRS, "v": VERB_PTRS, "a": ADJ_PTRS}
    edges: dict[str, set] = collections.defaultdict(set)
    for k in ids:
        pos, off = k[0], k[1:]
        for sym, tgt, tpos in tables[pos][off]["ptrs"]:
            rel = ptr_map[pos].get(sym)
            if rel is None:
                continue
            tk = ("s" if tpos == "s" else tpos) + tgt
            tk = ("a" + tgt) if tpos in ("a", "s") else (tpos + tgt)
            if tk in index:
                edges[rel].add((index[k], index[tk]))
    frames = {str(index[k]): tables["v"][k[1:]]["frames"]
              for k in ids if k[0] == "v" and tables["v"][k[1:]]["frames"]}

    return {
        "schema": 1,
        "name": "wordnet30-physical",
        "source": {"url": _vendor.UPSTREAM_URL, "sha256": _vendor.UPSTREAM_SHA256,
                   "release": "WordNet 3.0", "license": "WordNet 3.0 License"},
        "selection": _vendor.SELECTION,
        "nodes": nodes,
        "edges": {rel: sorted(map(list, e)) for rel, e in sorted(edges.items())},
        "frames": dict(sorted(frames.items(), key=lambda kv: int(kv[0]))),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cache", default="/tmp/wordnet.zip")
    p.add_argument("--out", default=str(_vendor.GRAPH_PATH))
    p.add_argument("--license-out", default=str(_vendor.LICENSE_PATH))
    args = p.parse_args(argv)

    blob = fetch(_vendor.UPSTREAM_URL, Path(args.cache))
    got = hashlib.sha256(blob).hexdigest()
    if got != _vendor.UPSTREAM_SHA256:
        print(f"upstream sha256 {got} != pinned {_vendor.UPSTREAM_SHA256}", file=sys.stderr)
        return 1
    z = zipfile.ZipFile(__import__("io").BytesIO(blob))
    Path(args.license_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.license_out).write_bytes(z.read("wordnet/LICENSE"))

    kg = build(blob)
    payload = json.dumps(kg, sort_keys=False, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    with gzip.GzipFile(args.out, "wb", compresslevel=9, mtime=0) as f:
        f.write(payload)
    print(f"{args.out}: {len(kg['nodes'])} nodes, "
          + ", ".join(f"{r} {len(e)}" for r, e in kg["edges"].items())
          + f", frames on {len(kg['frames'])}")
    print(f"raw json {len(payload)} B, gz {Path(args.out).stat().st_size} B")
    print(f"artefact sha256 {hashlib.sha256(Path(args.out).read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
