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
COLUMNS = (
    ("lm", "token_bits", "bits/tok", "{:.3f}"),
    ("lm", "token_floor_bits", " floor", "{:.3f}"),
    ("lm", "token_acc", "tok acc", "{:.3f}"),
    ("node", "label_acc", "lbl acc", "{:.3f}"),
    ("node", "label_lift", "lbl lift", "{:.3f}"),
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


def comparison_table(summaries: Sequence[dict[str, Any]], sort_by: str = "lbl lift") -> str:
    """One row per run. Runs missing a task simply show ``-`` in its columns."""
    if not summaries:
        return "no finished runs found (a run writes summary.json when it completes)"
    rows = [run_row(s) for s in summaries]

    def key(r: dict[str, Any]) -> float:
        v = r.get(sort_by)
        return -v if isinstance(v, (int, float)) and v == v else float("inf")
    rows.sort(key=key)

    widths = {"run": 18, "model": 12, "params": 11, "tasks": 9}
    head = (f"{'run':<{widths['run']}}{'model':<{widths['model']}}"
            f"{'params':>{widths['params']}}  {'tasks':<{widths['tasks']}}")
    for _, _, label, _ in COLUMNS:
        head += f"{label:>10}"
    lines = [head, "-" * len(head)]
    for r in rows:
        line = (f"{r['run']:<{widths['run']}}{r['model']:<{widths['model']}}"
                f"{r['params']:>{widths['params']},}  {r['tasks']:<{widths['tasks']}}")
        for _, _, label, spec in COLUMNS:
            line += f"{_fmt(r.get(label), spec):>10}"
        lines.append(line)
    lines.append("-" * len(head))
    lines.append("lift = (score - floor) / (1 - floor); 0 is the prior, 1 is perfect")
    return "\n".join(lines)


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
