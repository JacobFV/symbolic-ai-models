"""Can a retriever find what the answer depends on?

The advantage finding priced a language model that is handed **exactly** the
filings a query depends on, and got a flat ~5e7. That opponent does not exist:
knowing which lines matter is the read set, which is this substrate's output.
The opponent that exists is agentic retrieval — fetch what mentions the
question, read it, discover a new identifier, fetch again — and its failure mode
is stopping early with a context that *looks* complete.

So this simulates it, generously: an **ideal lexical retriever** with perfect
recall on any identifier it already holds, no embedding noise, no top-k cutoff.
Every filed line mentioning a known identifier comes back. The only thing it
cannot do is know an identifier it has not seen yet — which is the whole
question.

Two queries, deliberately different in kind:

* **the lookup** — "who does X file as its ultimate parent". A database
  question, and retrieval should win it.
* **determinacy** — "is that answer consistent with X's own filed ownership
  chain, or do the filings disagree". Its dependency runs through identifiers
  the question never mentions.

Predictions are in
`notes/decisions/2026-08-18-price-the-realistic-opponent-agentic-retrieval-not-an-oracle.md`.
"""

from __future__ import annotations

import collections
import importlib.util
import statistics
import time
from pathlib import Path
from typing import Mapping

from symbolic_ai_tasks.ultimate_parent import load_task

BASE = Path("data/sources/gleif/commandagi-r2-2026-08-15")

