"""What a dependency certificate is worth when the corpus actually changes.

Two filed SEC 13F snapshots are on disk — 2,282,570 distinct holdings edges in
December 2025 and 2,360,678 in the next, with 333,014 positions closed and
411,122 opened. That is a real corpus update, not an injected one, and it is the
first thing in this repo that can price a certificate at *maintenance* time
rather than at query time.

The question is not "how many answers survive". It is:

    value  =  (cost of recomputation / cost of revalidation)  x  (survival)

because revalidating a read set is |read set| digest comparisons, and for a
query that is itself one pass over its dependency those two costs are the same
number. The prediction under test (`notes/autonomy/predictions.jsonl`,
`cert-maintenance-13f` revision 2) is that the certificate is worth ~1x on a
cheap aggregate and >50x on a solver answer, so that its value is a property of
the *computation*, not of the size of the dependency.

Four query classes spanning four orders of magnitude of compute cost, all over
the same store, all certified by the same generic recording mechanism with no
per-query delta rule:

    holder_count(S)         one key, one len()          — the cheap end
    is_widely_held(S, k)    one key, plus a margin       — the stability rung
    overlap(F1, F2)         two keys, a set intersection
    min_filers_covering(X)  twelve keys, an NP-hard clingo solve — the dear end

ANCHOR: every answer is recomputed on the new snapshot. A certificate that
reports `valid` for an answer that moved is broken, not weaker, and the required
count of those is zero. Reported as `false_survivals` on every row.

Run: uv run python -u scripts/cert_maintenance_13f.py
"""

from __future__ import annotations

import itertools
import json
import random
import time
from pathlib import Path
from typing import Any, Callable, Hashable, Mapping

import pyarrow.parquet as pq

from symbolic_ai_core.runtime.certificate import (
    Certificate, certify, changed_keys, revalidate)

BASE = Path("data/sources/sec-edgar/commandagi-r2-2026-08-15/sec13f")
OLD_FILE = BASE / "holdings_dec2025_p0.parquet"
NEW_FILE = BASE / "holdings_p0.parquet"
USD_PER_CORE_HOUR = 0.02
SEED = 20260818
OUT = Path("runs/cert_maintenance_13f.json")


# --------------------------------------------------------------------------
# the store


def load_store(path: Path) -> dict[Hashable, frozenset[str]]:
    """Both directions of the holdings relation, keyed as facts.

    Granularity is the choice that decides how tight the certificate is. A key
    per *row* would give exact, enormous read sets; a key per adjacency gives a
    small read set that invalidates on any change beneath it. The adjacency is
    the honest one here because every query below is about a whole holder set or
    a whole portfolio — a row-level key would let a certificate claim to depend
    on 3,000 facts when the query asked one question of all of them.
    """
    t = pq.read_table(path)
    src = t.column("source_id").to_pylist()
    tgt = t.column("target_id").to_pylist()
    holders: dict[str, set[str]] = {}
    portfolios: dict[str, set[str]] = {}
    for f, s in zip(src, tgt):
        holders.setdefault(s, set()).add(f)
        portfolios.setdefault(f, set()).add(s)
    store: dict[Hashable, frozenset[str]] = {}
    for s, fs in holders.items():
        store[("holders", s)] = frozenset(fs)
    for f, ss in portfolios.items():
        store[("portfolio", f)] = frozenset(ss)
    return store


# --------------------------------------------------------------------------
# the four query classes


def q_holder_count(sec: str) -> Callable[[Mapping], int]:
    def compute(store: Mapping) -> int:
        return len(store.get(("holders", sec), frozenset()))
    return compute


def q_widely_held(sec: str, k: int) -> Callable[[Mapping], bool]:
    def compute(store: Mapping) -> bool:
        return len(store.get(("holders", sec), frozenset())) >= k
    return compute


def q_overlap(f1: str, f2: str) -> Callable[[Mapping], int]:
    def compute(store: Mapping) -> int:
        a = store.get(("portfolio", f1), frozenset())
        b = store.get(("portfolio", f2), frozenset())
        return len(a & b)
    return compute


def q_min_cover(secs: tuple[str, ...]) -> Callable[[Mapping], int]:
    """Smallest set of filers whose combined portfolios cover every security.

    A real portfolio question — "how few managers do I have to talk to to reach
    every one of these positions" — and a set cover, so it is NP-hard and it is
    what a solver kernel is for. Its dependency is exactly the holder set of
    each security in the query, which is twelve facts against a 2.3M-edge
    corpus: the shape where a certificate should pay.
    """
    def compute(store: Mapping) -> int:
        import clingo
        lines = []
        universe = []
        for i, s in enumerate(secs):
            hs = store.get(("holders", s), frozenset())
            if not hs:
                continue
            universe.append(i)
            for f in hs:
                lines.append(f'covers("{f}",{i}).')
        if not universe:
            return 0
        lines.append("filer(F) :- covers(F,_).")
        lines.append("{ pick(F) } :- filer(F).")
        lines.append(":- item(I), not covered(I).")
        lines.append("covered(I) :- pick(F), covers(F,I).")
        lines += [f"item({i})." for i in universe]
        lines.append("#minimize { 1,F : pick(F) }.")
        ctl = clingo.Control()
        ctl.add("base", [], "\n".join(lines))
        ctl.ground([("base", [])])
        best: list[int] = []
        with ctl.solve(yield_=True) as handle:
            for model in handle:
                best.append(sum(1 for a in model.symbols(shown=True)
                                if a.name == "pick"))
        return best[-1] if best else -1
    return compute


