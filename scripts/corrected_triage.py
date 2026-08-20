"""The triage set, corrected by its own prospective failure, scored on all seven.

The prospective test scored four of seven and named two omissions:

- **the floor is missing.** `legal_form` gained +0.106 from aliases and still
  landed 0.003 *below* a majority-class floor of 0.116. A screening set that
  cannot say "this relation needs 0.116 to be worth anything" is incomplete.
- **the positional ratio has no base guard.** `legal_form`'s 7.0x is computed on a
  containment of 0.054, so it is a small sample rather than a prior, and it bought
  +0.003 where `founder`'s 2.8x on containment 0.424 bought +8 articles.

A third gap showed up in the result rather than the predictions: `owned_by` has
**containment 0.547** — as high as `parent` — and reads at 0.058. Its gold values
are institutional shareholders (`BlackRock`, `The Vanguard Group`), which appear in
these articles for reasons other than ownership. That is **false containment**: the
string is there and the sentence does not state the relation.

Frame concentration is the candidate detector, and it is worth noting that this
statistic already **failed once** as a predictor of readability. The claim here is
narrower: diffuse frames around gold occurrences mean the occurrences are not a
relation being stated.

Every statistic below is model-free — gold strings, a proposer, and a floor.

Run: uv run python -u scripts/corrected_triage.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import (CapitalisedMentions,
                                             PhraseMentions, _units)

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
RELS = Path("data/artifacts/company_relations_scale_v3.jsonl")
OUT = Path("runs/corrected_triage.json")
RELATIONS = ("parent", "country", "headquarters", "founder", "industry",
             "legal_form", "owned_by")
STOP = frozenset("a an the of in to for and or is was are were be been by on at "
                 "as its it his her their this that with from".split())
#: Below this many stating sentences a positional ratio is a small sample.
MIN_BASE = 200
#: What the best arm of each relation actually achieved, from the measured runs.
BEST = {"parent": 0.144, "country": 0.390, "headquarters": 0.280,
        "founder": 0.096, "industry": 0.238, "legal_form": 0.113,
        "owned_by": 0.058}


def main() -> None:
    R.PARENTS, R.RELATIONS = CORPUS, RELS
    docs = R.corpus()
    rel = {json.loads(x)["qid"]: json.loads(x)
           for x in RELS.read_text().splitlines() if x.strip()}
    for d in docs:
        for r_ in RELATIONS:
            if r_ != "parent":
                d[r_] = rel.get(d["qid"], {}).get(r_) or []
    cm = CapitalisedMentions()

    print(f"    {'relation':<13}{'floor':>7}{'contain':>8}{'stating':>8}"
          f"{'top5':>7}{'pos':>7}{'ceil-floor':>11}  {'best':>6}{'clears?':>9}")
    out = {}
    for relation in RELATIONS:
        vals = [[norm(x) for x in (d.get(relation) or [])] for d in docs
                if d.get(relation)]
        c = Counter(v for vs in vals for v in vs)
        floor = sum(1 for vs in vals if c.most_common(1)[0][0] in vs) / len(vals)

        n = contained = 0
        frames: Counter = Counter()
        posc: Counter = Counter()
        tot: Counter = Counter()
        proposed = present = 0
        for d in docs:
            gold = [x for x in (d.get(relation) or []) if x]
            if not gold:
                continue
            n += 1
            units = _units(d["intro"])
            hit = False
            for i, u in enumerate(units):
                tot[min(i, 5)] += 1
                g = next((x for x in gold if x in u.text), None)
                if not g:
                    continue
                hit = True
                posc[min(i, 5)] += 1
                present += 1
                ments = cm.find(u)
                proposed += any(m.text == g for m in ments)
                tgt = next((m for m in ments if m.text == g), None)
                if tgt is None:
                    continue
                words = [w for w in u.tokens if w.kind in ("word", "num")]
                prev = max((m.end for m in ments if m.end <= tgt.start),
                           default=u.start)
                gap = [w.text.lower() for w in words
                       if prev <= w.start < tgt.start]
                cont = [w for w in gap if w not in STOP]
                frames[cont[-1] if cont else ""] += 1
            contained += hit

        nf = sum(frames.values()) or 1
        top5 = sum(v for _, v in frames.most_common(5)) / nf
        pr = [posc[i] / max(1, tot[i]) for i in range(6)]
        ratio = pr[0] / max(1e-9, pr[5])
        base = present
        ceil = (contained / n) * (proposed / max(1, present))
        best = BEST[relation]
        clears = "YES" if best > floor else "no"
        pos_txt = f"{ratio:.1f}x" if base >= MIN_BASE else "(base)"
        print(f"    {relation:<13}{floor:7.3f}{contained / n:8.3f}{base:8d}"
              f"{top5:7.3f}{pos_txt:>7}{ceil - floor:+11.3f}  {best:6.3f}"
              f"{clears:>9}")
        out[relation] = {"floor": floor, "containment": contained / n,
                         "stating_sentences": base, "top5": top5,
                         "positional_ratio": ratio if base >= MIN_BASE else None,
                         "ceiling_minus_floor": ceil - floor, "best": best,
                         "clears_floor": best > floor}

    print(f"\n    ceil-floor uses the CAPITALISED proposer, so a relation whose")
    print(f"    values are lowercase reads negative there and is telling the")
    print(f"    truth about that proposer, not about the relation.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
