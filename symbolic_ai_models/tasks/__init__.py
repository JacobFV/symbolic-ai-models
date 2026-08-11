"""The two questions every model in this repo is asked.

Both are prediction of a hidden symbol out of one shared vocabulary, using one
shared output head. What differs is what surrounds the hidden symbol: the text
that precedes it, or the graph around it.
"""

from __future__ import annotations

from .base import Task, TaskOutput, Totals, bits, lift
from .lm import LanguageModelling
from .masked_node import MaskedNode

__all__ = ["Task", "TaskOutput", "Totals", "bits", "lift",
           "LanguageModelling", "MaskedNode", "TASKS", "make_task", "task_names"]

TASKS = {"lm": LanguageModelling, "node": MaskedNode}


def make_task(name: str, **kw) -> Task:
    try:
        cls = TASKS[name]
    except KeyError:
        raise KeyError(f"unknown task {name!r}; have {task_names()}") from None
    return cls(**kw)


def task_names() -> list[str]:
    return sorted(TASKS)
