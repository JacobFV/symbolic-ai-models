"""Do the 251 real ownership conflicts also sit on fund-management hubs?

`notes/findings/2026-08-18-ambiguity-does-not-propagate-in-a-forest-and-that-is-why-retention-is-affordable.md`
measured exposure -- how many answers change if a conflict lands on a node --
across GLEIF's three largest relations and found four orders of magnitude
*within* each relation, driven by hubs (a fund manager with 1,258 funds, a fund
family with 3,847 subfunds). But the finding's "what would refute it" section
named a real gap: the 251 *actual* conflicts were only ever walked through the
ownership relation (`IS_DIRECTLY_CONSOLIDATED_BY`). `IS_FUND-MANAGED_BY`
(146,948 edges) and `IS_SUBFUND_OF` (71,833 edges) were never checked against
the entities that are actually conflicted -- only against the general
population, to build the percentile table.

Hypothesis, stated before the number: the 251 conflicts are entities whose
*direct-consolidation* filing disagrees with their *ultimate-consolidation*
filing -- both corporate ownership facts. A fund manager or a subfund is a
different part of GLEIF's entity population (funds and the firms that run
them), so I expect low overlap: most of the 251 will not appear in either fund
relation at all, and total exposure summed over the fund graphs for exactly
these 251 nodes will stay small (order of tens, not the 31,111 that the earlier
finding computed for conflicts placed *deliberately* on the highest-exposure
nodes).
"""

from __future__ import annotations

import collections
from pathlib import Path
from typing import Mapping

import pyarrow.parquet as pq

from symbolic_ai_core.runtime.ambiguity import exposure
from symbolic_ai_tasks.ultimate_parent import load_task

BASE = Path("data/sources/gleif/commandagi-r2-2026-08-15")
RELATIONSHIPS = BASE / "gleif" / "relationships_p0.parquet"

FUND_MANAGED_KIND = "IS_FUND-MANAGED_BY"
SUBFUND_KIND = "IS_SUBFUND_OF"


def load_children(kind: str) -> dict[str, list[str]]:
    """source -[kind]-> target, as target -> [sources] ("who reports to me")."""
    children: dict[str, list[str]] = collections.defaultdict(list)
    pf = pq.ParquetFile(RELATIONSHIPS)
    for batch in pf.iter_batches(columns=["source_id", "target_id", "kind"]):
        for row in batch.to_pylist():
            if row["kind"] == kind:
                children[row["target_id"]].append(row["source_id"])
    return dict(children)


def load_all_nodes(kind: str) -> set[str]:
    """Every entity touching ``kind`` in either role, leaf or hub."""
    nodes: set[str] = set()
    pf = pq.ParquetFile(RELATIONSHIPS)
    for batch in pf.iter_batches(columns=["source_id", "target_id", "kind"]):
        for row in batch.to_pylist():
            if row["kind"] == kind:
                nodes.add(row["source_id"])
                nodes.add(row["target_id"])
    return nodes


def _direct_chain(direct: Mapping[str, str], start: str,
                  *, max_depth: int = 64) -> list[str]:
    seen = [start]
    cur = start
    for _ in range(max_depth):
        nxt = direct.get(cur)
        if nxt is None or nxt in seen:
            return seen
        seen.append(nxt)
        cur = nxt
    return seen


def real_conflicts(task) -> list[str]:
    """The 251 from the retention finding: the filed ultimate parent names an
    entity that is a *mid-chain intermediate* on the entity's own filed
    direct-consolidation chain, not the chain's actual root. Reproduced here
    (matches 251 exactly) rather than reusing the registry's looser
    closure-disagrees-with-filed test, which is a different and larger set
    (4,992) -- the two prior findings used different definitions of
    "conflict" and this script is explicit about using the retention
    finding's, since that is the one this experiment is extending."""
    out = []
    for e in task.ids:
        chain = _direct_chain(task.direct, e)
        intermediates = set(chain[1:-1])
        if task.truth[e] in intermediates and task.truth[e] != chain[-1]:
            out.append(e)
    return out


