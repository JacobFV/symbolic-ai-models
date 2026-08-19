"""A wrong fact extracted once is also consulted a million times.

The persistence argument is that ingestion amortises: extract a fact once, answer
with it forever, and the per-query cost goes to nothing. Measured, and it holds —
$1.16e-04 once against $6.32e-03 per iterative-RAG query.

**The same arithmetic applies to the errors.** A context-window reader gets a
fresh chance at every query; a persistent world commits. A wrong claim about a
hub entity is not one wrong answer, it is every answer that passes through it.
Nobody has priced that, here or in the note that made the amortisation argument,
and it is the honest counter to it.

What is measured:

    fan-out          how many of the queries this world serves depend on each
                     extracted claim
    blast radius     the fan-out distribution of the claims that are WRONG
    weighted rate    accuracy weighted by how often each claim is consulted,
                     against the unweighted rate everything so far has quoted

The query set is the one the corpus actually supports: **1,661 one-hop questions**
(*who owns X?*) and **191 two-hop questions** (*who ultimately controls X?*). A
one-hop query depends on one claim; a two-hop query depends on two, so the
parent's claim is consulted once for its own article and once for every child
that reaches it.

Predicted before running:

- **Fan-out is heavy-tailed.** Most claims serve one query; a few hub entities
  serve dozens. The largest grandparent group in this corpus has ten children, so
  expect a maximum fan-out above ten and a mean near one.
- **Query-weighted accuracy differs from unweighted**, and the direction is the
  interesting part. Hubs are named in many articles, so a reader may read them
  *better* — in which case persistence is safer than the unweighted rate says. If
  hubs read worse, every published accuracy here overstates what the world
  actually serves.
- Refuted if fan-out is flat, in which case one wrong claim is one wrong answer
  and the amortisation argument carries no hidden liability.

Run: uv run python -u scripts/error_blast_radius.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_hop_world import link
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_scale.jsonl")
OUT = Path("runs/error_blast_radius.json")
FOLDS = 4


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
    print(f"{len(rows)} articles, {len(chains)} two-hop chains")

    read: dict[str, str | None] = {}
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
            read[d["qid"]] = best[1] if best else None

    correct = {q: bool(a) and norm(a) in
               [norm(x) for x in (by_qid[q].get("current") or [])]
               for q, a in read.items()}

    # ---- fan-out: how many queries consult each article's claim ---------
    fan: Counter = Counter()
    for q in read:                      # its own one-hop question
        fan[q] += 1
    for q, p, g in chains:              # the chain consults q's and p's claims
        fan[q] += 1
        mid = link(read.get(q), index) if read.get(q) else None
        if mid:
            fan[mid] += 1

    served = sum(fan.values())
    vals = sorted(fan.values(), reverse=True)
    print(f"\n    {served:,} query-consultations over {len(fan):,} claims")
    print(f"    fan-out: mean {statistics.mean(vals):.2f}, median "
          f"{statistics.median(vals):.0f}, max {vals[0]}, "
          f"top-1% share {sum(vals[:max(1, len(vals) // 100)]) / served:.3f}")

    # ---- the blast radius of the wrong ones -----------------------------
    wrong = [fan[q] for q in fan if not correct.get(q, False)]
    right = [fan[q] for q in fan if correct.get(q, False)]
    bad_consultations = sum(wrong)
    print(f"\n    unweighted accuracy      "
          f"{sum(correct.values()) / len(correct):.4f}")
    print(f"    CONSULTATION-weighted    "
          f"{sum(right) / served:.4f}")
    print(f"    fan-out of wrong claims: mean {statistics.mean(wrong):.2f}; "
          f"of right claims: mean {statistics.mean(right):.2f}")
    print(f"    {bad_consultations:,} of {served:,} consultations hit a wrong "
          f"claim ({bad_consultations / served:.3f})")

    # ---- are hubs read better or worse? ---------------------------------
    print(f"\n    {'fan-out':>9} {'claims':>8} {'accuracy':>9}")
    buckets = defaultdict(list)
    for q, f in fan.items():
        buckets[min(f, 4)].append(correct.get(q, False))
    for f in sorted(buckets):
        b = buckets[f]
        label = f"{f}" if f < 4 else "4+"
        print(f"    {label:>9} {len(b):8d} {sum(b) / len(b):9.3f}")

    # ---- the same world under a DEEPER query mix ------------------------
    # The mix above is 90% one-hop, so almost every claim is consulted once and
    # no fan-out can concentrate. An agent that asks "who ultimately controls X"
    # consults every claim on the chain, and the claims near the root are
    # consulted by every descendant. Same world, same reader, different question
    # distribution -- and the liability persistence carries is a property of the
    # mix, not of persistence.
    gold_edge = {r["qid"]: (r.get("current_ids") or [None])[0] for r in rows}
    deep: Counter = Counter()
    for q in read:
        node, seen = q, set()
        while node is not None and node not in seen and node in by_qid:
            seen.add(node)
            deep[node] += 1
            node = gold_edge.get(node)
    dserved = sum(deep.values())
    dright = sum(f for q, f in deep.items() if correct.get(q, False))
    indeg: Counter = Counter()
    for q, par in gold_edge.items():
        if par:
            indeg[par] += 1
    hub = [correct.get(q, False) for q in read if indeg.get(q, 0) >= 1]
    flat = [correct.get(q, False) for q in read if indeg.get(q, 0) == 0]
    print(f"\n    DEEPER MIX -- full ancestor chains, {dserved:,} consultations")
    print(f"      unweighted accuracy    {sum(correct.values()) / len(correct):.4f}")
    print(f"      consultation-weighted  {dright / dserved:.4f}")
    print(f"      hub articles (in-degree>=1): {len(hub)}, accuracy "
          f"{sum(hub) / len(hub):.3f}  against {sum(flat) / len(flat):.3f} "
          f"for the rest")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "claims": len(fan), "consultations": served,
        "unweighted_accuracy": sum(correct.values()) / len(correct),
        "weighted_accuracy": sum(right) / served,
        "fanout_mean": statistics.mean(vals), "fanout_max": vals[0],
        "fanout_top1pct_share": sum(vals[:max(1, len(vals) // 100)]) / served,
        "accuracy_by_fanout": {str(f): sum(b) / len(b)
                               for f, b in sorted(buckets.items())},
        "deep_consultations": dserved,
        "deep_weighted_accuracy": dright / dserved,
        "hub_accuracy": sum(hub) / len(hub),
        "non_hub_accuracy": sum(flat) / len(flat),
    }, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
