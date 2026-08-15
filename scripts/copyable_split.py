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
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")

import numpy as np
import torch

torch.set_num_threads(4)

from symbolic_ai_core.data.batch import IGNORE, collate_graph
from symbolic_ai_models.train import load_data, load_run


def split(path: str, batch_size: int = 16) -> dict[str, float]:
    model, tok, cfg = load_run(path, device="cpu")
    summary = json.loads((Path(path) / "summary.json").read_text())
    mode = (summary.get("masking") or {}).get("mask_mode", "scatter")
    _, ev = load_data(cfg)

    rng = np.random.default_rng(cfg.seed)
    hit = {True: 0, False: 0}
    n = {True: 0, False: 0}
    for start in range(0, len(ev), batch_size):
        chunk = ev[start:start + batch_size]
        batch = collate_graph(chunk, tok, max_nodes=cfg.max_nodes,
                              mask_rate=cfg.mask_rate, mask_mode=mode, rng=rng)
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
    }


def main(paths: list[str]) -> int:
    head = (f"{'model':<22}{'mode':<9}{'rate':>5}{'n':>7}{'copyable':>10}"
            f"{'acc | copyable':>16}{'acc | not':>11}{'acc all':>9}{'gap':>8}")
    print(head)
    print("-" * len(head))
    for p in paths:
        if not (Path(p) / "summary.json").exists():
            continue
        r = split(p)
        gap = r["acc_copyable"] - r["acc_not_copyable"]
        print(f"{r['model']:<22}{r['mode']:<9}{r['mask_rate']:>5.2f}"
              f"{r['n']:>7.0f}{r['copyable_share']:>10.3f}"
              f"{r['acc_copyable']:>16.3f}{r['acc_not_copyable']:>11.3f}"
              f"{r['acc_all']:>9.3f}{gap:>8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
