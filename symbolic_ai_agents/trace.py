"""Trajectories as something to read. Feeds no metric.

The counterpart of :mod:`symbolic_ai_models.decode`, and it has the same status:
it is for a person or a reviewing model to look at, and nothing here is ever
reported as a result. That separation is worth keeping strict — a transcript is
selected, and a number is not.

It earns its place more here than decoded samples do there, because an agent's
failure has a *shape*. "0.31 return on repair" says nothing about whether the
agent filled the first node wrongly and then followed its own mistake, or filled
eight nodes independently and got five. The transcript shows which, and that
distinction is the entire reason this package exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["read_trajectories", "transcript", "one"]


def read_trajectories(path: str | Path, *, env: str | None = None,
                      lesson: str | None = None) -> list[dict[str, Any]]:
    """Read ``trajectories.jsonl``, optionally filtered."""
    out = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if env and row.get("env") != env:
                continue
            if lesson and row.get("lesson_id") != lesson:
                continue
            out.append(row)
    return out


def one(traj: dict[str, Any], *, show_observation: bool = True) -> str:
    """One trajectory, step by step."""
    head = (f"=== {traj['env']}  {traj['lesson_id']}  {traj['instance_id']}  "
            f"return {traj['return']:+.3f}  "
            f"{'solved' if traj['solved'] else 'not solved'}")
    lines = [head]
    for i, move in enumerate(traj.get("moves", [])):
        if show_observation:
            body = "\n".join(f"    | {ln}" for ln in move["text"].splitlines())
            lines.append(f"  [{i}] saw:\n{body}")
            offered = move.get("actions") or []
            if offered:
                shown = ", ".join(repr(a) for a in offered[:8])
                extra = f" (+{len(offered) - 8} more)" if len(offered) > 8 else ""
                lines.append(f"      options: {shown}{extra}")
            if move.get("probes"):
                lines.append(f"      probes:  {', '.join(move['probes'][:6])}")
        mark = {True: "OK", False: "XX", None: "--"}[move.get("correct")]
        lines.append(f"  [{i}] did: {move['action']!r}  "
                     f"conf {move['confidence']:.2f}  "
                     f"reward {move['reward']:+.3f}  [{mark}]  "
                     f"{move.get('feedback', '')}")
    return "\n".join(lines)


def transcript(trajectories: Sequence[dict[str, Any]], *, limit: int = 10,
               show_observation: bool = True) -> str:
    """Several trajectories, with a note saying how many were left out.

    The count is printed rather than dropped silently. A transcript that shows
    ten of four thousand and does not say so reads as coverage, which is the
    same failure a silently truncated sweep is.
    """
    shown = list(trajectories)[:limit]
    parts = [one(t, show_observation=show_observation) for t in shown]
    if len(trajectories) > limit:
        parts.append(f"... {len(trajectories) - limit} more trajectories "
                     f"(this is a sample to read, not a measurement)")
    return "\n\n".join(parts)


def worst(trajectories: Iterable[dict[str, Any]], limit: int = 10
          ) -> list[dict[str, Any]]:
    """The lowest-return trajectories — where a policy is worth looking at.

    Reading the successes tells you what an agent does when it is right, which
    is rarely the interesting half.
    """
    return sorted(trajectories, key=lambda t: t.get("return", 0.0))[:limit]
