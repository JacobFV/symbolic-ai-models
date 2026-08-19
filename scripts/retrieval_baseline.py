"""What retrieval can and cannot do on a two-hop question, priced honestly.

`scripts/multi_hop_world.py` compares a persistent world against an API that
re-reads all 1,661 articles per query, and its own note says that comparison is
unfair: nobody deploys that. A retrieval system fetches a handful of documents
and pays for a handful. This measures the fair version.

The measurement is not about cost first, it is about **what retrieval can find**.
A two-hop question — *who ultimately controls RCA Records?* — needs the RCA
article and the Sony Music article. The first is retrievable from the question.
**The second is only retrievable once you know the answer to the first**, because
the question does not contain the string "Sony Music" and the Sony Music article
does not contain "RCA".

Three arms, all over the same corpus, with BM25 (pure Python, no new dependency)
as the retriever:

    single-shot   retrieve top-k for the question, read whatever comes back
    iterative     retrieve, read hop 1, retrieve AGAIN with hop 1's answer,
                  read hop 2 -- the standard multi-hop RAG loop
    persistent    the world, already joined, answering from an index

Predicted before running:

- **Single-shot retrieval finds the hop-2 article almost never.** The question
  names the subject and the hop-2 article is about a different company that the
  subject's name does not appear in. Expect the grandparent's article in the top
  5 for well under 20% of chains, and that is a hard ceiling on single-shot
  accuracy regardless of the reader.
- **Iterative retrieval finds it**, at two retrievals and two reads — and it
  inherits the *same* `p₁` the symbolic reader has, because the second retrieval
  is keyed on hop 1's extracted answer. Multi-hop RAG does not remove the
  extraction problem; it moves it into the retrieval loop.
- **Retrieval is cheap enough to change the cost verdict at low query counts** and
  not at high ones, because it pays per query and ingestion pays once.

Run: uv run python -u scripts/retrieval_baseline.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.cost import Price

from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_scale.jsonl")
OUT = Path("runs/retrieval_baseline.json")
TOPK = (1, 3, 5, 10)
API_USD_PER_MTOK = 3.0
_WORD = re.compile(r"[a-z0-9]+")


class BM25:
    """Okapi BM25. The standard sparse retriever, in forty lines.

    Chosen over an embedding index deliberately: it needs no model, no GPU and no
    pretrained weights, so the comparison is against something this repo could
    actually deploy beside its kernels. A dense retriever would find more, and
    the *structural* limit measured here -- that hop 2 is not reachable from the
    question -- is not one a better similarity function repairs.
    """

    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.toks = [_WORD.findall(d.lower()) for d in docs]
        self.len = [len(t) for t in self.toks]
        self.avg = sum(self.len) / max(1, len(self.len))
        self.df: Counter = Counter()
        self.tf: list[Counter] = []
        for t in self.toks:
            c = Counter(t)
            self.tf.append(c)
            self.df.update(c.keys())
        self.n = len(docs)
        self.idf = {w: math.log(1 + (self.n - d + 0.5) / (d + 0.5))
                    for w, d in self.df.items()}
        self.post: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.tf):
            for w in c:
                self.post[w].append(i)

    def search(self, query: str, k: int = 10) -> list[int]:
        scores: dict[int, float] = defaultdict(float)
        for w in _WORD.findall(query.lower()):
            idf = self.idf.get(w)
            if idf is None:
                continue
            for i in self.post[w]:
                f = self.tf[i][w]
                denom = f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg)
                scores[i] += idf * f * (self.k1 + 1) / denom
        return sorted(scores, key=lambda i: -scores[i])[:k]


def main() -> None:
    rows = [json.loads(x) for x in CORPUS.read_text().splitlines() if x.strip()]
    by_qid = {r["qid"]: r for r in rows}
    pos = {r["qid"]: i for i, r in enumerate(rows)}
    edge = {r["qid"]: r["current_ids"][0] for r in rows if r.get("current_ids")}
    chains = [(q, edge[q], edge[edge[q]]) for q in edge
              if edge[q] in edge and edge[q] in by_qid]
    index = BM25([r["intro"] for r in rows])
    print(f"{len(rows)} articles indexed, {len(chains)} two-hop chains")

    found = {k: {"hop1": 0, "hop2": 0, "both": 0} for k in TOPK}
    iterative = {k: 0 for k in TOPK}
    for q, p, g in chains:
        title = by_qid[q]["title"]
        gold_parent = (by_qid[q].get("current") or [""])[0]
        for k in TOPK:
            hits = set(index.search(title, k))
            h1 = pos[q] in hits
            h2 = pos[p] in hits
            found[k]["hop1"] += h1
            found[k]["hop2"] += h2
            found[k]["both"] += h1 and h2
            # Iterative: the second retrieval is keyed on hop 1's ANSWER, which
            # is why this loop cannot escape the extraction problem -- here it is
            # given the gold answer, so the number is retrieval's CEILING.
            iterative[k] += h1 and pos[p] in set(index.search(gold_parent, k))

    n = len(chains)
    print(f"\n    {'top-k':>6} {'hop1 found':>11} {'hop2 found':>11} "
          f"{'BOTH':>7} {'iterative (gold hop1)':>22}")
    for k in TOPK:
        f = found[k]
        print(f"    {k:>6} {f['hop1'] / n:>11.3f} {f['hop2'] / n:>11.3f} "
              f"{f['both'] / n:>7.3f} {iterative[k] / n:>22.3f}")

    # ---- cost, per query ------------------------------------------------
    price = Price()
    toks = [len(r["intro"]) / 4 for r in rows]
    avg_tok = sum(toks) / len(toks)
    single = API_USD_PER_MTOK * (5 * avg_tok) / 1e6
    itera = API_USD_PER_MTOK * (10 * avg_tok) / 1e6
    ingest_usd = 1.16e-04          # measured by scripts/multi_hop_world.py
    print(f"\n    average article {avg_tok:.0f} tokens")
    print(f"    single-shot RAG, 5 articles:   ${single:.2e} per query")
    print(f"    iterative RAG, 2x5 articles:   ${itera:.2e} per query")
    print(f"    persistent world ingestion:    ${ingest_usd:.2e} ONCE")
    print(f"    the world is cheaper from query "
          f"{math.ceil(ingest_usd / itera)} onward")
    for n_q in (1, 10, 100, 10_000):
        print(f"      at {n_q:>6,} queries: world ${ingest_usd / n_q:.2e}/query "
              f"vs iterative RAG ${itera:.2e}/query "
              f"({itera / (ingest_usd / n_q):,.1f}x)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"chains": n, "found": {str(k): v for k, v in found.items()},
         "iterative_gold_hop1": {str(k): v / n for k, v in iterative.items()},
         "usd_single_shot": single, "usd_iterative": itera,
         "usd_world_ingest": ingest_usd}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
