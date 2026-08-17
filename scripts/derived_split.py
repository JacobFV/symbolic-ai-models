"""Is the derived slot answered? The population the `derive:` arms act on.

``scripts/copyable_split.py`` splits the masked-node score by whether the answer
sits on a visible node. This splits it again, by whether the answer was
**derived** — not drawn at all, but determined by the object's kind through the
corpus-wide map in :mod:`symbolic_ai_kg.derive`. That is the only population on
which ``derive:wordnet`` and its control ``derive:wordnet-perm`` can differ, and
it is **0.20% of the curriculum's graph positions in 11 of 179 lessons**, so the
pooled table cannot see it by construction — see
``notes/decisions/2026-08-15-derivability-is-the-treatment-and-the-per-episode-permutation-is-the-control.md``.

What it reports, per run:

* ``acc | derived, not copyable`` — the number that decides the arm. A derived
  fill whose value also sits on a visible sibling object is answerable in
  **both** arms by copying, so the copyable half cannot separate them.
* ``acc | derived, copyable`` and the same two for the fills that are *not*
  derived, as the within-run control for "this model just got better at
  everything".
* the **derivation floor**: the commonest value seen in training for this kind,
  applied through the visible sibling kind. A lookup table with no reasoning in
  it, and deliberately stronger than ``task.split_floor``, which may not read a
  neighbour's label. Predicted ~1.00 on ``derive:wordnet`` and ~1/6 on
  ``derive:wordnet-perm``; **if those two do not separate, the experiment did not
  happen and no model number below should be read.**

Two decisions about the draw, both of which change what the number means:

* **The same 15% scatter regime the models were trained under**, repeated over
  several draws for n. Masking the derived positions specially would buy n by
  showing the models a regime they never saw, and would confound the arms with a
  distribution shift.
* **Evaluation seeds beyond the run's own**, on the lessons that carry a derived
  slot at all. The derived bucket is 0.2% of positions and the run's own draw
  holds about a dozen of them; restricting to the carrying lessons is not a
  slice of a result but the definition of the population, and it costs less than
  the full sweep's own evaluation. The run's own draw is *also* scored, once,
  and its pooled number asserted against the published one — that is what says
  this is the same model on the same contract.

    uv run python scripts/derived_split.py runs/derive179-wordnet/*
"""
from __future__ import annotations

import collections
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")

import numpy as np
import torch

torch.set_num_threads(4)

import symbolic_ai_data as lc
from symbolic_ai_core.data.batch import IGNORE
from symbolic_ai_core.data.curriculum import _binder_factory, generate, lesson_ids
from symbolic_ai_data.binding import using
from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import load_data, load_run

#: Masking draws of the derived evaluation set. Each is the run's own regime with
#: a different rng, so the population is unchanged and only n grows.
DRAWS = 8
#: Evaluation seeds per carrying lesson, from the eval range. 64 puts the
#: non-copyable derived bucket in the high hundreds, which is what the
#: pre-registration named as the minimum for the arms to be separable at all.
N_EVAL = 64
#: Training seeds the derivation floor is fitted on. The sweep's own n_train, so
#: the lookup sees exactly the evidence the models did.
N_TRAIN = 20

TASK_OF = {"scatter": "node", "subtree": "nodesub",
           "answer": "nodeans", "answer_one": "nodeans1"}

#: Every arm the derived population is intersected over, so that the bucket is
#: identical in each and a difference between two columns is a difference between
#: two models rather than between two populations. See :func:`matched_episodes`.
ARMS = ("derive:wordnet", "derive:wordnet-perm", "derive:wordnet-shuffled")


