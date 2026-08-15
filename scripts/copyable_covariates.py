"""Does the 0.90 arm really lose at matched evidence supply, with no bands?

An independent attack on
``notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md``.
That note stratifies ``acc | copyable`` by the evidence concentration
``v/V`` — visible nodes carrying the target's label, over visible labelled
nodes in the episode — using six author-chosen bands, and reports that the
0.90 arm sits at or below the 0.15 arm in every band with mass. Its own
stated weak point is the banding: the two arms' ``v/V`` distributions barely
overlap (``V`` is about 62 at 0.15 and about 7 at 0.90), so each band could
be hiding a composition shift running the same way everywhere.

This is a **separate implementation** — it does not import
``scripts/copyable_survivorship.py`` — that dumps one record per scored fill
and then asks the question five ways, three of which use no bands at all:

1. exact matching on the integer pair ``(v, V)``, which is as banding-free as
   a covariate adjustment gets, plus the size of the common support;
2. a logistic fit in ``log v`` and ``log V`` with the arm as an indicator;
3. the mean ``v/V`` *inside* each of the note's own bands, per arm, which is
   the composition the note could not rule out;
4. a **random-pointer control** whose expected accuracy is exactly ``v/V``,
   pushed through the identical standardisation. It has no ability at all, so
   whatever shortfall it shows is what the adjustment leaves on the table;
5. the same fill asked at both rates — the same episode, the same node index —
   which matches on identity rather than on any covariate;
6. joint cells of (node type, ``v/V``), because the copyable bucket's *type*
   mix moves too and concentration cannot see it;
7. ``--cross``: the 0.15-fitted weights scored on the 0.90 draw. The two arms
   are separately fitted models, which nothing in the record says out loud, and
   a model whose ability is frozen at 0.15 is the survivorship claim's ideal
   control.

Every replay reproduces ``evaluate_model``'s draw exactly (``task.rng =
np.random.default_rng(12345)``, unshuffled ``random.Random(0)`` order) and
asserts its pooled accuracy against the run's published ``final.node.label_acc``,
so these are decompositions of the published numbers and not a second
measurement of them.

    uv run python scripts/copyable_covariates.py \
        --r015 <dir>/runs/refit-node-r015 --r090 <dir>/runs/refute-node-r090
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")

import numpy as np
import torch

torch.set_num_threads(4)

from symbolic_ai_core.data.batch import IGNORE
from symbolic_ai_core.data.graph import TYPE_TO_ID
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run

MASK = TYPE_TO_ID["mask"]

#: The note's bands, reproduced exactly so the two analyses can be compared.
BANDS = (0.0, 0.02, 0.05, 0.10, 0.20, 0.40, 1.0001)
BAND_NAMES = ("0-0.02", "0.02-0.05", "0.05-0.1", "0.1-0.2", "0.2-0.4", "0.4-1")

_DATA: dict[tuple, tuple] = {}

#: Column order of the per-fill record table.
COLS = ("ep", "node", "correct", "copyable", "v", "V", "m", "D", "Vt", "type")


def _data(cfg):
    """``load_data`` once per distinct data config; it regenerates 3,580
    training episodes per call and twelve calls is eleven too many."""
    key = (cfg.data, cfg.lessons, cfg.n_train, cfg.n_eval, cfg.language,
           cfg.languages, cfg.max_nodes)
    if key not in _DATA:
        _DATA[key] = load_data(cfg)
    return _DATA[key]


def replay(path: str, draw_from: str | None = None
           ) -> tuple[np.ndarray, float, float, dict]:
    """One record per scored fill, from the run's own draw and weights.

    Mirrors :func:`symbolic_ai_core.data.sampler.batches` with ``shuffle=False``
    rather than calling it, because the episode *index* is needed for the
    paired-fill test and ``batches`` yields only the collated batch.

    ``draw_from`` takes the *task config* from a different run — used only to
    score one arm's weights on the other arm's draw. The two arms' tokenizers
    are byte-identical (``md5 0f29f1ea…``), so the draw does not depend on which
    run supplied it, and the published-accuracy assertion is skipped because
    there is no published number for a cross-fit.
    """
    model, tok, cfg = load_run(path, device="cpu")
    if draw_from is not None:
        _m2, _t2, cfg2 = load_run(draw_from, device="cpu")
        cfg = cfg2
    summary = json.loads((Path(path) / "summary.json").read_text())
    published = next(
        (v.get("label_acc") for v in (summary.get("final") or {}).values()
         if isinstance(v, dict) and "label_acc" in v), float("nan"))
    assert (summary.get("masking") or {}).get("mask_mode", "scatter") == "scatter"
    _train, ev = _data(cfg)

    task = make_task("node", mask_rate=cfg.mask_rate, max_nodes=cfg.max_nodes,
                     seed=cfg.seed)
    task.rng = np.random.default_rng(12345)
    model.eval()
    rows: list[tuple] = []
    n_src_unlabelled = 0
    order = list(range(len(ev)))
    window = cfg.batch_size * 8
    for start in range(0, len(order), window):
        chunk = order[start:start + window]
        chunk.sort(key=lambda i: len(ev[i].graph))
        for b in range(0, len(chunk), cfg.batch_size):
            idx = chunk[b:b + cfg.batch_size]
            if not idx:
                continue
            batch = task.collate([ev[i] for i in idx], tok)
            with torch.no_grad():
                pred = model(batch).symbol_logits.argmax(-1)
            scored = (batch.target_tokens != IGNORE).numpy()
            correct = ((pred == batch.target_tokens).numpy() & scored)
            copyable = (batch.target_source != IGNORE).numpy()
            lg = batch.label_group.numpy()
            labelled = lg != IGNORE
            visible = (batch.types != MASK).numpy() & batch.pad_mask.numpy()
            vislab = labelled & visible
            types = batch.types.numpy()
            ttypes = batch.target_types.numpy()
            for k, ep_i in enumerate(idx):
                sc = np.flatnonzero(scored[k])
                if not sc.size:
                    continue
                lgk, labk, visk = lg[k], labelled[k], vislab[k]
                ng = int(lgk[labk].max()) + 1
                cnt_vis = np.bincount(lgk[visk], minlength=ng)
                cnt_all = np.bincount(lgk[labk], minlength=ng)
                V = int(visk.sum())
                D = int((cnt_vis > 0).sum())
                for i in sc:
                    g = int(lgk[i])
                    assert g != IGNORE, "a scored fill with no label group"
                    t = int(ttypes[k, i])
                    v = int(cnt_vis[g])
                    Vt = int((visk & (types[k] == t)).sum())
                    if bool(copyable[k, i]) != (v > 0):
                        # `target_source` accepts a visible node of *any* type
                        # with the same label, `label_group` only non-structural
                        # ones. Counted rather than assumed away.
                        n_src_unlabelled += 1
                    rows.append((ep_i, int(i), int(correct[k, i]),
                                 int(copyable[k, i]), v, V, int(cnt_all[g]),
                                 D, Vt, t))
    rec = np.asarray(rows, dtype=np.int64)
    acc = float(rec[:, 2].mean())
    if draw_from is None:
        assert abs(acc - published) < 1e-9, (
            f"{path}: pooled {acc} != published {published}")
    return rec, acc, cfg.mask_rate, {"n_src_unlabelled": n_src_unlabelled,
                                     "model": summary.get("model")}


def col(rec: np.ndarray, name: str) -> np.ndarray:
    return rec[:, COLS.index(name)]


def band_of(ratio: np.ndarray, right: bool = True) -> np.ndarray:
    """Band index for ``v/V``.

    ``right=True`` is ``lo < x <= hi``, which is what
    ``copyable_survivorship._conc_band`` does; ``right=False`` is
    ``lo <= x < hi``. The convention is not cosmetic at 0.90, where ``V`` is
    about 7 and ``v/V`` lands exactly on 0.1, 0.2 and 0.4 constantly, so the
    two conventions move real mass between bands. Both are reported.
    """
    return np.digitize(ratio, BANDS[1:-1], right=right)


def standardise(a: np.ndarray, b: np.ndarray, key_a: np.ndarray,
                key_b: np.ndarray) -> tuple[float, float, float]:
    """Carry ``a``'s per-cell rates onto ``b``'s mix.

    Cells of ``b`` with no ``a`` mass have no counterfactual and are dropped —
    **from both sides**. Comparing a prediction made on the matched cells with
    an observation pooled over all of them is not a standardisation, it is a
    standardisation plus an unmatched difference, and on exact ``(v, V)``
    matching that error alone moved the answer by +0.08. The ability-free
    control below is what caught it: with the cells matched exactly its
    shortfall has to be identically zero, and it was not.
    """
    pred, wt, lost = 0.0, 0.0, 0.0
    obs, obs_w = 0.0, 0.0
    for c in np.unique(key_b):
        sel_b = key_b == c
        w = float(sel_b.sum())
        sel = key_a == c
        if not sel.any():
            lost += w
            continue
        pred += w * float(a[sel].mean())
        obs += float(b[sel_b].sum())
        obs_w += w
        wt += w
    n = float(len(b))
    return (pred / wt if wt else float("nan"),
            obs / obs_w if obs_w else float("nan"), lost / n)


def logistic(X: np.ndarray, y: np.ndarray, iters: int = 60) -> np.ndarray:
    """Plain IRLS. Small, dense and deterministic; no sklearn dependency."""
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-X @ w))
        s = np.clip(p * (1 - p), 1e-9, None)
        H = X.T @ (X * s[:, None]) + 1e-8 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        w = w + step
        if np.abs(step).max() < 1e-10:
            break
    return w


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r015", required=True)
    ap.add_argument("--r090", required=True)
    ap.add_argument("--models", default="corefer-001,ptrgen-001,routes-001,"
                                        "vsa_perm-002,evidence-001,grammar-001")
    ap.add_argument("--cache", default="")
    ap.add_argument("--cross", action="store_true",
                    help="also score the 0.15-fitted weights on the 0.90 draw")
    args = ap.parse_args(argv)
    names = [m for m in args.models.split(",") if m]

    recs: dict[tuple[str, str], np.ndarray] = {}
    for arm, root in (("0.15", args.r015), ("0.90", args.r090)):
        for name in names:
            path = Path(root) / name
            if not (path / "summary.json").exists() or not (path / "model.pt").exists():
                print(f"skipping {path}: not finished", file=sys.stderr)
                continue
            cached = Path(args.cache) / f"{arm}-{name}.npy" if args.cache else None
            if cached is not None and cached.exists():
                recs[arm, name] = np.load(cached)
                continue
            rec, acc, rate, info = replay(str(path))
            assert abs(rate - float(arm)) < 1e-9, f"{path} is rate {rate}"
            print(f"{arm} {name:<14} n={len(rec):>6} acc={acc:.6f} "
                  f"src-not-in-group={info['n_src_unlabelled']}")
            recs[arm, name] = rec
            if cached is not None:
                cached.parent.mkdir(parents=True, exist_ok=True)
                np.save(cached, rec)
    print()

    # The covariates are a property of the draw, not of the model: assert it
    # rather than trusting it, because everything downstream pools over models.
    for arm in ("0.15", "0.90"):
        got = [k for k in recs if k[0] == arm]
        base = recs[got[0]]
        for k in got[1:]:
            assert np.array_equal(recs[k][:, [0, 1, 3, 4, 5, 6, 7, 8, 9]],
                                  base[:, [0, 1, 3, 4, 5, 6, 7, 8, 9]]), k
        cp = base[:, COLS.index("copyable")] == 1
        print(f"arm {arm}: {len(base)} scored fills, copyable share "
              f"{cp.mean():.4f}, mean V {col(base, 'V').mean():.1f}, "
              f"mean v|copyable {col(base, 'v')[cp].mean():.2f}, "
              f"mean D {col(base, 'D').mean():.1f}")
    print()

    # Is the shortfall a property of the 0.90 *evaluation regime* or of the 0.90
    # *fit*? The two arms are separately fitted models, which the attacked note
    # does not say. Scoring the 0.15-fitted weights on the 0.90 draw separates
    # them: if the bucket simply got easier, the transferred model gains too.
    if args.cross:
        print(f"{'cross-fit: 0.15 weights on the 0.90 draw':<44}"
              f"{'acc all':>9}{'acc|copy':>10}{'0.90 fit':>10}{'delta':>8}")
        for name in names:
            src, dst = Path(args.r015) / name, Path(args.r090) / name
            if not (src / "model.pt").exists() or ("0.90", name) not in recs:
                continue
            cached = (Path(args.cache) / f"cross-{name}.npy") if args.cache else None
            if cached is not None and cached.exists():
                rec = np.load(cached)
            else:
                rec, _a, _r, _i = replay(str(src), draw_from=str(dst))
                if cached is not None:
                    np.save(cached, rec)
            own = recs["0.90", name]
            # Same draw, so the covariates must agree fill for fill.
            assert np.array_equal(rec[:, [0, 1, 3, 4, 5, 6, 7, 8, 9]],
                                  own[:, [0, 1, 3, 4, 5, 6, 7, 8, 9]]), name
            cp = col(rec, "copyable") == 1
            a_all, a_cp = float(col(rec, "correct").mean()), \
                float(col(rec, "correct")[cp].mean())
            b_cp = float(col(own, "correct")[cp].mean())
            print(f"{name:<44}{a_all:>9.4f}{a_cp:>10.4f}{b_cp:>10.4f}"
                  f"{a_cp-b_cp:>+8.4f}")
        print()

    # Episode index -> lesson, so the exact-matching support can be described
    # rather than trusted. The eval episodes are a function of the config, and
    # both arms' configs agree on everything but the mask rate.
    lesson_of = None
    for arm, root in (("0.15", args.r015),):
        for name in names:
            p = Path(root) / name
            if (p / "model.pt").exists():
                _m, _t, cfg = load_run(str(p), device="cpu")
                lesson_of = np.array([ep.lesson_id for ep in _data(cfg)[1]])
                break

    for name in names:
        if ("0.15", name) not in recs or ("0.90", name) not in recs:
            continue
        report(name, recs["0.15", name], recs["0.90", name], lesson_of)
    return 0


def _copyable(rec: np.ndarray):
    sel = col(rec, "copyable") == 1
    r = rec[sel]
    y = col(r, "correct").astype(float)
    v = col(r, "v").astype(float)
    V = col(r, "V").astype(float)
    return r, y, v, V


def report(name: str, a: np.ndarray, b: np.ndarray,
           lesson_of: np.ndarray | None = None) -> None:
    ra, ya, va, Va = _copyable(a)
    rb, yb, vb, Vb = _copyable(b)
    print("=" * 78)
    print(f"{name}: acc|copyable {ya.mean():.4f} (0.15, n={len(ya)}) -> "
          f"{yb.mean():.4f} (0.90, n={len(yb)})  delta {yb.mean()-ya.mean():+.4f}")

    # --- the note's own banding, plus the composition inside each band --------
    band_a, band_b = band_of(va / Va), band_of(vb / Vb)
    print(f"{'v/V band':<12}{'acc 015':>9}{'sh 015':>8}{'mean 015':>10}"
          f"{'acc 090':>9}{'sh 090':>8}{'mean 090':>10}{'d(acc)':>9}{'d(mean)':>9}")
    for k, bn in enumerate(BAND_NAMES):
        sa, sb = band_a == k, band_b == k
        if not sa.any() and not sb.any():
            continue
        aa = ya[sa].mean() if sa.any() else float("nan")
        ab = yb[sb].mean() if sb.any() else float("nan")
        ma = (va / Va)[sa].mean() if sa.any() else float("nan")
        mb = (vb / Vb)[sb].mean() if sb.any() else float("nan")
        print(f"{bn:<12}{aa:>9.3f}{sa.mean():>8.3f}{ma:>10.4f}"
              f"{ab:>9.3f}{sb.mean():>8.3f}{mb:>10.4f}"
              f"{ab-aa:>9.3f}{mb-ma:>9.4f}")
    pred, obs, lost = standardise(ya, yb, band_a, band_b)
    print(f"  banded standardisation: predicted {pred:.4f} observed {obs:.4f} "
          f"shortfall {obs-pred:+.4f} (weight lost {lost:.3f})")
    la, lb = band_of(va / Va, right=False), band_of(vb / Vb, right=False)
    pl, ol, _ = standardise(ya, yb, la, lb)
    print(f"  same bands, left-closed: predicted {pl:.4f} observed {ol:.4f} "
          f"shortfall {ol-pl:+.4f}")

    # How far apart are the two arms' supports? A standardisation over a
    # covariate the arms barely share is extrapolation whatever its bands.
    qs = (1, 5, 25, 50, 75, 95, 99)
    print("  V percentiles  0.15 " + " ".join(
        f"{p}%={np.percentile(Va, p):.0f}" for p in qs))
    print("  V percentiles  0.90 " + " ".join(
        f"{p}%={np.percentile(Vb, p):.0f}" for p in qs))
    hi90 = float(np.percentile(Vb, 99))
    print(f"  overlap: {float((Va <= hi90).mean()):.3f} of 0.15 fills have "
          f"V <= the 0.90 arm's 99th percentile ({hi90:.0f}); "
          f"{float((Vb >= np.percentile(Va, 1)).mean()):.3f} of 0.90 fills "
          f"have V >= the 0.15 arm's 1st percentile "
          f"({np.percentile(Va, 1):.0f})")

    # The same standardisation applied to a predictor with no ability: a
    # uniform pick among visible labelled nodes is right with probability
    # exactly v/V. Any shortfall it shows is the adjustment's own residue.
    ca, cb = va / Va, vb / Vb
    pr, ob, _ = standardise(ca, cb, band_a, band_b)
    print(f"  random-pointer control (E[acc] = v/V): predicted {pr:.4f} "
          f"observed {ob:.4f} shortfall {ob-pr:+.4f}")

    # --- no bands at all: exact matching on the integer pair (v, V) -----------
    ka = va.astype(np.int64) * 100_000 + Va.astype(np.int64)
    kb = vb.astype(np.int64) * 100_000 + Vb.astype(np.int64)
    pred, obs, lost = standardise(ya, yb, ka, kb)
    used = np.isin(ka, np.intersect1d(ka, kb))
    print(f"  exact (v,V) matching:   predicted {pred:.4f} observed {obs:.4f} "
          f"shortfall {obs-pred:+.4f} (weight lost {lost:.3f}; the prediction "
          f"rests on {int(used.sum())} of the {len(ya)} 0.15 fills)")
    pr2, ob2, _ = standardise(ca, cb, ka, kb)
    print(f"  exact (v,V), control:   predicted {pr2:.4f} observed {ob2:.4f} "
          f"shortfall {ob2-pr2:+.4f} (zero by construction; the check is that "
          f"the estimator has no leak)")
    if lesson_of is not None:
        les_a = lesson_of[col(ra, "ep")[used]]
        print(f"    that support is {len(np.unique(col(ra, 'ep')[used]))} "
              f"episodes over {len(np.unique(les_a))} of the "
              f"{len(np.unique(lesson_of))} lessons, against "
              f"{len(np.unique(lesson_of[col(ra, 'ep')]))} lessons in the "
              f"whole 0.15 copyable bucket")

    # --- no bands: a logistic fit with the arm as an indicator ----------------
    X = np.column_stack([
        np.ones(len(ya) + len(yb)),
        np.log(np.concatenate([va, vb])),
        np.log(np.concatenate([Va, Vb])),
        np.concatenate([np.zeros(len(ya)), np.ones(len(yb))]),
    ])
    y = np.concatenate([ya, yb])
    w = logistic(X, y)
    # The same fit with an interaction, in case one slope is doing the work.
    X2 = np.column_stack([X, X[:, 1] * X[:, 3], X[:, 2] * X[:, 3]])
    w2 = logistic(X2, y)
    # Marginal effect: the 0.90 fills scored under the 0.15 arm's fitted
    # surface, against their own.
    Xb = X[len(ya):]
    p_own = 1 / (1 + np.exp(-Xb @ w))
    p_as015 = 1 / (1 + np.exp(-(Xb * np.array([1, 1, 1, 0])) @ w))
    print(f"  logistic  b(log v)={w[1]:+.3f} b(log V)={w[2]:+.3f} "
          f"b(rate=0.90)={w[3]:+.3f}; counterfactual {p_as015.mean():.4f} "
          f"vs fitted {p_own.mean():.4f} ({p_own.mean()-p_as015.mean():+.4f})")
    Xb2 = X2[len(ya):]
    Xb2_0 = Xb2.copy()
    Xb2_0[:, 3:] = 0.0
    q_own = 1 / (1 + np.exp(-Xb2 @ w2))
    q_as015 = 1 / (1 + np.exp(-Xb2_0 @ w2))
    print(f"  logistic+interaction b(rate)={w2[3]:+.3f} "
          f"b(rate x log v)={w2[4]:+.3f} b(rate x log V)={w2[5]:+.3f}; "
          f"counterfactual {q_as015.mean():.4f} vs fitted {q_own.mean():.4f} "
          f"({q_own.mean()-q_as015.mean():+.4f})")

    # The same banded standardisation restricted to the V range both arms
    # actually occupy. If the reversal is an artefact of extrapolating the
    # 0.15 curve into graphs it almost never sees, this is where it dies.
    lo, hi = float(np.percentile(Va, 1)), float(np.percentile(Vb, 99))
    ka_, kb_ = (Va >= lo) & (Va <= hi), (Vb >= lo) & (Vb <= hi)
    if ka_.sum() > 200 and kb_.sum() > 200:
        pr4, ob4, lost4 = standardise(ya[ka_], yb[kb_], band_a[ka_], band_b[kb_])
        pc4, oc4, _ = standardise(ca[ka_], cb[kb_], band_a[ka_], band_b[kb_])
        print(f"  common V support [{lo:.0f}, {hi:.0f}]: n015={int(ka_.sum())} "
              f"n090={int(kb_.sum())}; predicted {pr4:.4f} observed {ob4:.4f} "
              f"shortfall {ob4-pr4:+.4f} (control {oc4-pc4:+.4f})")

    # --- is v/V even the right covariate? ------------------------------------
    for label, ga, gb in (
            ("v alone", va, vb),
            ("V alone", Va, Vb),
            ("v / D", va / col(ra, "D"), vb / col(rb, "D")),
            ("v / Vtype", va / np.maximum(col(ra, "Vt"), 1),
             vb / np.maximum(col(rb, "Vt"), 1)),
            ("m (multiplicity)", col(ra, "m"), col(rb, "m")),
    ):
        if label in ("v alone", "V alone", "m (multiplicity)"):
            ja, jb = ga.astype(np.int64), gb.astype(np.int64)
        else:
            ja, jb = band_of(ga), band_of(gb)
        pred, obs, lost = standardise(ya, yb, ja, jb)
        # The control is always the ability-free pointer, whatever the key.
        pr3, ob3, _ = standardise(ca, cb, ja, jb)
        print(f"  standardised on {label:<17} predicted {pred:.4f} "
              f"observed {obs:.4f} shortfall {obs-pred:+.4f} "
              f"(lost {lost:.3f}, control shortfall {ob3-pr3:+.4f})")

    # The obvious remaining confound: the copyable bucket at 0.90 may hold a
    # different mix of *node types*, and concentration would not see it. Joint
    # cells of (type, v/V band) hold both at once.
    ja = col(ra, "type") * 10 + band_a
    jb = col(rb, "type") * 10 + band_b
    pj, oj, lostj = standardise(ya, yb, ja, jb)
    pjc, ojc, _ = standardise(ca, cb, ja, jb)
    print(f"  joint (node type x v/V band): predicted {pj:.4f} observed "
          f"{oj:.4f} shortfall {oj-pj:+.4f} (lost {lostj:.3f}, "
          f"control {ojc-pjc:+.4f})")
    ta, tb = col(ra, "type"), col(rb, "type")
    pt, ot, lostt = standardise(ya, yb, ta, tb)
    print(f"  node type alone:              predicted {pt:.4f} observed "
          f"{ot:.4f} shortfall {ot-pt:+.4f} (lost {lostt:.3f})")

    # --- no covariate at all: the same fill, asked at both rates --------------
    key_a = col(a, "ep") * 1000 + col(a, "node")
    key_b = col(b, "ep") * 1000 + col(b, "node")
    common, ia, ib = np.intersect1d(key_a, key_b, return_indices=True)
    ca_, cb_ = col(a, "copyable")[ia] == 1, col(b, "copyable")[ib] == 1
    both = ca_ & cb_
    ha, hb = col(a, "correct")[ia], col(b, "correct")[ib]
    print(f"  paired fills: {len(common)} shared (episode, node); "
          f"copyable at both {int(both.sum())}")
    print(f"    all shared:        0.15 {ha.mean():.4f}  0.90 {hb.mean():.4f}  "
          f"{hb.mean()-ha.mean():+.4f}")
    if both.any():
        print(f"    copyable at both:  0.15 {ha[both].mean():.4f}  "
              f"0.90 {hb[both].mean():.4f}  "
              f"{hb[both].mean()-ha[both].mean():+.4f}")
        disc = int(((ha[both] == 1) & (hb[both] == 0)).sum()), \
            int(((ha[both] == 0) & (hb[both] == 1)).sum())
        print(f"    discordant pairs:  0.15 only {disc[0]}, 0.90 only {disc[1]}"
              f"  (McNemar z = "
              f"{(disc[1]-disc[0])/math.sqrt(max(disc[0]+disc[1], 1)):+.1f})")
        # Those same paired fills carry *more* concentrated evidence at 0.90
        # than at 0.15, so "no worse" is not "no shortfall": the 0.15 surface
        # says they should have got easier. This is the paired test asked as
        # the note asks it.
        sel_b = np.zeros(len(b), bool)
        sel_b[ib[both]] = True
        pb = sel_b[col(b, "copyable") == 1]
        va_p = col(a, "v")[ia[both]] / col(a, "V")[ia[both]]
        vb_p = col(b, "v")[ib[both]] / col(b, "V")[ib[both]]
        print(f"    on those pairs, mean v/V is {va_p.mean():.3f} at 0.15 and "
              f"{vb_p.mean():.3f} at 0.90; logistic counterfactual "
              f"{p_as015[pb].mean():.4f} vs observed {yb[pb].mean():.4f} "
              f"({yb[pb].mean()-p_as015[pb].mean():+.4f})")

    # --- how much of any of this is noise, clustered by episode --------------
    lo, hi = bootstrap_shortfall(ra, ya, rb, yb, band_a, band_b)
    print(f"  episode-clustered bootstrap of the banded shortfall: "
          f"[{lo:+.4f}, {hi:+.4f}] (95%, 400 resamples)")
    print()


def bootstrap_shortfall(ra, ya, rb, yb, band_a, band_b, n: int = 400):
    """Resample *episodes*, not fills: at 0.90 one episode contributes dozens
    of correlated fills and a fill-level interval would be far too tight."""
    rng = np.random.default_rng(7)
    ea, eb = col(ra, "ep"), col(rb, "ep")
    eps = np.unique(np.concatenate([ea, eb]))
    idx_a = {e: np.flatnonzero(ea == e) for e in eps}
    idx_b = {e: np.flatnonzero(eb == e) for e in eps}
    out = []
    for _ in range(n):
        draw = rng.choice(eps, size=len(eps), replace=True)
        sa = np.concatenate([idx_a[e] for e in draw])
        sb = np.concatenate([idx_b[e] for e in draw])
        if not len(sa) or not len(sb):
            continue
        pred, obs, _ = standardise(ya[sa], yb[sb], band_a[sa], band_b[sb])
        out.append(obs - pred)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