_spec = importlib.util.spec_from_file_location(
    "gleif_scoped_ambiguity",
    Path(__file__).with_name("gleif_scoped_ambiguity.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)                                # type: ignore[union-attr]
key_of = _mod.key_of
build_closure_mixture = _mod.build_closure_mixture

USD_PER_CORE_SECOND = 0.02 / 3600.0
FRONTIER_USD_PER_MTOK = 15.0
#: A round trip is not just its retrieved lines. Instructions, the question, the
#: prior turn's reasoning: charged flat and deliberately low, because the
#: conclusion should not rest on a generous estimate of the opponent's overhead.
PROMPT_OVERHEAD_TOKENS = 400.0


def tokens(text: str) -> float:
    return len(text) / 4.0


def line_of(child: str, parent: str, kind: str) -> str:
    return f"{child} {kind} {parent}\n"


def build_index(task) -> dict[str, list[str]]:
    """identifier -> every filed line mentioning it, in either position.

    This is the *ideal* retriever: perfect recall by exact identifier, which is
    the friendliest possible case for lexical search and strictly better than
    any embedding index would do on 20-character LEIs.
    """
    index: dict[str, list[str]] = collections.defaultdict(list)
    for c, p in task.direct.items():
        line = line_of(c, p, "direct")
        index[c].append(line)
        index[p].append(line)
    for c, p in task.truth.items():
        line = line_of(c, p, "ultimate")
        index[c].append(line)
        index[p].append(line)
    return index


def rounds_to_close(entity: str, task, index: Mapping[str, list[str]],
                    *, max_rounds: int = 64) -> tuple[int, float, bool]:
    """Retrieve until the *ownership chain* is closed.

    Returns (rounds, tokens retrieved, closed). A round fetches everything
    mentioning every identifier held so far; the next identifier the chain needs
    only becomes known once the previous hop's line has been read, which is what
    makes this multi-hop rather than one-shot.
    """
    known = {entity}
    seen_lines: set[str] = set()
    total = 0.0
    for r in range(1, max_rounds + 1):
        fetched = set()
        for ident in list(known):
            fetched.update(index.get(ident, ()))
        new = fetched - seen_lines
        seen_lines |= fetched
        total += sum(tokens(line) for line in new)
        # Has the chain from `entity` been walked to a root or a conflict?
        cur, walked, closed = entity, {entity}, False
        while True:
            nxt = task.direct.get(cur)
            if nxt is None or nxt in walked:
                closed = True
                break
            if nxt not in known:
                break                      # need another round to learn it
            walked.add(nxt)
            cur = nxt
        if closed:
            return r, total, True
        # The next round knows whatever the fetched lines named.
        before = len(known)
        for line in fetched:
            a, _, b = line.split()
            known.add(a)
            known.add(b)
        if len(known) == before:
            return r, total, False
    return max_rounds, total, False


def chain_of(entity: str, direct: Mapping[str, str], *, cap: int = 64
             ) -> list[str]:
    out, seen, cur = [entity], {entity}, entity
    for _ in range(cap):
        nxt = direct.get(cur)
        if nxt is None or nxt in seen:
            break
        out.append(nxt)
        seen.add(nxt)
        cur = nxt
    return out


def main() -> None:
    t0 = time.perf_counter()
    task = load_task(BASE)
    alts, conflicts = build_closure_mixture(task)
    conflicted = {k[1] for k in alts.choices}
    index = build_index(task)
    ids = task.ids
    print(f"{len(ids):,} entities, {len(index):,} indexed identifiers, "
          f"{len(conflicted):,} conflicted, in {time.perf_counter()-t0:.1f}s")

    # ---- the lookup: retrieval should win this, and it is not the point ----
    answerable_r1 = sum(1 for e in ids if e in task.truth)
    print(f"\n=== the lookup: 'who does X file as its ultimate parent' ===")
    print(f"  answered verbatim by round 1: {answerable_r1:,}/{len(ids):,} "
          f"({answerable_r1/len(ids)*100:.1f}%) -- this is a database question "
          f"and retrieval wins it")

    # ---- determinacy: the dependency runs through unnamed identifiers ------
    print(f"\n=== determinacy: 'do the filings agree about X?' ===")
    depth = [len(chain_of(e, task.direct)) for e in ids]
    print(f"  chain length p50 {statistics.median(depth):.0f}, "
          f"p90 {sorted(depth)[int(len(depth)*0.9)]}, max {max(depth)}")

    # At which round does the conflict become *visible at all*? A retriever
    # holds every identifier named in every line it has fetched -- including
    # the one its own filed ultimate names, which it sees in round 1. An
    # earlier version of this simulation seeded the held set with the chain
    # prefix only, which understated the opponent and flattered us; it is the
    # exact shape of control-constructed-to-pass this repo has a lesson about.
    def decidable_round(e: str, *, cap: int = 64) -> int:
        """Rounds until every line the conflict test needs has been fetched."""
        chain = chain_of(e, task.direct)
        needed = {line_of(c, task.direct[c], "direct")
                  for c in chain if c in task.direct}
        if e in task.truth:
            needed.add(line_of(e, task.truth[e], "ultimate"))
        known, fetched = {e}, set()
        for r in range(1, cap + 1):
            new_lines = set()
            for ident in known:
                new_lines.update(index.get(ident, ()))
            fetched |= new_lines
            if needed <= fetched:
                return r
            before = len(known)
            for line in new_lines:
                a, _, b = line.split()
                known.add(a)
                known.add(b)
            if len(known) == before:
                return cap + 1
        return cap + 1

    when = collections.Counter(decidable_round(e) for e in conflicted)
    cum = 0
    for k in (1, 2, 3, 4):
        cum += when.get(k, 0)
        silent = len(conflicted) - cum
        print(f"  k={k}: the conflict is still invisible to {silent:,} of "
              f"{len(conflicted):,} conflicted entities "
              f"({silent/len(ids)*100:.3f}% of the world would be answered "
              f"'determined' when it is not)")
    print(f"  rounds needed to make the conflict visible: p50 "
          f"{sorted(when.elements())[len(list(when.elements()))//2]}, "
          f"max {max(when)}")

    # ---- rounds to actually close the dependency --------------------------
    sample = ids[::37]                       # deterministic, 3,166 entities
    t0 = time.perf_counter()
    stats = [rounds_to_close(e, task, index) for e in sample]
    wall = time.perf_counter() - t0
    rounds = [r for r, _, _ in stats]
    toks = [t for _, t, _ in stats]
    closed = sum(1 for _, _, c in stats if c)
    print(f"\n=== rounds to close the dependency, over {len(sample):,} "
          f"entities ({wall:.1f}s to simulate) ===")
    print(f"  rounds p50 {statistics.median(rounds):.0f}, "
          f"p90 {sorted(rounds)[int(len(rounds)*0.9)]}, max {max(rounds)}; "
          f"closed {closed:,}/{len(sample):,}")
    print(f"  retrieved tokens p50 {statistics.median(toks):,.0f}, "
          f"mean {statistics.fmean(toks):,.0f}, "
          f"p99 {sorted(toks)[int(len(toks)*0.99)]:,.0f}, "
          f"max {max(toks):,.0f}")

    # ---- the realistic price ---------------------------------------------
    per_query_tok = statistics.fmean(
        [t + r * PROMPT_OVERHEAD_TOKENS for r, t, _ in stats])
    llm = per_query_tok / 1e6 * FRONTIER_USD_PER_MTOK
    sym_marginal = 1.22e-11                  # measured in ambiguity_advantage
    sym_amortised = 3.15e-11
    print(f"\n=== the realistic opponent's price ===")
    print(f"  {statistics.fmean(rounds):.2f} rounds x "
          f"({statistics.fmean(toks):,.0f} retrieved + "
          f"{PROMPT_OVERHEAD_TOKENS:.0f} overhead) = {per_query_tok:,.0f} "
          f"tokens/query")
    print(f"  at ${FRONTIER_USD_PER_MTOK}/Mtok input only: ${llm:.2e} per query")
    print(f"  against the substrate: marginal ${sym_marginal:.2e} -> "
          f"advantage {llm/sym_marginal:.2e}")
    print(f"                         amortised ${sym_amortised:.2e} -> "
          f"advantage {llm/sym_amortised:.2e}")
    print(f"  for comparison: oracle-retrieval opponent was 5.03e+07 and the "
          f"whole-corpus framing 5.01e+12")


if __name__ == "__main__":
    main()
