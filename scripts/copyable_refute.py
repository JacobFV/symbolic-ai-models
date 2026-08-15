"""The independent attack on the copyable/non-copyable split.

`scripts/copyable_split.py` reports the split. This reports the four things a
refuter needs and it does not:

* **coverage per bucket** — whether the non-copyable fills are simply the ones
  the vocabulary cannot name, which would make the split a fact about the
  tokenizer. They are not: coverage is *higher* there.
* **every floor the split could have been read against** — the pooled lookup,
  the same lookup fitted per bucket (a ceiling, not a floor: copyability is a
  function of the hidden label), and the **renaming-invariant** one, a
  structure-only pointer. The last is the comparison that decides the reading,
  because it scores exactly 0 on the non-copyable bucket and so does the oracle.
* **the split under renaming** — measured rather than reasoned about. The same
  permutation the repo already applies leaves the partition and the scored set
  bit-identical, so the two runs are paired fill by fill.
* **a lesson-cluster bootstrap** of the ranking inversion, plus the within-lesson
  and within-depth splits, which are confounds the finding did not test.

    uv run python scripts/copyable_refute.py runs/refute-node-r015/*

See `notes/findings/2026-08-15-the-copy-split-survives-and-its-floor-does-not.md`.
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

from symbolic_ai_core.data.batch import IGNORE
from symbolic_ai_core.invariance import build_renaming, rename_episodes
from symbolic_ai_core.shortcuts import node_text_leak
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run


def _batches(episodes, task, tok, batch_size, bucket=8):
    """`sampler.batches` with ``shuffle=False`` — the order `evaluate_model` uses.

    Reimplemented here only to keep the episode indices, which the sampler does
    not yield and the lesson-cluster bootstrap needs.
    """
    order = list(range(len(episodes)))
    window = batch_size * max(bucket, 1)
    for start in range(0, len(order), window):
        chunk = order[start:start + window]
        chunk.sort(key=lambda i: len(episodes[i].graph))
        for b in range(0, len(chunk), batch_size):
            idx = chunk[b:b + batch_size]
            if idx:
                yield idx, task.collate([episodes[i] for i in idx], tok)


def records(path: str, episodes, tok, cfg) -> dict[str, np.ndarray]:
    """One row per label-bearing masked node, on the draw the run itself scored.

    Censored fills are kept — they are the whole of the coverage question — and
    carry ``scored=False``. `main` asserts that the accuracy over the scored ones
    is the row's published `label_acc`, which is what makes this a decomposition
    of the published number and not a second measurement of it.
    """
    model, _tok, _cfg = load_run(path, device="cpu")
    task = make_task("node", mask_rate=cfg.mask_rate, max_nodes=cfg.max_nodes,
                     seed=cfg.seed)
    task.rng = np.random.default_rng(12345)
    model.eval()
    cols: dict[str, list] = {k: [] for k in
                             ("lesson", "copyable", "scored", "correct", "depth")}
    lesson_id: dict[str, int] = {}
    for idx, batch in _batches(episodes, task, tok, cfg.batch_size):
        with torch.no_grad():
            pred = model(batch).symbol_logits.argmax(-1)
        masked = batch.target_types != IGNORE
        labelled = (masked & (batch.label_group != IGNORE)).numpy()
        scored = (batch.target_tokens != IGNORE).numpy()
        correct = ((pred == batch.target_tokens).numpy() & scored)
        copyable = (batch.target_source != IGNORE).numpy()
        bs, ls = np.nonzero(labelled)
        for b, l in zip(bs.tolist(), ls.tolist()):
            name = batch.meta["lesson_ids"][b]
            cols["lesson"].append(lesson_id.setdefault(name, len(lesson_id)))
            cols["copyable"].append(bool(copyable[b, l]))
            cols["scored"].append(bool(scored[b, l]))
            cols["correct"].append(bool(correct[b, l]))
            cols["depth"].append(int(batch.depth[b, l]))
    return {k: np.asarray(v) for k, v in cols.items()}


def buckets(r) -> tuple[float, float, float]:
    cp, sc, ok = r["copyable"], r["scored"], r["correct"]
    return ok[cp & sc].mean(), ok[~cp & sc].mean(), ok[sc].mean()


def bootstrap(recs: dict[str, dict], a: str, b: str, n_boot: int = 2000,
              seed: int = 0) -> None:
    """Resample **lessons**, not fills: fills within a lesson are not independent."""
    ref = recs[a]
    sel = (~ref["copyable"]) & ref["scored"]
    lessons = ref["lesson"]
    by_lesson = [np.flatnonzero(sel & (lessons == L))
                 for L in range(int(lessons.max()) + 1)]
    rng = np.random.default_rng(seed)
    draws = {m: [] for m in (a, b)}
    wins = 0
    for _ in range(n_boot):
        pick = rng.integers(0, len(by_lesson), len(by_lesson))
        idx = np.concatenate([by_lesson[p] for p in pick if len(by_lesson[p])])
        vals = {m: recs[m]["correct"][idx].mean() for m in (a, b)}
        for m in (a, b):
            draws[m].append(vals[m])
        wins += vals[b] > vals[a]
    print(f"\nlesson-cluster bootstrap, {n_boot} draws over {len(by_lesson)} "
          f"lessons, non-copyable bucket")
    for m in (a, b):
        v = np.array(draws[m])
        print(f"  {m:<22}{v.mean():>8.4f}  95% CI "
              f"[{np.percentile(v, 2.5):.4f}, {np.percentile(v, 97.5):.4f}]")
    print(f"  {b} > {a} in {wins}/{n_boot} draws")
    ca, cb = recs[a]["correct"][sel], recs[b]["correct"][sel]
    print(f"  paired discordance on the same {int(sel.sum())} fills: "
          f"{b} right/{a} wrong {int((~ca & cb).sum())}, "
          f"{a} right/{b} wrong {int((ca & ~cb).sum())}")


def main(paths: list[str]) -> int:
    paths = [p for p in paths if (Path(p) / "summary.json").exists()]
    if not paths:
        return 2
    _m, tok, cfg = load_run(paths[0], device="cpu")
    train, ev = load_data(cfg)
    task = make_task("node", mask_rate=cfg.mask_rate, max_nodes=cfg.max_nodes)

    lookup = task.split_floor(ev, tok, train)
    per_bucket = task.split_floor(ev, tok, train, fit_per_bucket=True)
    pointer = task.split_copy_floor(ev, tok, train)
    published = json.loads((Path(paths[0]) / "summary.json").read_text())
    floor = published["final"]["node"]["label_floor"]
    assert abs(lookup["floor_pooled"] - floor) < 1e-12, "not the published floor"

    recs = {}
    head = (f"{'model':<22}{'acc | c':>9}{'acc | n':>9}{'all':>9}"
            f"{'c-lookup':>10}{'c-pointer':>11}{'n-lookup':>10}")
    print(head)
    print("-" * len(head))
    for p in paths:
        summary = json.loads((Path(p) / "summary.json").read_text())
        name = summary.get("model", Path(p).name)
        r = recs[name] = records(p, ev, tok, cfg)
        c, n, a = buckets(r)
        assert abs(a - summary["final"]["node"]["label_acc"]) < 1e-9, (
            f"{name}: pooled {a} is not the published label_acc")
        print(f"{name:<22}{c:>9.4f}{n:>9.4f}{a:>9.4f}"
              f"{c - lookup['floor_copyable']:>+10.4f}"
              f"{c - pointer['copyfloor_copyable']:>+11.4f}"
              f"{n - lookup['floor_not_copyable']:>+10.4f}")
    print("-" * len(head))
    print(f"{'lookup floor':<22}{lookup['floor_copyable']:>9.4f}"
          f"{lookup['floor_not_copyable']:>9.4f}{lookup['floor_pooled']:>9.4f}")
    print(f"{'  same, fitted per bucket':<22}{per_bucket['floor_copyable']:>9.4f}"
          f"{per_bucket['floor_not_copyable']:>9.4f}"
          f"{per_bucket['floor_pooled']:>9.4f}   (a ceiling, not a floor)")
    print(f"{'pointer floor (equiv.)':<22}{pointer['copyfloor_copyable']:>9.4f}"
          f"{pointer['copyfloor_not_copyable']:>9.4f}"
          f"{pointer['copyfloor_pooled']:>9.4f}")
    print(f"{'oracle pointer':<22}{pointer['ceiling_copyable']:>9.4f}"
          f"{pointer['ceiling_not_copyable']:>9.4f}")
    print(f"the published label_floor is {floor:.4f}: a structure-only *pointer* "
          f"beats it by {pointer['copyfloor_pooled'] - floor:+.4f}, so every "
          f"label lift in this arm is overstated by at least that much")

    r = recs[json.loads((Path(paths[0]) / "summary.json").read_text())["model"]]
    cp, sc = r["copyable"], r["scored"]
    print(f"\n{'bucket':<16}{'labelled':>10}{'scored':>9}{'censored':>10}"
          f"{'coverage':>10}")
    for label, s in (("copyable", cp), ("not copyable", ~cp)):
        print(f"{label:<16}{int(s.sum()):>10}{int((s & sc).sum()):>9}"
              f"{int((s & ~sc).sum()):>10}{(s & sc).sum() / s.sum():>10.4f}")

    print("\nthe split under renaming — the partition and the scored set are "
          "asserted unchanged, so the rows are paired fill by fill")
    renamed = rename_episodes(ev, build_renaming(ev, tok))
    print(f"{'model':<22}{'c plain':>9}{'n plain':>9}{'c renamed':>11}"
          f"{'n renamed':>11}")
    for p in paths:
        name = json.loads((Path(p) / "summary.json").read_text())["model"]
        q = records(p, renamed, tok, cfg)
        assert np.array_equal(q["copyable"], recs[name]["copyable"])
        assert np.array_equal(q["scored"], recs[name]["scored"])
        c, n, _ = buckets(recs[name])
        rc, rn, _ = buckets(q)
        print(f"{name:<22}{c:>9.4f}{n:>9.4f}{rc:>11.4f}{rn:>11.4f}")

    names = list(recs)
    if len(names) >= 2:
        bootstrap(recs, names[0], names[-1])

    leak = node_text_leak(ev, mask_rate=cfg.mask_rate, max_nodes=cfg.max_nodes)
    print(f"\nand the prose does not rescue the bucket: when the answer is absent "
          f"from the visible graph the prompt names it "
          f"{leak['recall_when_absent']:.3f} of the time, pins it down "
          f"{leak['uniquely_determined']:.3f}, and uniform guessing among the "
          f"candidates gives {leak['expected_acc_when_absent']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
