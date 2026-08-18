"""Why `acc | copyable` is not the same question at 0.15 and at 0.90.

`scripts/copyable_split.py` reports the two conditional accuracies.
`notes/questions/2026-08-15-the-supply-model-breaks-at-ninety-percent-masking.md`
asks why carrying them forward from `mask_rate=0.15` predicts the pooled score to
0.005 at 0.35 and 0.60 and then misses by 0.030 at 0.90, and names *survivorship*
as one of three candidate stories: at 10% visibility the fills that are still
copyable are the ones whose label is repeated often enough to have left a visible
copy, and a repeated label is easier to point at.

That story is testable without a new run, because everything it needs is already
in the batch. ``label_group`` groups every labelled non-structural node of an
episode by its label string, so for each scored fill this reports

* **m**, how many nodes of the graph carry that label at all, and
* **v**, how many of those are *visible* — which is exactly the quantity
  ``target_source`` thresholds at one to define the copyable bucket.

Stratified by either, a rise in `acc | copyable` that is entirely a shift in the
**mix** across strata is survivorship; a rise *within* strata is not, and would
be the model doing better at a fixed question.

    uv run python scripts/copyable_survivorship.py \
        runs/refit-node-r015/corefer-001 runs/refute-node-r090/corefer-001

Needs the weights, so it runs on a re-fit rather than on the published run
directories -- see the note, and `runs/refute-node-r015`, where a re-fit came
back bit-identical to the published arm.
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
from symbolic_ai_core.data.term_graph import NODE_TYPES, TYPE_TO_ID
from symbolic_ai_core.data.sampler import batches
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run

TASK_OF = {"scatter": "node", "subtree": "nodesub",
           "answer": "nodeans", "answer_one": "nodeans1"}

#: Multiplicity strata. Open-ended at the top because a label occurring twenty
#: times is a different object from one occurring twice and the curriculum has
#: both. `record_the_curve_not_the_argmax`: the strata are reported in full
#: rather than collapsed to whichever boundary separates the arms.
BANDS = [(1, 1), (2, 2), (3, 4), (5, 9), (10, 10 ** 9)]

#: Bands of ``v / V`` -- visible nodes carrying the answer's label over visible
#: labelled nodes in the episode. This is the *concentration* of the evidence,
#: and it is the quantity a pointer's job actually depends on: ``v`` alone says
#: how many right answers are on screen, ``V`` says how many wrong ones are, and
#: raising the mask rate moves both. Chosen before the numbers were read, wide
#: enough that the two rates can overlap at all -- at 0.15 a typical episode
#: leaves ~50 labelled nodes visible and at 0.90 it leaves ~6, so the same ``v``
#: is a different question at the two ends and unbanded ``v`` cannot say so.
CONC = [0.0, 0.02, 0.05, 0.10, 0.20, 0.40, 1.01]


def _band(k: int) -> str:
    for lo, hi in BANDS:
        if lo <= k <= hi:
            return f"{lo}" if lo == hi else (f"{lo}+" if hi > 10 ** 8 else f"{lo}-{hi}")
    return "0"


def _conc_band(x: float) -> str:
    for lo, hi in zip(CONC, CONC[1:]):
        if lo < x <= hi:
            return f"{lo:g}-{min(hi, 1.0):g}"
    return "0"


CONC_ORDER = [f"{lo:g}-{min(hi, 1.0):g}" for lo, hi in zip(CONC, CONC[1:])]


def measure(path: str) -> dict:
    model, tok, cfg = load_run(path, device="cpu")
    summary = json.loads((Path(path) / "summary.json").read_text())
    mode = (summary.get("masking") or {}).get("mask_mode", "scatter")
    _, ev = load_data(cfg)

    # `evaluate_model`'s own draw: rng reset to 12345, episodes unshuffled under
    # `random.Random(0)`. This is what makes `acc_all` below bit-identical to the
    # run's published `label_acc`, which `main` asserts.
    task = make_task(TASK_OF[mode], mask_rate=cfg.mask_rate,
                     max_nodes=cfg.max_nodes, seed=cfg.seed)
    task.rng = np.random.default_rng(12345)
    model.eval()
    mask_type = TYPE_TO_ID["mask"]

    hit = {True: 0, False: 0}
    n = {True: 0, False: 0}
    #: (bucket, band) -> [hits, n], for the two bands.
    by_v: dict[tuple[bool, str], list[int]] = {}
    by_m: dict[tuple[bool, str], list[int]] = {}
    by_type: dict[tuple[bool, str], list[int]] = {}
    by_conc: dict[str, list[int]] = {}
    visible_labelled = [0, 0]                       # running mean of V
    #: The mix itself, independent of any accuracy: how many *labelled* nodes of
    #: each total-multiplicity band exist, and how many of them are copyable.
    exposure: dict[str, list[int]] = {}

    for batch in batches(ev, task, tok, batch_size=cfg.batch_size,
                         rng=random.Random(0), shuffle=False):
        with torch.no_grad():
            pred = model(batch).symbol_logits.argmax(-1)
        scored = batch.target_tokens != IGNORE
        correct = (pred == batch.target_tokens) & scored
        copyable = batch.target_source != IGNORE
        grp = batch.label_group
        vis = batch.types != mask_type
        B, L = grp.shape
        for b in range(B):
            row = grp[b]
            ok = row != IGNORE
            if not bool(ok.any()):
                continue
            g = row[ok].numpy()
            size = int(g.max()) + 1
            m_all = np.bincount(g, minlength=size)                 # in the graph
            v_ok = ok & vis[b]
            m_vis = np.bincount(row[v_ok].numpy(), minlength=size) if bool(v_ok.any()) \
                else np.zeros(size, dtype=np.int64)
            V = int(v_ok.sum())
            idx = torch.nonzero(scored[b] & ok, as_tuple=False).flatten().tolist()
            if idx:
                visible_labelled[0] += V * len(idx)
                visible_labelled[1] += len(idx)
            for i in idx:
                gid = int(row[i])
                flag = bool(copyable[b, i])
                good = int(bool(correct[b, i]))
                n[flag] += 1
                hit[flag] += good
                for table, k in ((by_v, int(m_vis[gid])), (by_m, int(m_all[gid]))):
                    cell = table.setdefault((flag, _band(k)), [0, 0])
                    cell[0] += good
                    cell[1] += 1
                tname = NODE_TYPES[int(batch.target_types[b, i])]
                cell = by_type.setdefault((flag, tname), [0, 0])
                cell[0] += good
                cell[1] += 1
                cell = exposure.setdefault(_band(int(m_all[gid])), [0, 0])
                cell[0] += int(flag)
                cell[1] += 1
                if flag and V:
                    cell = by_conc.setdefault(_conc_band(int(m_vis[gid]) / V), [0, 0])
                    cell[0] += good
                    cell[1] += 1

    total = n[True] + n[False]
    return {
        "path": path, "mask_rate": cfg.mask_rate, "mode": mode,
        "model": summary.get("model", Path(path).name),
        "n": total, "copyable_share": n[True] / total,
        "acc_copyable": hit[True] / n[True] if n[True] else float("nan"),
        "acc_not": hit[False] / n[False] if n[False] else float("nan"),
        "acc_all": (hit[True] + hit[False]) / total,
        "published": next(
            (v.get("label_acc") for v in (summary.get("final") or {}).values()
             if isinstance(v, dict) and "label_acc" in v), float("nan")),
        "by_v": by_v, "by_m": by_m, "by_type": by_type, "exposure": exposure,
        "by_conc": by_conc,
        "mean_visible_labelled": visible_labelled[0] / max(visible_labelled[1], 1),
    }


def _bands_present(tables: list[dict], flag: bool) -> list[str]:
    seen = {k[1] for t in tables for k in t if k[0] is flag}
    order = [f"{lo}" if lo == hi else (f"{lo}+" if hi > 10 ** 8 else f"{lo}-{hi}")
             for lo, hi in BANDS]
    return [b for b in order if b in seen]


def _stratum_table(rows: list[dict], key: str, flag: bool, what: str) -> None:
    bands = _bands_present([r[key] for r in rows], flag)
    print(f"\n{what}")
    head = f"{'rate':>6}" + "".join(f"{b:>18}" for b in bands)
    print(head)
    print("-" * len(head))
    for r in rows:
        cells = []
        tot = sum(v[1] for k, v in r[key].items() if k[0] is flag) or 1
        for b in bands:
            cell = r[key].get((flag, b))
            cells.append("           --     " if not cell or not cell[1]
                         else f"{cell[0] / cell[1]:>9.3f}{cell[1] / tot:>9.1%}")
        print(f"{r['mask_rate']:>6.2f}" + "".join(cells))
    print("  each cell is `accuracy` then `share of the bucket's fills`; "
          "a rise that lives only in the shares is a mix effect")


def main(paths: list[str]) -> int:
    rows = [measure(p) for p in paths]
    for r in rows:
        assert abs(r["acc_all"] - r["published"]) < 1e-9, (
            f"{r['model']}: pooled {r['acc_all']} != published {r['published']}")
    head = (f"{'model':<20}{'rate':>6}{'n':>8}{'copyable':>10}"
            f"{'acc | copyable':>16}{'acc | not':>11}{'acc all':>9}")
    print(head)
    print("-" * len(head))
    for r in rows:
        print(f"{r['model']:<20}{r['mask_rate']:>6.2f}{r['n']:>8}"
              f"{r['copyable_share']:>10.3f}{r['acc_copyable']:>16.4f}"
              f"{r['acc_not']:>11.4f}{r['acc_all']:>9.4f}")

    _stratum_table(rows, "by_v", True,
                   "acc | copyable, by v = visible nodes carrying the same label")
    _stratum_table(rows, "by_m", True,
                   "acc | copyable, by m = nodes carrying the same label at all")
    _stratum_table(rows, "by_m", False,
                   "acc | NOT copyable, by m")

    print("\nacc | copyable, by v/V = visible same-label nodes / visible labelled nodes")
    bands = [b for b in CONC_ORDER if any(b in r["by_conc"] for r in rows)]
    head = f"{'rate':>6}{'mean V':>9}" + "".join(f"{b:>18}" for b in bands)
    print(head)
    print("-" * len(head))
    for r in rows:
        cells = []
        tot = sum(v[1] for v in r["by_conc"].values()) or 1
        for b in bands:
            cell = r["by_conc"].get(b)
            cells.append("           --     " if not cell or cell[1] < 30
                         else f"{cell[0] / cell[1]:>9.3f}{cell[1] / tot:>9.1%}")
        print(f"{r['mask_rate']:>6.2f}{r['mean_visible_labelled']:>9.1f}"
              + "".join(cells))
    print("  bands with fewer than 30 fills at a rate are left blank; this is the "
          "stratification the two rates can actually be compared inside")

    print("\nthe mix, with no accuracy in it: copyable share within each m band")
    bands = _bands_present([r["exposure"] for r in rows], True) or \
        [b for b in ("1", "2", "3-4", "5-9", "10+")
         if any(b in r["exposure"] for r in rows)]
    head = f"{'rate':>6}" + "".join(f"{b:>18}" for b in bands)
    print(head)
    print("-" * len(head))
    for r in rows:
        cells = []
        tot = sum(v[1] for v in r["exposure"].values()) or 1
        for b in bands:
            cell = r["exposure"].get(b)
            cells.append("           --     " if not cell or not cell[1]
                         else f"{cell[0] / cell[1]:>9.3f}{cell[1] / tot:>9.1%}")
        print(f"{r['mask_rate']:>6.2f}" + "".join(cells))
    print("  `copyable share within the band` then `the band's share of all fills`")

    print("\nacc | copyable, by node type")
    types = sorted({k[1] for r in rows for k in r["by_type"] if k[0] is True})
    head = f"{'rate':>6}" + "".join(f"{t:>18}" for t in types)
    print(head)
    print("-" * len(head))
    for r in rows:
        cells = []
        tot = sum(v[1] for k, v in r["by_type"].items() if k[0] is True) or 1
        for t in types:
            cell = r["by_type"].get((True, t))
            cells.append("           --     " if not cell or cell[1] < 30
                         else f"{cell[0] / cell[1]:>9.3f}{cell[1] / tot:>9.1%}")
        print(f"{r['mask_rate']:>6.2f}" + "".join(cells))
    print("  types with fewer than 30 copyable fills at a rate are left blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
