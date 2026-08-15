"""Audit the copy head per item, so a pointer lead can be tested rather than read.

The copy column is a pooled accuracy over ~5,785 questions and the top four
pointers in this repo are separated by 0.0125 of it, which is about one standard
error. A table of pooled means cannot tell a lead from a draw, and it cannot
tell "answered better" from "answered less often" either. This does both.

Reproduces ``evaluate_model``'s batching and masking exactly, then records, for
every scored item:

* whether the pointer was right -- ``picked`` is computed with the same three
  lines as :func:`~symbolic_ai_models.tasks.masked_node._pointer_counts` rather
  than reimplemented, because a second copy of a scoring rule drifts;
* whether the model cast a vote on that node at all (read off the harness
  output: an unvoted row is flat at 0.0 over the visible positions and every
  vote adds at least 1.0), so coverage can be reported beside accuracy per
  ``notes/questions/2026-08-13-coverage-versus-accuracy-in-an-agent-column.md``;
* what the *flat pointer back-off* would have picked there, which is the copy
  head's version of the check in
  ``notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md``.

From those it prints McNemar (exact paired) and a bootstrap resampled by
**lesson**, the conservative cluster, plus the renaming control and the
per-bucket breakdowns a mechanism claim needs.

    uv run python scripts/pointer_audit.py <run-root> <model,model,...> \\
        <mask-seed,...> <out.json> [eval-seed0]

``eval-seed0`` defaults to 1,000,000, the published evaluation draw. Any other
value >= 1,000,000 draws a fresh evaluation set from the same lessons, which is
the strongest replication available without refitting. The copy floor is
recomputed for whichever draw is in use rather than carried over.

Set ``SKIP_RENAME=1`` to drop the renaming control, which costs one extra pass
per model.
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MKL_NUM_THREADS", "4")

import json
import random
import sys
from pathlib import Path

import numpy as np
import torch

torch.set_num_threads(4)

from symbolic_ai_core.data.batch import IGNORE
from symbolic_ai_core.data.sampler import batches
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run, _task_kwargs


def per_item(model, cfg, tok, eval_eps, mask_seed: int):
    """One row per scored pointer question, in a deterministic order."""
    task = make_task("node", **_task_kwargs(cfg, "node"))
    task.rng = np.random.default_rng(mask_seed)
    rows = []
    with torch.no_grad():
        for bi, batch in enumerate(batches(eval_eps, task, tok,
                                           batch_size=cfg.batch_size,
                                           rng=random.Random(0), shuffle=False)):
            out = model(batch)
            logits = out.source_logits
            assert logits is not None, "model emits no pointer on this batch"
            asked = batch.label_group != IGNORE
            masked = batch.target_types != IGNORE
            scored = asked & masked
            valid = batch.pad_mask.clone()
            eye = torch.eye(valid.shape[1], dtype=torch.bool)
            allowed = valid[:, None, :] & ~eye[None]
            picked = logits.masked_fill(~allowed, float("-inf")).argmax(-1)
            picked_group = torch.gather(batch.label_group, 1, picked)
            correct = (picked_group == batch.label_group) & scored
            # A row the model never voted on is flat at 0.0 over the visible
            # positions; every vote adds at least 1.0.  So this is "did the
            # model speak here", read off the harness output rather than off
            # any model's internals.
            voted = logits.masked_fill(~allowed, float("-inf")).max(-1).values > 0.5
            # The tie-break the flat back-off produces: lowest visible j != i.
            backoff = torch.zeros_like(logits).masked_fill(
                ~allowed, float("-inf")).argmax(-1)
            back_group = torch.gather(batch.label_group, 1, backoff)
            back_ok = (back_group == batch.label_group) & scored
            # label head, for the crosstalk mechanism test
            lab_pred = out.symbol_logits.argmax(-1)
            lab_scored = batch.target_tokens != IGNORE
            lab_ok = (lab_pred == batch.target_tokens) & lab_scored
            n_nodes = batch.pad_mask.sum(1)
            arity: dict[tuple, int] = {}
            sigs: dict[tuple, int] = {}
            for b in range(batch.pad_mask.shape[0]):
                view = model._view(batch, b)
                for i in range(len(view)):
                    arity[(b, i)] = len(view.children(i))
                if hasattr(model, "_signatures_for"):
                    for i, ss in enumerate(model._signatures_for(view)):
                        sigs[(b, i)] = len(ss)
            for b, i in zip(*torch.nonzero(scored, as_tuple=True)):
                b, i = int(b), int(i)
                grp = int(batch.label_group[b, i])
                same = int(((batch.label_group[b] == grp) & valid[b]).sum()) - 1
                lessons = (batch.meta or {}).get("lesson_ids") or []
                rows.append({
                    "key": (bi, b, i),
                    "lesson": lessons[b] if b < len(lessons) else "?",
                    "ok": bool(correct[b, i]),
                    "voted": bool(voted[b, i]),
                    "back_ok": bool(back_ok[b, i]),
                    "n_nodes": int(n_nodes[b]),
                    "same_label": same,
                    "arity": arity.get((b, i), 0),
                    "sigs": sigs.get((b, i), -1),
                    "lab_scored": bool(lab_scored[b, i]),
                    "lab_ok": bool(lab_ok[b, i]),
                })
    return rows


def mcnemar(a, b):
    n01 = sum(1 for x, y in zip(a, b) if (not x["ok"]) and y["ok"])
    n10 = sum(1 for x, y in zip(a, b) if x["ok"] and (not y["ok"]))
    n = n01 + n10
    chi = ((abs(n10 - n01) - 1) ** 2 / n) if n else 0.0
    # two-sided p from chi2_1 without scipy
    from math import erfc, sqrt
    p = erfc(sqrt(chi / 2.0)) if chi > 0 else 1.0
    return n10, n01, chi, p


def cluster_bootstrap(a, b, iters=2000, seed=7, unit="episode"):
    """Paired difference in accuracy, resampled by cluster.

    Items inside one episode are not independent -- they share a graph -- and
    episodes inside one lesson share a generator, so an item-level interval is
    the optimistic one. Both units are reported.
    """
    rng = np.random.default_rng(seed)
    by_ep: dict = {}
    for k, row in enumerate(a):
        key = row["key"][:2] if unit == "episode" else row["lesson"]
        by_ep.setdefault(key, []).append(k)
    eps = list(by_ep.values())
    diffs = []
    for _ in range(iters):
        pick = rng.integers(0, len(eps), len(eps))
        idx = [k for p in pick for k in eps[p]]
        da = sum(a[k]["ok"] for k in idx) / len(idx)
        db = sum(b[k]["ok"] for k in idx) / len(idx)
        diffs.append(da - db)
    d = np.array(diffs)
    return float(d.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main(argv):
    root = Path(argv[0])
    names = argv[1].split(",")
    seeds = [int(s) for s in argv[2].split(",")]
    loaded = {n: load_run(root / n) for n in names}
    cfg = next(iter(loaded.values()))[2]
    seed0 = int(argv[4]) if len(argv) > 4 else 1_000_000
    train_eps, eval_eps = load_data(cfg)
    if seed0 != 1_000_000:
        from symbolic_ai_core.data.curriculum import generate, resolve_lessons
        eval_eps = list(generate(resolve_lessons(cfg.lessons), n=cfg.n_eval,
                                 seed0=seed0, language=cfg.language,
                                 max_nodes=cfg.max_nodes))
    print(f"{len(eval_eps)} eval episodes (seed0 {seed0}), "
          f"batch {cfg.batch_size}", flush=True)
    # A number without its floor is not a result, so the floor is recomputed
    # for whichever evaluation draw is in use rather than carried over.
    tok0 = next(iter(loaded.values()))[1]
    floor_task = make_task("node", **_task_kwargs(cfg, "node"))
    copy_floor = floor_task._copy_floor(eval_eps, train_eps, tok0)
    from symbolic_ai_core.floors import lift as _lift
    print(f"copy floor on this draw: {copy_floor:.4f}", flush=True)
    result = {}
    for seed in seeds:
        rows = {}
        for n in names:
            model, tok, c = loaded[n]
            rows[n] = per_item(model, c, tok, eval_eps, seed)
        keys = {n: [r["key"] for r in rows[n]] for n in names}
        base = keys[names[0]]
        for n in names:
            assert keys[n] == base, f"{n} scores a different set of items"
        print(f"\n=== mask seed {seed}: n = {len(base)} identical items", flush=True)
        print(f"{'model':<24}{'copy acc':>10}{'copy lift':>11}{'cover':>8}"
              f"{'acc|vote':>10}{'acc|silent':>12}{'lab acc':>9}")
        for n in names:
            r = rows[n]
            acc = sum(x["ok"] for x in r) / len(r)
            cov = sum(x["voted"] for x in r) / len(r)
            v = [x for x in r if x["voted"]]
            s = [x for x in r if not x["voted"]]
            av = sum(x["ok"] for x in v) / len(v) if v else float("nan")
            asl = sum(x["ok"] for x in s) / len(s) if s else float("nan")
            ls = [x for x in r if x["lab_scored"]]
            la = sum(x["lab_ok"] for x in ls) / len(ls) if ls else float("nan")
            print(f"{n:<24}{acc:>10.4f}{_lift(acc, copy_floor):>+11.4f}"
                  f"{cov:>8.3f}{av:>10.4f}{asl:>12.4f}{la:>9.4f}")
            result.setdefault(n, {})[seed] = {"acc": acc, "cover": cov,
                                              "acc_vote": av, "acc_silent": asl,
                                              "label_acc": la}
        back = sum(x["back_ok"] for x in rows[names[0]]) / len(base)
        print(f"{'(flat pointer back-off)':<24}{back:>10.4f}")
        result.setdefault("_backoff", {})[seed] = back
        for x, y in [(names[i], names[j]) for i in range(len(names))
                     for j in range(i + 1, len(names))][1:]:
            n10, n01, chi, p = mcnemar(rows[x], rows[y])
            m, lo, hi = cluster_bootstrap(rows[x], rows[y], unit="lesson")
            print(f"  {x} vs {y}: {m:+.4f} "
                  f"lesson CI [{lo:+.4f}, {hi:+.4f}] McNemar p {p:.4f}")
        if len(names) >= 2:
            a, b = rows[names[0]], rows[names[1]]
            n10, n01, chi, p = mcnemar(a, b)
            m, lo, hi = cluster_bootstrap(a, b, unit="episode")
            ml, lol, hil = cluster_bootstrap(a, b, unit="lesson")
            print(f"  {names[0]} vs {names[1]}: "
                  f"only-A-right {n10}, only-B-right {n01}, "
                  f"McNemar chi2 {chi:.2f}, p {p:.3f}")
            print(f"  paired diff {m:+.4f}, episode-cluster 95% CI "
                  f"[{lo:+.4f}, {hi:+.4f}]; lesson-cluster CI "
                  f"[{lol:+.4f}, {hil:+.4f}]")
            result.setdefault("_pair", {})[seed] = {
                "n10": n10, "n01": n01, "chi2": chi, "p": p,
                "diff": m, "lo": lo, "hi": hi, "lo_lesson": lol,
                "hi_lesson": hil}
        # H6: the pointer under a permutation of every symbol, no refitting.
        if seed == seeds[0] and not os.environ.get("SKIP_RENAME"):
            from symbolic_ai_core.invariance import (build_renaming,
                                                     rename_episodes)
            ren = build_renaming(eval_eps, next(iter(loaded.values()))[1])
            renamed = rename_episodes(eval_eps, ren)
            print(f"\n  renaming control ({len(ren)} symbols permuted, "
                  f"no refitting):")
            for n in names:
                model, tok, c = loaded[n]
                rr = per_item(model, c, tok, renamed, seed)
                acc = sum(x["ok"] for x in rr) / len(rr)
                plain = result[n][seed]["acc"]
                print(f"    {n:<24}{plain:>10.4f} -> {acc:>8.4f}  "
                      f"drop {plain - acc:+.4f}   (n {len(rr)})")
                result[n][seed]["rename_copy"] = acc
        # mechanism test: label accuracy by node arity bucket
        if len(names) >= 3:
            # H7. The crosstalk story predicts the metta-minus-vsa label gap
            # grows with graph width, with node arity, and with the number of
            # atomspace signatures the node carries.
            sig_of = {r["key"]: r["sigs"] for n in names for r in rows[n]
                      if r["sigs"] >= 0}
            for what, edges, get in (
                    ("graph size", [(0, 15), (15, 25), (25, 40), (40, 300)],
                     lambda x: x["n_nodes"]),
                    ("node arity", [(0, 1), (1, 2), (2, 3), (3, 99)],
                     lambda x: x["arity"]),
                    ("signatures/node", [(7, 10), (10, 13), (13, 18),
                                         (18, 9999)],
                     lambda x: sig_of.get(x["key"], -1))):
                print(f"\n  label acc by {what} (crosstalk test):")
                print(f"    {'bucket':>12}{'n':>7}" +
                      "".join(f"{n[:14]:>16}" for n in names) + f"{'gap':>10}")
                for lo_, hi_ in edges:
                    cells, cnt = [], 0
                    for n in names:
                        sel = [x for x in rows[n] if x["lab_scored"]
                               and lo_ <= get(x) < hi_]
                        cnt = len(sel)
                        cells.append(sum(x["lab_ok"] for x in sel) / len(sel)
                                     if sel else float("nan"))
                    gap = cells[0] - cells[2] if len(cells) > 2 else float("nan")
                    print(f"    {f'{lo_}-{hi_}':>12}{cnt:>7}" +
                          "".join(f"{c:>16.4f}" for c in cells) +
                          f"{gap:>+10.4f}")
            print("\n  copy acc by number of same-label candidates:")
            for lo_, hi_ in [(1, 2), (2, 3), (3, 5), (5, 100)]:
                cells, cnt = [], 0
                for n in names:
                    sel = [x for x in rows[n] if lo_ <= x["same_label"] < hi_]
                    cnt = len(sel)
                    cells.append(sum(x["ok"] for x in sel) / len(sel)
                                 if sel else float("nan"))
                back_sel = [x for x in rows[names[0]]
                            if lo_ <= x["same_label"] < hi_]
                bk = (sum(x["back_ok"] for x in back_sel) / len(back_sel)
                      if back_sel else float("nan"))
                print(f"    {f'{lo_}-{hi_}':>12}{cnt:>7}" +
                      "".join(f"{c:>16.4f}" for c in cells) +
                      f"   backoff {bk:.4f}")
    Path(argv[3]).write_text(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
