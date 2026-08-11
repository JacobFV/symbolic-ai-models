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
    ("node", "label_coverage", "lbl cov", "{:.2f}"),
    ("node", "type_acc", "typ acc", "{:.3f}"),
    ("node", "type_lift", "typ lift", "{:.3f}"),
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
    lines.append("lift = (score - floor) / (1 - floor); 0 is the prior, 1 is perfect")
    lines.append("params: neural = tensor weights, rule-based = discrete rules "
                 "and counts. The two are not comparable and are not meant to be.")
    lines.append("ans = the answer span alone (~1.4% of positions); tok = all of "
                 "them, so tok lift is mostly boilerplate. lbl cov = share of "
                 "masked labels the vocabulary can name and the score covers.")
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

#: `steps` is deliberately absent from both: a rule-based model fits in one pass
#: and reports 0, so a mixed table always disagrees and always would.


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
