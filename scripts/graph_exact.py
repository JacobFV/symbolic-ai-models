"""Rung 4, minus the render: is the completed graph ever exactly right?

The ladder's last rung was "render and score exact-match end to end". The
renderer takes the generator's own term object, not this repo's flattened
:class:`~symbolic_ai_core.data.graph.Graph`, so a real end-to-end render needs an
inverse of ``graph_from_json`` — real work with its own correctness burden. It is
also, for now, unnecessary, because the render is a **deterministic function of
the term**: a graph that is not exactly right cannot render to text that is. So

    exact_match  <=  graph exact-match

and the cheap side of that inequality is enough to answer the ladder's third
refutation condition. If no episode's hidden region is ever reconstructed
exactly, the render adds nothing but a longer pipeline.

This reloads a finished run — the sweep's own fitted model, the run's own
config, all 179 lessons, evaluation seeds — and scores three nested things:

* ``label``: the ordinary per-node label accuracy, as a check that this agrees
  with the run's own `summary.json` and is therefore scoring the same thing;
* ``episode_labels``: every scored label in the episode right at once;
* ``episode_all``: every scored label **and** every masked type right at once,
  which is what "the completed graph is the graph" means.

    uv run python scripts/graph_exact.py runs/infill-node-r015/corefer-001
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


def run(path: str, batch_size: int = 16) -> dict[str, float]:
    model, tok, cfg = load_run(path, device="cpu")
    summary = json.loads((Path(path) / "summary.json").read_text())
    masking = summary.get("masking") or {}
    mode = masking.get("mask_mode", "scatter")
    _, ev = load_data(cfg)

    rng = np.random.default_rng(cfg.seed)
    lab_hit = lab_n = 0
    ep_lab_hit = ep_all_hit = ep_n = 0
    for start in range(0, len(ev), batch_size):
        chunk = ev[start:start + batch_size]
        batch = collate_graph(chunk, tok, max_nodes=cfg.max_nodes,
                              mask_rate=cfg.mask_rate, mask_mode=mode, rng=rng)
        with torch.no_grad():
            out = model(batch)
        label_pred = out.symbol_logits.argmax(-1)
        type_pred = out.type_logits.argmax(-1)
        for b in range(len(chunk)):
            lab_mask = batch.target_tokens[b] != IGNORE
            typ_mask = batch.target_types[b] != IGNORE
            if not bool(lab_mask.any()):
                continue                       # unscored episode, not a zero
            ep_n += 1
            lab_ok = (label_pred[b][lab_mask] == batch.target_tokens[b][lab_mask])
            typ_ok = (type_pred[b][typ_mask] == batch.target_types[b][typ_mask])
            lab_hit += int(lab_ok.sum())
            lab_n += int(lab_mask.sum())
            ep_lab_hit += int(bool(lab_ok.all()))
            ep_all_hit += int(bool(lab_ok.all()) and bool(typ_ok.all()))
    return {
        "label_acc": lab_hit / lab_n if lab_n else float("nan"),
        "label_n": float(lab_n),
        "episodes_scored": float(ep_n),
        "episode_labels_exact": ep_lab_hit / ep_n if ep_n else float("nan"),
        "episode_all_exact": ep_all_hit / ep_n if ep_n else float("nan"),
        "summary_label_acc": next(
            (v.get("label_acc") for v in (summary.get("final") or {}).values()
             if isinstance(v, dict) and "label_acc" in v), float("nan")),
        "mask_mode": mode, "mask_rate": cfg.mask_rate,
    }


def main(paths: list[str]) -> int:
    head = (f"{'run':<44}{'mode':<10}{'rate':>6}{'lbl acc':>9}"
            f"{'(summary)':>11}{'eps':>7}{'lbl exact':>11}{'all exact':>11}")
    print(head)
    print("-" * len(head))
    for p in paths:
        r = run(p)
        print(f"{p:<44}{r['mask_mode']:<10}{r['mask_rate']:>6.2f}"
              f"{r['label_acc']:>9.3f}{r['summary_label_acc']:>11.3f}"
              f"{r['episodes_scored']:>7.0f}{r['episode_labels_exact']:>11.4f}"
              f"{r['episode_all_exact']:>11.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
