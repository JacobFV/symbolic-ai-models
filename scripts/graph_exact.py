"""Rung 4, minus the render: is the completed graph ever exactly right?

The ladder's last rung was "render and score exact-match end to end". The
renderer takes the generator's own term object, not this repo's flattened
:class:`~symbolic_ai_core.data.term_graph.TermGraph`, so a real end-to-end render needs an
inverse of ``term_graph_from_json`` — real work with its own correctness burden.

**The inequality this script was first written under was the wrong way round.**
It said ``exact_match <= graph exact-match`` "because the render is a
deterministic function of the term". Determinism gives the opposite implication:
a function maps equal inputs to equal outputs, so a graph that *is* exactly right
renders to text that is, and therefore

    exact_match  >=  graph exact-match.

The stated bound needs the render to be **injective** — two different terms never
rendering to the same text — which nothing in this repo has measured and which
`notes/findings/2026-08-13-the-renderer-is-deterministic.md` does not claim. A
hidden label that never surfaces in the prose can be predicted wrongly at no cost
to the rendered text, and then text exactness is strictly *easier* than graph
exactness.

So this scores the bracket instead, which is what the cheap side can honestly
say. Under the natural implementation of rung 4 — patch the true term at the
masked positions with the model's predictions, then render, which is the only
version in which the graph's own lossiness (``max_nodes``, float rounding,
exploded strings) does not contaminate the measurement:

* ``episode_labels`` is a **lower** bound on ``exact_match``;
* ``episode_surfacing`` — every scored label *whose symbol appears as a word of
  the prompt* right, the rest free — is an **upper** estimate, exact if a label
  surfaces in the text only when its own string does.

This reloads a finished run — the sweep's own fitted model, the run's own
config, all 179 lessons, evaluation seeds — and scores:

* ``label``: the ordinary per-node label accuracy, as a check that this agrees
  with the run's own `summary.json` and is therefore scoring the same thing;
* ``episode_labels``: every scored label in the episode right at once;
* ``episode_all``: every scored label **and** every masked type right at once,
  which is what "the completed graph is the graph" means;
* ``surfacing``: the share of scored fills whose symbol is a word of the prompt;
* ``episode_surfacing``: every *surfacing* scored label right at once.

    uv run python scripts/graph_exact.py runs/infill-node-r015/corefer-001
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
from symbolic_ai_core.data.term_graph import NODE_TYPES
from symbolic_ai_core.data.sampler import batches
# The prompt-leak audit's own splitter, imported rather than copied: whether a
# symbol "appears in the prompt" has to mean the same thing in both places.
from symbolic_ai_core.shortcuts import _words
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run

#: Which registered task each masking mode belongs to.
TASK_OF = {"scatter": "node", "subtree": "nodesub",
           "answer": "nodeans", "answer_one": "nodeans1"}


def run(path: str, batch_size: int = 16) -> dict[str, float]:
    model, tok, cfg = load_run(path, device="cpu")
    summary = json.loads((Path(path) / "summary.json").read_text())
    masking = summary.get("masking") or {}
    mode = masking.get("mask_mode", "scatter")
    _, ev = load_data(cfg)

    # The run's own draw, not another sample from the same regime:
    # `evaluate_model` resets the task's rng to 12345 and walks the episodes
    # unshuffled under `random.Random(0)`. `label_acc` below is then bit-identical
    # to the row's published one, which is the check that this scores the same
    # fills the exactness is being claimed about.
    task = make_task(TASK_OF[mode], mask_rate=cfg.mask_rate,
                     max_nodes=cfg.max_nodes, seed=cfg.seed)
    task.rng = np.random.default_rng(12345)
    model.eval()
    lab_hit = lab_n = 0
    ep_lab_hit = ep_all_hit = ep_n = 0
    surf_n = surf_hit = 0
    ep_surf_hit = 0
    #: node type -> [surfacing fills, scored fills]. Reported because "the symbol
    #: is a word of the prompt" is a *proxy* for "the renderer prints it", and a
    #: proxy that behaved oddly per type -- field names surfacing, say -- would
    #: be the first sign the proxy is wrong.
    surf_type: dict[str, list[int]] = {}
    for batch in batches(ev, task, tok, batch_size=cfg.batch_size,
                         rng=random.Random(0), shuffle=False):
        with torch.no_grad():
            out = model(batch)
        label_pred = out.symbol_logits.argmax(-1)
        type_pred = out.type_logits.argmax(-1)
        prompts = (batch.meta or {}).get("prompts") or []
        for b in range(int(batch.tokens.shape[0])):
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

            # The render side. A hidden symbol the prose never says cannot make
            # the rendered text wrong however badly it is guessed, so only the
            # surfacing fills bound `exact_match` from above. An episode with no
            # surfacing fill renders correctly whatever the model does, which is
            # why it counts as a hit here and is the whole reason this number is
            # not the one above.
            words = set(_words(prompts[b])) if b < len(prompts) else set()
            all_surf_ok = True
            for i in torch.nonzero(lab_mask, as_tuple=False).flatten().tolist():
                here = tok.itos[int(batch.target_tokens[b, i])].lower() in words
                cell = surf_type.setdefault(
                    NODE_TYPES[int(batch.target_types[b, i])], [0, 0])
                cell[0] += int(here)
                cell[1] += 1
                if not here:
                    continue
                surf_n += 1
                good = bool(label_pred[b, i] == batch.target_tokens[b, i])
                surf_hit += int(good)
                all_surf_ok &= good
            ep_surf_hit += int(all_surf_ok)
    return {
        "label_acc": lab_hit / lab_n if lab_n else float("nan"),
        "label_n": float(lab_n),
        "episodes_scored": float(ep_n),
        "episode_labels_exact": ep_lab_hit / ep_n if ep_n else float("nan"),
        "episode_all_exact": ep_all_hit / ep_n if ep_n else float("nan"),
        "surfacing_share": surf_n / lab_n if lab_n else float("nan"),
        "surfacing_by_type": surf_type,
        "surfacing_acc": surf_hit / surf_n if surf_n else float("nan"),
        "episode_surfacing_exact": ep_surf_hit / ep_n if ep_n else float("nan"),
        "summary_label_acc": next(
            (v.get("label_acc") for v in (summary.get("final") or {}).values()
             if isinstance(v, dict) and "label_acc" in v), float("nan")),
        "mask_mode": mode, "mask_rate": cfg.mask_rate,
    }


def main(paths: list[str]) -> int:
    head = (f"{'run':<40}{'mode':<9}{'rate':>6}{'lbl acc':>9}"
            f"{'(summary)':>11}{'eps':>7}{'lbl exact':>11}{'all exact':>11}"
            f"{'surfacing':>11}{'surf acc':>10}{'surf exact':>12}")
    print(head)
    print("-" * len(head))
    last = None
    for p in paths:
        r = run(p)
        r["run"] = p
        last = r
        print(f"{p:<40}{r['mask_mode']:<9}{r['mask_rate']:>6.2f}"
              f"{r['label_acc']:>9.3f}{r['summary_label_acc']:>11.3f}"
              f"{r['episodes_scored']:>7.0f}{r['episode_labels_exact']:>11.4f}"
              f"{r['episode_all_exact']:>11.4f}{r['surfacing_share']:>11.3f}"
              f"{r['surfacing_acc']:>10.3f}{r['episode_surfacing_exact']:>12.4f}")
    print("`lbl exact` is a LOWER bound on rung 4's exact_match and `surf exact` "
          "an upper estimate;\nthe published `exact_match <= graph exactness` had "
          "the inequality the wrong way round.")
    if last is not None:
        print("\nshare of scored fills whose symbol is a word of the prompt, "
              f"by node type ({last['run']})")
        for name, cell in sorted(last["surfacing_by_type"].items(),
                                 key=lambda kv: -kv[1][1]):
            if cell[1] < 30:
                continue
            print(f"  {name:<10}{cell[1]:>8}{cell[0] / cell[1]:>9.3f}")
        print("  types with fewer than 30 scored fills are omitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
