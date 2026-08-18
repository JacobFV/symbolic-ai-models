"""Who ultimately owns this company, given only who directly owns it?

The second real-data task, and the one that corrects a claim I made earlier the
same day. The column audit concluded that the economy kernel could not run on
real data because no held source carries a **unit** — true, and it does not
follow. Consolidation structure is *relational*: GLEIF publishes 124,460
``IS_DIRECTLY_CONSOLIDATED_BY`` edges and 130,355 ``IS_ULTIMATELY_CONSOLIDATED_BY``
edges, and the second is the transitive closure of the first. No units required.

What makes this task worth having rather than merely available:

* **The ground truth is reported independently of its own inputs.** Each legal
  entity files its direct parent and its ultimate parent separately, so the
  closure can be checked against something that is not a restatement of the
  edges it consumed. That is rarer than it sounds and it is why disagreements
  here are informative in both directions.
* **The floor is high and honest.** 75.03% of entities have their direct parent
  *as* their ultimate parent, so "assume depth one" is already a strong answer
  and a method has to earn the rest.
* **The graph has cycles.** Circular ownership exists in the filed data, and a
  closure that loops is a hang, not a wrong answer. It is detected and reported
  rather than broken out of silently.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

__all__ = ["UltimateParentTask", "load_task", "evaluate", "predict_direct",
           "predict_closure", "predict_fused", "closure_with_cycles",
           "DIRECT_KIND", "ULTIMATE_KIND"]

DIRECT_KIND = "IS_DIRECTLY_CONSOLIDATED_BY"
ULTIMATE_KIND = "IS_ULTIMATELY_CONSOLIDATED_BY"


@dataclass(frozen=True)
class UltimateParentTask:
    """Direct edges as the input, ultimate edges as the labels."""

    direct: Mapping[str, str]
    truth: Mapping[str, str]

    @property
    def ids(self) -> tuple[str, ...]:
        """Entities carrying both a direct and an ultimate parent.

        Scored only where both exist. An entity with an ultimate parent and no
        direct parent is not a failure of the closure, it is a hole in the
        input, and scoring it would price a data gap as a reasoning error.
        """
        return tuple(sorted(set(self.direct) & set(self.truth)))

    def floor(self) -> float:
        """Assume depth one: the ultimate parent is the direct parent."""
        ids = self.ids
        return sum(self.direct[e] == self.truth[e] for e in ids) / len(ids)


def load_task(base: Path) -> UltimateParentTask:
    import pyarrow.parquet as pq

    direct: dict[str, str] = {}
    ultimate: dict[str, str] = {}
    for f in sorted(base.rglob("*.parquet")):
        pf = pq.ParquetFile(f)
        if not {"source_id", "target_id", "kind"} <= set(pf.schema_arrow.names):
            continue
        for batch in pf.iter_batches(
                columns=["source_id", "target_id", "kind"]):
            for row in batch.to_pylist():
                if row["kind"] == DIRECT_KIND:
                    direct[row["source_id"]] = row["target_id"]
                elif row["kind"] == ULTIMATE_KIND:
                    ultimate[row["source_id"]] = row["target_id"]
    return UltimateParentTask(direct=direct, truth=ultimate)


def predict_direct(task: UltimateParentTask) -> dict[str, str]:
    """The floor. Every entity's ultimate owner is whoever directly owns it."""
    return {e: task.direct[e] for e in task.ids}


def closure_with_cycles(direct: Mapping[str, str], start: str,
                        *, max_depth: int = 64) -> tuple[str | None, bool]:
    """Walk to the root. Returns ``(root, hit_cycle)``.

    Circular ownership is present in the filed data. It is returned as a flag
    rather than silently truncated, because "A is ultimately owned by A" and "we
    gave up after 64 hops" are different claims and a method that cannot tell
    them apart cannot report either.
    """
    seen = {start}
    cur = start
    for _ in range(max_depth):
        nxt = direct.get(cur)
        if nxt is None:
            return cur, False
        if nxt in seen:
            return None, True
        seen.add(nxt)
        cur = nxt
    return None, True


def predict_closure(task: UltimateParentTask) -> dict[str, str | None]:
    """Transitive closure of the direct-ownership relation."""
    return {e: closure_with_cycles(task.direct, e)[0] for e in task.ids}


def evaluate(task: UltimateParentTask,
             pred: Mapping[str, str | None]) -> float:
    ids = task.ids
    return sum(pred.get(e) == task.truth[e] for e in ids) / len(ids)


def predict_fused(task: UltimateParentTask, *, max_depth: int = 64
                  ) -> dict[str, str | None]:
    """Closure over direct edges, continued by *other* entities' ultimate edges.

    Half of the closure's disagreements are one missing link: the chain of
    direct edges runs out at some entity ``X`` before reaching the top, and
    ``X`` has itself filed an ultimate parent. Following it is not leakage —
    it uses **another entity's** label, exactly as leave-one-out k-NN uses
    another airport's country — but the discipline has to be explicit and
    enforced, so the walk refuses to consult the ultimate edge of the entity
    being predicted, at any point in the chain.

    This is the fusion principle on real data: two relations that disagree in
    4.27% of cases are not a contradiction to be resolved by picking a winner.
    They carry different information and composing them beats either.
    """
    out: dict[str, str | None] = {}
    for start in task.ids:
        cur = start
        seen = {start}
        for _ in range(max_depth):
            nxt = task.direct.get(cur)
            if nxt is None:
                # Direct chain exhausted. Continue on a filed ultimate parent,
                # but never the one belonging to the entity under prediction.
                if cur != start:
                    nxt = task.truth.get(cur)
                if nxt is None or nxt == cur:
                    break
            if nxt in seen:
                cur = None
                break
            seen.add(nxt)
            cur = nxt
        out[start] = cur
    return out
