"""Reading runs back out and putting them next to each other.

The counterpart of :mod:`symbolic_ai_models.report`, with one structural
difference: the columns are not fixed. A model run always answers the same two
questions, so that table can name its columns in advance; an agent run answers
whichever environments it was pointed at, so the columns are built from the
environments the summaries actually contain. A table of ``choice``-only runs is
narrow and a table of everything is wide, and neither invents a column of
dashes for something nobody ran.

Everything else is deliberately identical. Every return is printed with its
floor and its lift, lift is what the rows are sorted on, and
:func:`config_drift` warns when the rows of one table were not produced under
one config — because a comparison table's whole claim is that the rows differ
only in the agent, and nothing else enforces that.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["load_summaries", "comparison_table", "run_row", "config_drift",
           "environment_table"]

#: What is worth printing for each environment, in the order it belongs in.
#:
#: ``lift`` comes before ``ret`` on purpose. A return means nothing on its own —
#: ``retry`` pays ``1/tries`` and ``probe`` subtracts a cost, so the three
#: environments are not even on the same scale — while lift is the fraction of
#: the headroom above that environment's own floor, and is the only column that
#: can honestly be read across them.
PER_ENV = (
    ("return_lift", "lift", "{:+.3f}"),
    ("return", "ret", "{:.3f}"),
    ("success", "win", "{:.3f}"),
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


def environments_in(summaries: Sequence[dict[str, Any]]) -> list[str]:
    """Every environment any row was scored on, in registry order where known."""
    seen: set[str] = set()
    for s in summaries:
        seen.update((s.get("final") or {}).keys())
    from .envs import env_names
    known = [n for n in env_names() if n in seen]
    return known + sorted(seen - set(known))


def run_row(summary: dict[str, Any], envs: Sequence[str]) -> dict[str, Any]:
    final = summary.get("final") or {}
    row: dict[str, Any] = {
        "run": Path(summary.get("_run", "?")).name,
        "agent": summary.get("agent", "?"),
        "params": summary.get("parameters", 0),
    }
    for env in envs:
        metrics = final.get(env, {})
        for key, label, _ in PER_ENV:
            row[f"{env} {label}"] = metrics.get(key)
    return row


def _fmt(value: Any, spec: str) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and value != value:      # NaN
        return "-"
    return spec.format(value) if isinstance(value, (int, float)) else str(value)


def comparison_table(summaries: Sequence[dict[str, Any]],
                     sort_by: str | None = None) -> str:
    """One row per run, one block of columns per environment."""
    if not summaries:
        return ("no finished runs found (a run writes summary.json when it "
                "completes)")
    envs = environments_in(summaries)
    rows = [run_row(s, envs) for s in summaries]
    sort_key = sort_by or (f"{envs[0]} lift" if envs else "agent")

    def key(r: dict[str, Any]) -> float:
        v = r.get(sort_key)
        return -v if isinstance(v, (int, float)) and v == v else float("inf")
    rows.sort(key=key)

    head = f"{'agent':<14}{'params':>11}  "
    for env in envs:
        head += f"|{env:^{10 * len(PER_ENV) - 1}}"
    lines = [head]
    sub = f"{'':<14}{'':>11}  "
    for _ in envs:
        sub += "|" + "".join(f"{label:>10}" for _, label, _ in PER_ENV)[1:]
    lines.append(sub)
    lines.append("-" * len(head))
    for r in rows:
        line = f"{r['agent']:<14}{r['params']:>11,}  "
        for env in envs:
            line += "|" + "".join(
                f"{_fmt(r.get(f'{env} {label}'), spec):>10}"
                for _, label, spec in PER_ENV)[1:]
        lines.append(line)
    lines.append("-" * len(head))
    lines.append("lift = (return - floor) / (1 - floor); 0 is the floor, 1 is "
                 "perfect. It is the only column comparable across environments "
                 "-- returns are not on one scale (retry pays 1/tries, probe "
                 "subtracts a cost).")
    lines.append("the floor is the best of random / shortcut / context, run in "
                 "that environment. Those three are registered agents too, so "
                 "each has zero lift wherever it is the winning floor -- that "
                 "row is the baseline, not a result.")
    lines.extend(floor_note(summaries, envs))
    lines.extend(config_drift(summaries))
    return "\n".join(lines)


def floor_note(summaries: Sequence[dict[str, Any]],
               envs: Sequence[str]) -> list[str]:
    """Name which cheat won each environment's floor.

    *Which* one wins says what leaked — ``recency`` means answers sit in the
    prompt, ``odd_one_out`` means the distractors are built by a different
    recipe than the answer. That is a fact about the lessons and it belongs
    under the table rather than inside a single floor number.
    """
    named: dict[str, set[str]] = {}
    for s in summaries:
        for env in envs:
            by = ((s.get("final") or {}).get(env) or {}).get("floor_by")
            if by:
                named.setdefault(env, set()).add(str(by))
    if not named:
        return []
    parts = ", ".join(f"{env}: {'/'.join(sorted(v))}" for env, v in sorted(named.items()))
    return ["", f"floor set by -- {parts}"]


#: What every row must agree on: the episodes and the shape of the environments.
#: An agent evaluated on different lessons, a different mask rate or a different
#: probe cost is answering a different question.
COMPARABLE = ("lessons", "n_train", "n_eval", "language", "seed", "vocab_size",
              "max_nodes", "envs", "tries", "mask_rate", "max_steps",
              "max_actions", "probe_cost", "max_probes")


def config_drift(summaries: Sequence[dict[str, Any]]) -> list[str]:
    """Warn when rows in one table were produced under different configs.

    Written because the model harness needed it: ``configs/full179.toml`` did
    not pin ``d_model``, so a partial re-run silently trained models 2.7x wider
    into a directory whose other rows were narrower, and the drifted rows
    printed looking exactly like the rest. The same failure is available here
    and is cheaper to hit — ``probe_cost`` alone decides whether probing can
    ever pay.

    Warning rather than raising: the numbers are real and a reader may well want
    them, and a sweep that dies at the last line after hours of work is a worse
    failure than the one being reported.
    """
    if len(summaries) < 2:
        return []
    drifted: list[str] = []
    for key in COMPARABLE:
        seen: dict[str, list[str]] = {}
        for s in summaries:
            cfg = s.get("config") or {}
            if key not in cfg:
                continue
            seen.setdefault(repr(cfg[key]), []).append(str(s.get("agent", "?")))
        if len(seen) > 1:
            groups = "; ".join(f"{v}={', '.join(sorted(m))}"
                               for v, m in sorted(seen.items()))
            drifted.append(f"  {key}: {groups}")
    if not drifted:
        return []
    return ["", "!! these rows were NOT produced under one config, so the "
            "comparison is not like-for-like:"] + drifted


def environment_table(summary: dict[str, Any]) -> str:
    """One run in full: every metric of every environment it was scored on.

    The comparison table keeps three columns per environment because a table
    twelve wide is unreadable; this is where the rest lives — how many nodes
    ``repair`` found recoverable, how many segments ``probe`` bought, how often it
    answered at all.
    """
    final = summary.get("final") or {}
    if not final:
        return "no metrics in this summary"
    lines = [f"=== {summary.get('agent', '?')} "
             f"({summary.get('parameters', 0):,} learned) ==="]
    for env, metrics in sorted(final.items()):
        lines.append(f"\n{env}")
        for key, value in sorted(metrics.items()):
            lines.append(f"  {key:<20}{_fmt(value, '{:.4f}')}")
    return "\n".join(lines)
