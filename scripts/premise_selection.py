"""The middle row: what the exact lookup scores when it must *choose* its premise.

``scripts/derived_split.py`` publishes both ends of a three-rung ladder on the
derived bucket of ``derive:wordnet``. The deduction is the same table in both:

* ``derivation_floor`` — 1.000. A lookup that was **told** which sibling is the
  kind, because :func:`~scripts.derived_split._positions` hands it ``ki``.
* its blind half — 0.167. The same lookup with the sibling term dropped.

The gap is 0.833 wide and it is *entirely premise selection*. This script runs
the rung between them, which nobody had: the same table, choosing for itself
which visible node to read. That is the residual CoTu ([arXiv:2607.14735])
claims is what remains once deduction is delegated to an exact solver.

Pre-registered in
``notes/decisions/2026-08-16-premise-selection-preregistration.md`` before the
number landed, because the two readings point in opposite directions.

Two things about how this is wired, both deliberate:

* **It writes its own JSON.** ``runs/*/derived_split.json`` holds 22 published
  model rows per arm that cannot be recomputed — the weights under ``runs/`` are
  untracked — so nothing here opens that file for writing.
* **No model is loaded, and none can be.** Only ``summary.json`` and
  ``rules.txt`` are tracked, so ``load_run`` cannot work at all. The config is
  rebuilt from ``summary["config"]`` and the tokenizer from
  :func:`build_tokenizer`, both pure functions of what is recorded. The gate on
  that is :func:`check_reconstruction`: the rebuilt population must reproduce the
  **published** floors bit for bit, or the run aborts. That check is the only
  reason any number here may be read.

    uv run python scripts/premise_selection.py runs/derive179-wordnet \\
                                               runs/derive179-perm
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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_split import (ARMS, DRAWS, N_EVAL, N_TRAIN, carrying_lessons,
                           derivation_floor, matched_episodes)

from symbolic_ai_models.tasks import make_task
from symbolic_ai_models.train import (TrainConfig, build_tokenizer, load_data)

#: Candidate scopes. ``siblings`` is the literal design in the question note --
#: the other children of the ``obj`` predicate, which is four nodes. ``graph``
#: is the faithful version of CoTu's problem: every visible node in the episode.
#: Reporting only the first would be the flattering half; see the
#: pre-registration.
SCOPES = ("siblings", "graph")

#: Dirichlet prior strengths the whole-graph row is re-scored at. A selector's
#: floor that moves with its own smoothing constant is a statement about the
#: constant, so the sensitivity is computed by *this* script rather than by a
#: scratch one -- the repo has twice had a scratch script contradict the
#: authority and flatter the write-up both times.
ALPHAS = (0.5, 1.0, 10.0, 100.0)


def _children(g, n: int) -> dict[int, list[int]]:
    kids: dict[int, list[int]] = collections.defaultdict(list)
    for i in range(n):
        p = g.parent[i]
        if 0 <= p < n:
            kids[p].append(i)
    return kids


def _candidates(g, n: int, vi: int, scope: str, hidden: set[int]) -> list[int]:
    """Visible nodes this selector is allowed to read for the fill at ``vi``.

    ``hidden`` is the draw's own mask, so the candidate set is what a model
    actually sees rather than what the unmasked graph holds -- the mistake
    ``MaskedNodeTask._nodes`` documents having made for a long time.
    """
    if scope == "graph":
        pool = range(n)
    else:
        p = g.parent[vi]
        pool = _children(g, n).get(p, ()) if 0 <= p < n else ()
    return [j for j in pool if j != vi and j not in hidden and g.labels[j]]


def fit_selector(train_pairs, scope: str) -> tuple[dict, list[str]]:
    """``label -> Counter(derived value)`` over training, for this scope.

    Training only (seeds ``0..19``), and the *whole* graph is visible when
    fitting: the knowledge base is complete, and it is the inference-time
    premise that has to be chosen. That is CoTu's setting, where the solver's
    facts exist and the question is which to hand over.
    """
    table: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter)
    values: collections.Counter = collections.Counter()
    for ep, pos in train_pairs:
        g = ep.graph
        n = len(g)
        kids = _children(g, n)
        for vi, _ki in pos:
            val = g.labels[vi]
            values[val] += 1
            if scope == "graph":
                pool = range(n)
            else:
                p = g.parent[vi]
                pool = kids.get(p, ()) if 0 <= p < n else ()
            for j in pool:
                if j != vi and g.labels[j]:
                    table[g.labels[j]][val] += 1
    return table, sorted(values)


def _score(counter, n_values: int, alpha: float = 1.0) -> float:
    """Evidence-shrunk mode probability: Dirichlet(alpha) posterior predictive.

    Without the shrinkage a once-seen label is perfectly peaked and gets picked
    over a kind label seen seventy times -- and the object-id sibling ``o0`` is
    a *systematically* spurious candidate, not a rare accident. A selector that
    cannot resist those is not a weak selector, it is a broken measurement of
    how hard selection is.
    """
    if not counter:
        return 1.0 / n_values
    total = sum(counter.values())
    return (max(counter.values()) + alpha) / (total + alpha * n_values)


def self_selected_floor(train_pairs, ev_pairs, tok, task, scope: str,
                        draws: int = DRAWS, alpha: float = 1.0
                        ) -> dict[str, float]:
    """The same lookup as ``derivation_floor``, choosing its own premise.

    Every filter is ``derivation_floor``'s, unchanged and in the same order, so
    the denominator is identical and the three rungs are one ladder. Note the
    ``ki in hidden`` guard is kept even though this row never uses ``ki``: the
    published rows are conditioned on the kind sibling being visible, and
    dropping the guard would score a different -- easier or harder, but
    different -- population.
    """
    table, values = fit_selector(train_pairs, scope)
    n_values = max(len(values), 1)
    # The blind fallback, identical to derivation_floor's: the commonest derived
    # value in training, used when the chosen candidate carries no evidence.
    overall: collections.Counter = collections.Counter()
    for ep, pos in train_pairs:
        for vi, _ki in pos:
            overall[ep.graph.labels[vi]] += 1
    blind_pred = overall.most_common(1)[0][0] if overall else None
    # Diagnostic, not part of the selector: the six labels that appear as a kind
    # anywhere in training. Separating "picked a useless label" from "picked a
    # useful label about the wrong object" is the whole mechanism claim, and it
    # has to come from the reporting script rather than a scratch one.
    kind_labels = {ep.graph.labels[ki] for ep, pos in train_pairs
                   for _vi, ki in pos}

    hit = {True: 0, False: 0}
    n = {True: 0, False: 0}
    picked_kind = {True: 0, False: 0}
    picked_a_kind_label = 0
    n_cand = 0
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
                cands = _candidates(g, nn, vi, scope, hidden)
                n_cand += len(cands)
                best_j, best_s = None, -1.0
                for j in cands:  # ties to the lowest node index
                    s = _score(table.get(g.labels[j]), n_values, alpha)
                    if s > best_s:
                        best_j, best_s = j, s
                counts = table.get(g.labels[best_j]) if best_j is not None else None
                pred = counts.most_common(1)[0][0] if counts else blind_pred
                n[copyable] += 1
                hit[copyable] += pred == g.labels[vi]
                picked_kind[copyable] += best_j == ki
                picked_a_kind_label += (best_j is not None
                                        and g.labels[best_j] in kind_labels)
    total = n[True] + n[False]
    div = lambda a, b: a / b if b else float("nan")
    return {
        f"self_{scope}_copyable": div(hit[True], n[True]),
        f"self_{scope}_not_copyable": div(hit[False], n[False]),
        f"self_{scope}_all": div(hit[True] + hit[False], total),
        f"self_{scope}_picked_kind": div(picked_kind[True] + picked_kind[False],
                                         total),
        # right *sort* of premise, whatever object it was about
        f"self_{scope}_picked_a_kind_label": div(picked_a_kind_label, total),
        f"self_{scope}_mean_candidates": div(n_cand, total),
        f"self_{scope}_n": float(total),
        # the headline is read on the not-copyable half, so its own n is the one
        # any interval on it has to use -- `dfloor_n` is the pooled count.
        f"self_{scope}_n_not_copyable": float(n[False]),
    }


def rebuild(arm_dir: Path) -> tuple[TrainConfig, object]:
    """Config and tokenizer from a tracked ``summary.json``, no weights needed."""
    runs = sorted(p for p in arm_dir.iterdir()
                  if (p / "summary.json").exists())
    if not runs:
        raise SystemExit(f"{arm_dir}: no run with a summary.json")
    summary = json.loads((runs[0] / "summary.json").read_text())
    cfg = TrainConfig.from_dict(summary["config"])
    train_eps, _ev = load_data(cfg)
    return cfg, build_tokenizer(cfg, train_eps)


def check_reconstruction(arm_dir: Path, floors: dict) -> str:
    """The published floors, or nothing here may be read.

    ``derived_split.json`` is tracked and holds the floors the 22 model rows were
    measured against. If a rebuilt config and tokenizer reproduce them exactly
    then the population, the masking draws and the scorable set are the published
    ones; if they do not, every number this script prints is about some other
    bucket. Exact equality, not a tolerance -- these are deterministic counts.
    """
    pub_path = arm_dir / "derived_split.json"
    if not pub_path.exists():
        return "no published derived_split.json to check against"
    pub = json.loads(pub_path.read_text())["floors"]
    bad = [(k, v, floors.get(k)) for k, v in pub.items()
           if floors.get(k) is None or abs(floors[k] - v) > 1e-12]
    if bad:
        raise SystemExit(
            f"{arm_dir}: rebuilt floors do not reproduce the published ones "
            f"{bad}; the population is not the one the published rows sit on")
    return f"reproduced {len(pub)} published floors exactly"


def run(arm_dir: Path) -> dict:
    cfg, tok = rebuild(arm_dir)
    lessons = carrying_lessons(ARMS, max_nodes=cfg.max_nodes)
    ev_pairs = matched_episodes(cfg.curriculum, ARMS, lessons, n=N_EVAL,
                                seed0=1_000_000, max_nodes=cfg.max_nodes)
    train_pairs = matched_episodes(cfg.curriculum, ARMS, lessons, n=N_TRAIN,
                                   seed0=0, max_nodes=cfg.max_nodes)
    task = make_task("node", mask_rate=cfg.mask_rate, max_nodes=cfg.max_nodes,
                     seed=cfg.seed)
    floors = derivation_floor(train_pairs, ev_pairs, tok, task)
    note = check_reconstruction(arm_dir, floors)
    out = dict(floors)
    for scope in SCOPES:
        out |= self_selected_floor(train_pairs, ev_pairs, tok, task, scope)
    sens = {str(a): self_selected_floor(train_pairs, ev_pairs, tok, task,
                                        "graph", alpha=a)["self_graph_not_copyable"]
            for a in ALPHAS}
    return {"arm": cfg.curriculum, "dir": str(arm_dir), "lessons": lessons,
            "reconstruction": note, "draws": DRAWS, "n_eval": N_EVAL,
            "n_train": N_TRAIN, "floors": out, "graph_alpha_sensitivity": sens}


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 1
    results = []
    for p in paths:
        r = run(Path(p))
        results.append(r)
        print(f"\n{r['arm']}  ({r['dir']})")
        print(f"  {r['reconstruction']}; "
              f"{len(r['lessons'])} carrying lessons, {r['draws']} draws")
        f = r["floors"]
        head = (f"  {'rung':<34}{'n':>7}{'acc|all':>9}{'acc|cp':>9}"
                f"{'acc|not cp':>12}{'right node':>12}{'a kind lbl':>12}"
                f"{'cands':>8}")
        print(head)
        print("  " + "-" * (len(head) - 2))
        print(f"  {'oracle premise (told the kind)':<34}{f['dfloor_n']:>7.0f}"
              f"{f['dfloor_all']:>9.3f}{f['dfloor_copyable']:>9.3f}"
              f"{f['dfloor_not_copyable']:>12.3f}{1.0:>12.3f}{1.0:>12.3f}"
              f"{1:>8.1f}")
        for scope in SCOPES:
            print(f"  {'self-selected (' + scope + ')':<34}"
                  f"{f[f'self_{scope}_n']:>7.0f}{f[f'self_{scope}_all']:>9.3f}"
                  f"{f[f'self_{scope}_copyable']:>9.3f}"
                  f"{f[f'self_{scope}_not_copyable']:>12.3f}"
                  f"{f[f'self_{scope}_picked_kind']:>12.3f}"
                  f"{f[f'self_{scope}_picked_a_kind_label']:>12.3f}"
                  f"{f[f'self_{scope}_mean_candidates']:>8.1f}")
        print(f"  {'blind (no premise)':<34}{f['dfloor_n']:>7.0f}"
              f"{f['blind_all']:>9.3f}{f['blind_copyable']:>9.3f}"
              f"{f['blind_not_copyable']:>12.3f}{0.0:>12.3f}{0.0:>12.3f}"
              f"{0:>8.1f}")
        print("  `right node` is the kind sibling of *this* object; `a kind "
              "lbl` is any of the six kind labels, about any object. The gap "
              "between those two columns is the whole mechanism.")
        print("  acc|not cp of the whole-graph rung against the selector's own "
              "Dirichlet prior: "
              + ", ".join(f"a={a} {v:.3f}"
                          for a, v in r["graph_alpha_sensitivity"].items()))
        out = Path(p) / "premise_selection.json"
        out.write_text(json.dumps(r, indent=1))
        print(f"  written to {out}")
    perm = next((r for r in results if r["arm"].endswith("-perm")), None)
    if perm:
        print("\nthe control decides whether the treatment may be read: in "
              "`-perm` the kind->value correspondence is redrawn per episode, so "
              "there is nothing to select for and every rung must sit at ~1/6. "
              "A self-selected row above the blind row *there* is a within-"
              "episode leak, not premise selection.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