# --------------------------------------------------------------------------
# the ladder


def run_class(name: str, computes: list[tuple[Any, Callable]],
              old: Mapping, new: Mapping,
              delta_size: Mapping[Hashable, int],
              margin_of: Callable[[Any, Mapping], int] | None = None,
              ) -> dict[str, Any]:
    """Certify on the old snapshot, revalidate against the new, anchor on truth.

    Three rungs, each strictly cheaper than the last and each sound:

    R0  no certificate  — recompute every answer. What an opponent must do.
    R1  read set        — compare one digest per fact read. Generic; no
                          per-query rule was written for any of the four.
    R2  stability       — a query-supplied margin, checked against the *delta*
                          rather than the corpus. NOT generic, and labelled so:
                          only the threshold query can state one.
    """
    # --- R0: certify on old, and recompute on new (the anchor and the opponent)
    certs: list[Certificate] = []
    t0 = time.perf_counter_ns()
    for _, compute in computes:
        certs.append(certify(compute, old))
    certify_ns = time.perf_counter_ns() - t0

    t0 = time.perf_counter_ns()
    truth = [compute(new) for _, compute in computes]
    recompute_ns = time.perf_counter_ns() - t0

    # --- digests: only over the keys some certificate actually read. Hashing
    # the whole 2.3M-member corpus would be the amortised cost; hashing the
    # union of read sets is the honest one, and it is what a cache would do.
    touched = set().union(*(set(c.digests) for c in certs)) if certs else set()
    t0 = time.perf_counter_ns()
    digests = {k: _digest_of(new.get(k)) for k in touched}
    digest_ns = time.perf_counter_ns() - t0

    # --- R1
    t0 = time.perf_counter_ns()
    revals = [revalidate(c, digests) for c in certs]
    reval_ns = time.perf_counter_ns() - t0

    unchanged = [t == c.answer for t, c in zip(truth, certs)]
    r1_survive = sum(r.valid for r in revals)
    r1_false = sum(1 for r, u in zip(revals, unchanged) if r.valid and not u)

    row: dict[str, Any] = {
        "query_class": name,
        "n": len(certs),
        "read_set_size_mean": (sum(c.size for c in certs) / len(certs)
                               if certs else 0),
        "answers_actually_unchanged": sum(unchanged),
        "compute_ns_per_answer": recompute_ns / len(certs) if certs else 0,
        "certify_ns_per_answer": certify_ns / len(certs) if certs else 0,
        "r1_revalidate_ns_per_answer": reval_ns / len(certs) if certs else 0,
        "r1_digest_ns_total": digest_ns,
        "r1_keys_digested": len(touched),
        "r1_survived": r1_survive,
        "r1_survival_frac": r1_survive / len(certs) if certs else 0,
        "r1_false_survivals": r1_false,
    }
    per_answer_reval = row["r1_revalidate_ns_per_answer"]
    row["r1_speedup_per_answer"] = (row["compute_ns_per_answer"] / per_answer_reval
                                    if per_answer_reval else 0.0)
    # Where the amortised digest pass pays for itself, in maintained answers.
    saved = row["compute_ns_per_answer"] - per_answer_reval
    row["r1_breakeven_answers"] = (digest_ns / saved) if saved > 0 else None
    # What the whole maintenance pass cost either way, in dollars.
    row["usd_recompute_all"] = recompute_ns * USD_PER_CORE_HOUR / 3600 / 1e9
    row["usd_revalidate_all"] = ((reval_ns + digest_ns) * USD_PER_CORE_HOUR
                                 / 3600 / 1e9)
    # And the work that has to happen anyway: an invalidated answer is re-solved.
    resolve = (len(certs) - r1_survive) * row["compute_ns_per_answer"]
    row["usd_maintain_with_cert"] = ((reval_ns + digest_ns + resolve)
                                     * USD_PER_CORE_HOUR / 3600 / 1e9)
    row["maintenance_advantage"] = (row["usd_recompute_all"]
                                    / row["usd_maintain_with_cert"]
                                    if row["usd_maintain_with_cert"] else 0.0)

    # --- R2: the stability rung. Only where the query can state a margin, and
    # deliberately *not* generic — R1 is what the recording mechanism gives you
    # for free, R2 is what a query author can add on top when the answer is a
    # comparison rather than a value.
    #
    # Soundness: the count can move by at most the size of the symmetric
    # difference of the holder set, so a margin strictly greater than that
    # difference cannot be crossed. The check reads `delta_size`, which is
    # proportional to the *update*, and never touches the corpus or the answer.
    if margin_of is not None:
        t0 = time.perf_counter_ns()
        r2 = []
        for (obj, _), c in zip(computes, certs):
            m = margin_of(obj, old)
            moved = max((delta_size.get(k, 0) for k in c.digests), default=0)
            r2.append(moved < m)
        r2_ns = time.perf_counter_ns() - t0
        r2_survive = sum(r2)
        row["r2_survived"] = r2_survive
        row["r2_survival_frac"] = r2_survive / len(certs) if certs else 0
        row["r2_false_survivals"] = sum(1 for s, u in zip(r2, unchanged)
                                        if s and not u)
        row["r2_ns_per_answer"] = r2_ns / len(certs) if certs else 0
        row["r2_generic"] = False
    return row


