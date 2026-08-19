"""Can the load-bearing set be had without solving 28 times?

A complete explanation must cite the claims whose deletion changes the answer.
Finding them exhaustively costs **25.5x the answer**. The soundness work hit the
same shape and fixed it with a certificate, so: does a cheap per-kind argument
recover the same set?

Run: uv run python -u scripts/cheap_load_bearing.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from symbolic_ai_generators.flood import generate
from symbolic_ai_generators.flood.certificate import load_bearing_cheap
from symbolic_ai_generators.flood.flow import solve

sys.path.insert(0, "scripts")
from load_bearing_completeness import load_bearing  # noqa: E402

OUT = Path("runs/cheap_load_bearing.json")
N = 120


def main() -> None:
    cases = [c for c in (generate(s) for s in range(N)) if solve(c.world)[0]]
    t0 = time.perf_counter()
    exact = [load_bearing(c) for c in cases]
    exact_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    cheap = [load_bearing_cheap(c.world) for c in cases]
    cheap_s = time.perf_counter() - t0

    recall = [len(e & c) / len(e) if e else 1.0 for e, c in zip(exact, cheap)]
    prec = [len(e & c) / len(c) if c else 1.0 for e, c in zip(exact, cheap)]
    missed: dict = {}
    extra: dict = {}
    for case, e, c in zip(cases, exact, cheap):
        for i in e - c:
            k = case.world.claims[i].predicate
            missed[k] = missed.get(k, 0) + 1
        for i in c - e:
            k = case.world.claims[i].predicate
            extra[k] = extra.get(k, 0) + 1

    n = len(cases)
    print(f"{n} non-empty cases\n")
    print(f"  exhaustive : {exact_s / n * 1000:8.2f} ms/case")
    print(f"  cheap      : {cheap_s / n * 1000:8.2f} ms/case   "
          f"({exact_s / cheap_s:.0f}x faster)")
    print(f"\n  recall of the load-bearing set : "
          f"{statistics.mean(recall):.3f}")
    print(f"  precision                      : {statistics.mean(prec):.3f}")
    if missed:
        print(f"\n  MISSED by kind (per case): "
              f"{ {k: round(v / n, 2) for k, v in sorted(missed.items())} }")
    if extra:
        print(f"  over-claimed by kind     : "
              f"{ {k: round(v / n, 2) for k, v in sorted(extra.items())} }")

    r = statistics.mean(recall)
    print()
    if r > 0.95:
        print(f"-> THE CHEAP SET RECOVERS IT. Recall {r:.3f} at "
              f"{exact_s / cheap_s:.0f}x less cost, so a complete explanation "
              f"no\n   longer costs 25.5x the answer. Over-claiming is the safe "
              f"direction here: citing a\n   claim that did not matter makes a "
              f"paragraph longer, not wrong.")
    elif r > 0.8:
        print(f"-> MOSTLY. Recall {r:.3f} -- usable as a cheap first pass, and "
              f"the misses are\n   concentrated in "
              f"{max(missed, key=missed.get) if missed else 'nothing'}, which "
              f"is where the cheap argument is weakest.")
    else:
        print(f"-> NOT RECOVERED: recall {r:.3f}. The per-kind arguments are "
              f"too loose, and finding\n   what an explanation owes still costs "
              f"a solve per claim.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"n": n, "exact_ms": exact_s / n * 1000, "cheap_ms": cheap_s / n * 1000,
         "recall": statistics.mean(recall), "precision": statistics.mean(prec),
         "missed": {k: v / n for k, v in missed.items()},
         "extra": {k: v / n for k, v in extra.items()}}, indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
