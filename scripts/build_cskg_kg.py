"""Build the vendored CSKG projection under ``symbolic_ai_kg/data/``.

    uv run --with pyarrow python scripts/build_cskg_kg.py \
        --parquet ~/Downloads/kg/cskg/cskg_full_p0.parquet

Same contract as ``scripts/build_wordnet_kg.py``: a **deterministic projection**
of a verbatim upstream artefact, whose input and output both carry a pinned
sha256, committed so that nothing reaches the network or a 14 GB local corpus at
generation time. ``pyarrow`` is a build-time dependency of this script only and
deliberately not a dependency of the package — the committed artefact is plain
gzipped JSON, read by :mod:`symbolic_ai_kg.graph` with the standard library.

Why a second graph at all
-------------------------

The WordNet projection is a **lexical** resource and the seam needed a
*selectional* one. The gap is visible in one number: WordNet contributes 1,408
``part`` and 156 ``substance`` edges, which is what the per-object attribute
constraint draws from, so an object's "colour" is bound to one of its kind's
**parts** — ``beak``, ``wing`` — which is not what the slot means and is a
constraint the graph is not really making. CSKG carries 46k property assertions
(``/r/HasProperty`` and Webchild's ``mw:MayHaveProperty``), 22k ``/r/PartOf``,
25k ``/r/CapableOf``, and 139k ``/r/IsA`` over English concepts. The slot the
decision note is about — *once ``o0`` is a penguin, what it can be coloured is
no longer a uniform draw* — is a relation this graph states and WordNet does not.

**And it did not work out**, which belongs at the top rather than in a note
somebody has to find. The 30,513 property edges this script keeps sit on 2,490
of its 30,315 nodes, so the per-object constraint fires on 17% of scene objects
against WordNet's 53%; and ConceptNet's ``IsA`` is flat enough that the families
the binder anchors are *(interior, crocheting, snout, crusade, conk,
salesmanship)*. No curriculum arm is registered for this graph. The artefact is
committed anyway because the join that would work — WordNet's taxonomy with
CSKG's properties — needs it. See
``notes/decisions/2026-08-15-the-commonsense-arms-are-built-and-not-run.md``.

Provenance, including the part that is weaker than WordNet's
------------------------------------------------------------

Upstream is **CSKG** (Ilievski, Szekely & Zhang, *CSKG: The CommonSense
Knowledge Graph*, ESWC 2021), which consolidates ConceptNet 5.7, WordNet 3.0,
ATOMIC, Visual Genome, FrameNet, Roget and Wikidata-CS under CC BY-SA 4.0. What
is hashed here is not the Zenodo tarball but a **local re-export** of it
(``cskg/cskg_full_p0.parquet``, 28,838,905 bytes) taken from a private R2
bucket, because that is the artefact that was actually read. That is a real
weakness relative to the WordNet builder, whose upstream is a public immutable
URL, and it is stated rather than glossed: a reader cannot re-fetch this input
from the pinned URL. What they *can* do is check the committed output's sha256,
and check that this script reproduces it from the same parquet.

The selection rule
------------------

* **Lemmas.** ConceptNet ids of the form ``/c/en/<lemma>`` or
  ``/c/en/<lemma>/<pos>``; a lemma is kept only if it is a single lowercase
  alphabetic word, the same rule the WordNet projection uses, so the two graphs
  put the same *kind* of symbol into an episode and an arm difference is not a
  difference in how many underscores a label has.
* **Collapse by lemma, not by sense.** ConceptNet states some edges on
  ``/c/en/red`` and some on ``/c/en/red/a``; those denote one word and this repo
  prints one string for both, so keeping them apart would make two graph nodes
  that an episode cannot tell apart. Part of speech is then inferred from how
  the graph uses the lemma (see ``POS`` below), which is a decision made *here*.
* **Relations**, mapped onto the projection's own names so that
  :mod:`symbolic_ai_kg.graph` needs no CSKG-specific query:

  =====================  ===========  =========================================
  CSKG relation          projection   direction
  =====================  ===========  =========================================
  ``/r/IsA``             ``isa``      hyponym -> hypernym, as WordNet writes it
  ``/r/HasA``            ``part``     whole -> part
  ``/r/PartOf``          ``part``     reversed, so it is also whole -> part
  ``/r/MadeOf``          ``substance``  whole -> substance
  ``/r/HasProperty``     ``property``   thing -> adjective
  ``mw:MayHaveProperty`` ``property``   thing -> adjective
  ``/r/SimilarTo``       ``similar``
  ``/r/Antonym``         ``antonym``
  ``/r/CapableOf``       ``can``      thing -> verb
  =====================  ===========  =========================================

  ``property`` and ``can`` are relations WordNet's projection does not have, so
  adding them cannot move a WordNet number: every WordNet query over them
  returns the empty tuple and the two arms already published stay bit-identical.
  ``/r/RelatedTo`` and ``/r/Synonym`` are **dropped** — 1.5M edges of "these two
  words co-occur", which would swamp the taxonomy and constrain nothing.
* **Closure.** Every kept node is closed under ``isa`` so the taxonomy reaches
  its roots, and a node is kept at all only if it takes part in at least one
  edge of a *selectional* relation (``isa``, ``part``, ``substance``,
  ``property``, ``can``) after the lemma filter.

The one judgement this repo makes, stated so it can be argued with
------------------------------------------------------------------

WordNet ships lexicographer files, so ``KnowledgeGraph.lex`` — which decides
animacy and which nodes are people, places and artifacts — is Princeton's
decision. **CSKG ships nothing equivalent.** The ``lex`` assigned here is
derived from the graph's own ``isa`` closure over a short list of root lemmas
(:data:`LEX_ROOTS`): a node is ``noun.animal`` if the graph puts it under
``animal``, ``noun.person`` if under ``person``, and so on. The list is this
repo's; the ancestry is the graph's. It is printed by the builder so the sizes
of the resulting pools are auditable.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from symbolic_ai_kg import _vendor  # noqa: E402

#: CSKG relation -> (projection relation, reversed?).
REL_MAP: dict[str, tuple[str, bool]] = {
    "/r/IsA": ("isa", False),
    "/r/InstanceOf": ("isa", False),
    "/r/HasA": ("part", False),
    "/r/PartOf": ("part", True),
    "/r/MadeOf": ("substance", False),
    "/r/HasProperty": ("property", False),
    "mw:MayHaveProperty": ("property", False),
    "/r/SimilarTo": ("similar", False),
    "/r/Antonym": ("antonym", False),
    "/r/CapableOf": ("can", False),
}

#: Which relations make a node worth keeping. ``similar`` and ``antonym`` are
#: not in here: a node whose only edge is "is unlike something" constrains
#: nothing and would arrive with no taxonomy.
SELECTIONAL = ("isa", "part", "substance", "property", "can")

#: lemma -> lexname. A node inherits the first of these it sits under in the
#: graph's own ``isa`` closure, tried in this order. See the module docstring:
#: the list is this repo's judgement, the ancestry is CSKG's.
LEX_ROOTS: tuple[tuple[str, str], ...] = (
    ("person", "noun.person"), ("human", "noun.person"),
    ("animal", "noun.animal"), ("mammal", "noun.animal"),
    ("bird", "noun.animal"), ("fish", "noun.animal"),
    ("insect", "noun.animal"), ("plant", "noun.plant"),
    ("food", "noun.food"), ("body_part", "noun.body"),
    ("substance", "noun.substance"), ("material", "noun.substance"),
    ("place", "noun.location"), ("location", "noun.location"),
    ("area", "noun.location"), ("room", "noun.location"),
    ("building", "noun.location"), ("shape", "noun.shape"),
    ("artifact", "noun.artifact"), ("tool", "noun.artifact"),
    ("device", "noun.artifact"), ("container", "noun.artifact"),
    ("furniture", "noun.artifact"), ("vehicle", "noun.artifact"),
    ("machine", "noun.artifact"), ("instrument", "noun.artifact"),
    ("object", "noun.object"),
)

#: How many ``isa`` hops the lexname search may climb. A fitted parameter of the
#: data, so it is named rather than inline -- see
#: ``notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md``.
#: At the unbounded depth the first version used, 12,770 of 36,257 nodes filed
#: as ``noun.person``; the counts at 3 / 4 / 6 hops are printed by the builder.
LEX_DEPTH = 4

PREFIX = "kg:cskg:/c/en/"
LEMMA_RE = re.compile(r"^[a-z]+$")


def lemma_of(nid: str) -> tuple[str, str] | None:
    """``kg:cskg:/c/en/penguin/n`` -> ``("penguin", "n")``.

    The second element is ConceptNet's own part-of-speech tag and is ``""``
    when the id carries none. None if this is not a kept English lemma.
    """
    if not nid.startswith(PREFIX):
        return None
    parts = nid[len(PREFIX):].split("/")
    if not LEMMA_RE.match(parts[0]):
        return None
    tag = parts[1] if len(parts) > 1 and parts[1] in ("n", "v", "a", "r", "s") else ""
    return parts[0], tag


def read_edges(path: Path):
    """(source lemma, projection relation, target lemma) for every kept row.

    ``isa`` additionally requires **both endpoints to carry ConceptNet's own
    part-of-speech tag**, which drops 46,089 raw `/r/IsA` assertions to 34,257.
    That filter is not cosmetic and it is not this repo's judgement about which
    facts are true: an untagged `/c/en/x` node is the undisambiguated string,
    and its `IsA` edges are where ConceptNet's noise lives. Measured on the
    unfiltered version, the binder anchored families like *(debacle, coma,
    interjection, splinter, concertina, cripple)* — six "kinds" with nothing in
    common, which is a semantically **incoherent** neighbourhood dressed as a
    semantic one, and would have made the treatment arm a worse control than
    its own control.
    """
    import pyarrow.parquet as pq                                # noqa: PLC0415

    f = pq.ParquetFile(path)
    for i in range(f.metadata.num_row_groups):
        t = f.read_row_group(i, columns=["source_id", "kind", "target_id"])
        for s, k, d in zip(t["source_id"].to_pylist(), t["kind"].to_pylist(),
                           t["target_id"].to_pylist()):
            m = REL_MAP.get(k)
            if m is None:
                continue
            rel, rev = m
            sa, sb = lemma_of(s), lemma_of(d)
            if sa is None or sb is None or sa[0] == sb[0]:
                continue
            if rel == "isa" and not (sa[1] and sb[1]):
                continue
            a, b = sa[0], sb[0]
            yield (b, rel, a) if rev else (a, rel, b)


def build(path: Path) -> dict:
    raw: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for a, rel, b in read_edges(path):
        raw[rel].add((a, b))

    # keep only lemmas touched by a selectional relation, then close under isa
    keep: set[str] = set()
    for rel in SELECTIONAL:
        for a, b in raw.get(rel, ()):
            keep.add(a)
            keep.add(b)
    isa = {(a, b) for a, b in raw.get("isa", ()) if a in keep and b in keep}
    up: dict[str, set[str]] = collections.defaultdict(set)
    for a, b in isa:
        up[a].add(b)

    # part of speech, inferred from use: a lemma the graph gives properties to
    # or puts in a taxonomy is a noun; one asserted *as* a property is an
    # adjective; one asserted as a capability is a verb. Nouns win ties, because
    # every other slot in the binder wants nouns and a mislabelled noun costs a
    # candidate while a mislabelled adjective costs a whole slot.
    pos: dict[str, str] = {}
    adjs = {b for _a, b in raw.get("property", ())}
    verbs = {b for _a, b in raw.get("can", ())}
    nouns = ({a for a, _b in raw.get("property", ())}
             | {a for a, _b in raw.get("can", ())}
             | {x for pair in isa for x in pair}
             | {x for pair in raw.get("part", ()) for x in pair}
             | {x for pair in raw.get("substance", ()) for x in pair})
    for w in keep:
        pos[w] = "n" if w in nouns else ("a" if w in adjs else
                                         ("v" if w in verbs else "n"))

    # lexnames, from the graph's own ancestry over LEX_ROOTS
    rank = {w: i for i, (w, _x) in enumerate(LEX_ROOTS)}
    lexname = {w: x for w, x in LEX_ROOTS}

    def ancestors(w: str, limit: int = 24) -> set[str]:
        seen, frontier = set(), {w}
        for _ in range(limit):
            nxt = set()
            for m in frontier:
                for h in up.get(m, ()):
                    if h not in seen:
                        seen.add(h)
                        nxt.add(h)
            if not nxt:
                break
            frontier = nxt
        return seen

    def nearest_root(w: str, limit: int = LEX_DEPTH) -> str | None:
        """The closest ``LEX_ROOTS`` lemma above ``w``, ties by list order.

        *Closest*, not highest-priority-anywhere, and the difference is not
        cosmetic. CSKG's ``isa`` is a noisy DAG in which almost everything
        eventually reaches ``person`` through some occupation or role; taking
        the best root over the whole ancestor set filed 12,770 of 36,257 nodes
        as ``noun.person`` and made ``animate()`` true for most of the graph.
        Nearest-first with a depth cap files a node under the thing it is
        actually a kind of.
        """
        seen, frontier = {w}, [w]
        for _ in range(limit):
            here = [x for x in frontier if x in rank]
            if here:
                return min(here, key=lambda x: rank[x])
            nxt = []
            for m in frontier:
                for h in sorted(up.get(m, ())):
                    if h not in seen:
                        seen.add(h)
                        nxt.append(h)
            if not nxt:
                return None
            frontier = nxt
        return None

    lex: dict[str, str] = {}
    for w in sorted(keep):
        best = nearest_root(w)
        lex[w] = lexname[best] if best else ("adj.all" if pos[w] == "a" else
                                             "verb.all" if pos[w] == "v" else
                                             "noun.Tops")

    ids = sorted(keep)
    index = {w: i for i, w in enumerate(ids)}
    nodes = [{"i": w, "p": pos[w], "x": lex[w], "w": [w]} for w in ids]
    edges: dict[str, list] = {}
    for rel in sorted(raw):
        pairs = sorted({(index[a], index[b]) for a, b in raw[rel]
                        if a in index and b in index})
        if pairs:
            edges[rel] = [list(p) for p in pairs]

    # `frames` is WordNet's sentence-frame table, which is how `verbs_for`
    # decides whether a verb takes an animate subject. CSKG has no frames and
    # this repo is not inventing any: it derives the same distinction from the
    # graph's own `can` edges, giving a verb the animate frame set if most of
    # the things asserted capable of it are animate. A verb no animate thing is
    # capable of gets the inanimate set. Same interface, different evidence.
    from symbolic_ai_kg.graph import ANIMATE_FRAMES, INANIMATE_FRAMES

    subj: dict[str, list[str]] = collections.defaultdict(list)
    for a, b in raw.get("can", ()):
        if a in index and b in index:
            subj[b].append(a)
    animate_lex = ("noun.animal", "noun.person")
    frames: dict[str, list[int]] = {}
    for v, subs in subj.items():
        if pos[v] != "v":
            continue
        n_an = sum(1 for s in subs
                   if lex[s] in animate_lex
                   or any(lex[a] in animate_lex for a in ancestors(s)))
        want = ANIMATE_FRAMES if n_an * 2 >= len(subs) else INANIMATE_FRAMES
        frames[str(index[v])] = sorted(want)

    return {
        "schema": 1,
        "name": "cskg-commonsense",
        "source": {"url": _vendor.CSKG_UPSTREAM_URL,
                   "sha256": _vendor.CSKG_UPSTREAM_SHA256,
                   "release": _vendor.CSKG_RELEASE,
                   "license": _vendor.CSKG_LICENSE_NAME},
        "selection": _vendor.CSKG_SELECTION,
        # Nothing is inherited down this taxonomy. ConceptNet states its
        # assertions at the concept, and climbing turned six distinct kinds into
        # ~1,130 shared properties each. See `KnowledgeGraph.inherit`.
        "inherit": [],
        "nodes": nodes,
        "edges": edges,
        "frames": dict(sorted(frames.items(), key=lambda kv: int(kv[0]))),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--parquet", default=str(Path.home() /
                                            "Downloads/kg/cskg/cskg_full_p0.parquet"))
    p.add_argument("--out", default=str(_vendor.CSKG_GRAPH_PATH))
    args = p.parse_args(argv)

    src = Path(args.parquet).expanduser()
    got = hashlib.sha256(src.read_bytes()).hexdigest()
    if got != _vendor.CSKG_UPSTREAM_SHA256:
        print(f"upstream sha256 {got} != pinned {_vendor.CSKG_UPSTREAM_SHA256}",
              file=sys.stderr)
        return 1

    kg = build(src)
    payload = json.dumps(kg, sort_keys=False, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(args.out, "wb", compresslevel=9, mtime=0) as f:
        f.write(payload)
    print(f"{args.out}: {len(kg['nodes'])} nodes, "
          + ", ".join(f"{r} {len(e)}" for r, e in kg["edges"].items())
          + f", frames on {len(kg['frames'])}")
    lexc = collections.Counter(n["x"] for n in kg["nodes"])
    print("  lexnames: " + ", ".join(f"{k} {v}" for k, v in lexc.most_common()))
    posc = collections.Counter(n["p"] for n in kg["nodes"])
    print("  pos: " + ", ".join(f"{k} {v}" for k, v in posc.most_common()))
    print(f"raw json {len(payload)} B, gz {Path(args.out).stat().st_size} B")
    print(f"artefact sha256 {hashlib.sha256(Path(args.out).read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