def _digest_of(value: Any) -> Any:
    from symbolic_ai_core.runtime.certificate import MISSING, _digest
    return _digest(MISSING if value is None else value)


# --------------------------------------------------------------------------


def main() -> None:
    rng = random.Random(SEED)
    print("loading two filed snapshots ...", flush=True)
    t0 = time.perf_counter()
    old = load_store(OLD_FILE)
    new = load_store(NEW_FILE)
    print(f"  old {len(old):,} keys, new {len(new):,} keys "
          f"({time.perf_counter() - t0:.1f}s)", flush=True)

    delta = changed_keys(old, new)
    print(f"  delta: {len(delta):,} keys moved of "
          f"{len(set(old) | set(new)):,}", flush=True)

    # How *far* each key moved, in members. This is the only thing R2 reads, and
    # in a real update stream it arrives with the filing rather than being
    # derived from two snapshots — so charging R2 for deriving it here would be
    # charging it for the shape of the fixture rather than for the mechanism.
    empty: frozenset[str] = frozenset()
    delta_size = {k: len(old.get(k, empty) ^ new.get(k, empty)) for k in delta}

    secs = sorted(k[1] for k in old if k[0] == "holders")
    filers = sorted(k[1] for k in old if k[0] == "portfolio")
    print(f"  {len(secs):,} securities, {len(filers):,} filers", flush=True)

    rows = []

    # 1. cheap aggregate
    sample = rng.sample(secs, 5000)
    rows.append(run_class("holder_count", [(s, q_holder_count(s))
                                           for s in sample],
                          old, new, delta_size))

    # 2. threshold, with a margin the query can state
    k = 100

    def margin(sec: str, store: Mapping) -> int:
        return abs(len(store.get(("holders", sec), empty)) - k)

    rows.append(run_class("is_widely_held(k=100)",
                          [(s, q_widely_held(s, k)) for s in sample],
                          old, new, delta_size, margin_of=margin))

    # 3. medium: two reads and a set intersection
    pairs = []
    while len(pairs) < 5000:
        a, b = rng.choice(filers), rng.choice(filers)
        if a != b:
            pairs.append((a, b))
    rows.append(run_class("portfolio_overlap",
                          [(p, q_overlap(*p)) for p in pairs],
                          old, new, delta_size))

    # 4. the dear end: an NP-hard cover over twelve securities
    covers = [tuple(rng.sample(secs, 12)) for _ in range(300)]
    rows.append(run_class("min_filers_covering(12)",
                          [(c, q_min_cover(c)) for c in covers],
                          old, new, delta_size))

    print()
    hdr = (f"{'query class':<26} {'n':>5} {'|read|':>7} {'compute/ans':>13} "
           f"{'reval/ans':>11} {'speedup':>9} {'survive':>8} {'false':>6} "
           f"{'maint adv':>10}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['query_class']:<26} {r['n']:>5} "
              f"{r['read_set_size_mean']:>7.1f} "
              f"{r['compute_ns_per_answer']:>11,.0f}ns "
              f"{r['r1_revalidate_ns_per_answer']:>9,.0f}ns "
              f"{r['r1_speedup_per_answer']:>8.1f}x "
              f"{r['r1_survival_frac']:>7.1%} "
              f"{r['r1_false_survivals']:>6} "
              f"{r['maintenance_advantage']:>9.1f}x")

    print()
    for r in rows:
        be = r.get("r1_breakeven_answers")
        print(f"{r['query_class']:<26} breakeven at "
              f"{'never (revalidation is not cheaper)' if be is None else f'{be:,.0f} maintained answers'}"
              f"; {r['r1_keys_digested']:,} keys digested in "
              f"{r['r1_digest_ns_total']/1e6:.1f}ms")
        if "r2_survived" in r:
            print(f"{'':<26} R2 stability margin (query-supplied, not generic): "
                  f"{r['r2_survival_frac']:.1%} survive vs "
                  f"{r['r1_survival_frac']:.1%} for the read set, "
                  f"{r['r2_false_survivals']} false")

    bad = [r for r in rows if r["r1_false_survivals"]
           or r.get("r2_false_survivals")]
    print()
    if bad:
        print("ANCHOR FAILED: a certificate certified an answer that moved. "
              f"{[r['query_class'] for r in bad]}")
    else:
        print(f"anchor: {sum(r['n'] for r in rows):,} answers recomputed on the "
              "new snapshot, 0 false survivals across every rung")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"seed": SEED, "old": str(OLD_FILE), "new": str(NEW_FILE),
         "delta_keys": len(delta), "rows": rows}, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