def arms_for(curriculum: str) -> tuple[str, ...]:
    """The family a curriculum belongs to, for `carrying_lessons` and the match.

    The population has to be intersected across an arm's **own** treatment and
    control, never across families. The `-kN` rungs widen the pool the episode's
    six kinds are drawn from, so they draw different kinds and different scenes
    from the base arm — intersecting a `k24` run against `derive:wordnet` would
    hold a population neither of them is scored on, which is the exact failure
    `matched_episodes` exists to prevent, one level up.
    """
    base = curriculum
    for suffix in ("-perm", "-shuffled"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    if base == "derive:wordnet":
        return ARMS
    return (base, f"{base}-perm")


def _positions(g, derived) -> list[tuple[int, int]]:
    """``(value position, kind position)`` for each derived fill in this graph.

    Located by **object id**, never by matching labels against the value list:
    several lessons build an ``obj`` predicate themselves without going through
    ``bind_scene``, and a label match would count one of their undetermined
    kind/value pairs as derived once in six by chance — in both arms, which is
    worse than in one.
    """
    n = len(g)
    kids: dict[int, list[int]] = collections.defaultdict(list)
    for i in range(n):
        p = g.parent[i]
        if 0 <= p < n:
            kids[p].append(i)
    want = {oid: (kind, val) for oid, kind, val in derived}
    out: list[tuple[int, int]] = []
    for p in range(n):
        if g.types[p] != "pred" or g.labels[p] != "obj":
            continue
        ch = kids.get(p, ())
        ids = [c for c in ch if g.labels[c] in want]
        if len(ids) != 1:
            continue
        kind, val = want[g.labels[ids[0]]]
        vs = [c for c in ch if c not in ids and g.labels[c] == val]
        ks = [c for c in ch if c not in ids and g.labels[c] == kind]
        if vs and ks:
            out.append((vs[0], ks[0]))
    return out


def derived_episodes(curriculum: str, lessons, *, n: int, seed0: int,
                     max_nodes: int):
    """Episodes of this arm, each with the positions its binder derived.

    The binder is re-run for ``(lesson, seed)`` — it is a pure function of that
    address — so nothing has to have been written down at sweep time.
    """
    make = _binder_factory(curriculum)
    if make is None:
        return []
    out = []
    for ep in generate(lessons, n=n, seed0=seed0, max_nodes=max_nodes,
                       curriculum=curriculum):
        b = make(ep.lesson_id, ep.seed)
        if not hasattr(b, "derived"):
            return []
        with using(b):
            lc.get(ep.lesson_id).structured(ep.seed)
        out.append((ep, _positions(ep.graph, b.derived())))
    return out


def carrying_lessons(arms=None, *, seeds: int = 8, max_nodes: int = 128):
    """Lessons whose graphs contain a derived position **in any arm**.

    The union, not the arm's own list, and that is not a detail. Asked per arm it
    comes back as 11 lessons for the treatment and 10 for the control —
    ``definitions`` survives the post-``bind_scene`` redraw in one and not the
    other at these seeds — so the two arms would be scored on different episode
    sets, hence different batch compositions, hence different masking draws.
    Measured before it was fixed: 1,325 scored derived fills against 1,403, a 6%
    gap that is entirely bookkeeping and would have sat inside the column being
    subtracted.
    """
    arms = tuple(arms or ARMS)
    hit = []
    for lid in lesson_ids():
        if any(any(pos for _ep, pos in
                   derived_episodes(a, [lid], n=seeds, seed0=0,
                                    max_nodes=max_nodes))
               for a in arms):
            hit.append(lid)
    return hit


def matched_episodes(curriculum: str, arms, lessons, *, n: int, seed0: int,
                     max_nodes: int):
    """This arm's episodes, restricted to positions derived in **every** arm.

    Necessary, and found the loud way. ``compositional_reference`` redraws
    colours in a rejection loop *after* ``bind_scene`` has run — ``while sum(1
    for o in lefts if o["color"] == tgt_color) > 1: o["color"] =
    rng.choice(COLORS)`` — so on some episodes an object's value is a fresh
    uniform draw rather than the derived one, and *which* objects survive
    depends on the arm. Measured on five scene lessons at six seeds: 114
    surviving positions in the treatment against 112 in the control, 1.8% apart.

    Small, and the wrong thing to shrug at. ``acc | derived, not copyable`` is
    read per arm and subtracted; if the arms score slightly different populations
    the difference is partly a bucket difference, which is the failure
    ``notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md``
    is about. Intersecting makes the population identical by construction, and
    the tree shapes are identical across arms so a position index means the same
    node in each.
    """
    per_arm = {a: derived_episodes(a, lessons, n=n, seed0=seed0,
                                   max_nodes=max_nodes) for a in arms}
    keep: dict[tuple[str, int], set[int]] = {}
    for a, rows in per_arm.items():
        for ep, pos in rows:
            key = (ep.lesson_id, ep.seed)
            here = {vi for vi, _ki in pos}
            keep[key] = here if key not in keep else (keep[key] & here)
    out = []
    for ep, pos in per_arm[curriculum]:
        allowed = keep.get((ep.lesson_id, ep.seed), set())
        out.append((ep, [(vi, ki) for vi, ki in pos if vi in allowed]))
    return out


def _batched(pairs, task, tok, batch_size, bucket=8):
    """``sampler.batches`` with the episode indices, and the same composition.

    Reimplemented rather than wrapped because the sampler sorts within a window
    and does not say where it put what; the per-position ``derived`` flags have
    to line up with the batch it actually built.
    """
    order = list(range(len(pairs)))
    window = batch_size * max(bucket, 1)
    for start in range(0, len(order), window):
        chunk = order[start:start + window]
        chunk.sort(key=lambda i: len(pairs[i][0].graph))
        for b in range(0, len(chunk), batch_size):
            picked = chunk[b:b + batch_size]
            if picked:
                yield picked, task.collate([pairs[i][0] for i in picked], tok)


def derivation_floor(train_pairs, ev_pairs, tok, task, draws: int = DRAWS
                     ) -> dict[str, float]:
    """The commonest training value for this kind, read off the visible sibling.

    Not a floor in ``task.floor``'s sense and not comparable with one: it reads a
    *symbol* on a neighbouring node, which the structural floor is forbidden to
    do. It is here because "did anything learn the map" needs the score of the
    dumbest thing that could — a lookup table — before any model number means
    anything.
    """
    rule: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for ep, pos in train_pairs:
        for vi, ki in pos:
            rule[ep.graph.labels[ki]][ep.graph.labels[vi]] += 1
    overall: collections.Counter = collections.Counter()
    for c in rule.values():
        overall.update(c)
    hit = {True: 0, False: 0}
    blind = {True: 0, False: 0}
    n = {True: 0, False: 0}
    # The same lookup with the sibling term removed: the commonest derived value
    # in training, full stop. It is the *blind* half of this floor and it is what
    # says the two arms differ in the conditional and not in the marginal —
    # both must sit at 1/6, in both arms, or the arms are not matched on the
    # value distribution and the comparison is between two populations.
    blind_pred = overall.most_common(1)[0][0] if overall else None
    for d in range(draws):
        rng = np.random.default_rng(12345 + d)
        for ep, pos in ev_pairs:
            if not pos:
                continue
            g = ep.graph
            nn = min(len(g), task.max_nodes)
            hidden = task._hidden(ep, nn, rng)
            for vi, ki in pos:
                if vi not in hidden or vi >= nn or ki >= nn or ki in hidden:
                    continue
                if not task._scorable(g.labels[vi], g.types[vi], tok):
                    continue
                copyable = any(j not in hidden and j != vi
                               and g.labels[j] == g.labels[vi] for j in range(nn))
                counts = rule.get(g.labels[ki]) or overall
                pred = counts.most_common(1)[0][0] if counts else None
                n[copyable] += 1
                hit[copyable] += pred == g.labels[vi]
                blind[copyable] += blind_pred == g.labels[vi]
    total = n[True] + n[False]
    div = lambda a, b: a / b if b else float("nan")
    return {"dfloor_copyable": div(hit[True], n[True]),
            "dfloor_not_copyable": div(hit[False], n[False]),
            "dfloor_all": div(hit[True] + hit[False], total),
            "blind_copyable": div(blind[True], n[True]),
            "blind_not_copyable": div(blind[False], n[False]),
            "blind_all": div(blind[True] + blind[False], total),
            "dfloor_n": float(total)}


def reproduce_published(path: str, model, tok, cfg, summary) -> tuple[float, float]:
    """The run's own evaluation draw, rescored. Must equal what it published."""
    mode = (summary.get("masking") or {}).get("mask_mode", "scatter")
    _train, ev = load_data(cfg)
    task = make_task(TASK_OF[mode], mask_rate=cfg.mask_rate,
                     max_nodes=cfg.max_nodes, seed=cfg.seed)
    task.rng = np.random.default_rng(12345)
    import random as _random

    from symbolic_ai_core.data.sampler import batches
    hits = seen = 0
    for batch in batches(ev, task, tok, batch_size=cfg.batch_size,
                         rng=_random.Random(0), shuffle=False):
        with torch.no_grad():
            pred = model(batch).symbol_logits.argmax(-1)
        scored = batch.target_tokens != IGNORE
        hits += int(((pred == batch.target_tokens) & scored).sum())
        seen += int(scored.sum())
    published = next(
        (v.get("label_acc") for v in (summary.get("final") or {}).values()
         if isinstance(v, dict) and "label_acc" in v), float("nan"))
    return (hits / seen if seen else float("nan")), published


def split(path: str, ev_pairs, train_pairs, draws: int = DRAWS) -> dict:
    model, tok, cfg = load_run(path, device="cpu")
    summary = json.loads((Path(path) / "summary.json").read_text())
    mode = (summary.get("masking") or {}).get("mask_mode", "scatter")
    got, published = reproduce_published(path, model, tok, cfg, summary)
    task = make_task(TASK_OF[mode], mask_rate=cfg.mask_rate,
                     max_nodes=cfg.max_nodes, seed=cfg.seed)
    model.eval()
    cell = {a: {b: [0, 0] for b in (True, False)} for a in (True, False)}
    for d in range(draws):
        task.rng = np.random.default_rng(12345 + d)
        for idx, batch in _batched(ev_pairs, task, tok, cfg.batch_size):
            derived = torch.zeros_like(batch.target_tokens, dtype=torch.bool)
            anchor_seen = torch.zeros_like(derived)
            for b, i in enumerate(idx):
                for vi, ki in ev_pairs[i][1]:
                    if vi < derived.shape[1] and ki < derived.shape[1]:
                        derived[b, vi] = True
                        # a derived fill whose anchor is itself hidden is not
                        # derivable from anything, in either arm
                        anchor_seen[b, vi] = batch.target_types[b, ki] == IGNORE
            derived = derived & anchor_seen
            with torch.no_grad():
                pred = model(batch).symbol_logits.argmax(-1)
            scored = batch.target_tokens != IGNORE
            correct = (pred == batch.target_tokens) & scored
            copyable = batch.target_source != IGNORE
            for a in (True, False):
                for c in (True, False):
                    sel = scored & (derived if a else ~derived) \
                        & (copyable if c else ~copyable)
                    cell[a][c][1] += int(sel.sum())
                    cell[a][c][0] += int((correct & sel).sum())
    div = lambda a, b: a / b if b else float("nan")
    dn = cell[True][True][1] + cell[True][False][1]
    return {
        "model": summary.get("model", Path(path).name),
        "curriculum": cfg.curriculum, "draws": draws,
        "published": published, "reproduced": got,
        "derived_n": float(dn),
        "derived_copyable_share": div(cell[True][True][1], dn),
        "acc_derived": div(cell[True][True][0] + cell[True][False][0], dn),
        "acc_derived_copyable": div(cell[True][True][0], cell[True][True][1]),
        "acc_derived_not_copyable": div(cell[True][False][0], cell[True][False][1]),
        "rest_n": float(cell[False][True][1] + cell[False][False][1]),
        "acc_rest_copyable": div(cell[False][True][0], cell[False][True][1]),
        "acc_rest_not_copyable": div(cell[False][False][0], cell[False][False][1]),
    }


def main(paths: list[str]) -> int:
    # `--n-train N` follows the run's own training budget. The derivation floor
    # is fitted on `N_TRAIN` seeds so that "the lookup sees exactly the evidence
    # the models did" stays true; a run swept at 40 and floored at 20 would be
    # comparing a model against a floor built from a different corpus. Defaults
    # to 20, so every published row is unaffected.
    global N_TRAIN
    if "--n-train" in paths:
        i = paths.index("--n-train")
        N_TRAIN = int(paths[i + 1])
        paths = paths[:i] + paths[i + 2:]
    paths = [p for p in sorted(paths) if (Path(p) / "summary.json").exists()]
    if not paths:
        print("no finished runs given")
        return 1
    _m, tok0, cfg0 = load_run(paths[0], device="cpu")
    arm = cfg0.curriculum
    family = arms_for(arm)
    lessons = carrying_lessons(family, max_nodes=cfg0.max_nodes)
    print(f"curriculum {arm}")
    print(f"lessons carrying a derived slot in any arm: {len(lessons)} of 179 "
          f"-- {', '.join(lessons)}")
    ev_pairs = matched_episodes(arm, family, lessons, n=N_EVAL, seed0=1_000_000,
                                max_nodes=cfg0.max_nodes)
    train_pairs = matched_episodes(arm, family, lessons, n=N_TRAIN, seed0=0,
                                   max_nodes=cfg0.max_nodes)
    print(f"evaluation episodes {len(ev_pairs)} (seeds {1_000_000}..), "
          f"derived positions {sum(len(p) for _e, p in ev_pairs)}; "
          f"{DRAWS} masking draws")

    task = make_task("node", mask_rate=cfg0.mask_rate, max_nodes=cfg0.max_nodes,
                     seed=cfg0.seed)
    floors = derivation_floor(train_pairs, ev_pairs, tok0, task)
    print()
    head = (f"{'model':<22}{'n':>7}{'cp share':>9}{'acc|der':>9}"
            f"{'acc|der,cp':>12}{'acc|der,not':>13}{'acc|rest,not':>14}")
    print(head)
    print("-" * len(head))
    rows = []
    for p in paths:
        r = split(p, ev_pairs, train_pairs)
        assert abs(r["reproduced"] - r["published"]) < 1e-9, (
            f"{r['model']}: rescored {r['reproduced']} != published "
            f"{r['published']}; this is not the run's contract")
        rows.append(r)
        print(f"{r['model']:<22}{r['derived_n']:>7.0f}"
              f"{r['derived_copyable_share']:>9.3f}{r['acc_derived']:>9.3f}"
              f"{r['acc_derived_copyable']:>12.3f}"
              f"{r['acc_derived_not_copyable']:>13.3f}"
              f"{r['acc_rest_not_copyable']:>14.3f}")
    print("-" * len(head))
    print(f"{'DERIVATION FLOOR':<22}{floors['dfloor_n']:>7.0f}"
          f"{'':>9}{floors['dfloor_all']:>9.3f}"
          f"{floors['dfloor_copyable']:>12.3f}"
          f"{floors['dfloor_not_copyable']:>13.3f}")
    print(f"{'  same, sibling blind':<22}{floors['dfloor_n']:>7.0f}"
          f"{'':>9}{floors['blind_all']:>9.3f}"
          f"{floors['blind_copyable']:>12.3f}"
          f"{floors['blind_not_copyable']:>13.3f}")
    print("the derivation floor reads the *sibling kind's label*, which the "
          "structural floor may not; it is a lookup table and is the number a "
          "model has to reach before anything here is inference. The blind row "
          "is the same lookup with the sibling term dropped -- it must sit at "
          "1/6 in *both* arms, or they differ in the marginal and not only in "
          "the conditional.")
    # Merge rather than overwrite. The published weights under `runs/` are
    # untracked, so a later agent adding *one* model to an arm can only rescore
    # that one -- and writing the file from scratch would then delete nineteen
    # published rows that cannot be recomputed. Rows are keyed by model name, so
    # rerunning a model replaces its own row and nothing else.
    out = Path(paths[0]).parent / "derived_split.json"
    merged = {r["model"]: r for r in rows}
    if out.exists():
        prior = json.loads(out.read_text())
        assert prior["curriculum"] == arm, (
            f"{out} holds {prior['curriculum']}, this run is {arm}")
        for key, was in prior["floors"].items():
            now = floors.get(key)
            assert now is not None and abs(now - was) < 1e-9, (
                f"floor {key} moved {was} -> {now}; the population is not the "
                "one the published rows were measured on, so they must not be "
                "merged with these")
        merged = {r["model"]: r for r in prior["rows"]} | merged
    out.write_text(json.dumps(
        {"curriculum": arm, "lessons": lessons, "floors": floors,
         "rows": [merged[k] for k in sorted(merged)]}, indent=1))
    print(f"\nwritten to {out} ({len(merged)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
