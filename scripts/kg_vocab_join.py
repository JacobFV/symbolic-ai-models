"""Join the curriculum's words against the ingested graph's node labels.

This is the step that makes the corpus usable at all, and it had never been run:
the first normalisation pass threw the node tables away, leaving 1.2 billion
edges between opaque `kg:` identifiers. The curriculum's vocabulary is *words*,
so a label is the only join key between the two, and without one no lesson can
address a single node in this graph.

What it reports, in the order the question is actually asked
------------------------------------------------------------

1. **does the word find a labelled node at all?** — coverage, the number the
   earlier finding put at ~100% against the vendored WordNet projection;
2. **does it find one that is anchorable** (`is-a` / `instance-of`)?
3. **does it find one that is anchorable AND carries a determined attribute**
   (`has-property`, `capable-of`, the ATOMIC block, ...)?

(3) is the population that matters. `kg_derivable.py` measured it corpus-wide at
9,849 entities without ever asking whether any of them is a word the curriculum
says. This asks that.

**A label comes from two places, and missing the second would have been fatal.**
The obvious one is a `*.nodes.tsv.gz` table. But `cskg` — the source of
essentially every determined attribute in the corpus, and therefore of the whole
usable population — **ships no node table at all**. Its identifiers are
ConceptNet URIs, `kg:cskg:/c/en/adipose_tissue/n/wn/body`, which carry the lemma
in the id. Joining on node tables alone would have returned a near-zero usable
coverage that was an artefact of which sources happen to export a node file, and
it would have looked exactly like a finding. `label_from_id` handles that one
namespace explicitly and returns nothing for every other, because guessing a
label out of `kg:wikidata:Q42` is how this pipeline produced 19.3 M phantom
rejections the first time round.

Two matchers, reported apart
----------------------------

`exact` — the node's whole label, lowercased and whitespace-collapsed, equals the
word. `token` — any whitespace token of the label equals it, so "red" matches
"Red Sea". They are both defensible and they disagree, so both are printed;
picking the flattering one is the failure this repo has a lesson about.

Four controls, all of which can fail
------------------------------------

* **nonce** — `kg_coverage.py`'s `NONCE_VOCAB`: words the curriculum *invents*
  (`B_CONCEPT_NAMES`, `TYPE_NAMES`, ...), nonce by design because
  `lexical_novelty` is a declared difficulty axis. A matcher that scores these
  high is too permissive and every other number it produces is inflated.
* **anagram** — every curriculum word with its characters shuffled at a fixed
  seed. Same length, same alphabet, same word count, no meaning. This is the
  same-shape-but-meaningless control that has corrected four results here.
* **dict-uniform** — a uniform sample of `/usr/share/dict/american-english`, the
  same size as the curriculum vocabulary.
* **dict-lenmatched** — a sample matched to the curriculum's *length*
  distribution, since length correlates with frequency and frequency is the
  obvious confound.

**Neither dictionary control is frequency-matched, and the confound therefore has
an unknown sign** — a uniform dictionary draw is mostly rare words, which would
make the curriculum look better for a reason that has nothing to do with the
curriculum; but the curriculum also contains proper names and technical labels a
dictionary does not, which pushes the other way. The comparison that does not
depend on it is the **conditional**: given that a word matched some node at all,
how often is that node anchorable and determined? Both populations are then
conditioned on having a label in the graph, and if the conditional is flat across
vocabularies the bottleneck is a property of the graph rather than of the words.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kg_derivable import ANCHOR, DERIVE, _lines, inputs   # noqa: E402

DICT = Path("/usr/share/dict/american-english")

#: The one namespace whose identifiers carry their own lemma. Everything else
#: (`kg:wikidata:Q42`, `kg:geonames:2988507`, `kg:openalex:W123`) is opaque and
#: must come from a node table or not at all.
CSKG = "kg:cskg:/c/en/"
CSKG_B = CSKG.encode()


def norm(s: str) -> str:
    return " ".join(s.lower().split())


def label_from_id(ident: str) -> str | None:
    """ConceptNet URIs only. `kg:cskg:/c/en/adipose_tissue/n/wn/body` -> that
    lemma; the trailing segments are part of speech and WordNet domain, not part
    of the word."""
    if not ident.startswith(CSKG):
        return None
    lemma = ident[len(CSKG):].split("/", 1)[0]
    return norm(lemma.replace("_", " ")) or None


def curriculum_vocab() -> dict[str, set[str]]:
    """Two enumerations of the curriculum's words, because they disagree by 229.

    ``symbolic_ai_data.grammar.compile.curriculum_vocabulary()`` is the repo's
    own importable answer to "every English word the curriculum's generators can
    coin" — **423 words**, with ``classify()`` bucketing them noun / adj / verb /
    word / sym. It is the honest denominator and is the primary here.

    ``scripts/kg_coverage.py``'s four hand-written tables are a **194-word
    subset** of those 423. They are the set the published coverage finding
    actually measured — its "~100% of the curriculum's vocabulary" is 100% of
    the 69-word `strict` table — so they are carried unchanged for
    comparability, not as the inventory. Reporting only the 423 would make this
    incomparable to the record; reporting only the 194 would repeat a
    denominator that quietly excludes 229 coinable words.

    ``nonce`` is the permissiveness control and is not part of either
    denominator.
    """
    import kg_coverage as KC
    from symbolic_ai_data.grammar.compile import classify, curriculum_vocabulary

    coined = [w for w in curriculum_vocabulary() if w]
    out: dict[str, set[str]] = {"coined-423": {norm(w) for w in coined}}
    buckets: dict[str, set[str]] = defaultdict(set)
    for w in coined:
        buckets[f"coined:{classify(w)}"].add(norm(w))
    out.update(buckets)
    strict = {norm(w) for w in KC._words(KC.STRICT_VOCAB)}
    out["kgcov-strict"] = strict
    out["kgcov-wide"] = strict | {norm(w) for w in KC._words(KC.WIDE_EXTRA)}
    out["kgcov-proper"] = {norm(w) for w in KC._words(KC.PROPER_VOCAB)}
    out["nonce"] = {norm(w) for w in KC._words(KC.NONCE_VOCAB)}
    return out


def controls(vocab: dict[str, set[str]], seed: int = 20260815) -> dict[str, set[str]]:
    rng = random.Random(seed)
    real = vocab["coined-423"] | vocab["kgcov-wide"] | vocab["kgcov-proper"]
    anagram = set()
    for w in sorted(real):
        chars = list(w)
        rng.shuffle(chars)
        anagram.add("".join(chars))
    out = {"anagram": anagram - real}
    if DICT.exists():
        words = sorted({norm(w) for w in
                        DICT.read_text(encoding="utf-8", errors="replace").split()
                        if w.isalpha()} - real)
        out["dict-uniform"] = set(rng.sample(words, min(len(real), len(words))))
        by_len: dict[int, list[str]] = defaultdict(list)
        for w in words:
            by_len[len(w)].append(w)
        lm: set[str] = set()
        for w in sorted(real):
            pool = by_len.get(len(w))
            if pool:
                lm.add(rng.choice(pool))
        out["dict-lenmatched"] = lm
    return out


def scan_nodes(root: Path, targets: set[str]) -> dict:
    """Pass A: node tables -> which words have a labelled node, and which ids.

    Ids are kept as raw strings, not hashes: only nodes whose label matches one
    of ~1,700 target words are retained, so the set is small enough that the
    collision caveat `kg_derivable` has to carry is simply not incurred here.
    """
    exact: dict[str, set[str]] = defaultdict(set)
    token: dict[str, set[str]] = defaultdict(set)
    nodes = labelled = 0
    kinds: Counter[str] = Counter()
    per_file: dict[str, int] = {}
    files = sorted(root.glob("*.nodes.tsv.gz"))
    for path in files:
        it = _lines(path)
        head = next(it, b"")
        if not head.startswith(b"id\tkind\tlabel"):
            raise SystemExit(f"{path}: unexpected node header {head!r}")
        k = 0
        for raw in it:
            f = raw.rstrip(b"\n").split(b"\t")
            if len(f) < 3:
                continue
            nodes += 1
            k += 1
            lab = f[2].decode("utf-8", "replace")
            if not lab:
                continue
            labelled += 1
            n = norm(lab)
            words = {t for t in n.split() if t in targets}
            whole = n if n in targets else None
            if whole is None and not words:
                continue
            hid = f[0].decode()
            if whole:
                exact[hid].add(whole)
                token[hid].add(whole)
            for t in words:
                token[hid].add(t)
            kinds[f[1].decode()] += 1
        per_file[path.name] = k
    return {"files": per_file, "nodes": nodes, "labelled": labelled,
            "exact": exact, "token": token, "kinds": dict(kinds.most_common(20))}


def scan_edges(root: Path, exact: dict[str, set[str]], token: dict[str, set[str]],
               targets: set[str]) -> dict:
    """Pass B: which candidate ids anchor, and which carry a determiner.

    Also picks up ConceptNet ids on the fly, in **either** position and under
    **any** predicate — `cskg` ships no node table, so its entities can only
    enter the candidate set from their own identifiers, and a word whose only
    appearance is as the *object* of `has-property` still has a label in this
    graph. An earlier version of this function registered a ConceptNet id only
    when it was the subject of an anchor or a determiner, which silently turned
    column 1 ("does the word find a labelled node at all?") into a restatement
    of column 3 and reported `blue` and `book` as absent from a graph that
    contains both.

    Anchoring and determining are still **subject-position only**, as in
    `kg_derivable`: an entity that appears as the object of someone else's
    `is-a` has not thereby been typed.
    """
    anchored: set[str] = set()
    determined: set[str] = set()
    from_id = 0
    files, chosen = inputs(root)
    for path in files:
        it = _lines(path)
        tsv = path.name.endswith(".tsv.gz")
        if tsv:
            next(it, b"")
        n = 0

        def register(sid: str) -> bool:
            nonlocal from_id
            if sid in token:
                return True
            w = label_from_id(sid)
            if w is None or w not in targets:
                return False
            exact[sid].add(w)
            token[sid].add(w)
            from_id += 1
            return True

        for raw in it:
            n += 1
            if tsv:
                f = raw.rstrip(b"\n").split(b"\t", 3)
                if len(f) < 3:
                    continue
                s_b, p_b, o_b = f[0], f[1], f[2]
                # Decode only what can possibly match: the bytes check is free
                # and skips 99.8% of a 1.2-billion-row corpus.
                if o_b.startswith(CSKG_B):
                    register(o_b.decode())
                p = p_b.decode()
                anchor_or_derive = p in ANCHOR or p in DERIVE
                if not anchor_or_derive and not s_b.startswith(CSKG_B):
                    continue
                sid = s_b.decode()
            else:
                r = json.loads(raw)
                register(r["o"])
                p = r["p"]
                anchor_or_derive = p in ANCHOR or p in DERIVE
                sid = r["s"]
            if not register(sid) or not anchor_or_derive:
                continue
            (anchored if p in ANCHOR else determined).add(sid)
        print(f"    {path.name:<24} {n:>13,} rows  "
              f"anchored {len(anchored):>8,}  determined {len(determined):>8,}",
              flush=True)
    return {"anchored": anchored, "determined": determined,
            "candidates_from_id": from_id, "form": chosen}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("normalized", help="kg/normalized/vN")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.normalized)

    vocab = curriculum_vocab()
    vocab.update(controls(vocab))
    targets = set().union(*vocab.values())
    print(f"{len(targets):,} distinct target words across {len(vocab)} vocabularies")
    for k in sorted(vocab):
        print(f"  {k:<18} {len(vocab[k]):>6,}")

    print("\npass A: node tables")
    A = scan_nodes(root, targets)
    print(f"  {len(A['files'])} node files, {A['nodes']:,} nodes, "
          f"{A['labelled']:,} with a label, "
          f"{len(A['token']):,} matching some target word")

    from_nodes = len(A["token"])
    print("\npass B: edge tables")
    B = scan_edges(root, A["exact"], A["token"], targets)
    print(f"  {B['candidates_from_id']:,} further candidates entered from "
          f"ConceptNet identifiers (cskg ships no node table)")
    usable = B["anchored"] & B["determined"]

    idx = {"exact": defaultdict(set), "token": defaultdict(set)}
    for matcher, m in (("exact", A["exact"]), ("token", A["token"])):
        for hid, words in m.items():
            for w in words:
                idx[matcher][w].add(hid)

    report = {}
    for name, words in sorted(vocab.items()):
        row: dict = {"words": len(words)}
        for matcher in ("exact", "token"):
            I = idx[matcher]
            hit = {w for w in words if I.get(w)}
            anc = {w for w in hit if I[w] & B["anchored"]}
            use = {w for w in hit if I[w] & usable}
            row[matcher] = {
                "labelled_node": len(hit),
                "anchorable": len(anc),
                "anchorable_and_determined": len(use),
                "share_labelled": len(hit) / max(len(words), 1),
                "share_usable": len(use) / max(len(words), 1),
                "share_usable_given_labelled": len(use) / max(len(hit), 1),
                "examples_usable": sorted(use)[:12],
                "examples_missed": sorted(words - hit)[:12],
            }
        report[name] = row

    for matcher in ("exact", "token"):
        print(f"\n  -- matcher: {matcher}")
        print(f"  {'vocabulary':<18} {'words':>6} {'labelled':>16} "
              f"{'anchor':>8} {'usable':>8} {'usable|lab':>11}")
        for name in sorted(report):
            r = report[name][matcher]
            print(f"  {name:<18} {report[name]['words']:>6,} "
                  f"{r['labelled_node']:>8,} ({r['share_labelled']:5.1%})"
                  f" {r['anchorable']:>8,} {r['anchorable_and_determined']:>8,} "
                  f"{r['share_usable_given_labelled']:>10.1%}")

    stats = {
        "node_files": A["files"], "nodes_total": A["nodes"],
        "nodes_with_label": A["labelled"], "node_kinds_matched": A["kinds"],
        "input_form_per_source": B["form"],
        "candidates_from_node_tables": from_nodes,
        "candidates_from_conceptnet_ids": B["candidates_from_id"],
        "candidates_anchorable": len(B["anchored"]),
        "candidates_determined": len(B["determined"]),
        "candidates_usable": len(usable),
        "by_vocabulary": report,
        "note": ("`usable` = the word has at least one node that is both "
                 "anchorable and carries a determined attribute. Labels come "
                 "from *.nodes.tsv.gz and, for cskg only, from the ConceptNet "
                 "identifier itself -- cskg ships no node table and is where "
                 "essentially every determined attribute lives. Controls: nonce "
                 "(permissiveness), anagram (same shape, no meaning), and two "
                 "dictionary samples that are NOT frequency-matched, so that "
                 "confound is two-sided -- read the conditional column."),
    }
    out = Path(args.out or (root / "stats-vocab.json"))
    out.write_text(json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
