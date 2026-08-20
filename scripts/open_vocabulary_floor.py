"""What does 0.288 beat? The floor audit the open-vocabulary result has not had.

The WordNet arm reported the learned reader answering **0.288** on occupation
values it was never supervised on, and called it open-vocabulary reading. That
number has no floor under it, and this repo's most expensive recurring mistake is
quoting a lift over a floor that was too low -- `rgt`'s "+0.587, first of
nineteen" was a floor 0.065 short.

Four floors, all given the **same WordNet candidate set** the reader gets, so the
comparison is about the reasoning and not about the proposer:

    prior        always answer the most frequent training occupation. On the
                 unseen slice this must score exactly 0.000 by construction --
                 it is a harness check, not a floor. Anything above zero means
                 the vocabulary split leaks.
    first        the first proposed candidate in the document.
    longest      the longest proposed candidate, i.e. the most specific.
    copular      the candidate immediately following `is/was a/an`, optionally
                 through one or two adjectives. One regex, no learning. This is
                 the floor that matters: biography intros are formulaic, and if
                 a pattern this cheap matches 0.288 the learned reader bought
                 nothing.

Registered before running: `first` lands above 0.20 and `copular` is close to or
above the reader, because *"X (born 1953) is a British politician"* states the
answer in a fixed position.

Run: uv run python -u scripts/open_vocabulary_floor.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import PhraseMentions, _units

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm
from scripts.occupation_control import FOLDS, REL
from scripts.people_decomposition import RELATIONS, corpus
from scripts.wordnet_proposer import person_nouns

OUT = Path("runs/open_vocabulary_floor.json")
#: `is a`, `was an`, `is a former`, `is a British` -- up to two modifiers, which
#: is what a nationality plus an adjective costs.
COP = re.compile(r"\b(?:is|was|are|were)\s+(?:a|an|the)\b", re.I)
#: How far past the copula the head noun can sit. *"is a British former
#: professional racing cyclist"* is 34 characters of modifier before the head,
#: so a tight window is a floor built to fail -- and a floor built to fail is
#: this repo's most expensive recurring mistake.
WINDOW = 60


def hit(guess: str | None, gold: list[str]) -> bool:
    return bool(guess) and norm(guess) in [norm(g) for g in gold]


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    prop = PhraseMentions(person_nouns())
    print(f"{len(docs)} biographies, {len(vocab)} occupations")

    names = ("prior", "first", "longest", "copular",
             "copular_long", "sent1_long")
    tot = {("seen", k): [0, 0] for k in names}
    tot |= {("unseen", k): [0, 0] for k in names}

    for slice_ in ("seen", "unseen"):
        for fold in range(FOLDS):
            if slice_ == "seen":
                te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
                tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            else:
                held = {v for i, v in enumerate(vocab) if i % FOLDS == fold}
                te = [d for d in docs if all(v in held for v in d[REL])]
                tr = [d for d in docs if not any(v in held for v in d[REL])]
            if not (te and tr):
                continue
            common = Counter(v for d in tr for v in d[REL]).most_common(1)
            top = common[0][0] if common else None

            for d in te:
                gold = [g for g in d[REL] if g]
                if not gold:
                    continue
                cands = []
                s1: list[tuple[str, int]] = []
                for i_u, u in enumerate(_units(d["intro"])):
                    for m in prop.find(u):
                        cands.append((m.text, m.start))
                        if i_u == 0:
                            s1.append((m.text, m.start))
                guesses = {
                    "prior": top,
                    "first": cands[0][0] if cands else None,
                    "longest": (max(cands, key=lambda c: len(c[0]))[0]
                                if cands else None),
                    "copular": None, "copular_long": None,
                    # No pattern at all: the longest person-noun in sentence
                    # one. Named as this audit's own refuter -- if it reaches
                    # the reader's 0.288 the lift is gone entirely.
                    "sent1_long": (max(s1, key=lambda c: len(c[0]))[0]
                                   if s1 else None),
                }
                # copular: the first candidate starting at or just after a
                # copula match. The regex locates the position; the candidate
                # set supplies the string, so it is scored like the others.
                for m in COP.finditer(d["intro"]):
                    at = m.end()
                    near = [c for c in cands if 0 <= c[1] - at <= WINDOW]
                    if near:
                        # first candidate after the copula, and separately the
                        # longest one in the window -- *racing cyclist* beats
                        # *cyclist* when both are proposed inside the same NP.
                        guesses["copular"] = min(
                            near, key=lambda c: c[1] - at)[0]
                        guesses["copular_long"] = max(
                            near, key=lambda c: (len(c[0]), -c[1]))[0]
                        break
                for k in names:
                    tot[(slice_, k)][1] += 1
                    tot[(slice_, k)][0] += hit(guesses[k], gold)

    print(f"\n{'floor':<12}{'seen':>9}{'unseen':>9}{'n seen':>9}{'n unseen':>10}")
    out = {}
    for k in names:
        s, n_s = tot[("seen", k)]
        u, n_u = tot[("unseen", k)]
        out[k] = {"seen": s / max(1, n_s), "unseen": u / max(1, n_u),
                  "n_seen": n_s, "n_unseen": n_u}
        print(f"{k:<12}{out[k]['seen']:9.3f}{out[k]['unseen']:9.3f}"
              f"{n_s:9d}{n_u:10d}")
    print(f"{'LEARNED':<12}{0.536:9.3f}{0.288:9.3f}   (WordNet proposer)")

    best_u = max(out, key=lambda k: out[k]["unseen"])
    best_s = max(out, key=lambda k: out[k]["seen"])
    print(f"\n--- the audit")
    print(f"best floor on unseen: {best_u} at {out[best_u]['unseen']:.3f}; "
          f"reader 0.288 -> lift {0.288 - out[best_u]['unseen']:+.3f}")
    print(f"best floor on seen:   {best_s} at {out[best_s]['seen']:.3f}; "
          f"reader 0.536 -> lift {0.536 - out[best_s]['seen']:+.3f}")
    if out["prior"]["unseen"] > 0.0:
        print("!! prior scores above zero on the unseen slice: the vocabulary "
              "split LEAKS and every unseen number in this arm is suspect")
    else:
        print("prior is exactly 0.000 on unseen, as it must be: the split holds")
    if out[best_u]["unseen"] >= 0.288:
        print("!! THE HEADLINE DOES NOT SURVIVE: a floor matches or beats the "
              "learned reader on the slice the claim was about")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
