"""Does reading a child correctly predict reading its parent correctly?

The clumping claim — a hand-written pattern reader beats independence on two-hop
queries because pattern success clumps on canonically-phrased articles — rests on
**20 two-hop successes**, and the promotion queue says so. But the *mechanism* it
asserts is a correlation between neighbouring articles, and that can be measured
on **every chain pair**, whether or not both hops succeeded.

For each (child, parent) pair with both articles in the corpus, a 2x2 table of
child-read-correctly against parent-read-correctly. 415 pairs, of which 50-73
have a correct child depending on the reader — three times the events the ratio
test had, and it tests the mechanism rather than its consequence.

Predicted: the hand reader shows `P(parent ok | child ok) > P(parent ok)` and the
learned reader does not. Refuted if the hand reader's conditional matches its
marginal, which would mean the two-hop excess came from somewhere other than
neighbour correlation and the mechanism story was invention.

Run: uv run python -u scripts/neighbour_correlation.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm, read_parent

CORPUS = Path(sys.argv[sys.argv.index("--corpus") + 1]
              if "--corpus" in sys.argv
              else "data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/neighbour_correlation.json")
FOLDS = 4


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    edge = {r["qid"]: (r.get("current_ids") or [None])[0] for r in rows}
    pairs = [(q, edge[q]) for q in edge
             if edge.get(q) in by_qid and edge.get(edge[q])]

    R.PARENTS = CORPUS
    docs = R.corpus()
    read: dict[str, dict[str, str | None]] = {}
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        reader = LearnedSpanReader(
            mentions=CapitalisedMentions(), extra_features=R.extra(),
            extra_role_features=R.role_frame_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            res = reader.run(d["intro"], query=d.get("title", ""))
            best = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == "parent" and isinstance(v, EntityRef):
                    if best is None or res.confidence_of(i) > best[0]:
                        best = (res.confidence_of(i), v.id)
            read.setdefault(d["qid"], {})["learned"] = best[1] if best else None
    for d in docs:
        read.setdefault(d["qid"], {})["hand"] = read_parent(d["intro"])

    def ok(arm: str, q: str) -> bool:
        a = read.get(q, {}).get(arm)
        return bool(a) and norm(a) in [norm(x)
                                       for x in (by_qid[q].get("current") or [])]

    print(f"{len(pairs)} (child, parent) pairs with both articles present\n")
    print(f"    {'reader':<10}{'P(parent)':>11}{'| child ok':>12}"
          f"{'| child bad':>13}{'odds ratio':>12}{'chi2 p':>9}")
    out = {}
    for arm in ("learned", "hand"):
        a = b = c = d = 0
        for q, p in pairs:
            ci, pi = ok(arm, q), ok(arm, p)
            a, b, c, d = (a + (ci and pi), b + (ci and not pi),
                          c + (not ci and pi), d + (not ci and not pi))
        n = a + b + c + d
        # Yates-corrected chi-square: the smallest cell here is 6.
        num = n * (abs(a * d - b * c) - n / 2) ** 2
        den = (a + b) * (c + d) * (a + c) * (b + d)
        chi = num / den if den else 0.0
        pv = math.erfc(math.sqrt(chi / 2)) if chi > 0 else 1.0
        odds = (a * d) / (b * c) if b * c else float("inf")
        print(f"    {arm:<10}{(a + c) / n:11.3f}{a / max(1, a + b):12.3f}"
              f"{c / max(1, c + d):13.3f}{odds:12.2f}{pv:9.3f}")
        print(f"      2x2: both {a}, child only {b}, parent only {c}, "
              f"neither {d}")
        out[arm] = {"both": a, "child_only": b, "parent_only": c, "neither": d,
                    "marginal": (a + c) / n, "cond_child_ok": a / max(1, a + b),
                    "cond_child_bad": c / max(1, c + d), "odds_ratio": odds,
                    "chi2_p": pv}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"pairs": len(pairs), "arms": out}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
