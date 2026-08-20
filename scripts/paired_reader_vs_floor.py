"""Paired comparison: does the learned reader beat the two-line rule item by item?

The head-noun arm compared the reader (0.288) against an agentive-suffix floor
(0.310) with **unpaired** intervals and concluded they are indistinguishable. That
is the weaker test. Both are scored on the *same* 184 items, so the pairing is
free, and McNemar uses only the items where the two disagree -- which is where all
the information about a difference lives.

If the reader is genuinely a vocabulary model with nothing extra on novel values,
the discordant pairs should split near evenly. If it is doing something the rule
cannot, it wins the discordant pairs.

This is the refuter the previous finding named, and it can reverse it: a paired
test is strictly more powerful, so an unpaired null is not evidence of no effect.

Run: uv run python -u scripts/paired_reader_vs_floor.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (LearnedSpanReader, PhraseMentions,
                                             _units)
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.head_noun_floor import agentive
from scripts.multi_relation_world import norm
from scripts.occupation_control import FOLDS, REL
from scripts.open_vocabulary_floor import COP, WINDOW, hit
from scripts.people_decomposition import RELATIONS, corpus
from scripts.wordnet_proposer import person_nouns

OUT = Path("runs/paired_reader_vs_floor.json")


def mcnemar(b: int, c: int) -> float:
    """Two-sided exact-ish p via the normal approximation with continuity."""
    n = b + c
    if n == 0:
        return 1.0
    chi = (abs(b - c) - 1) ** 2 / n
    return math.erfc(math.sqrt(chi / 2))


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    people = person_nouns()
    prop = PhraseMentions(people)
    orig = PhraseMentions.induce
    out = {}

    for slice_ in ("unseen", "seen"):
        both = r_only = f_only = neither = 0
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
            PhraseMentions.induce = staticmethod(
                lambda fillers, **kw: PhraseMentions(people))
            try:
                reader = LearnedSpanReader(
                    mentions=prop, extra_features=R.frame_features,
                    extra_role_features=R.role_frame_features).fit(
                    [R.supervise_distant(d) for d in tr])
            finally:
                PhraseMentions.induce = orig

            for d in te:
                gold = [g for g in d[REL] if g]
                if not gold:
                    continue
                # the reader
                res = reader.run(d["intro"], query=d.get("title", ""))
                best = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == REL and isinstance(v, EntityRef):
                        if best is None or res.confidence_of(i) > best[0]:
                            best = (res.confidence_of(i), v.id)
                r_ok = bool(best) and norm(best[1]) in [norm(g) for g in gold]
                # the two-line rule
                cands = [(m.text, m.start, m.end)
                         for u in _units(d["intro"]) for m in prop.find(u)]
                guess = None
                for m in COP.finditer(d["intro"]):
                    near = [c for c in cands
                            if 0 <= c[1] - m.end() <= WINDOW and agentive(c[0])]
                    if near:
                        guess = max(near, key=lambda c: (c[2], len(c[0])))[0]
                        break
                f_ok = hit(guess, gold)

                both += r_ok and f_ok
                r_only += r_ok and not f_ok
                f_only += f_ok and not r_ok
                neither += not r_ok and not f_ok

        n = both + r_only + f_only + neither
        p = mcnemar(r_only, f_only)
        out[slice_] = {"both": both, "reader_only": r_only,
                       "floor_only": f_only, "neither": neither, "n": n,
                       "reader": (both + r_only) / max(1, n),
                       "floor": (both + f_only) / max(1, n), "p": p}
        v = out[slice_]
        print(f"\n=== {slice_}  (n={n})")
        print(f"  both right      {both:5d}")
        print(f"  reader only     {r_only:5d}   <- discordant")
        print(f"  floor only      {f_only:5d}   <- discordant")
        print(f"  neither         {neither:5d}")
        print(f"  reader {v['reader']:.3f}   floor {v['floor']:.3f}   "
              f"McNemar p = {p:.4f}")
        if p < 0.05:
            who = "reader" if r_only > f_only else "floor"
            print(f"  -> SEPARATED: the {who} is ahead, paired p={p:.4f}")
        else:
            print(f"  -> not separated at n={n}: the discordant pairs "
                  f"({r_only} vs {f_only}) do not favour either")

    print("\n--- what this does to the previous finding")
    u = out["unseen"]
    if u["p"] >= 0.05:
        print("the unpaired null SURVIVES the more powerful paired test: on "
              "novel vocabulary the learned reader is not distinguishable from "
              "two lines of morphology.")
    else:
        print("the unpaired null was UNDERPOWERED: the paired test separates "
              "them, and the previous finding must be corrected.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
