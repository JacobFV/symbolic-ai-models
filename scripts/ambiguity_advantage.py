"""How big is the advantage when the opponent is *given only what it needs*?

This repo's advantage curve — 6,750x on country-from-coordinate, 1.5e6 on
shortest path, **1.85e11 on ultimate parent** — prices a language model at the
cost of being handed the whole structure: 1.99M tokens of ownership edges for a
question about one company. Nobody had asked how much of that a query actually
depends on, because until the read set was measurable there was no way to.

There is now. So this prices five query classes twice:

* **naive** — hand over the corpus, which is the published framing;
* **necessary** — hand over exactly the filings the answer depends on, which is
  an opponent with a perfect retriever, and the harder comparison to win.

Conventions, all stated because a ratio without a price sheet is not a number:

* symbolic cost = measured CPU seconds x $0.02/core-hour (`cost.py`);
* LLM cost = **input tokens only** at published rates, assuming a perfect model
  that emits nothing and pays nothing for retrieval — a **lower bound** on its
  cost, which is why these rows carry no equal-accuracy assumption;
* rates $1/Mtok (cheap tier) and $15/Mtok (frontier tier), the two this repo's
  earlier rows used;
* tokens = characters / 4.

Predictions are in
`notes/decisions/2026-08-18-drop-the-dense-graph-arm-and-measure-the-dependency-instead.md`.
"""

from __future__ import annotations

import collections
import importlib.util
import statistics
import time
from pathlib import Path
from typing import Mapping, Sequence

from symbolic_ai_core.runtime.ambiguity import (Alternatives, additive_bounds,
                                                possible_answers_scoped)
from symbolic_ai_tasks.ultimate_parent import load_task

BASE = Path("data/sources/gleif/commandagi-r2-2026-08-15")

