"""A grounded verdict paragraph for machine assignment.

The third instance of the grounding contract, and the one that tests a claim the
solvency finding left loose. Solvency showed the **contract** transfers while the
**mechanism** does not -- but solvency and scheduling both answer a **boolean**,
so the question here is whether the boolean contradiction check is reusable
*within an answer type*.

The domain-specific middle check -- route adjacency in flood, date validity in
solvency -- is **capability validity** here: every capability the paragraph names
must be one some machine or job actually mentions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from symbolic_ai_core.world import Quantity

from ..grounding import boolean_contradiction
from .surface import CAPABILITIES

__all__ = ["Answer", "render_answer", "ungrounded"]

_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_ENT = re.compile(r"\b(?:machine|job)_\d+\b")


@dataclass
class Answer:
    structured: bool = False
    text: str = ""


def _tables(case):
    caps: dict[str, set[str]] = {}
    hours: dict[str, float] = {}
    need: dict[str, str] = {}
    dur: dict[str, float] = {}
    for c in case.world.claims:
        v = c.roles.get("value")
        if c.predicate == "capacity":
            hours[c.roles["of"].id] = float(v.value)
        elif c.predicate == "duration":
            dur[c.roles["of"].id] = float(v.value)
        elif c.predicate == "has_capability":
            caps.setdefault(c.roles["machine"].id, set()).add(
                str(c.roles["capability"]))
        elif c.predicate == "needs_capability":
            need[c.roles["job"].id] = str(c.roles["capability"])
    return caps, hours, need, dur


def render_answer(case: Any, structured: bool) -> Answer:
    caps, hours, need, dur = _tables(case)
    demand = round(sum(dur.values()), 2)
    capacity = round(sum(hours.values()), 2)
    parts = ["Every job can be assigned." if structured
             else "The jobs cannot all be assigned."]
    parts.append(f" Total work is {demand:.2f} hours against {capacity:.2f} "
                 f"hours of capacity.")

    # An infeasible order fails for one of two reasons and the paragraph has to
    # say which: a capability nobody holds, or the hours not packing.
    if not structured:
        orphaned = sorted(j for j, c in need.items()
                          if not any(c in caps.get(m, ()) for m in hours))
        if orphaned:
            parts.append(" No machine is set up for the work "
                         + ", ".join(orphaned) + " requires.")
        else:
            tight = sorted(caps, key=lambda m: -hours.get(m, 0.0))[:1]
            parts.append(" Capability is available for every job, so the "
                         "constraint is time: the hours do not pack onto the "
                         "machines that can take them")
            if tight:
                parts.append(f", the largest being {tight[0]} at "
                             f"{hours.get(tight[0], 0.0):.2f} hours")
            parts.append(".")
    return Answer(structured=structured, text="".join(parts))


def ungrounded(answer: Answer, case: Any) -> list[str]:
    caps, hours, need, dur = _tables(case)
    known_nums = {f"{v:.2f}" for v in list(hours.values()) + list(dur.values())}
    known_nums.add(f"{round(sum(dur.values()), 2):.2f}")
    known_nums.add(f"{round(sum(hours.values()), 2):.2f}")
    known_ents = set(hours) | set(dur) | set(caps) | set(need)
    mentioned_caps = set(need.values()) | {c for s in caps.values() for c in s}

    # The shared check: identical to solvency's but for the verdict wording,
    # which is the evidence that the mechanism transfers within an answer type.
    bad: list[str] = list(boolean_contradiction(
        answer.text, answer.structured,
        yes="Every job can be assigned", no="cannot all be assigned"))
    for cap in CAPABILITIES:
        if re.search(rf"\b{cap}\b", answer.text) and cap not in mentioned_caps:
            bad.append(f"capability {cap} is named by no machine or job")
    for tok in _ENT.findall(answer.text):
        if tok not in known_ents:
            bad.append(f"entity {tok} is not on the floor")
    for tok in _NUM.findall(answer.text):
        if tok not in known_nums:
            bad.append(f"number {tok} appears in no claim")
    return bad
