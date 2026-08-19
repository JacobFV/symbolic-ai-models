"""The derived margin cut invalidations 10.1x. Does it cut the BILL?

`notes/findings/2026-08-18-the-rung-...-is-derivable.md` reported the derived
margin at **25x cheaper per quality point**, "from recording one extra number per
answer". That priced **recompute** for both arms and left **revalidation** out of
both, which is not apples-to-apples:

    read-set check   one digest comparison per key
    derived check    a symmetric difference over the whole holder set

§3b's own formula is `advantage = min(compute/check, 1/P_hit)` and the margin
improved only the **second** term. If the check got dearer than the recomputes it
saved, the mechanism is elegant and economically inert -- and the finding needs a
correction rather than a caveat.

Two regimes, because they are genuinely different systems and §3b's margin row
quietly assumed the first:

**delta supplied.** A corpus update *is* a set of adds and removes, so
`|old_k XOR new_k|` is computed **once per key per update** and amortised over
every query that reads it. Revalidation is then a lookup, a multiply and a
compare. (§3b's `r2` arm used a precomputed `delta_size` -- this makes that
assumption explicit and prices it.)

**delta recomputed.** No update stream; the certificate holder diffs the sets
itself, per query. This is the honest worst case and the one my headline ignored.

The deciding number is the **net maintenance advantage**,
`recompute_all / (amortised pass + revalidation + resolve)`, and the variable
that decides it is **queries per key**. A first version of this script sampled
5,000 queries over ~4,500 distinct keys -- about one query per key -- which is
the worst possible case for amortisation and made the supplied-delta arm look
like the recomputed one. The amortised pass is a property of the *update*; the
queries are what it is spread over, so the answer is a curve and not a number.

Run: uv run python -u scripts/cert_margin_net_cost.py
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Hashable, Mapping

from scripts.cert_maintenance_13f import NEW_FILE, OLD_FILE, load_store
from symbolic_ai_core.runtime.certificate import Counted

OUT = Path("runs/cert_margin_net_cost.json")
SEED = 20260818
M_KEYS = 3000
QUERIES_PER_KEY_MAX = 4
K = 100
USD_PER_CORE_HOUR = 0.02


def main() -> None:
    rng = random.Random(SEED)
    old = load_store(OLD_FILE)
    new = load_store(NEW_FILE)
    secs = sorted({k[1] for k in set(old) & set(new) if k[0] == "holders"})
    distinct = [("holders", s) for s in rng.sample(secs, M_KEYS)]
    sizes = [len(old[k]) for k in distinct]
    print(f"{M_KEYS:,} distinct keys; mean holder set "
          f"{sum(sizes)/len(sizes):.1f}, p90 "
          f"{sorted(sizes)[int(len(sizes)*0.9)]}\n", flush=True)

    # --- the two amortised passes, each priced ONCE per key per update.
    t = time.perf_counter_ns()
    new_digests = {k: hash(new.get(k, frozenset())) for k in distinct}
    digest_ns_per_key = (time.perf_counter_ns() - t) / M_KEYS
    t = time.perf_counter_ns()
    delta = {k: len(old[k] ^ new.get(k, frozenset())) for k in distinct}
    delta_ns_per_key = (time.perf_counter_ns() - t) / M_KEYS
    old_digests = {k: hash(old[k]) for k in distinct}
    print(f"amortised per key per update: digest pass "
          f"{digest_ns_per_key:,.0f}ns, delta pass {delta_ns_per_key:,.0f}ns "
          f"({delta_ns_per_key/digest_ns_per_key:.1f}x dearer)\n", flush=True)

    # --- per-query costs, measured over a workload of Q queries per key.
    keys = distinct * QUERIES_PER_KEY_MAX
    rng.shuffle(keys)
    n = len(keys)
    old_counts = {k: len(old[k]) for k in distinct}
    slack = {k: Counted(c).at_least(K)[1].slack for k, c in old_counts.items()}

    t = time.perf_counter_ns()
    answers_new = [len(new.get(k, frozenset())) >= K for k in keys]
    recompute_ns = (time.perf_counter_ns() - t) / n

    t = time.perf_counter_ns()
    flag_rs = [new_digests[k] != old_digests[k] for k in keys]
    reval_rs_ns = (time.perf_counter_ns() - t) / n

    t = time.perf_counter_ns()
    flag_ds = [not (delta[k] < slack[k]) for k in keys]
    reval_ds_ns = (time.perf_counter_ns() - t) / n

    t = time.perf_counter_ns()
    flag_rc = [not (len(old[k] ^ new.get(k, frozenset())) < slack[k])
               for k in keys]
    reval_rc_ns = (time.perf_counter_ns() - t) / n

    assert flag_ds == flag_rc, "the two derived regimes must agree on flagging"
    for f, k, a_new in zip(flag_ds, keys, answers_new):
        if not f and (old_counts[k] >= K) != a_new:
            raise AssertionError("derived margin survived a moved answer")

    ff_rs = sum(flag_rs) / n
    ff_de = sum(flag_ds) / n
    print(f"recompute {recompute_ns:,.1f}ns/answer; flagged: read set "
          f"{ff_rs:.2%}, derived margin {ff_de:.2%}\n", flush=True)
    print(f"revalidation per answer: read set {reval_rs_ns:,.1f}ns, "
          f"derived(supplied) {reval_ds_ns:,.1f}ns, "
          f"derived(recomputed) {reval_rc_ns:,.1f}ns\n", flush=True)

    # --- the curve. Amortised cost is per KEY per update; queries are what it
    # is spread over.
    def advantage(reval: float, amort_per_key: float, flagged: float,
                  q: float) -> float:
        total = reval + amort_per_key / q + flagged * recompute_ns
        return recompute_ns / total

    arms = (("read set", reval_rs_ns, digest_ns_per_key, ff_rs),
            ("derived, delta supplied", reval_ds_ns, delta_ns_per_key, ff_de),
            ("derived, delta recomputed", reval_rc_ns, 0.0, ff_de))
    qs = (1, 2, 5, 10, 20, 50, 200, 1000)
    print(f"{'queries per key':<28}" + "".join(f"{q:>9}" for q in qs))
    print("-" * (28 + 9 * len(qs)))
    curves = {}
    for name, reval, amort, ff in arms:
        vals = [advantage(reval, amort, ff, q) for q in qs]
        curves[name] = dict(zip(map(str, qs), vals))
        print(f"{name:<28}" + "".join(f"{v:>8.2f}x" for v in vals))

    print(f"\nan arm is worth having only above 1.00x. Ceilings, at q -> inf:")
    for name, reval, amort, ff in arms:
        print(f"  {name:<28} {advantage(reval, amort, ff, 1e12):>6.2f}x")

    # --- where the derived margin overtakes the read set, and where it starts
    # paying for itself at all.
    def crossover(a, b) -> float | None:
        lo, hi = 1.0, 1e6
        fa = lambda q: advantage(a[1], a[2], a[3], q)
        fb = lambda q: advantage(b[1], b[2], b[3], q)
        if fa(hi) <= fb(hi):
            return None
        for _ in range(200):
            mid = (lo + hi) / 2
            if fa(mid) > fb(mid):
                hi = mid
            else:
                lo = mid
        return hi

    ds = arms[1]
    over = crossover(ds, arms[0])
    pays = crossover(ds, ("unit", 0.0, 0.0, 1.0))
    print(f"\nderived(supplied) overtakes the read set at "
          f"{over:,.1f} queries per key" if over else
          "\nderived(supplied) never overtakes the read set")
    print(f"derived(supplied) exceeds 1.00x at "
          f"{pays:,.1f} queries per key" if pays else
          "derived(supplied) never exceeds 1.00x")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "m_keys": M_KEYS, "n": n, "k": K,
         "recompute_ns_per_answer": recompute_ns,
         "digest_ns_per_key": digest_ns_per_key,
         "delta_ns_per_key": delta_ns_per_key,
         "flagged": {"read_set": ff_rs, "derived": ff_de},
         "reval_ns": {"read_set": reval_rs_ns, "derived_supplied": reval_ds_ns,
                      "derived_recomputed": reval_rc_ns},
         "curves": curves, "overtakes_at_q": over, "pays_at_q": pays},
        indent=2))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