_spec = importlib.util.spec_from_file_location(
    "gleif_scoped_ambiguity",
    Path(__file__).with_name("gleif_scoped_ambiguity.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)                                # type: ignore[union-attr]
key_of, ultimate = _mod.key_of, _mod.ultimate
build_closure_mixture = _mod.build_closure_mixture
_first_conflict = _mod._first_conflict

USD_PER_CORE_SECOND = 0.02 / 3600.0
CHEAP_USD_PER_MTOK = 1.0
FRONTIER_USD_PER_MTOK = 15.0


def tokens(text: str) -> float:
    """Characters over four. Stated, not implied."""
    return len(text) / 4.0


def edge_line(child: str, parent: str, kind: str) -> str:
    return f"{child} {kind} {parent}\n"


def corpus_tokens(task) -> float:
    """The naive framing: every filed edge, as text."""
    n = sum(tokens(edge_line(c, p, "direct")) for c, p in task.direct.items())
    n += sum(tokens(edge_line(c, p, "ultimate")) for c, p in task.truth.items())
    return n


def chain_context(entity: str, task, conflict_set) -> str:
    """Exactly the filings a correct answerer must see for one point query.

    The direct-ownership chain from the entity up to the first conflicted
    ancestor or the root, plus the filed ultimate of every entity on it — which
    is what makes the conflict visible and what makes "this is determined"
    checkable rather than assumed.
    """
    out, seen, cur = [], {entity}, entity
    while True:
        if cur in task.truth:
            out.append(edge_line(cur, task.truth[cur], "ultimate"))
        if key_of(cur) in conflict_set:
            break
        nxt = task.direct.get(cur)
        if nxt is None or nxt in seen:
            break
        out.append(edge_line(cur, nxt, "direct"))
        seen.add(nxt)
        cur = nxt
    return "".join(out)


def row(name: str, symbolic_seconds: float, n_answers: int,
        naive_tok: float, needed_tok: float) -> dict:
    sym = symbolic_seconds * USD_PER_CORE_SECOND / max(1, n_answers)
    naive = naive_tok / 1e6 * FRONTIER_USD_PER_MTOK
    naive_cheap = naive_tok / 1e6 * CHEAP_USD_PER_MTOK
    need = needed_tok / 1e6 * FRONTIER_USD_PER_MTOK
    need_cheap = needed_tok / 1e6 * CHEAP_USD_PER_MTOK
    return dict(name=name, sym=sym, naive_tok=naive_tok, needed_tok=needed_tok,
                naive=naive, need=need,
                adv_naive=naive / sym, adv_need=need / sym,
                adv_naive_cheap=naive_cheap / sym, adv_need_cheap=need_cheap / sym)


def show(rows: Sequence[dict]) -> None:
    print(f"\n{'query class':<34} {'ctx naive':>11} {'ctx needed':>11} "
          f"{'$ symbolic':>12} {'adv naive':>11} {'adv needed':>11}")
    for r in rows:
        print(f"{r['name']:<34} {r['naive_tok']:>11,.0f} {r['needed_tok']:>11,.0f} "
              f"{r['sym']:>12.2e} {r['adv_naive']:>11.2e} {r['adv_need']:>11.2e}")


def main() -> None:
    t_setup = time.perf_counter()
    task = load_task(BASE)
    alts, conflicts = build_closure_mixture(task)
    setup = time.perf_counter() - t_setup
    conflict_set = set(alts.choices)
    corpus = corpus_tokens(task)
    print(f"corpus: {len(task.direct):,} direct + {len(task.truth):,} ultimate "
          f"filings = {corpus:,.0f} tokens at chars/4")
    print(f"  (the published figure for this corpus is 1.99M -- same order, "
          f"and this convention is stated rather than inherited)")
    ids = task.ids
    rows = []

    # ---- 1. the point query ------------------------------------------
    t0 = time.perf_counter()
    for e in ids:
        possible_answers_scoped(lambda a, e=e: ultimate(e, task.direct, a), alts)
    wall = time.perf_counter() - t0
    ctx = [tokens(chain_context(e, task, conflict_set)) for e in ids]
    print(f"\npoint query: {len(ids):,} answers in {wall:.2f}s; necessary "
          f"context p50 {statistics.median(ctx):.0f} tok, mean "
          f"{statistics.fmean(ctx):.0f}, p99 "
          f"{sorted(ctx)[int(len(ctx)*0.99)]:.0f}, max {max(ctx):.0f}")
    rows.append(row("point: who ultimately owns X", wall, len(ids), corpus,
                    statistics.fmean(ctx)))

    # ---- 2. determinacy, which is the inspectability claim -----------
    t0 = time.perf_counter()
    undetermined = 0
    for e in ids:
        got = possible_answers_scoped(
            lambda a, e=e: ultimate(e, task.direct, a), alts)
        undetermined += got.ambiguous
    wall = time.perf_counter() - t0
    print(f"determinacy: {undetermined:,} of {len(ids):,} undetermined; the "
          f"context is the same filings, because a conflict here is visible "
          f"from the entity's own chain")
    rows.append(row("determined? + the alternatives", wall, len(ids), corpus,
                    statistics.fmean(ctx)))

    # ---- 3. the hub bracket ------------------------------------------
    children: dict[str, list[str]] = collections.defaultdict(list)
    for child, parent in task.direct.items():
        children[parent].append(child)
    nodes = set(task.direct) | set(task.direct.values())
    first = {e: _first_conflict(e, task.direct, conflict_set) for e in nodes}

    def subtree(h: str) -> list[str]:
        out, stack, seen = [], [h], {h}
        while stack:
            x = stack.pop()
            out.append(x)
            for c in children.get(x, ()):
                if c not in seen:
                    seen.add(c)
                    stack.append(c)
        return out

    hubs = []
    for h in children:
        members = subtree(h)
        ks = {first[e] for e in members} - {None}
        if len(members) > 1 and ks:
            hubs.append((h, members, sorted(ks, key=repr)))
    print(f"\n{len(hubs):,} hubs whose portfolio answer depends on the mixture")

    t0 = time.perf_counter()
    hub_ctx = []
    for h, members, ks in hubs:
        target = ultimate(h, task.direct, {})
        local = Alternatives({k: alts.choices[k] for k in ks})
        routed = collections.Counter(first[e] for e in members
                                     if first[e] is not None)
        base = sum(1 for e in members if first[e] is None
                   and ultimate(e, task.direct, {}) == target)
        additive_bounds(local,
                        lambda s, v, routed=routed, target=target:
                            routed[s] if v == target else 0, base=float(base))
        hub_ctx.append(tokens("".join(
            chain_context(e, task, conflict_set) for e in members)))
    wall = time.perf_counter() - t0
    print(f"  bounded in {wall:.2f}s; necessary context p50 "
          f"{statistics.median(hub_ctx):,.0f} tok, max {max(hub_ctx):,.0f}")
    rows.append(row("portfolio bracket for one hub", wall, len(hubs), corpus,
                    statistics.fmean(hub_ctx)))

    # ---- 4. the census: which answers are undetermined at all ---------
    t0 = time.perf_counter()
    census = sum(
        possible_answers_scoped(
            lambda a, e=e: ultimate(e, task.direct, a), alts).ambiguous
        for e in ids)
    wall = time.perf_counter() - t0
    print(f"\ncensus: {census:,} undetermined answers over the whole world in "
          f"{wall:.2f}s -- the dependency IS the corpus, so retrieval cannot "
          f"shrink it")
    rows.append(row("census: which answers are open", wall, 1, corpus, corpus))

    show(rows)

    # The marginal rows above charge a query for itself and nothing else. The
    # system that answers them had to read 476,875 filed rows and build the
    # mixture first, and this repo's own rule is that cost is charged to the
    # SYSTEM -- an upstream that a reasoner depends on is in the ledger. So the
    # same point query, amortised over the corpus that made it answerable:
    print(f"\n=== charged to the system, not to the query ===")
    print(f"  setup (parquet ingest + mixture build): {setup:.2f}s")
    amortised = (setup / len(ids)) * USD_PER_CORE_SECOND + rows[0]["sym"]
    print(f"  point query, marginal:  ${rows[0]['sym']:.2e} -> advantage "
          f"{rows[0]['need'] / rows[0]['sym']:.2e}")
    print(f"  point query, amortised: ${amortised:.2e} -> advantage "
          f"{rows[0]['need'] / amortised:.2e}  "
          f"({rows[0]['sym'] and (rows[0]['need']/rows[0]['sym'])/(rows[0]['need']/amortised):.1f}x "
          f"of the marginal figure was unamortised setup)")
    print(f"  and the setup is paid once for all {len(ids):,} queries, so a "
          f"workload of one pays ${setup * USD_PER_CORE_SECOND:.2e} and the "
          f"advantage there is {rows[0]['need'] / (setup * USD_PER_CORE_SECOND + rows[0]['sym']):.2e}")

    print("\n=== what retrieval takes away ===")
    for r in rows:
        print(f"  {r['name']:<34} naive {r['adv_naive']:.2e} -> needed "
              f"{r['adv_need']:.2e}  ({r['adv_naive']/r['adv_need']:,.0f}x of "
              f"the claimed advantage was the framing)")
    print("\n  at the cheap tier ($1/Mtok) the needed-context advantages are: "
          + ", ".join(f"{r['adv_need_cheap']:.2e}" for r in rows))


if __name__ == "__main__":
    main()
