"""Was the limit the lexical APPROACH, or just the size of the inventory?

The suffix arm concluded that a lexical proposer cannot generalise a long-tailed
inventory, on the grounds that both routes drawn from **training fillers** --
exact phrase and shared head -- read 0.000 on unseen occupations while
containment stayed at 0.582. That conclusion named its own refuter, and this is
it: an inventory drawn from **outside** the training data.

WordNet's `noun.person` supersense is exactly the right shape -- 11,087 synsets
of people-by-role: cyclist, physicist, bishop, cartographer. This repo's standing
rule is that external standards are **givens** rather than things to re-derive,
so using it is the intended move rather than a shortcut.

If the unseen slice recovers, the previous finding's strong claim is wrong: the
limit was inventory *size*, and a lexical proposer is fine once it is not
restricted to what supervision happened to contain. That is why this is worth the
run -- it is the experiment that embarrasses the thing just committed.

Run: uv run python -u scripts/wordnet_proposer.py
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import PhraseMentions
from symbolic_ai_generators.wordnet import _tables, wordnet_path

import scripts.real_text_reader as R
from scripts.occupation_control import FOLDS, REL, pooled, score
from scripts.people_decomposition import RELATIONS, corpus

OUT = Path("runs/wordnet_proposer.json")


def person_nouns() -> list[str]:
    """Every WordNet lemma with a `noun.person` sense, underscores unpacked."""
    lemma_offsets, offset_class, _ = _tables("noun")
    out = set()
    for lemma, offsets in lemma_offsets.items():
        if any(offset_class.get(o) == "noun.person" for o in offsets):
            out.add(lemma.replace("_", " ").lower())
    return sorted(out)


def main() -> None:
    if wordnet_path() is None:
        print("no WordNet on disk; blocked")
        return
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    people = person_nouns()
    print(f"{len(docs)} biographies, {len(vocab)} distinct occupations")
    print(f"{len(people)} WordNet noun.person lemmas, e.g. {people[3000:3004]}")

    covered = sum(1 for v in vocab if v.lower() in set(people))
    print(f"WordNet covers {covered}/{len(vocab)} = {covered / len(vocab):.3f} "
          f"of the gold vocabulary exactly")

    out = {}
    orig = PhraseMentions.induce
    for name in ("seen", "unseen"):
        rows = []
        for fold in range(FOLDS):
            if name == "seen":
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            else:
                held = {v for i, v in enumerate(vocab) if i % FOLDS == fold}
                te = [d for d in docs if all(v in held for v in d[REL])]
                tr = [d for d in docs if not any(v in held for v in d[REL])]
            if not (te and tr):
                continue
            # The proposer no longer depends on the fillers at all: the same
            # external inventory is handed to every fold. Training fillers still
            # supervise the CLASSIFIER; only the candidate set changes.
            PhraseMentions.induce = staticmethod(
                lambda fillers, **kw: PhraseMentions(people))
            try:
                rows.append(score(tr, te))
            finally:
                PhraseMentions.induce = orig
        out[name] = pooled(rows)

    print(f"\n{'slice':<8}{'contain':>9}{'propose':>9}{'clf':>7}{'rank':>7}"
          f"{'product':>9}{'measured':>10}{'n':>7}")
    for k in ("seen", "unseen"):
        v = out[k]
        print(f"{k:<8}{v['containment']:9.3f}{v['proposal']:9.3f}"
              f"{v['classifier']:7.3f}{v['ranker']:7.3f}{v['product']:9.3f}"
              f"{v['measured']:10.3f}{v['n']:7d}")

    u = out["unseen"]
    print("\n--- the verdict on the previous finding")
    print(f"unseen: training-induced 0.000 -> WordNet {u['measured']:.3f}, "
          f"proposal 0.000 -> {u['proposal']:.3f}")
    if u["proposal"] > 0.30 and u["measured"] > 0.15:
        print("PREVIOUS FINDING REFUTED: the limit was inventory SIZE, not the "
              "lexical approach. A lexical proposer generalises fine once it is "
              "not restricted to what supervision contained.")
    elif u["proposal"] > 0.30:
        print("SPLIT: the proposer recovers and the RATE does not -- the "
              "classifier/ranker depended on the induced vocabulary too.")
    else:
        print("PREVIOUS FINDING STANDS: even 11k external person-nouns do not "
              "propose these values. The limit is the lexical approach.")
    print(f"seen: 0.600 -> {out['seen']['measured']:.3f} "
          f"(cost of a large inventory)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
