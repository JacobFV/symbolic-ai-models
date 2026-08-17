"""Before tuning a guarded-rule model, ask whether its guards can name the thing.

    uv run python scripts/guard_ceiling.py runs/derive179-wordnet

A guarded rule is scored on **every fill its guard admits**, so a rule that is
perfect on a rare sub-population cannot survive verification unless some guard
in the language *isolates* that sub-population. If the best available guard is
half something else, the rule is capped near one half however right it is on the
part that matters — and it loses to a resolver that is mediocre everywhere.

This reports that ceiling. It enumerates the whole guard lattice, and for every
guard covering at least ``--min-recall`` of the target sub-population it prints
the purity: what share of the fills the guard admits are actually in it.

**Read it before tuning anything.** A ceiling near 0.5 means no threshold, no
search budget and no extra round will help, and the answer is a new guard atom.
That was learned the expensive way — see
``notes/lessons/2026-08-17-a-rule-is-verified-on-the-population-its-guard-admits.md``.
`frontier-001` answers 55% of the derived bucket while its own rule answers 100%
with the guard removed, and two plausible causes were built, run and refuted
(the proposal gate: 8,786 guards proposed instead of 5,316, bucket identical to
six decimals; the rank ordering: 0.0000 of the misses were blocked by it) before
this measurement was made and settled it in one command. The ceiling is **0.531**
at recall 0.799, on ``[phead='obj', slot=1]``.

The sub-population here is "the fill was **derived** rather than drawn", located
by object id through ``derived_split._positions`` — the same locator the
published rungs use, so this is the same population they are scored on. The
guard language is ``frontier``'s :data:`GUARD_KEYS`, read through its own
:func:`_guard_atoms`, so the ceiling is that model's ceiling and not an
idealisation of it.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import itertools
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "derived_split", Path(__file__).resolve().parent / "derived_split.py")
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)

from symbolic_ai_core.data.batch import IGNORE                     # noqa: E402
from symbolic_ai_models.models.frontier_001.model import (          # noqa: E402
    GUARD_KEYS, _guard_atoms)
from symbolic_ai_models.tasks import make_task                      # noqa: E402
from symbolic_ai_models.train import load_run                       # noqa: E402


def collect(arm_dir: Path, model: str, draws: int, n_train: int):
    """``(atoms of derived fills, atoms of every other fill)`` in the same lessons.

    Training seeds, not evaluation ones: this is a question about what the
    search could ever have found, which is settled on the episodes it was fitted
    on. Restricted to the lessons that carry a derived slot at all, because
    including the other 168 would inflate every purity by adding fills no guard
    needs to exclude.
    """
    model_obj, tok, cfg = load_run(str(arm_dir / model), device="cpu")
    model_obj.eval()
    lessons = ds.carrying_lessons(ds.ARMS, max_nodes=cfg.max_nodes)
    pairs = ds.matched_episodes(cfg.curriculum, ds.ARMS, lessons, n=n_train,
                                seed0=0, max_nodes=cfg.max_nodes)
    task = make_task("node", mask_rate=cfg.mask_rate, max_nodes=cfg.max_nodes,
                     seed=cfg.seed)
    inside: list[tuple] = []
    outside: list[tuple] = []
    for d in range(draws):
        task.rng = np.random.default_rng(999 + d)
        for idx, batch in ds._batched(pairs, task, tok, cfg.batch_size):
            for b, i in enumerate(idx):
                view = model_obj._view(batch, b)
                targets = {vi for vi, _ki in pairs[i][1]}
                for vi in view.hidden:
                    if int(batch.target_tokens[b, vi]) == IGNORE:
                        continue
                    (inside if vi in targets else outside).append(
                        _guard_atoms(view, vi))
    return inside, outside, tok, cfg


def ceiling(inside, outside, min_recall: float, top: int):
    """Best purity at ``>= min_recall``, over the whole subset lattice."""
    rows = []
    for size in range(1, len(GUARD_KEYS) + 1):
        for keys in itertools.combinations(range(len(GUARD_KEYS)), size):
            ci = collections.Counter(tuple(a[k] for k in keys) for a in inside)
            co = collections.Counter(tuple(a[k] for k in keys) for a in outside)
            for val, n_in in ci.items():
                recall = n_in / max(len(inside), 1)
                if recall < min_recall:
                    continue
                n_out = co.get(val, 0)
                rows.append({
                    "guard": [[GUARD_KEYS[k], v] for k, v in zip(keys, val)],
                    "purity": n_in / (n_in + n_out),
                    "recall": recall, "in": n_in, "out": n_out})
    rows.sort(key=lambda r: (-r["purity"], -r["recall"]))
    return rows[:top]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("arm", help="a run directory, e.g. runs/derive179-wordnet")
    ap.add_argument("--model", default="frontier-001",
                    help="which run under `arm` to borrow the config from")
    ap.add_argument("--min-recall", type=float, default=0.5)
    ap.add_argument("--draws", type=int, default=3)
    ap.add_argument("--n-train", type=int, default=20)
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args(argv)

    arm = Path(args.arm)
    inside, outside, tok, cfg = collect(arm, args.model, args.draws, args.n_train)
    print(f"{cfg.curriculum}: {len(inside)} derived fills, {len(outside)} other "
          f"fills, in the carrying lessons only")
    rows = ceiling(inside, outside, args.min_recall, args.top)
    if not rows:
        print(f"no guard reaches recall {args.min_recall}")
        return 1
    print(f"\nbest guards at recall >= {args.min_recall}:")
    for r in rows:
        pretty = ", ".join(
            f"{k}={tok.itos[v]!r}" if k == "phead" and isinstance(v, int)
            else f"{k}={v!r}" for k, v in r["guard"])
        print(f"  purity {r['purity']:.4f}  recall {r['recall']:.4f}  "
              f"in {r['in']:>4}  out {r['out']:>4}   [{pretty}]")
    best = rows[0]["purity"]
    print(f"\nCEILING {best:.4f}. ", end="")
    if best < 0.75:
        print("No guard in this language names the sub-population. A rule that\n"
              "is perfect on it is verified on a population that is largely\n"
              "something else, so it cannot survive at any threshold. Tuning\n"
              "support, precision, rounds or rule count will not move this —\n"
              "the answer is a new guard atom.")
    else:
        print("A guard can isolate the sub-population, so a rule that is right\n"
              "on it can survive verification. If it is not surviving, the\n"
              "cause is somewhere else — proposal, ranking or the resolver.")
    (arm / "guard_ceiling.json").write_text(json.dumps(
        {"curriculum": cfg.curriculum, "n_inside": len(inside),
         "n_outside": len(outside), "min_recall": args.min_recall,
         "rows": rows}, indent=1))
    print(f"\nwritten to {arm / 'guard_ceiling.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
