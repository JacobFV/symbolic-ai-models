"""The certificate's value is the freshness requirement divided by the churn.

`cert_maintenance_13f.py` measured the batch case — one quarterly update, every
answer needed once — and found the read-set certificate worth **1.0x on a solver
answer and 0.3x on an aggregate**, because the read set that makes a certificate
cheap to check is the same read set that makes it likely to be hit. Under 75.7%
key churn a twelve-key dependency survives with probability 0.24^12.

But a quarter is not the unit in which 13F changes. It changes one **filing** at
a time, and the batch measurement is the endpoint of a curve rather than the
value of the mechanism. This measures the curve.

The setting: a cache of N answers that must be **correct after every update**.

* The opponent — an LM or a retrieval agent, which cannot certify that an answer
  did not depend on a changed fact — must re-derive all N after every update.
  Its cost is ``N x updates x compute``, and it is *extrapolated* from measured
  per-answer compute rather than run: 300 solver answers across 8,000 filings is
  4.5 hours of clingo and nothing is learned by spending it.
* The certificate holds an inverted index from fact key to the certificates that
  read it, so an update visits only the certs registered on the keys that moved.
  That side is actually executed.

The claim under test is a law, not a number:

    advantage  ~  N_answers / keys_touched_per_update

and the batch endpoint must reproduce the 1.0x already on disk, or the two
experiments are measuring different things and neither is safe.

Run: uv run python -u scripts/cert_freshness_13f.py
"""

from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Hashable, Mapping

from scripts.cert_maintenance_13f import (
    BASE, NEW_FILE, OLD_FILE, SEED, USD_PER_CORE_HOUR, load_store,
    q_holder_count, q_min_cover, q_overlap)
from symbolic_ai_core.runtime.certificate import certify

OUT = Path("runs/cert_freshness_13f.json")
BATCHES = (1, 2, 5, 20, 100, 500, 2000, 0)      # 0 = the whole quarter at once


def filing_updates(old: Mapping, new: Mapping) -> list[frozenset[Hashable]]:
    """One entry per filer whose portfolio moved: the fact keys that filing touched.

    This is the real update unit. A 13F filing restates one manager's whole
    portfolio, so it moves that manager's portfolio key and the holder set of
    every security they opened or closed.
    """
    empty: frozenset[str] = frozenset()
    filers = {k[1] for k in old if k[0] == "portfolio"}
    filers |= {k[1] for k in new if k[0] == "portfolio"}
    out = []
    for f in sorted(filers):
        a = old.get(("portfolio", f), empty)
        b = new.get(("portfolio", f), empty)
        moved = a ^ b
        if not moved:
            continue
        keys: set[Hashable] = {("portfolio", f)}
        keys |= {("holders", s) for s in moved}
        out.append(frozenset(keys))
    return out


def replay(certs: list, updates: list[frozenset[Hashable]], batch: int,
           compute_ns: float) -> dict[str, Any]:
    """Maintain the cache across the update stream, and price both sides.

    The invalidation is *counted*, not re-solved: re-solving would re-run the
    kernel to produce an answer whose cost we already measured, which is the
    thing `CLAUDE.md` says not to spend time on. The recomputation is charged at
    the measured per-answer cost.
    """
    if batch == 0:
        batches = [frozenset().union(*updates)] if updates else []
    else:
        batches = [frozenset().union(*updates[i:i + batch])
                   for i in range(0, len(updates), batch)]

    # key -> indices of the certificates that read it. Built once; a real cache
    # builds it as answers are inserted, so it is not a per-update cost.
    index: dict[Hashable, list[int]] = defaultdict(list)
    for i, c in enumerate(certs):
        for k in c.digests:
            index[k].append(i)

    n = len(certs)
    invalidations = 0
    touched_total = 0
    t0 = time.perf_counter_ns()
    for keys in batches:
        hit: set[int] = set()
        for k in keys:
            hit.update(index.get(k, ()))
        invalidations += len(hit)
        touched_total += len(keys)
    check_ns = time.perf_counter_ns() - t0

    resolve_ns = invalidations * compute_ns
    ours_ns = check_ns + resolve_ns
    # Extrapolated, not run: the opponent re-derives the whole cache per update.
    theirs_ns = n * len(batches) * compute_ns
    return {
        "batch": batch or len(updates),
        "updates": len(batches),
        "keys_touched_per_update": touched_total / len(batches) if batches else 0,
        "invalidations": invalidations,
        "invalidations_per_update_frac": (invalidations / (len(batches) * n)
                                          if batches and n else 0.0),
        "check_ns": check_ns,
        "resolve_ns": resolve_ns,
        "ours_usd": ours_ns * USD_PER_CORE_HOUR / 3600 / 1e9,
        "theirs_usd_extrapolated": theirs_ns * USD_PER_CORE_HOUR / 3600 / 1e9,
        "advantage": theirs_ns / ours_ns if ours_ns else 0.0,
        "predicted_law_n_over_touched": (
            n / (touched_total / len(batches)) if batches and touched_total
            else 0.0),
    }


