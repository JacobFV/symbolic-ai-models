"""``text -> reading`` for the solvency surface.

This domain had no committed reader: its "signature reader 1.000 at every V" was
measured by a script. The gap mattered once the signature-determinacy audit made
a **prediction** about solvency that needed checking — the audit says its
ambiguity mass is 0.000, so a reader should type every sentence from its shape
alone and interleaving should not touch it.

Two claim kinds, and their shapes do not collide:

- ``owns`` — two entities, no number, no date
- ``revenue`` — one entity, one number, one date

The covenant threshold and the determination date are **not claims**; they are
prose in the final paragraph, and the answer depends on both. They are read here
by shape too — a number with no entity is the threshold, a date with no entity is
the determination date — which is the same discipline and worth stating, because
the audit only sees claim spans and would not have flagged them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["Reading", "read_signature", "decide_reading"]

_ENTITY = re.compile(r"\bsub_\d+\b|\bgroup\b")
#: The parent is named ``group``, with NO number -- it does not follow the
#: ``name_number`` convention the other generators use. A regex requiring the
#: suffix silently drops every parent filing, which made an earlier version of
#: this reader answer False on all 60 cases and score 0.583: EXACTLY the
#: majority-class floor. The word also appears in prose ("the obligor group is
#: assessed"), which is harmless -- one entity with no number and no date
#: matches no branch and falls through.
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_LONG = re.compile(rf"\b(\d{{1,2}}) ({'|'.join(_MONTHS)}) (\d{{4}})\b")
_MONEY = re.compile(r"\b(\d+\.\d{2})\b")


def _dates(text: str) -> list[str]:
    """Every date in the sentence, normalised to ISO.

    The generator renders half its corpus as "1 June 2026". A reader keyed only
    to the ISO form would lose the date on those cases and read the day and the
    year as two more quantities.
    """
    out = [f"{y}-{m}-{d}" for y, m, d in _ISO.findall(text)]
    out += [f"{y}-{_MONTHS.index(mon) + 1:02d}-{int(d):02d}"
            for d, mon, y in _LONG.findall(text)]
    return out


@dataclass
class Reading:
    """What the reader recovered. Deliberately not a WorldSnapshot.

    Solvency has no flow graph, so the answer comes from the same bitemporal
    rule the oracle uses; the reading is the input to that rule.
    """

    members: set = field(default_factory=set)
    #: (entity, value, known_from), the same shape ``SolvencyCase.filings`` has
    filings: list = field(default_factory=list)
    threshold: float | None = None
    decision_date: str | None = None


def read_signature(text: str) -> Reading:
    """Type every sentence by its shape. No content word is consulted."""
    r = Reading()
    for sent in re.split(r"(?<=\.)\s+|(?<=\?)\s+", text.replace("\n\n", " ")):
        if not sent.strip():
            continue
        ents = list(dict.fromkeys(_ENTITY.findall(sent)))
        dates = _dates(sent)
        money = [float(m) for m in _MONEY.findall(sent)]
        if len(ents) == 2 and not money and not dates:
            r.members.update(ents)
        elif len(ents) == 1 and money and dates:
            r.members.add(ents[0])
            r.filings.append((ents[0], money[0], dates[0]))
        elif not ents and money and not dates:
            r.threshold = money[0]
        elif not ents and dates and not money:
            r.decision_date = dates[0]
    return r


def decide_reading(reading: Reading) -> bool | None:
    """The covenant verdict implied by a reading.

    For each member take the **latest** figure known on or before the
    determination date -- the most recent filing, not the largest one -- sum,
    and compare with the threshold. A reading missing the threshold or the date
    returns ``None`` rather than guessing: an unanswerable reading is not a
    negative answer, the same distinction the ASP kernel draws between
    unsatisfiable and unfinished.

    **This said "largest" and did the largest, which is a different rule.**
    Revisions here go down as well as up -- seed 69's group files 198.80 and
    then revises to 188.36 -- so the two disagree on 62 of 948 member-dates and
    flip the verdict on **9 of 400 cases**. It measured 1.000 over 60 seeds,
    which is too few to see a 2% error rate, and the tests used 30. Found while
    auditing a *different* bug class, which is the only reason it was found at
    all.
    """
    if reading.threshold is None or reading.decision_date is None:
        return None
    # Cents, for the same reason ``decide`` uses them: a sum compared with a
    # threshold needs exact arithmetic, and ``round(total, 2)`` does not supply
    # it -- rounding a sum that is already 1e-13 low can leave it low.
    cents = 0
    for m in reading.members:
        seen = [(k, v) for e, v, k in reading.filings
                if e == m and k <= reading.decision_date]
        if seen:
            # latest by DATE, not largest by value
            cents += int(round(max(seen)[1] * 100))
    return cents >= int(round(reading.threshold * 100))
