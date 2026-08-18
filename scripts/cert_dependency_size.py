"""Which of the two ceilings binds: dependency size, or the cost of the answer?

`cert_freshness_13f.py` produced a result that inverts the obvious intuition.
At single-filing granularity the certificate is worth **1,342x** on a two-key
set intersection and **37x** on a twelve-key NP-hard cover — so the *most*
expensive computation has the *least* valuable certificate, by 36x.

Two ceilings explain that, and they are different mechanisms:

    check-bound         advantage -> compute_per_answer / check_per_answer
    invalidation-bound  advantage -> 1 / P(some read fact moved in this update)

and ``P ~ r x keys_touched / total_keys`` for a dependency of ``r`` facts. Cheap
queries sit under the first ceiling, dear ones under the second. If that reading
is right, the solver's disadvantage is **entirely** its twelve-fact dependency
and has nothing to do with its cost — so holding the kernel fixed and sweeping
``r`` should give ``advantage ~ 544/r``, and holding ``r`` fixed while making the
kernel dearer should change nothing at all.

Both halves are run here, because the first alone would be consistent with cost
and dependency being confounded, which they are in every query class measured so
far: the dear query is also the one with the big read set.

Run: uv run python -u scripts/cert_dependency_size.py
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from scripts.cert_freshness_13f import filing_updates, replay
from scripts.cert_maintenance_13f import (
    NEW_FILE, OLD_FILE, SEED, load_store, q_min_cover)
from symbolic_ai_core.runtime.certificate import certify

OUT = Path("runs/cert_dependency_size.json")
SIZES = (1, 2, 4, 8, 12, 24, 48)
N_QUERIES = 200


def q_padded_count(sec: str, work: int) -> Callable[[Mapping], int]:
    """One fact read, and an arbitrary amount of arithmetic on top of it.

    The dear-kernel-with-a-small-dependency case, which no real query class in
    this repo occupies and which is exactly the cell the confound hides in.
    """
    def compute(store: Mapping) -> int:
        n = len(store.get(("holders", sec), frozenset()))
        acc = 0
        for i in range(work):
            acc = (acc * 1103515245 + 12345 + n) & 0x7FFFFFFF
        return n + (acc & 0)          # the padding cannot change the answer
    return compute


def main() -> None:
    rng = random.Random(SEED)
    print("loading two filed snapshots ...", flush=True)
    old, new = load_store(OLD_FILE), load_store(NEW_FILE)
    updates = filing_updates(old, new)
    total_keys = len(set(old) | set(new))
    touched = sum(len(u) for u in updates) / len(updates)
    print(f"  {len(updates):,} filings, {touched:.1f} keys each, "
          f"{total_keys:,} keys total", flush=True)
    secs = sorted(k[1] for k in old if k[0] == "holders")

    rows: list[dict[str, Any]] = []

    print("\nA. dependency size swept, kernel held fixed (clingo set cover)",
          flush=True)
    for r in SIZES:
        covers = [tuple(rng.sample(secs, r)) for _ in range(N_QUERIES)]
        t0 = time.perf_counter()
        certs = [certify(q_min_cover(c), old) for c in covers]
        compute_ns = sum(c.compute_ns for c in certs) / len(certs)
        row = replay(certs, updates, 1, compute_ns)
        row |= {"arm": "sweep_r", "r": r, "compute_ns_per_answer": compute_ns,
                "n_answers": len(certs), "predicted": 1.0 / (r * touched / total_keys)}
        rows.append(row)
        print(f"  r={r:>3}  compute {compute_ns/1e6:>8.2f} ms  "
              f"P(hit) {row['invalidations_per_update_frac']:>7.3%}  "
              f"advantage {row['advantage']:>8.1f}x  "
              f"(1/P predicts {row['predicted']:>7.1f}x)  "
              f"[{time.perf_counter()-t0:.0f}s]", flush=True)

    print("\nB. kernel cost swept, dependency held fixed at one fact", flush=True)
    for work in (0, 100, 10_000, 1_000_000):
        sample = rng.sample(secs, N_QUERIES)
        certs = [certify(q_padded_count(s, work), old) for s in sample]
        compute_ns = sum(c.compute_ns for c in certs) / len(certs)
        row = replay(certs, updates, 1, compute_ns)
        row |= {"arm": "sweep_cost", "r": 1, "work": work,
                "compute_ns_per_answer": compute_ns, "n_answers": len(certs),
                "predicted": 1.0 / (1 * touched / total_keys)}
        rows.append(row)
        print(f"  work={work:>9}  compute {compute_ns/1e3:>10.1f} us  "
              f"P(hit) {row['invalidations_per_update_frac']:>7.3%}  "
              f"advantage {row['advantage']:>8.1f}x  "
              f"(1/P predicts {row['predicted']:>7.1f}x)", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seed": SEED, "keys_per_filing": touched,
                               "total_keys": total_keys, "rows": rows},
                              indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
