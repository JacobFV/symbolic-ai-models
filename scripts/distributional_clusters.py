"""Does a distributed representation move the ceiling? The cheapest possible test.

Eight levers are closed on the real-text reader and supervision has been excluded
as the explanation, which leaves the **representation**. The expensive version of
that hypothesis is a pretrained encoder, which `CLAUDE.md` scopes out. This is the
cheap version, and it needs no dependency the repo does not have: **distributional
word clusters induced from the corpus itself.**

Co-occurrence counts over the 2,502 intros, PPMI-weighted, truncated by SVD to 64
dimensions, k-means into clusters. A word's cluster id then becomes a feature
beside the word itself, at the classifier and the ranker. It is the classic
Brown-cluster trick and it is a genuine distributed representation — just one
learned from 2.3 MB of text rather than from the internet.

Why it might work where WordNet did not: supersenses gave `subsidiary`,
`division` and `unit` the category `noun.group` **along with every other group
noun in the language**, and the feature fired in every sentence. A distributional
cluster is induced from *this* corpus, so `subsidiary`/`division`/`unit`/`arm`
cluster by the contexts they actually occur in here, and nothing else joins them.

Predicted before running: a **modest gain** on `parent`, 0.182 → 0.19–0.22,
because clustering lets a trigger seen twice borrow evidence from a trigger seen
forty times. Against it: the content-word triggers already have a mean count of
4.40 at this corpus size, so there may be little left to share. If clusters buy
nothing, the cheap version of the representation hypothesis is dead and the
expensive one is the only one left standing — which is a useful thing to know
before spending on it.

Run: uv run python -u scripts/distributional_clusters.py
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/distributional_clusters.json")
FOLDS = 4
VOCAB, CONTEXT, DIMS, CLUSTERS, WINDOW = 6000, 3000, 64, 256, 5
_WORD = __import__("re").compile(r"[a-z][a-z'-]+")


def induce_clusters(texts: list[str]) -> dict[str, int]:
    """PPMI + SVD + k-means, in numpy. No dependency the repo lacks."""
    toks = [_WORD.findall(t.lower()) for t in texts]
    freq: Counter = Counter(w for t in toks for w in t)
    vocab = [w for w, _ in freq.most_common(VOCAB)]
    ctx = [w for w, _ in freq.most_common(CONTEXT)]
    vi = {w: i for i, w in enumerate(vocab)}
    ci = {w: i for i, w in enumerate(ctx)}
    M = np.zeros((len(vocab), len(ctx)), dtype=np.float32)
    for t in toks:
        for i, w in enumerate(t):
            r = vi.get(w)
            if r is None:
                continue
            for j in range(max(0, i - WINDOW), min(len(t), i + WINDOW + 1)):
                if j == i:
                    continue
                c = ci.get(t[j])
                if c is not None:
                    M[r, c] += 1.0
    total = M.sum()
    if total == 0:
        return {}
    # Positive pointwise mutual information: the standard way to stop raw counts
    # from making every word look like "the".
    row, col = M.sum(1, keepdims=True), M.sum(0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((M * total) / np.maximum(row * col, 1e-9))
    P = np.maximum(np.nan_to_num(pmi), 0.0)
    U, S, _ = np.linalg.svd(P, full_matrices=False)
    E = U[:, :DIMS] * S[:DIMS]
    E /= np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-9)

    rng = np.random.default_rng(19)
    cent = E[rng.choice(len(E), size=min(CLUSTERS, len(E)), replace=False)]
    for _ in range(15):
        assign = np.argmax(E @ cent.T, axis=1)
        for k in range(len(cent)):
            members = E[assign == k]
            if len(members):
                v = members.mean(0)
                cent[k] = v / max(np.linalg.norm(v), 1e-9)
    return {w: int(assign[i]) for w, i in vi.items()}


def main() -> None:
    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()
    print(f"{len(docs)} articles; inducing clusters ...", flush=True)
    clusters = induce_clusters([d["intro"] for d in docs])
    print(f"    {len(clusters)} words in {len(set(clusters.values()))} clusters")
    for probe in ("subsidiary", "division", "unit", "owned", "acquired"):
        k = clusters.get(probe)
        if k is None:
            continue
        near = [w for w, c in clusters.items() if c == k][:9]
        print(f"    {probe:<11} cluster {k:3d}: {', '.join(near)}")

    def cluster_unit_features(u, ments):
        out = []
        inside = {i for m in ments for i in range(m.start, m.end)}
        for t in u.tokens:
            if t.kind != "word" or t.start in inside:
                continue
            k = clusters.get(t.text.lower())
            if k is not None:
                out.append(f"cl={k}")
        return list(dict.fromkeys(out))

    def cluster_role_features(pred, role, cands, j, u):
        base = list(R.role_frame_features(pred, role, cands, j, u))
        t = cands[j]
        words = [w for w in u.tokens if w.kind == "word"]
        prev = max((c.end for c in cands if c.end <= t.start), default=u.start)
        left = [w.text.lower() for w in words if prev <= w.start < t.start]
        ks = [clusters.get(w) for w in left if clusters.get(w) is not None]
        if ks:
            base += [f"clw={ks[-1]}", f"clw2={'_'.join(map(str, ks[-2:]))}"]
        return base

    # `R.extra()` is flag-driven and returns None with no flags; the baseline
    # here is the best reader this session produced, which is frames at the
    # classifier and the ranker.
    arms = {
        "baseline": (R.frame_features, R.role_frame_features),
        "+ clusters": (lambda u, m: list(R.frame_features(u, m))
                       + cluster_unit_features(u, m), cluster_role_features),
    }
    print(f"\n    {'arm':<14}{'coverage':>10}{'correct':>9}{'precision':>11}"
          f"{'k/n':>12}")
    out = {}
    for name, (ef, erf) in arms.items():
        ok = ans = n = 0
        for fold in range(FOLDS):
            te = [d for i, d in enumerate(docs) if i % FOLDS == fold]
            tr = [d for i, d in enumerate(docs) if i % FOLDS != fold]
            reader = LearnedSpanReader(
                mentions=CapitalisedMentions(), extra_features=ef,
                extra_role_features=erf).fit(
                [R.supervise_distant(d) for d in tr])
            for d in te:
                gold = [norm(x) for x in (d.get("parent") or [])]
                if not gold:
                    continue
                n += 1
                res = reader.run(d["intro"], query=d.get("title", ""))
                best = None
                for i, c in enumerate(res.claims):
                    v = c.roles.get("value")
                    if c.predicate == "parent" and isinstance(v, EntityRef):
                        if best is None or res.confidence_of(i) > best[0]:
                            best = (res.confidence_of(i), v.id)
                if best:
                    ans += 1
                    ok += norm(best[1]) in gold
        print(f"    {name:<14}{ans / n:10.3f}{ok / n:9.3f}"
              f"{ok / max(1, ans):11.3f}{f'{ok}/{n}':>12}")
        out[name] = {"coverage": ans / n, "correct": ok / n,
                     "precision": ok / max(1, ans), "k": ok, "n": n}
    d = out["+ clusters"]["correct"] - out["baseline"]["correct"]
    print(f"    delta correct {d:+.3f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
