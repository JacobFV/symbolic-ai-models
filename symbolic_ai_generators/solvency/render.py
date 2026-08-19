"""A grounded verdict paragraph for the covenant test — and it has to cite dates.

`symbolic_ai_generators/flood/render.py` established the contract: the structured
answer is canonical, the paragraph is strictly downstream, and an unsupported or
contradictory assertion is caught mechanically. This is that contract on a
structurally opposite task, which is the test of whether it generalises.

**The explanation here is bitemporal.** A covenant does not fail because a number
is small; it fails because a figure was **not knowable** at the decision date. So
the paragraph has to say

    sub_3's only return is dated 2026-06-01, after the 2026-05-30
    determination, so it could not be counted.

and that is the first explanation in this repo that must cite a **date** rather
than a value. It is exactly what ``transaction_time`` is for.

`ungrounded` therefore checks three things, mirroring the flood renderer:

* every number and entity asserted appears in a claim,
* every date asserted is a filing date or the decision date,
* the verdict asserted **agrees with the structured answer** -- a paragraph that
  says the covenant was met when the decision says otherwise is caught, which is
  the check the whole reasoning/generation separation depends on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from symbolic_ai_core.world import Quantity

from ..grounding import boolean_contradiction

__all__ = ["Citation", "Answer", "render_answer", "ungrounded"]

_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_ENT = re.compile(r"\b(?:group|sub_\d+)\b")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


@dataclass(frozen=True)
class Citation:
    start: int
    end: int
    source: str


@dataclass
class Answer:
    #: the canonical verdict, exactly as the kernel returned it
    structured: bool = False
    text: str = ""
    citations: tuple[Citation, ...] = ()


class _Para:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.cites: list[Citation] = []
        self._n = 0

    def say(self, text: str, source: str | None = None) -> None:
        start = self._n
        self.parts.append(text)
        self._n += len(text)
        if source:
            self.cites.append(Citation(start, self._n, source))

    def glue(self, text: str) -> None:
        self.parts.append(text)
        self._n += len(text)

    def text(self) -> str:
        return "".join(self.parts)


def render_answer(case: Any, structured: bool) -> Answer:
    """A verdict paragraph that explains itself by date, not only by value."""
    as_of = case.decision_date
    p = _Para()

    usable: dict[str, tuple[float, str]] = {}
    excluded: dict[str, tuple[float, str]] = {}
    for member in case.members:
        seen = [(v, k) for e, v, k in case.filings if e == member]
        known = [(v, k) for v, k in seen if k <= as_of]
        if known:
            usable[member] = max(known, key=lambda pair: pair[1])
        elif seen:
            excluded[member] = min(seen, key=lambda pair: pair[1])

    total = round(sum(v for v, _ in usable.values()), 2)
    p.say("The covenant was met." if structured
          else "The covenant was not met.", "kernel:verdict")
    p.glue(" On the information available at ")
    p.say(as_of, "case:decision_date")
    p.glue(", consolidated revenue was ")
    p.say(f"{total:.2f}", "derived:sum_of_usable_filings")
    p.glue(" USD against a requirement of ")
    p.say(f"{case.threshold:.2f}", "case:threshold")
    p.glue(" USD. ")

    if excluded:
        p.glue("Excluded as not yet knowable: ")
        for n, (member, (value, when)) in enumerate(sorted(excluded.items())):
            if n:
                p.glue("; ")
            p.say(member, f"claim:revenue.{member}")
            p.glue(" filed ")
            p.say(f"{value:.2f}", f"claim:revenue.{member}")
            p.glue(" USD dated ")
            p.say(when, f"claim:revenue.{member}.transaction_time")
            p.glue(", after the determination")
        p.glue(". ")

    revised = [m for m in usable
               if len([1 for e, _, k in case.filings
                       if e == m and k <= as_of]) > 1]
    if revised:
        p.glue("Restated before the determination and counted at the later "
               "figure: ")
        for n, member in enumerate(sorted(revised)):
            if n:
                p.glue(", ")
            p.say(member, f"claim:revenue.{member}")
        p.glue(". ")

    return Answer(structured=structured, text=p.text(),
                  citations=tuple(p.cites))


def ungrounded(answer: Answer, case: Any) -> list[str]:
    """Assertions nothing supports, including a verdict that disagrees."""
    known_nums = {f"{case.threshold:.2f}"}
    known_dates = {case.decision_date}
    known_ents = set(case.members)
    for member, value, when in case.filings:
        known_nums.add(f"{value:.2f}")
        known_dates.add(when)
        known_ents.add(member)
    for c in case.world.claims:
        v = c.roles.get("value")
        if isinstance(v, Quantity):
            known_nums.add(f"{float(v.value):.2f}")
    # the derived total is a legitimate assertion the kernel computed
    usable = []
    for member in case.members:
        known = [(v, k) for e, v, k in case.filings
                 if e == member and k <= case.decision_date]
        if known:
            usable.append(max(known, key=lambda pair: pair[1])[0])
    known_nums.add(f"{round(sum(usable), 2):.2f}")

    # The check the whole separation depends on. Shared with scheduling: the
    # only domain-specific part is the pair of verdict phrases.
    bad: list[str] = list(boolean_contradiction(
        answer.text, answer.structured,
        yes="covenant was met", no="covenant was not met"))
    for tok in _DATE.findall(answer.text):
        if tok not in known_dates:
            bad.append(f"date {tok} is neither a filing date nor the "
                       f"determination date")
    for tok in _ENT.findall(answer.text):
        if tok not in known_ents:
            bad.append(f"entity {tok} is not in the group")
    # Dates are scanned separately above, so they must be removed before the
    # number scan -- otherwise every date contributes three spurious "numbers"
    # (2026, 05, 30) and the checker flags every paragraph. It did: 0/60.
    without_dates = _DATE.sub(" ", answer.text)
    for tok in _NUM.findall(without_dates):
        if tok not in known_nums:
            bad.append(f"number {tok} appears in no claim")
    return bad
