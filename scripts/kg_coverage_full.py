"""Coverage against the curriculum's *own* enumerator, not a hand-classified subset.

`scripts/kg_coverage.py` measures reach against hand-built tables — `STRICT`
(69 words), `WIDE` (180), `PROPER` (14) — and the "~100% covered" headline is the
`STRICT` number. That was quoted, by me, as *"coverage of the curriculum's
vocabulary is already ~100%"* and used to argue that a bigger graph is the wrong
prescription.

The repo ships an importable enumerator nobody pointed at that question:
``curriculum_vocabulary()`` returns **423** words the generators can coin and
``rendered_vocabulary()`` **749** including record field names that reach the
page. `WIDE ∪ PROPER` is 194 and a strict subset of the 423, so **229 coinable
words were never in the measurement.**

This script re-runs it on the real denominators, against the **60.6 M normalised
node labels** — which the first pass could not do, because it threw the node
tables away.

Three numbers per denominator, and the third is the one that matters:

* **labelled** — a node in the graph carries this word as its label at all;
* **anchorable** — that node is the subject of an `is-a` / `instance-of` edge;
* **determined** — it is also the subject of a determiner edge, so a slot could
  *follow* from it. That is the population a derivability curriculum can use,
  and the previous whole-corpus figure was 9,849 entities.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

ANCHOR = {"is-a", "instance-of"}
DERIVE = {"has-property", "capable-of", "used-for", "made-of", "causes", "has-a",
          "desires", "not-desires", "manner-of", "defined-as",
          "agent-attribute", "agent-effect", "agent-wants", "agent-needs",
          "agent-reacts", "agent-intends", "other-wants", "other-effect",
          "other-reacts", "precondition-of", "subevent-of"}


def norm(w: str) -> str:
    return w.strip().lower().replace("_", " ")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("normalized", help="kg/normalized/vN")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.normalized)

    from symbolic_ai_data.grammar.compile import (curriculum_vocabulary,
                                                  rendered_vocabulary)
    vocabs = {"curriculum_423": {norm(w) for w in curriculum_vocabulary()},
              "rendered_749": {norm(w) for w in rendered_vocabulary()}}
    wanted = set().union(*vocabs.values())

    # label -> ids. Only ids whose label is a curriculum word are kept, so this
    # stays small however many nodes the corpus has.
    ids_for: dict[str, set[str]] = {}
    n_nodes = 0
    for f in sorted(root.glob("*.nodes.tsv.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            next(fh, None)
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                n_nodes += 1
                lab = norm(parts[2])
                if lab in wanted:
                    ids_for.setdefault(lab, set()).add(parts[0])

    # cskg ships NO node table and is the source of nearly every determiner, so
    # a join on node tables alone would report a near-zero usable coverage that
    # is an artefact of which sources export a node file. Its ConceptNet ids
    # carry the lemma: kg:cskg:/c/en/penguin/n -> "penguin".
    def lemma_of(ident: str) -> str | None:
        if not ident.startswith("kg:cskg:/c/"):
            return None
        parts = ident.split("/")
        return norm(parts[4]) if len(parts) > 4 else None

    anchored: set[str] = set()
    determined: set[str] = set()
    n_edges = 0
    for f in sorted(root.glob("*.tsv.gz")):
        if f.name.endswith(".nodes.tsv.gz"):
            continue
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            next(fh, None)
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                n_edges += 1
                s, p = parts[0], parts[1]
                if p in ANCHOR:
                    anchored.add(s)
                elif p in DERIVE:
                    determined.add(s)
                lem = lemma_of(s)
                if lem is not None and lem in wanted:
                    ids_for.setdefault(lem, set()).add(s)

    out: dict[str, object] = {"nodes_read": n_nodes, "edges_read": n_edges,
                              "normalized": str(root)}
    for name, vocab in vocabs.items():
        lab = {w for w in vocab if ids_for.get(w)}
        anc = {w for w in lab if ids_for[w] & anchored}
        det = {w for w in lab if ids_for[w] & determined}
        both = anc & det
        out[name] = {
            "words": len(vocab),
            "labelled": len(lab), "labelled_pct": round(len(lab) / len(vocab), 4),
            "anchorable": len(anc), "anchorable_pct": round(len(anc) / len(vocab), 4),
            "with_determiner": len(det),
            "BOTH": len(both), "BOTH_pct": round(len(both) / len(vocab), 4),
            "missing_examples": sorted(vocab - lab)[:25],
        }
        d = out[name]
        print(f"{name:>16}  n={d['words']:>4}  labelled {d['labelled']:>4} "
              f"({d['labelled_pct']:.1%})  anchorable {d['anchorable']:>4} "
              f"({d['anchorable_pct']:.1%})  BOTH {d['BOTH']:>4} ({d['BOTH_pct']:.1%})")

    dest = Path(args.out or (root / "stats-vocab.json"))
    dest.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
