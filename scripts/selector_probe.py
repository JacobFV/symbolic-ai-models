"""Can the reader tell when it is the one to trust?

The paired arm found the learned reader and a two-line morphological rule agree on
only **77.2%** of unseen items and **70.5%** of seen ones, and fail on different
ones: an oracle that knew which to believe would gain **+0.103** and **+0.102**.
That is larger than any single intervention measured in this arm.

The cheapest possible selector is the reader's own confidence, which it already
emits. This asks whether that confidence carries the signal -- AUC over the
**discordant** items only, which is the population a selector actually has to
sort. Pooled AUC over all items would be flattered by the easy agreements, and
this repo has been burned by pooled-versus-per-question AUC before.

Predicted before running: **it does not separate them**, AUC below 0.60, because
the confidence is calibrated on the classifier's label decision while the
disagreements live in the **ranker's** choice among candidates.

Run: uv run python -u scripts/selector_probe.py
"""

from __future__ import annotations

import json
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

OUT = Path("runs/selector_probe.json")


def auc(pos: list[float], neg: list[float]) -> float:
    """Mann-Whitney U, ties at half."""
    if not pos or not neg:
        return float("nan")
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    people = person_nouns()
    prop = PhraseMentions(people)
    orig = PhraseMentions.induce
    out = {}

    for slice_ in ("unseen", "seen"):
        rows = []
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
                res = reader.run(d["intro"], query=d.get("title", ""))
                best = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == REL and isinstance(v, EntityRef):
                        if best is None or res.confidence_of(i) > best[0]:
                            best = (res.confidence_of(i), v.id)
                conf = best[0] if best else 0.0
                r_ok = bool(best) and norm(best[1]) in [norm(g) for g in gold]
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
                agree = bool(best) and guess is not None and \
                    norm(best[1]) == norm(guess)
                rows.append({"conf": conf, "r": r_ok, "f": f_ok,
                             "agree": agree, "has_f": guess is not None})

        disc = [x for x in rows if x["r"] != x["f"]]
        pos = [x["conf"] for x in disc if x["r"]]
        neg = [x["conf"] for x in disc if x["f"]]
        a_disc = auc(pos, neg)
        a_all = auc([x["conf"] for x in rows if x["r"]],
                    [x["conf"] for x in rows if not x["r"]])

        n = len(rows)
        rd = sum(x["r"] for x in rows) / max(1, n)
        fl = sum(x["f"] for x in rows) / max(1, n)
        orc = sum(x["r"] or x["f"] for x in rows) / max(1, n)
        # the trivial rule: believe the reader unless it disagrees with the
        # floor AND its own confidence is below the median of disagreements
        confs = sorted(x["conf"] for x in rows if not x["agree"] and x["has_f"])
        thr = confs[len(confs) // 2] if confs else 0.0
        sel = sum((x["f"] if (not x["agree"] and x["has_f"]
                              and x["conf"] < thr) else x["r"])
                  for x in rows) / max(1, n)
        cap = (sel - max(rd, fl)) / (orc - max(rd, fl)) if orc > max(rd, fl) \
            else float("nan")

        out[slice_] = {"n": n, "reader": rd, "floor": fl, "oracle": orc,
                       "auc_discordant": a_disc, "auc_pooled": a_all,
                       "n_discordant": len(disc), "selector": sel,
                       "headroom_captured": cap, "threshold": thr}
        print(f"\n=== {slice_}  n={n}, discordant {len(disc)}")
        print(f"  reader {rd:.3f}  floor {fl:.3f}  oracle {orc:.3f}")
        print(f"  AUC of reader confidence on DISCORDANT items: {a_disc:.3f}")
        print(f"  AUC pooled over all items (flattered):        {a_all:.3f}")
        print(f"  trivial selector {sel:.3f} -> captures "
              f"{cap:.1%} of the +{orc - max(rd, fl):.3f} headroom")

    print("\n--- verdict")
    u = out["unseen"]
    if u["auc_discordant"] >= 0.60:
        print("the confidence DOES carry selector signal; a cheap router is "
              "worth building.")
    else:
        print(f"the confidence does not separate them (AUC "
              f"{u['auc_discordant']:.3f} on discordant items). The +0.10 "
              f"headroom is real but this is not the key to it.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
