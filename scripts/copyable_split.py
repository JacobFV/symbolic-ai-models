"""How much of the masked-node score is coreference?

Rung 3 found that the curriculum's own answer is 0% copyable — hiding it means
hiding every node that says it — and that on that question every equivariant
model falls to the abstention row. The obvious next question is what the
*published* number is made of. 71.9% of scored answers on ordinary scattered
masking already sit on a visible node, so `label_acc` is a mixture of two very
different questions, and nothing in the repo has ever reported them apart.

This rescores a finished `node` run — the sweep's own fitted model, the run's
own config, all 179 lessons, evaluation seeds — splitting the scored fills by
whether `target_source` found a visible node carrying the same label:

* **copyable**: the answer is in plain sight somewhere else in the graph;
* **not copyable**: it is not, and the symbol has to come from somewhere else.

A model whose two columns are far apart is answering by coreference and the
single number is hiding it. A model whose columns are close is naming.

    uv run python scripts/copyable_split.py runs/infill-node-r015/*
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")

import numpy as np
import torch

torch.set_num_threads(4)

from symbolic_ai_core.data.batch import IGNORE
from symbolic_ai_core.data.sampler import batches
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run

#: Which registered task each masking mode belongs to, so the floor is the
#: floor of the arm being read rather than of `node`.
TASK_OF = {"scatter": "node", "subtree": "nodesub",
           "answer": "nodeans", "answer_one": "nodeans1"}


def split(path: str, batch_size: int = 16,
          floors: dict | None = None) -> dict[str, float]:
    model, tok, cfg = load_run(path, device="cpu")
    summary = json.loads((Path(path) / "summary.json").read_text())
    mode = (summary.get("masking") or {}).get("mask_mode", "scatter")
    train, ev = load_data(cfg)

    if floors is not None and "floor_copyable" not in floors:
        task = make_task(TASK_OF[mode], mask_rate=cfg.mask_rate,
                         max_nodes=cfg.max_nodes)
        floors.update(task.split_floor(ev, tok, train))
        # The guard against `split_floor` having become a second implementation
        # of the floor: pooled, it must be the number the run itself published.
        published = next(
            (v.get("label_floor") for v in (summary.get("final") or {}).values()
             if isinstance(v, dict) and "label_floor" in v), None)
        if published is not None:
            assert abs(floors["floor_pooled"] - published) < 1e-12, (
                f"split floor {floors['floor_pooled']} != published {published}")

    # The *same* draw the run itself scored, not another sample from the same
    # regime: `evaluate_model` resets the task's rng to 12345 and walks the
    # episodes unshuffled under `random.Random(0)`. Reproducing that is what
    # makes `acc_all` below bit-identical to the run's published `label_acc`,
    # and `main` asserts it — an independent draw agrees only to about 0.018,
    # which is enough to make a reader wonder which number they are reading.
    task = make_task(TASK_OF[mode], mask_rate=cfg.mask_rate,
                     max_nodes=cfg.max_nodes, seed=cfg.seed)
    task.rng = np.random.default_rng(12345)
    model.eval()
    hit = {True: 0, False: 0}
    n = {True: 0, False: 0}
    for batch in batches(ev, task, tok, batch_size=cfg.batch_size,
                         rng=random.Random(0), shuffle=False):
        with torch.no_grad():
            pred = model(batch).symbol_logits.argmax(-1)
        scored = batch.target_tokens != IGNORE
        correct = (pred == batch.target_tokens) & scored
        copyable = batch.target_source != IGNORE
        for flag in (True, False):
            sel = scored & (copyable if flag else ~copyable)
            n[flag] += int(sel.sum())
            hit[flag] += int((correct & sel).sum())
    total = n[True] + n[False]
    return {
        "copyable_share": n[True] / total if total else float("nan"),
        "acc_copyable": hit[True] / n[True] if n[True] else float("nan"),
        "acc_not_copyable": hit[False] / n[False] if n[False] else float("nan"),
        "acc_all": (hit[True] + hit[False]) / total if total else float("nan"),
        "n": float(total), "mask_rate": cfg.mask_rate, "mode": mode,
        "model": summary.get("model", Path(path).name),
        "published": next(
            (v.get("label_acc") for v in (summary.get("final") or {}).values()
             if isinstance(v, dict) and "label_acc" in v), float("nan")),
    }


def main(paths: list[str]) -> int:
    head = (f"{'model':<22}{'mode':<9}{'rate':>5}{'n':>7}{'copyable':>10}"
            f"{'acc | copyable':>16}{'acc | not':>11}{'acc all':>9}{'gap':>8}")
    print(head)
    print("-" * len(head))
    floors: dict[str, float] = {}
    for p in paths:
        if not (Path(p) / "summary.json").exists():
            continue
        r = split(p, floors=floors)
        # The run scored this model on this draw; if the pooled number here is
        # not that number, this is measuring something else.
        assert abs(r["acc_all"] - r["published"]) < 1e-9, (
            f"{r['model']}: pooled {r['acc_all']} != published {r['published']}")
        gap = r["acc_copyable"] - r["acc_not_copyable"]
        print(f"{r['model']:<22}{r['mode']:<9}{r['mask_rate']:>5.2f}"
              f"{r['n']:>7.0f}{r['copyable_share']:>10.3f}"
              f"{r['acc_copyable']:>16.3f}{r['acc_not_copyable']:>11.3f}"
              f"{r['acc_all']:>9.3f}{gap:>8.3f}")
    if floors:
        print("-" * len(head))
        print(f"{'FLOOR (structure only)':<22}{'':<9}{'':>5}"
              f"{floors['n_copyable'] + floors['n_not_copyable']:>7.0f}"
              f"{floors['n_copyable'] / (floors['n_copyable'] + floors['n_not_copyable']):>10.3f}"
              f"{floors['floor_copyable']:>16.3f}"
              f"{floors['floor_not_copyable']:>11.3f}"
              f"{floors['floor_pooled']:>9.3f}"
              f"{floors['floor_copyable'] - floors['floor_not_copyable']:>8.3f}")
        print("the pooled floor is asserted equal to the run's own `label_floor`, "
              "which is what says this is the same floor and not a second one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