def summarize(label: str, values: list[int]) -> None:
    n = len(values)
    s = sorted(values)
    nonzero = sum(1 for v in values if v > 1)
    print(f"{label}: n={n} sum={sum(values)} "
          f"mean={sum(values) / n:.3f} median={s[n // 2]} max={max(values)} "
          f"nodes_with_exposure>1={nonzero}")


def main() -> None:
    task = load_task(BASE)
    conflicts = real_conflicts(task)
    print(f"real conflicts (mid-chain intermediate contradicts the filed "
          f"ultimate): {len(conflicts)}")

    ownership_children: dict[str, list[str]] = collections.defaultdict(list)
    for child, parent in task.direct.items():
        ownership_children[parent].append(child)
    ownership_exposure = [exposure(e, ownership_children) for e in conflicts]
    summarize("exposure via ownership (the finding's own baseline)",
              ownership_exposure)

    fund_children = load_children(FUND_MANAGED_KIND)
    subfund_children = load_children(SUBFUND_KIND)
    print(f"IS_FUND-MANAGED_BY hub nodes: {len(fund_children)}  "
          f"IS_SUBFUND_OF hub nodes: {len(subfund_children)}")

    in_fund = sum(1 for e in conflicts if e in fund_children)
    in_subfund = sum(1 for e in conflicts if e in subfund_children)
    print(f"of the {len(conflicts)} conflicts, {in_fund} are a fund-management "
          f"hub and {in_subfund} are a subfund-family hub")

    fund_nodes = load_all_nodes(FUND_MANAGED_KIND)
    subfund_nodes = load_all_nodes(SUBFUND_KIND)
    touches_either = sum(1 for e in conflicts
                        if e in fund_nodes or e in subfund_nodes)
    print(f"of the {len(conflicts)} conflicts, {touches_either} appear "
          f"anywhere (leaf or hub) in either fund relation; "
          f"{len(conflicts) - touches_either} touch neither at all")

    fund_exposure = [exposure(e, fund_children) for e in conflicts]
    subfund_exposure = [exposure(e, subfund_children) for e in conflicts]
    summarize("exposure via IS_FUND-MANAGED_BY", fund_exposure)
    summarize("exposure via IS_SUBFUND_OF", subfund_exposure)

    combined_children: dict[str, list[str]] = collections.defaultdict(list)
    for d in (fund_children, subfund_children):
        for k, v in d.items():
            combined_children[k].extend(v)
    combined_exposure = [exposure(e, combined_children) for e in conflicts]
    summarize("exposure via fund+subfund combined", combined_exposure)

    print(f"\ntotal exposure (fund+subfund) for the real 251: "
          f"{sum(combined_exposure)}")

    # The refuter this finding named: "restricting to IS_FUND-MANAGED_BY /
    # IS_SUBFUND_OF misses a third cross-population relation this script did
    # not check -- IS_INTERNATIONAL_BRANCH_OF (1,920 edges) and IS_FEEDER_TO
    # (1,359 edges) are smaller and unexamined here." Checked now, on the same
    # 251, with the same walk.
    print()
    for kind in ("IS_INTERNATIONAL_BRANCH_OF", "IS_FEEDER_TO"):
        kids = load_children(kind)
        all_nodes = load_all_nodes(kind)
        hubs = sum(1 for e in conflicts if e in kids)
        anywhere = sum(1 for e in conflicts if e in all_nodes)
        exp = [exposure(e, kids) for e in conflicts]
        print(f"{kind}: {len(all_nodes):,} nodes, {len(kids):,} hubs; of the "
              f"{len(conflicts)} conflicts {hubs} are a hub and {anywhere} "
              f"appear anywhere")
        summarize(f"exposure via {kind}", exp)


if __name__ == "__main__":
    main()
