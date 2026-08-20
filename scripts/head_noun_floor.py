"""The floor audit's own refuter: pick the HEAD of the copular NP, not the longest.

The floor audit left the learned reader ahead by **+0.065** on unseen occupation
values, over a floor that takes the *longest* WordNet person-noun within 60
characters of *"is/was a"*. That note named its own weakness: "longest" is not
the linguistic rule. **The head of an English noun phrase is final** -- in *"is a
British former professional racing cyclist"* the answer is `cyclist` because it
ends the phrase, and `racing cyclist` wins on length only by accident of
correlation.

So the honest floor is rightmost-head, and it has never been tried. If it reaches
0.288 the lift is gone and the learned reader is doing nothing a two-line rule
cannot.

Four position rules inside the same copular window, same candidate set:

    long        longest candidate            (the audit's floor, 0.223)
    head        candidate that ENDS last     (the head of the NP)
    suffix      rightmost candidate whose final word carries an agentive
                suffix -- -ist, -er, -or, -ian, -man, -ee, -ant
    head_first  the head of the FIRST copular NP only, ignoring later ones

Run: uv run python -u scripts/head_noun_floor.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import PhraseMentions, _units

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm
from scripts.occupation_control import FOLDS, REL
from scripts.open_vocabulary_floor import COP, WINDOW, hit
from scripts.people_decomposition import RELATIONS, corpus
from scripts.wordnet_proposer import person_nouns

OUT = Path("runs/head_noun_floor.json")
AGENT = ("ist", "er", "or", "ian", "man", "ee", "ant", "ent", "ary", "eer",
         "ess", "wright", "smith", "ler", "yer")


def agentive(text: str) -> bool:
    return text.split()[-1].lower().endswith(AGENT) if text.split() else False


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    prop = PhraseMentions(person_nouns())
    print(f"{len(docs)} biographies, {len(vocab)} occupations")

    names = ("long", "head", "suffix", "head_first")
    tot = {(s, k): [0, 0] for s in ("seen", "unseen") for k in names}

    for slice_ in ("seen", "unseen"):
        for fold in range(FOLDS):
            if slice_ == "seen":
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            else:
                held = {v for i, v in enumerate(vocab) if i % FOLDS == fold}
                te = [d for d in docs if all(v in held for v in d[REL])]
            if not te:
                continue
            for d in te:
                gold = [g for g in d[REL] if g]
                if not gold:
                    continue
                cands = [(m.text, m.start, m.end)
                         for u in _units(d["intro"]) for m in prop.find(u)]
                g = {k: None for k in names}
                first_np = True
                for m in COP.finditer(d["intro"]):
                    at = m.end()
                    near = [c for c in cands if 0 <= c[1] - at <= WINDOW]
                    if not near:
                        continue
                    if g["long"] is None:
                        g["long"] = max(near, key=lambda c: (len(c[0]), -c[1]))[0]
                    # the head ends the phrase: rightmost END, ties to the longer
                    if g["head"] is None:
                        g["head"] = max(near, key=lambda c: (c[2], len(c[0])))[0]
                    if g["suffix"] is None:
                        ag = [c for c in near if agentive(c[0])]
                        if ag:
                            g["suffix"] = max(
                                ag, key=lambda c: (c[2], len(c[0])))[0]
                    if first_np:
                        g["head_first"] = max(
                            near, key=lambda c: (c[2], len(c[0])))[0]
                        first_np = False
                    if all(g[k] is not None for k in names):
                        break
                for k in names:
                    tot[(slice_, k)][1] += 1
                    tot[(slice_, k)][0] += hit(g[k], gold)

    print(f"\n{'rule':<12}{'seen':>9}{'unseen':>9}")
    out = {}
    for k in names:
        s, n_s = tot[("seen", k)]
        u, n_u = tot[("unseen", k)]
        out[k] = {"seen": s / max(1, n_s), "unseen": u / max(1, n_u)}
        print(f"{k:<12}{out[k]['seen']:9.3f}{out[k]['unseen']:9.3f}")
    print(f"{'LEARNED':<12}{0.536:9.3f}{0.288:9.3f}")

    best = max(out, key=lambda k: out[k]["unseen"])
    lift = 0.288 - out[best]["unseen"]
    print(f"\n--- the verdict")
    print(f"best floor: {best} at {out[best]['unseen']:.3f} unseen "
          f"(audit's floor was 0.223)")
    print(f"reader 0.288 -> lift {lift:+.3f}, was +0.065")
    if out[best]["unseen"] >= 0.288:
        print("!! THE LIFT IS GONE: a two-line positional rule matches the "
              "learned reader on values it never saw.")
    elif lift < 0.03:
        print("-> the lift is inside noise at n=184. The learned reader is not "
              "distinguishable from a positional rule on novel values.")
    else:
        print("-> the reader still leads. The lift is smaller and real.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
