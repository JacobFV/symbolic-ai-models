"""Detecting a lexicon problem before you have a lexicon.

`country`'s hand reader beats a **perfect classifier** — 0.692 against an oracle
ceiling of 0.458 — because it reads *"a Japanese company"* as `country=Japan`, and
the string `Japan` never appears. Distant supervision is blind to that sentence,
so no model trained on it can reach the relation.

That produced a triage rule — *a relation whose containment is far below its true
statement rate is a lexicon problem, not a model problem* — and no way to apply
it, because the true statement rate is exactly what you cannot measure. This makes
it operational with a **morphological proxy that needs no lexicon**:

    exact      the gold string appears verbatim
    prefix     some token in the article starts with the gold's first 5
               characters -- `Japan` -> `Japanese`, `Norway` -> `Norwegian`
    token      some token of the gold string appears at all

`prefix - exact` is the share of articles where the relation is plausibly stated
in an **inflected or derived form** that verbatim matching cannot see. A large gap
says *build a lexicon*; a small one says *fix the model*.

Predicted before running: `country` shows much the largest gap, because country
names have adjectival forms and companies do not. `parent`, `headquarters` and
`founder` are proper nouns that do not inflect, so their gaps should be small and
mostly noise from short gold strings matching unrelated words. `industry` should
sit in between — `automotive industry` against *automotive company*.

Run: uv run python -u scripts/lexicon_gap_diagnostic.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import scripts.real_text_reader as R

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v2.jsonl")
OUT = Path("runs/lexicon_gap_diagnostic.json")
RELATIONS = ("parent", "country", "headquarters", "founder", "industry")
PREFIX = 5
STOP = frozenset("the of and for in a an de la group inc ltd llc corporation "
                 "company holdings holding co".split())
_TOK = re.compile(r"[A-Za-z][A-Za-z'-]+")


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        for r_ in RELATIONS:
            if r_ != "parent":
                d[r_] = rel.get(d["qid"], {}).get(r_) or []
    print(f"{len(docs)} articles\n")
    print(f"    {'relation':<14}{'gold':>7}{'exact':>8}{'prefix':>8}"
          f"{'token':>8}{'GAP':>8}   verdict")

    out = {}
    for relation in RELATIONS:
        n = e = p = t = 0
        for d in docs:
            gold = [g for g in (d.get(relation) or []) if g]
            if not gold:
                continue
            n += 1
            text = d["intro"]
            low = text.lower()
            toks = {w.lower() for w in _TOK.findall(text)}
            if any(g in text for g in gold):
                e += 1
            # A derived form shares a stem: `Japan` -> `Japanese`. Five
            # characters is long enough that `Ind` -> `India`/`Indonesia`
            # collisions are rare and short enough to catch real derivations.
            stems = {g.lower()[:PREFIX] for g in gold
                     if len(g) >= PREFIX and g.lower() not in STOP}
            if any(any(w.startswith(s) for w in toks) for s in stems):
                p += 1
            words = {w for g in gold for w in _TOK.findall(g.lower())
                     if w not in STOP and len(w) > 3}
            if words & toks:
                t += 1
        gap = (p - e) / max(1, n)
        verdict = ("LEXICON problem" if gap >= 0.15
                   else "model problem" if gap < 0.06 else "mixed")
        print(f"    {relation:<14}{n:7d}{e / n:8.3f}{p / n:8.3f}{t / n:8.3f}"
              f"{gap:8.3f}   {verdict}")
        out[relation] = {"n": n, "exact": e / n, "prefix": p / n,
                         "token": t / n, "gap": gap, "verdict": verdict}

    print(f"\n    the rule this operationalises: `country`'s hand reader beats a")
    print(f"    PERFECT classifier (0.692 vs 0.458) because it reads a form the")
    print(f"    gold never contains. The gap column is that, measured without a")
    print(f"    hand reader and without a lexicon.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
