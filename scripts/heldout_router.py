"""The router with nothing fitted on the items it scores.

The selector arm reported a router taking novel-vocabulary reading 0.310 -> 0.370,
and flagged its own flaw: the threshold was the **median of disagreements on the
test items themselves**. That is fitted on the thing being scored, so 0.370 is
optimistic by an unknown amount. This measures the honest version.

There is a wrinkle that makes it more than bookkeeping. For the **unseen** slice
the training documents are, by construction, entirely **seen** vocabulary -- the
regime where the reader is the stronger system and its confidence distribution is
shifted. So a held-out threshold is not merely held out, it has to **transfer
across regimes**. If it does not, the router is a fair-weather result.

Three routers, in increasing order of how much they assume:

    agreement   defer to the floor whenever the two disagree. Nothing fitted at
                all -- not even a threshold. The strictest possible baseline for
                the idea.
    heldout     threshold swept on the TRAINING documents, applied to test.
    insample    the selector arm's number, recomputed here for comparison.

Run: uv run python -u scripts/heldout_router.py
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

OUT = Path("runs/heldout_router.json")


def judge(reader, prop, d) -> dict:
    """One document: what each system said, and whether it was right."""
    gold = [g for g in d[REL] if g]
    res = reader.run(d["intro"], query=d.get("title", ""))
    best = None
    for i, c in enumerate(res.claims):
        v = c.roles.get("value")
        if c.predicate == REL and isinstance(v, EntityRef):
            if best is None or res.confidence_of(i) > best[0]:
                best = (res.confidence_of(i), v.id)
    cands = [(m.text, m.start, m.end)
             for u in _units(d["intro"]) for m in prop.find(u)]
    guess = None
    for m in COP.finditer(d["intro"]):
        near = [c for c in cands
                if 0 <= c[1] - m.end() <= WINDOW and agentive(c[0])]
        if near:
            guess = max(near, key=lambda c: (c[2], len(c[0])))[0]
            break
    return {"conf": best[0] if best else 0.0,
            "r": bool(best) and norm(best[1]) in [norm(g) for g in gold],
            "f": hit(guess, gold),
            "agree": bool(best) and guess is not None
            and norm(best[1]) == norm(guess),
            "has_f": guess is not None}


def route(rows, thr):
    """Believe the reader unless it disagrees with the floor and is unsure."""
    return sum((x["f"] if (not x["agree"] and x["has_f"] and x["conf"] < thr)
                else x["r"]) for x in rows) / max(1, len(rows))


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    people = person_nouns()
    prop = PhraseMentions(people)
    orig = PhraseMentions.induce
    out = {}

    for slice_ in ("unseen", "seen"):
        te_rows, ho_rows, is_rows = [], [], []
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

            # fit the threshold on a sample of TRAINING documents only
            fit_rows = [judge(reader, prop, d) for d in tr[:400]]
            grid = sorted({x["conf"] for x in fit_rows} | {0.0, 1.0})
            thr = max(grid, key=lambda t: route(fit_rows, t))

            rows = [judge(reader, prop, d) for d in te]
            te_rows += rows
            ho_rows.append((rows, thr))

        n = len(te_rows)
        rd = sum(x["r"] for x in te_rows) / max(1, n)
        fl = sum(x["f"] for x in te_rows) / max(1, n)
        orc = sum(x["r"] or x["f"] for x in te_rows) / max(1, n)
        # held-out: each fold routed with ITS OWN training-fitted threshold
        ho = sum(route(rows, t) * len(rows) for rows, t in ho_rows) / max(1, n)
        # in-sample, for comparison with the selector arm
        confs = sorted(x["conf"] for x in te_rows
                       if not x["agree"] and x["has_f"])
        ins = route(te_rows, confs[len(confs) // 2] if confs else 0.0)
        # agreement-only: nothing fitted anywhere
        agr = sum((x["f"] if (not x["agree"] and x["has_f"]) else x["r"])
                  for x in te_rows) / max(1, n)

        base = max(rd, fl)
        def cap(v):
            return (v - base) / (orc - base) if orc > base else float("nan")

        out[slice_] = {"n": n, "reader": rd, "floor": fl, "oracle": orc,
                       "agreement": agr, "heldout": ho, "insample": ins,
                       "cap_agreement": cap(agr), "cap_heldout": cap(ho),
                       "cap_insample": cap(ins),
                       "thresholds": [t for _, t in ho_rows]}
        v = out[slice_]
        print(f"\n=== {slice_}  n={n}")
        print(f"  reader {rd:.3f}   floor {fl:.3f}   oracle {orc:.3f}")
        print(f"  {'router':<12}{'rate':>8}{'vs best':>10}{'headroom':>11}")
        for k in ("agreement", "heldout", "insample"):
            print(f"  {k:<12}{v[k]:8.3f}{v[k] - base:+10.3f}"
                  f"{cap(v[k]):11.1%}")
        print(f"  thresholds fitted per fold: "
              f"{[round(t, 3) for t in v['thresholds']]}")

    print("\n--- verdict")
    u = out["unseen"]
    if u["heldout"] > u["floor"]:
        print(f"the router SURVIVES holding out the threshold: "
              f"{u['heldout']:.3f} against the best single system "
              f"{max(u['reader'], u['floor']):.3f}")
    else:
        print(f"the router does NOT survive: held out it scores "
              f"{u['heldout']:.3f}, at or below the floor's {u['floor']:.3f}. "
              f"The 0.370 was the in-sample threshold.")
    print(f"in-sample {u['cap_insample']:.1%} -> held out "
          f"{u['cap_heldout']:.1%} of the oracle headroom; "
          f"agreement-only {u['cap_agreement']:.1%}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