def main() -> None:
    rng = random.Random(SEED)
    print("loading two filed snapshots ...", flush=True)
    old, new = load_store(OLD_FILE), load_store(NEW_FILE)
    updates = filing_updates(old, new)
    total_keys = len(set(old) | set(new))
    print(f"  {len(updates):,} filings moved something, over {total_keys:,} keys",
          flush=True)
    sizes = sorted(len(u) for u in updates)
    print(f"  keys per filing: p50 {sizes[len(sizes)//2]}, "
          f"p90 {sizes[int(len(sizes)*0.9)]}, max {sizes[-1]}, "
          f"mean {sum(sizes)/len(sizes):.1f} "
          f"({sum(sizes)/len(sizes)/total_keys:.3%} of the corpus)", flush=True)

    secs = sorted(k[1] for k in old if k[0] == "holders")
    filers = sorted(k[1] for k in old if k[0] == "portfolio")

    # Certificates are built on the old snapshot once. The per-answer compute
    # cost comes from the same run, so the two sides are priced off one clock.
    classes: list[tuple[str, list]] = []

    sample = rng.sample(secs, 5000)
    classes.append(("holder_count", [q_holder_count(s) for s in sample]))

    pairs = []
    while len(pairs) < 5000:
        a, b = rng.choice(filers), rng.choice(filers)
        if a != b:
            pairs.append((a, b))
    classes.append(("portfolio_overlap", [q_overlap(*p) for p in pairs]))

    covers = [tuple(rng.sample(secs, 12)) for _ in range(300)]
    classes.append(("min_filers_covering(12)", [q_min_cover(c) for c in covers]))

    rows = []
    for name, computes in classes:
        print(f"\ncertifying {name} ({len(computes)} answers) ...", flush=True)
        certs = [certify(c, old) for c in computes]
        compute_ns = sum(c.compute_ns for c in certs) / len(certs)
        print(f"  {compute_ns:,.0f} ns/answer, "
              f"read set {sum(c.size for c in certs)/len(certs):.1f} keys",
              flush=True)
        for b in BATCHES:
            r = replay(certs, updates, b, compute_ns)
            r["query_class"] = name
            r["n_answers"] = len(certs)
            r["compute_ns_per_answer"] = compute_ns
            rows.append(r)

    print()
    hdr = (f"{'query class':<24} {'batch':>6} {'updates':>8} {'keys/upd':>9} "
           f"{'invalid/upd':>12} {'ours $':>12} {'theirs $':>12} {'adv':>10} "
           f"{'N/touched':>10}")
    print(hdr)
    print("-" * len(hdr))
    last = None
    for r in rows:
        if last and last != r["query_class"]:
            print("-" * len(hdr))
        last = r["query_class"]
        print(f"{r['query_class']:<24} {r['batch']:>6} {r['updates']:>8} "
              f"{r['keys_touched_per_update']:>9,.0f} "
              f"{r['invalidations_per_update_frac']:>11.2%} "
              f"{r['ours_usd']:>12.2e} {r['theirs_usd_extrapolated']:>12.2e} "
              f"{r['advantage']:>9.1f}x {r['predicted_law_n_over_touched']:>9.1f}")

    print("\ncontrol — the whole-quarter endpoint must reproduce the batch "
          "experiment's ~1.0x:")
    for r in rows:
        if r["batch"] == len(updates):
            print(f"  {r['query_class']:<24} {r['advantage']:.2f}x "
                  f"({r['invalidations']}/{r['n_answers']} invalidated)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "filings": len(updates),
                               "total_keys": total_keys, "rows": rows},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
