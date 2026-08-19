"""Can the reader buy a relation nobody curated, by bootstrapping from a seed?

The bottleneck pricing ends on the case it does not cover: *"a relation nobody
has curated is exactly as expensive as it was in 1984, and this reader has no way
to acquire one."* The classical answer to that is **bootstrapping** — start from a
handful of examples, extract, keep what you are confident about, refit, repeat.

This runs it. The seed is a **fraction of the training articles' distant labels**;
everything else is treated as unlabelled. Each round the reader reads the
unlabelled pool, its most confident extractions become pseudo-labels, and it
refits. The logistic model is used so confidence is a probability rather than a
margin.

Three reference points, all on the same held-out articles:

    seed only        the fit that a hand-collected seed set would buy
    bootstrapped     after each round of self-training
    full distant     every training article's distant label -- the ceiling this
                     experiment is trying to approach without a KB

Predicted before running: **semantic drift.** Round one improves a little because
the confident extractions are mostly right; by round three accuracy falls below
seed-only, because the reader's confident *errors* are self-reinforcing and
nothing in the loop can tell a confident error from a confident success. If
calibration prevents that — the beliefs here are held-out calibrated, which the
classical bootstrapping literature did not have — the curve plateaus instead of
falling, and that would be the interesting outcome.

Run: uv run python -u scripts/bootstrap_relation.py
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from symbolic_ai_core.reader.learned import CapitalisedMentions, LearnedSpanReader
from symbolic_ai_core.world import Claim, EntityRef

import scripts.real_text_reader as R
from scripts.multi_relation_world import norm

CORPUS = Path("data/artifacts/wikipedia_parents_closed.jsonl")
OUT = Path("runs/bootstrap_relation.json")
SEED_SHARE = 0.10
ROUNDS = 8
#: How many pseudo-labelled articles to add per round, highest belief first.
ADD = 200
#: Three splits, because a single seed draw is a single draw -- and this session
#: has already withdrawn two headlines that were one.
SPLITS = (31, 32, 33)


def accuracy(reader, held) -> tuple[float, int, int]:
    ok = n = 0
    for d in held:
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
        ok += bool(best) and norm(best[1]) in gold
    return ok / max(1, n), ok, n


def fit(units):
    return LearnedSpanReader(
        model="logistic", mentions=CapitalisedMentions(),
        extra_features=R.extra(),
        extra_role_features=R.role_frame_features).fit(units)


def one_split(docs, split_seed: int) -> dict:
    order = list(docs)
    random.Random(split_seed).shuffle(order)   # a prefix is not a sample
    held = order[:400]
    pool = order[400:]
    seed = pool[:int(len(pool) * SEED_SHARE)]
    unlabelled = pool[int(len(pool) * SEED_SHARE):]


    ceiling = fit([R.supervise_distant(d) for d in pool])
    c_rate, c_k, c_n = accuracy(ceiling, held)
    reader = fit([R.supervise_distant(d) for d in seed])
    s_rate, s_k, s_n = accuracy(reader, held)
    rows = [{"round": 0, "rate": s_rate, "k": s_k, "n": s_n, "pseudo": 0}]
    train = [R.supervise_distant(d) for d in seed]
    remaining = list(unlabelled)
    added = 0
    prev: dict[int, str] = {}
    for rnd in range(1, ROUNDS + 1):
        scored = []
        for d in remaining:
            res = reader.run(d["intro"], query=d.get("title", ""))
            best = None
            for i, c in enumerate(res.claims):
                v = c.roles.get("value")
                if c.predicate == "parent" and isinstance(v, EntityRef):
                    if best is None or res.confidence_of(i) > best[0]:
                        best = (res.confidence_of(i), v.id, i)
            if best:
                scored.append((best[0], best[1], d))
        scored.sort(key=lambda x: -x[0])
        take = scored[:ADD]
        # Unsupervised signals, recorded because the case this is FOR has no
        # held-out gold: a relation nobody curated cannot tell you when to stop.
        # If none of these tracks the accuracy peak, bootstrapping needs a
        # stopping rule it does not have.
        signals = {
            "mean_belief": (statistics.mean(x[0] for x in take)
                            if take else 0.0),
            "coverage": len(scored) / max(1, len(remaining)),
            "churn": (statistics.mean(
                1.0 if prev.get(id(d)) not in (None, g) else 0.0
                for _, g, d in scored) if scored else 0.0),
        }
        prev = {id(d): g for _, g, d in scored}
        if not take:
            print("    (nothing confident enough to add; stopping)")
            break
        # A pseudo-label is the reader's OWN answer, supervised the same way a
        # gold one would be: label every sentence containing the string it read.
        for _, guess, d in take:
            units = R.supervise_distant({**d, "parent": [guess],
                                         "country": [], "headquarters": []})
            train.append(units)
        chosen = {id(d) for _, _, d in take}
        remaining = [d for d in remaining if id(d) not in chosen]
        added += len(take)

        reader = fit(train)
        rate, k, n = accuracy(reader, held)
        rows.append({"round": rnd, "rate": rate, "k": k, "n": n,
                     "pseudo": added, **signals})
    return {"split": split_seed, "ceiling": c_rate, "ceiling_k": c_k,
            "n": c_n, "rounds": rows}


def main() -> None:
    R.PARENTS = CORPUS
    R.RELATIONS = Path("data/artifacts/company_relations_scale.jsonl")
    docs = R.corpus()
    results = []
    for sp in SPLITS:
        print(f"  split {sp} ...", flush=True)
        results.append(one_split(docs, sp))

    n = results[0]["n"]
    print(f"\n    held out {n} articles with gold, {len(SPLITS)} splits")
    print(f"    {'arm':<24}" + "".join(f"{'split ' + str(s):>12}"
                                       for s in SPLITS) + f"{'mean':>9}")

    def line(label, vals):
        print(f"    {label:<24}" + "".join(f"{v:12.3f}" for v in vals)
              + f"{statistics.mean(vals):9.3f}")

    line("full distant (ceiling)", [r["ceiling"] for r in results])
    for rnd in range(ROUNDS + 1):
        vals = [r["rounds"][rnd]["rate"] for r in results
                if rnd < len(r["rounds"])]
        if len(vals) == len(SPLITS):
            line("seed only" if rnd == 0 else f"bootstrap round {rnd}", vals)

    print(f"\n    UNSUPERVISED SIGNALS (mean over splits) -- would any of these"
          f"\n    have told you to stop, without the held-out column above?")
    print(f"    {'round':<8}{'accuracy':>10}{'mean belief':>13}"
          f"{'coverage':>10}{'churn':>8}")
    for rnd in range(1, ROUNDS + 1):
        got = [r["rounds"][rnd] for r in results if rnd < len(r["rounds"])]
        if len(got) != len(SPLITS):
            continue
        print(f"    {rnd:<8}{statistics.mean(g['rate'] for g in got):10.3f}"
              f"{statistics.mean(g['mean_belief'] for g in got):13.3f}"
              f"{statistics.mean(g['coverage'] for g in got):10.3f}"
              f"{statistics.mean(g['churn'] for g in got):8.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
