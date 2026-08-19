"""What a persistent world should refuse to write down, and whether composition holds along the way.

A persistent world commits: a wrong claim is consulted forever, hub errors are
the expensive ones, and the cheap corroboration check turned out empty. The one
lever left is **not writing the claim** — ingest only what the reader believes
above a threshold and accept lower coverage for higher precision.

Sweeping that threshold does two things at once.

**The practical one.** Does selectivity help *composed* queries more than simple
ones? A two-hop answer needs both links right, so an argument can be made either
way: errors multiply, so precision should matter more; but a missing link fails
the chain exactly as a wrong one does, so refusing may cost as much as it saves.

**The scientific one, and it is the better reason to run this.** The composition
law was confirmed at a single operating point — the learned reader's two-hop
accuracy landed at 0.031 against `p₁²` = 0.032. The hand reader **violated** it at
1.93x, because pattern success clumps. Sweeping the threshold traces the whole
precision/coverage curve and asks whether `two-hop ≈ (one-hop)²` holds *along*
it. One point is an anecdote; a curve is a law.

Predicted before running:

- **`two-hop ≈ (one-hop)²` across the sweep**, because thresholding the belief
  should not correlate the two hops — it removes claims by confidence, and a
  chain's two links are read from different articles. Expect the ratio to stay
  near 1 across the range.
- **No interior maximum in two-hop accuracy.** If composition holds, maximising
  the composed query is the same as maximising the simple one, so selectivity
  buys nothing *specific* to depth. That is worth knowing precisely because the
  opposite is the intuition.
- Refuted if the ratio drifts systematically with the threshold — that would mean
  confidence is correlated across articles (the reader is confident about the
  same *kinds* of company at both ends), which is the hand reader's failure mode
  appearing in the learned one under selection.

Run: uv run python -u scripts/selective_ingestion.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_hop_world import link
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_scale.jsonl")
OUT = Path("runs/selective_ingestion.json")
FOLDS = 4
THRESHOLDS = (0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    edge = {r["qid"]: r["current_ids"][0] for r in rows if r.get("current_ids")}
    chains = [(q, edge[q], edge[edge[q]]) for q in edge
              if edge[q] in edge and edge[q] in by_qid]
    index: dict[str, str] = {}
    for r in rows:
        for key in (r["title"], norm(r["title"])):
            index.setdefault(key, r["qid"])

    R.PARENTS = CORPUS
    docs = R.corpus()
    #: qid -> (belief, parent string). Read ONCE; the sweep re-thresholds the
    #: same beliefs, so every row is the same reading seen at a different
    #: ingestion policy rather than a different fit.
    best: dict[str, tuple[float, str]] = {}
    for fold in range(FOLDS):
        te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
        tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
        reader = LearnedSpanReader(
            model="logistic", mentions=CapitalisedMentions(),
            extra_features=R.extra(),
            extra_role_features=R.role_frame_features).fit(
            [R.supervise_distant(d) for d in tr])
        for d in te:
            res = reader.run(d["intro"], query=d.get("title", ""))
            top = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == "parent" and isinstance(v, EntityRef):
                    b = res.confidence_of(i)
                    if top is None or b > top[0]:
                        top = (b, v.id)
            if top:
                best[d["qid"]] = top

    print(f"{len(rows)} articles, {len(best)} with a parent claim, "
          f"{len(chains)} two-hop chains")
    print(f"\n    {'tau':>5} {'ingested':>9} {'1-hop corr':>11} {'1-hop prec':>11} "
          f"{'2-hop corr':>11} {'(1-hop)^2':>11} {'ratio':>7}")
    out = []
    for tau in THRESHOLDS:
        world = {q: a for q, (b, a) in best.items() if b >= tau}
        # one hop, over the SAME 191 chains, so the two columns are comparable
        ok1 = {q: (q in world and norm(world[q]) in
                   [norm(x) for x in (by_qid[q].get("current") or [])])
               for q, _, _ in chains}
        p1 = sum(ok1.values()) / len(chains)
        answered = sum(1 for q, _, _ in chains if q in world)
        prec = (sum(ok1.values()) / answered) if answered else float("nan")

        two = 0
        for q, p, g in chains:
            if not ok1[q]:
                continue
            mid = link(world.get(q), index)
            if mid is None or mid not in world:
                continue
            gold2 = [norm(x) for x in (by_qid[mid].get("current") or [])]
            two += norm(world[mid]) in gold2
        p2 = two / len(chains)
        ratio = (p2 / (p1 * p1)) if p1 else float("nan")
        print(f"    {tau:5.2f} {len(world):9d} {p1:11.3f} {prec:11.3f} "
              f"{p2:11.3f} {p1 * p1:11.3f} {ratio:7.2f}")
        out.append({"tau": tau, "ingested": len(world), "one_hop": p1,
                    "precision": prec, "two_hop": p2, "square": p1 * p1,
                    "ratio": ratio})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
