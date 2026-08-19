"""One world from 1,661 articles, and a question no article answers.

*Who ultimately controls RCA Records?* The RCA Records article says Sony Music.
Nothing in it says who owns Sony Music — that is in a different article, written
by someone else, that never mentions RCA. The answer exists only in a world
assembled from both, which is the capability this programme is for and the thing
a prompt-window reader cannot do without being handed both documents.

**191 two-hop chains lie entirely inside the corpus** (118 distinct
grandparents), so the query is scoreable against Wikidata rather than judged.

It is also the sharpest available test of the composition law. Earlier arms
measured that a composed query multiplies reader error — `parent` at 0.149 and
`country` at 0.181 gave 0.007 F1 on their join. Here **both hops are the same
relation read by the same reader**, so `p₁ = p₂` exactly and the prediction is
unambiguous.

Three ways to lose an answer, separated rather than pooled:

    extraction   hop 1 or hop 2 read wrong
    linking      hop 1 read RIGHT but its string not matched to the article
                 that is about that entity -- cross-document entity resolution,
                 which single-hop questions never needed and this one requires
    composition  both hops right, the chain still wrong

Predicted before running:

- **Two-hop accuracy ≈ (one-hop)²** if the hops are independent. For the learned
  reader that is ~0.03 from a one-hop of ~0.18; for the hand reader ~0.15 from
  0.39. A large positive deviation would mean the hops are correlated — the
  articles a reader can read are the same kind of article at both ends.
- **Linking is not free.** The earlier finding that entity resolution "buys
  nothing" was measured where nothing needed it; here it is load-bearing, and
  exact title matching should lose 20-40% of correctly-read parents.
- Refuted if two-hop lands near one-hop, which would mean the second hop is
  nearly free and composition does not multiply.

Run: uv run python -u scripts/multi_hop_world.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.cost import Price
from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm, read_parent

CORPUS = Path("data/artifacts/wikipedia_parents_scale.jsonl")
OUT = Path("runs/multi_hop_world.json")
FOLDS = 4


def link(name: str, index: dict[str, str]) -> str | None:
    """A read string to the article that is ABOUT that entity.

    Exact, then case-folded, then the longest title that is a prefix of the
    string or contains it -- `Sony Music` against `Sony Music Entertainment`.
    Nothing here is tuned: each fallback is strictly weaker than the last and
    they are applied in that order.
    """
    if not name:
        return None
    for key in (name, norm(name)):
        if key in index:
            return index[key]
    hits = [t for t in index if t and (t in norm(name) or norm(name) in t)]
    return index[max(hits, key=len)] if hits else None


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    edge = {r["qid"]: r["current_ids"][0] for r in rows if r.get("current_ids")}
    chains = [(q, edge[q], edge[edge[q]]) for q in edge
              if edge[q] in edge and edge[q] in by_qid]
    print(f"{len(rows)} articles, {len(chains)} two-hop chains inside the corpus")

    #: title -> qid, for the cross-document join. Built from the corpus itself.
    index = {}
    for r in rows:
        for key in (r["title"], norm(r["title"])):
            index.setdefault(key, r["qid"])

    R.PARENTS = CORPUS
    docs = R.corpus()
    by_doc = {d["qid"]: d for d in docs}

    # ---- read every article once, cross-validated -----------------------
    read: dict[str, dict[str, str | None]] = defaultdict(dict)
    t0 = time.perf_counter()
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
            read[d["qid"]]["learned"] = best[1] if best else None
    ingest_s = time.perf_counter() - t0
    for d in docs:
        read[d["qid"]]["hand"] = read_parent(d["intro"])

    # ---- one hop, then two ----------------------------------------------
    out = {}
    for arm in ("learned", "hand"):
        hop1 = hop2 = linked = both_right = 0
        for q, p, g in chains:
            gold1 = [norm(x) for x in (by_qid[q].get("current") or [])]
            gold2 = [norm(x) for x in (by_qid[p].get("current") or [])]
            a1 = read[q].get(arm)
            ok1 = bool(a1) and norm(a1) in gold1
            hop1 += ok1
            mid = link(a1, index) if a1 else None
            linked += ok1 and mid is not None
            if not mid:
                continue
            a2 = read.get(mid, {}).get(arm)
            ok2 = bool(a2) and norm(a2) in [
                norm(x) for x in (by_qid[mid].get("current") or [])]
            both_right += ok1 and ok2
            hop2 += bool(a2) and norm(a2) in gold2 and ok1
        n = len(chains)
        p1 = hop1 / n
        out[arm] = {"one_hop": p1, "two_hop": hop2 / n,
                    "predicted_square": p1 * p1,
                    "link_rate": linked / max(1, hop1),
                    "both_hops_right": both_right / n}
        print(f"\n    {arm}")
        print(f"      one hop            {p1:.3f}")
        print(f"      two hop            {hop2 / n:.3f}   "
              f"(independent prediction {p1 * p1:.3f})")
        print(f"      linked | hop1 ok   {linked / max(1, hop1):.3f}")
        print(f"      both hops read ok  {both_right / n:.3f}")

    # ---- what the world costs, and what a query costs after it ----------
    price = Price()
    chars = sum(len(d["intro"]) for d in docs)
    ingest_usd = ingest_s * price.usd_per_core_second()
    print(f"\n    ingestion: {len(docs)} articles, {chars / 4:,.0f} tokens, "
          f"{ingest_s:.1f} s = ${ingest_usd:.2e} ONCE")
    for n_q in (1, 100, 10_000, 1_000_000):
        print(f"      amortised over {n_q:>9,} queries: "
              f"${ingest_usd / n_q:.2e} per query")
    api = 3.0 * (chars / 4) / 1e6
    print(f"    a $3/Mtok API re-reading the corpus per query: ${api:.3f} EACH; "
          f"the world pays that once at {api / ingest_usd:,.0f}x less")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"chains": len(chains), "arms": out,
                               "ingest_seconds": ingest_s,
                               "ingest_usd": ingest_usd,
                               "api_usd_per_full_reread": api}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
