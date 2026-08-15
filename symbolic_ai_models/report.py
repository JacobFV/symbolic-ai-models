"""Reading runs back out and putting them next to each other.

A comparison table is the actual output of this repo, so it gets its own module
rather than being formatted inline in the CLI. Every accuracy is printed with
its floor and its lift, and lift is what the rows are sorted on — an
architecture that reaches 0.71 on node types where the floor is 0.70 has done
nothing, and a table that sorts on accuracy would put it at the top.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["load_summaries", "comparison_table", "run_row", "history_table"]

#: The metrics worth putting in a comparison, in the order they belong in.
#:
#: ``ans`` comes before ``tok`` on purpose. Only about 1.4% of scored
#: language-modelling positions are the answer; the rest is the question and the
#: fixed scaffolding around it, and a model can hold a large ``tok lift`` purely
#: by reproducing boilerplate. The answer columns are the ones that say whether
#: anything was understood, so they are read first.
COLUMNS = (
    ("lm", "answer_acc", "ans acc", "{:.3f}"),
    ("lm", "answer_lift", "ans lift", "{:.3f}"),
    ("lm", "token_bits", "bits/tok", "{:.3f}"),
    ("lm", "token_lift", "tok lift", "{:.3f}"),
    ("node", "label_acc", "lbl acc", "{:.3f}"),
    ("node", "label_lift", "lbl lift", "{:.3f}"),
    # Next to the accuracy lift, never instead of it. These two rank the models
    # close to inversely and the repo quoted only the first for its whole
    # history; printing them side by side is what stops the next ranking from
    # silently being about the metric rather than about the models.
    ("node", "label_bits_lift", "lbl bits", "{:.3f}"),
    ("node", "label_coverage", "lbl cov", "{:.2f}"),
    ("node", "type_acc", "typ acc", "{:.3f}"),
    ("node", "type_lift", "typ lift", "{:.3f}"),
    # The two readouts nothing used to be scored on. Blank for a model that
    # emits neither channel, which is the honest cell for "cannot point" and is
    # not the same cell as a zero. `site` is attachment on the text surface and
    # `copy` is binding on the graph; both are pointer questions and both are
    # invisible in an accuracy over the vocabulary, which is what every column
    # to the left of them is.
    ("node", "copy_acc", "cpy acc", "{:.3f}"),
    ("lm", "site_acc", "site acc", "{:.3f}"),
    ("lm", "site_lift", "site lift", "{:.3f}"),
)

#: The infilling variants print the same graph columns under their own task
#: name, so one table can hold a `node` row and a `nodeans` row without either
#: being read as the other. `copy_ceiling` is in here and not above because it
#: is the number that moves *mechanically* with the mask rate — masking removes
#: the visible same-label nodes a pointer needs — and a pointer column quoted
#: without it is quoting the harness.
COLUMNS = COLUMNS + tuple(
    (task, key, f"{short} {label}", fmt)
    for task, short in (("nodesub", "sub"), ("nodeans", "ans"),
                        ("nodeans1", "an1"))
    for key, label, fmt in (
        ("label_acc", "acc", "{:.3f}"),
        ("label_lift", "lift", "{:.3f}"),
        ("type_lift", "typ", "{:.3f}"),
        ("copy_acc", "cpy", "{:.3f}"),
        ("copy_ceiling", "ceil", "{:.3f}"),
    )
) + tuple(
    (task, key, f"{short} {label}", fmt)
    for task, short in (("nodeans", "ansnd"), ("nodeans1", "an1nd"))
    for key, label, fmt in (("ansnode_acc", "acc", "{:.3f}"),
                            ("ansnode_lift", "lift", "{:.3f}"),
                            ("ansnode_coverage", "cov", "{:.2f}"))
)


def load_summaries(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    """Read ``summary.json`` from each run directory, skipping unfinished ones."""
    out = []
    for p in paths:
        f = Path(p) / "summary.json" if Path(p).is_dir() else Path(p)
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        data["_run"] = str(Path(f).parent)
        out.append(data)
    return out


def run_row(summary: dict[str, Any]) -> dict[str, Any]:
    final = summary.get("final") or {}
    row: dict[str, Any] = {
        "run": Path(summary.get("_run", "?")).name,
        "model": summary.get("model", "?"),
        "family": summary.get("family", "neural"),
        "params": summary.get("parameters", 0),
        "tasks": ",".join(summary.get("config", {}).get("tasks", [])),
    }
    for task, key, label, _ in COLUMNS:
        row[label] = final.get(task, {}).get(key)
    return row


def _fmt(value: Any, spec: str) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and value != value:      # NaN
        return "-"
    return spec.format(value) if isinstance(value, (int, float)) else str(value)


def comparison_table(summaries: Sequence[dict[str, Any]], sort_by: str = "ans lift") -> str:
    """One row per run. Runs missing a task simply show ``-`` in its columns."""
    if not summaries:
        return "no finished runs found (a run writes summary.json when it completes)"
    rows = [run_row(s) for s in summaries]

    def key(r: dict[str, Any]) -> float:
        v = r.get(sort_by)
        return -v if isinstance(v, (int, float)) and v == v else float("inf")
    rows.sort(key=key)

    widths = {"model": 13, "family": 12, "params": 11, "tasks": 9}
    head = (f"{'model':<{widths['model']}}{'family':<{widths['family']}}"
            f"{'params':>{widths['params']}}  {'tasks':<{widths['tasks']}}")
    for _, _, label, _ in COLUMNS:
        head += f"{label:>10}"
    lines = [head, "-" * len(head)]
    for r in rows:
        line = (f"{r['model']:<{widths['model']}}{r['family']:<{widths['family']}}"
                f"{r['params']:>{widths['params']},}  {r['tasks']:<{widths['tasks']}}")
        for _, _, label, spec in COLUMNS:
            line += f"{_fmt(r.get(label), spec):>10}"
        lines.append(line)
    lines.append("-" * len(head))
    # Which curriculum, printed whenever it is not the default or the table
    # mixes more than one. A score is comparable only to a score drawn from the
    # same curriculum, and a table that silently pools two of them is the
    # `symbolic_ai_core/registry.py` failure with a new way in: every published
    # number here is defined on `base`, and `kg:*` rows are a different corpus
    # wearing the same model names.
    curricula = sorted({(s.get("config") or {}).get("curriculum", "base")
                        for s in summaries})
    if curricula != ["base"]:
        lines.append("curriculum: " + ", ".join(curricula)
                     + ("   <- MIXED. These rows are not comparable to each "
                        "other; a floor and a copy ceiling are properties of a "
                        "curriculum." if len(curricula) > 1 else
                        "   (not `base`: not comparable to any published number)"))
    lines.append("lift = (score - floor) / (1 - floor); 0 is the prior, 1 is perfect")
    lines.append("params: neural = tensor weights, rule-based = discrete rules "
                 "and counts. The two are not comparable and are not meant to be.")
    lines.append("ans = the answer span alone (~1.4% of positions); tok = all of "
                 "them, so tok lift is mostly boilerplate. lbl cov = share of "
                 "masked labels the vocabulary can name and the score covers.")
    lines.append("cpy = binding on the graph (which node says it); site = "
                 "attachment on the text (which read word is the head). Both "
                 "are pointer questions and both are invisible in every column "
                 "to their left. A blank is a model that emits no such channel "
                 "-- unscored, which is not the same cell as zero.")
    rename = [(s.get("model", "?"), (s.get("renaming") or {}))
              for s in summaries if (s.get("renaming") or {}).get("drop") is not None]
    if rename:
        lines.append("")
        lines.append("renaming (fitted on the original episodes, scored on permuted ones):")
        for name, r in sorted(rename, key=lambda t: t[1]["drop"]):
            lines.append(f"  {name:<14}{r['label_acc']:.3f} -> "
                         f"{r['renamed_label_acc']:.3f}   {-r['drop']:+.3f}")
    lines.extend(config_drift(summaries))
    return "\n".join(lines)


#: What every row must agree on: the data and the task. A model evaluated on
#: different lessons, a different mask rate or a different split is answering a
#: different question whatever family it belongs to.
COMPARABLE_DATA = ("vocab_size", "max_len", "max_nodes", "mask_rate", "lessons",
                   "n_train", "n_eval", "language", "seed")

#: Network shape, checked only among neural rows. A rule-based model records
#: `d_model` because it shares one config object, and has no tensors to apply it
#: to -- flagging those rows would fire on every mixed table and teach the
#: reader to skip the warning, which is how a warning stops working.
COMPARABLE_SHAPE = ("d_model", "n_layers", "n_heads", "d_ff")

#: `steps` is absent from both because a rule-based model fits in one pass and
#: reports 0, so a mixed table always disagrees. It is checked separately among
#: neural rows, where an unequal budget is exactly the confound this repo spent
#: several days on: 300 steps put every network below the floor and 2000 put the
#: first one above it, and a half-finished re-run leaves both kinds of row in
#: one directory looking identical.


def config_drift(summaries: Sequence[dict[str, Any]]) -> list[str]:
    """Warn when rows in one table were produced under different configs.

    A comparison table's whole claim is that the rows differ only in the model.
    Nothing enforced that. `configs/full179.toml` did not pin `d_model`, whose
    default is 256, so a re-run of part of a sweep silently trained models 2.7x
    wider into a directory whose other rows were built at 96 -- and the drifted
    rows would have printed in this table looking exactly like the rest, because
    the config is recorded per run and never compared across them.

    Warning rather than raising: the numbers are real and a reader may well want
    them, and a sweep that dies at the last line after hours of work would be a
    worse failure than the one being reported.
    """
    if len(summaries) < 2:
        return []
    neural = [s for s in summaries if s.get("family") == "neural"]
    drifted: list[str] = []
    # Read from the summary's own `steps`, not `config.steps`: the config records
    # what was asked for and this records what ran, and a run killed part-way is
    # precisely the case worth catching.
    # The floor is the other half of every lift, and it changes when the floor
    # *code* changes, not just when a config does. Strengthening the type floor
    # moved it 0.795 -> 0.860, which silently rescales every row not re-run
    # against it -- the same failure as a stale step budget, in the denominator.
    floors: dict[str, list[str]] = {}
    for s in summaries:
        node = (s.get("floors") or {}).get("node") or {}
        if node:
            key = repr(tuple(round(float(node.get(k, float("nan"))), 6)
                             for k in ("label_acc", "type_acc")))
            floors.setdefault(key, []).append(str(s.get("model", "?")))
    if len(floors) > 1:
        groups = "; ".join(f"{v}={', '.join(sorted(m))}"
                           for v, m in sorted(floors.items()))
        drifted.append(f"  floors: {groups}")

    budgets: dict[str, list[str]] = {}
    for s in neural:
        if "steps" in s:
            budgets.setdefault(repr(s["steps"]), []).append(str(s.get("model", "?")))
    if len(budgets) > 1:
        groups = "; ".join(f"{v}={', '.join(sorted(m))}"
                           for v, m in sorted(budgets.items()))
        drifted.append(f"  steps: {groups}")
    for key, rows in ([(k, summaries) for k in COMPARABLE_DATA]
                      + [(k, neural) for k in COMPARABLE_SHAPE]):
        if len(rows) < 2:
            continue
        seen: dict[str, list[str]] = {}
        for s in rows:
            cfg = s.get("config") or {}
            if key not in cfg:
                continue
            seen.setdefault(repr(cfg[key]), []).append(str(s.get("model", "?")))
        if len(seen) > 1:
            groups = "; ".join(f"{v}={', '.join(sorted(m))}"
                               for v, m in sorted(seen.items()))
            drifted.append(f"  {key}: {groups}")
    if not drifted:
        return []
    return ["", "!! these rows were NOT produced under one config, so the "
            "comparison is not like-for-like:"] + drifted


def history_table(run_dir: str | Path) -> str:
    """The eval curve of one run, step by step."""
    f = Path(run_dir) / "history.json"
    if not f.exists():
        return f"no history at {f}"
    history = json.loads(f.read_text(encoding="utf-8"))
    head = f"{'step':>7}{'lm loss':>10}{'node loss':>11}"
    for _, _, label, _ in COLUMNS:
        head += f"{label:>10}"
    lines = [head, "-" * len(head)]
    for h in history:
        line = (f"{h['step']:>7}{_fmt(h['train_loss'].get('lm'), '{:.3f}'):>10}"
                f"{_fmt(h['train_loss'].get('node'), '{:.3f}'):>11}")
        for task, key, label, spec in COLUMNS:
            line += f"{_fmt(h['eval'].get(task, {}).get(key), spec):>10}"
        lines.append(line)
    return "\n".join(lines)
