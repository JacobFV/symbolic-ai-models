"""Can the reader read an occupation it has never seen? The mechanism is there.

The control arm found `occupation` collapses to **exactly 0.000** on unseen
values, with **proposal 0.000** and containment still **0.582** -- the answer is
in the text and the proposer never offers it. The finding named the refuter: a
proposer that raises proposal but leaves the end-to-end rate near zero, which
would mean the classifier and ranker silently depended on the induced vocabulary
too.

Before building a new proposer, notice `PhraseMentions` already carries the
mechanism. It induces **productive suffixes** -- `... industry`, `... services` --
so an unseen `pharmaceutical industry` is proposable from a suffix it has seen.
The gate is `min_share=0.15`: a suffix must appear in 15% of fillers. That
threshold was set for `industry`, an inventory of a handful of values. Occupations
number **494 across 847 articles**, so almost nothing clears 15% and the mechanism
never fires.

So this is not a new component. It is asking whether the existing generalisation
mechanism works when its threshold is not tuned for a five-value inventory, on
the slice that currently reads zero.

Reported as a curve, deliberately. Picking a `min_share` off this table would be
tuning a knob against the measurement, which is the trap this repo has walked
into before; the question here is whether the mechanism moves at all.

Run: uv run python -u scripts/suffix_generalisation.py
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

OUT = Path("runs/suffix_generalisation.json")
SHARES = (0.15, 0.05, 0.02, 0.01, 0.005, 0.002)


def scored(train, test, share):
    """`score` with the proposer's suffix gate opened to `share`."""
    orig = PhraseMentions.induce

    def induce(fillers, *, min_share=share, capitalised=True,
               alias_heads=False):
        return orig(fillers, min_share=share, capitalised=capitalised,
                    alias_heads=alias_heads)

    PhraseMentions.induce = staticmethod(induce)
    try:
        return score(train, test)
    finally:
        PhraseMentions.induce = orig


def main() -> None:
    R.RELS = RELATIONS
    docs = [d for d in corpus() if d.get(REL)]
    vocab = sorted({v for d in docs for v in d[REL]})
    print(f"{len(docs)} biographies, {len(vocab)} distinct occupations")

    out = {}
    print(f"\n{'min_share':>10}  {'slice':<8}{'suffixes':>9}{'contain':>9}"
          f"{'propose':>9}{'clf':>7}{'rank':>7}{'measured':>10}{'n':>7}")
    for share in SHARES:
        nsuf = len(PhraseMentions.induce(
            [v for d in docs for v in d[REL]], min_share=share).suffixes)
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
                if te and tr:
                    rows.append(scored(tr, te, share))
            if not rows:
                continue
            v = pooled(rows)
            out[f"{share}:{name}"] = v | {"suffixes": nsuf}
            print(f"{share:>10}  {name:<8}{nsuf:9d}{v['containment']:9.3f}"
                  f"{v['proposal']:9.3f}{v['classifier']:7.3f}"
                  f"{v['ranker']:7.3f}{v['measured']:10.3f}{v['n']:7d}")

    print("\n--- the refuter, stated in the control finding")
    base_u = out.get("0.15:unseen", {}).get("measured", 0.0)
    best = max((v for k, v in out.items() if k.endswith("unseen")),
               key=lambda v: v["measured"], default=None)
    if best:
        print(f"unseen: {base_u:.3f} at the shipped gate -> {best['measured']:.3f} "
              f"at its best gate, with proposal "
              f"{out['0.15:unseen']['proposal']:.3f} -> {best['proposal']:.3f}")
        if best["proposal"] > 0.30 and best["measured"] < 0.10:
            print("REFUTER FIRES: proposal recovers and the rate does not. The "
                  "classifier/ranker depended on the induced vocabulary too.")
        elif best["measured"] >= 0.10:
            print("Refuter does NOT fire: the rate follows the proposer, so the "
                  "limit really was the one component.")
        else:
            print("Inconclusive: the proposer itself did not recover.")
    s0 = out.get("0.15:seen", {}).get("measured", 0.0)
    s1 = min((v["measured"] for k, v in out.items() if k.endswith("seen")
              and not k.endswith("unseen")), default=0.0)
    print(f"seen slice cost: {s0:.3f} at the shipped gate, worst {s1:.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
