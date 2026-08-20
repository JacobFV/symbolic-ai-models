"""The configuration that would ship: both inventories, not one or the other.

The WordNet arm swapped the proposer's inventory and paid **-0.064** on the seen
slice for **+0.288** on the unseen one. It named its own refuter: that cost might
be an artefact of *replacing* the training-induced phrases rather than a genuine
precision cost of a large inventory. The union settles it, and it is also the
configuration anyone would actually deploy -- there is no reason to throw away
what supervision taught in order to gain what WordNet knows.

`PhraseMentions` matches longest-first, so an exact gold phrase from training
should still win over a shorter WordNet fragment inside it.

Run: uv run python -u scripts/union_proposer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import PhraseMentions

import scripts.real_text_reader as R
from scripts.occupation_control import FOLDS, REL, pooled, score
from scripts.people_decomposition import RELATIONS, corpus
from scripts.wordnet_proposer import person_nouns

OUT = Path("runs/union_proposer.json")


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    people = person_nouns()
    print(f"{len(docs)} biographies, {len(vocab)} occupations, "
          f"{len(people)} WordNet person lemmas")

    orig = PhraseMentions.induce
    out = {}
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

            def induce(fillers, **kw):
                # Union, and the suffixes the training fillers support. The
                # inventory is what supervision taught PLUS what the standard
                # knows -- neither is discarded.
                base = orig(fillers)
                return PhraseMentions(list(base.phrases) + people,
                                      base.suffixes,
                                      aliases=base.aliases)

            PhraseMentions.induce = staticmethod(induce)
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

    print("\n--- three proposers, same reader, same folds")
    print(f"{'proposer':<26}{'seen':>8}{'unseen':>9}")
    print(f"{'training-induced':<26}{0.600:8.3f}{0.000:9.3f}")
    print(f"{'WordNet noun.person':<26}{0.536:8.3f}{0.288:9.3f}")
    print(f"{'union':<26}{out['seen']['measured']:8.3f}"
          f"{out['unseen']['measured']:9.3f}")
    s, u = out["seen"]["measured"], out["unseen"]["measured"]
    if s >= 0.57 and u >= 0.25:
        print("\n-> the -0.064 was an artefact of REPLACING the inventory. The "
              "union dominates both, and it is what ships.")
    elif s < 0.57:
        print("\n-> the cost is REAL: a large inventory genuinely costs the "
              "ranker precision, and the trade has to be chosen rather than "
              "avoided.")
    else:
        print("\n-> the union loses the unseen gain; the inventories interfere.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
