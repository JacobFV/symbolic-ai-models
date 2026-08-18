"""Generating a group, its subsidiaries, and the revisions to their filings.

Pure in the seed, like every generator here. The revision model is deliberately
mild — most figures are never revised, and those that are move by single-digit
percentages — because the interesting claim is that even a mild revision process
flips a non-trivial share of decisions, and an aggressive one would prove nothing
except that the generator was built to.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any

from symbolic_ai_core.artifact.value import Interval
from symbolic_ai_core.world import (Claim, Entity, EntityRef, Facet, Quantity,
                                    WorldSnapshot)

__all__ = ["SolvencyCase", "generate", "decide", "REVISION_RATE"]

#: Share of filings that get revised at least once. Mild on purpose.
REVISION_RATE = 0.35
#: A revision moves the figure by this much, as a fraction, either way.
REVISION_SIZE = (0.02, 0.09)
#: Days after period end that a first filing appears, and a revision after that.
FIRST_FILING_DAYS = (30, 75)
REVISION_DAYS = (60, 200)

PERIOD = "2026Q1"
PERIOD_END = "2026-03-31"


@dataclass(frozen=True)
class SolvencyCase:
    seed: int
    world: WorldSnapshot
    group: str
    members: tuple[str, ...]
    threshold: float
    decision_date: str
    #: (entity, value, known_from) for every filing and revision
    filings: tuple[tuple[str, float, str], ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)


def _rng(seed: int) -> random.Random:
    h = hashlib.blake2b(f"solvency|{seed}".encode(), digest_size=8)
    return random.Random(int.from_bytes(h.digest(), "big"))


def _day(offset: int) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(PERIOD_END) + timedelta(days=offset)).isoformat()


def generate(seed: int, *, n_subs: int = 4) -> SolvencyCase:
    """One group, its filings, and a decision date somewhere in the middle."""
    r = _rng(seed)
    group = "group"
    subs = tuple(f"sub_{i}" for i in range(n_subs))
    members = (group,) + subs

    filings: list[tuple[str, float, str]] = []
    first_total = final_total = 0.0
    for m in members:
        base = round(r.uniform(40.0, 260.0), 2)
        first = _day(r.randint(*FIRST_FILING_DAYS))
        filings.append((m, base, first))
        first_total += base
        final = base
        if r.random() < REVISION_RATE:
            frac = r.uniform(*REVISION_SIZE) * r.choice((-1.0, 1.0))
            final = round(base * (1.0 + frac), 2)
            filings.append((m, final, _day(r.randint(*REVISION_DAYS))))
        final_total += final

    # The covenant bar is set from the FIRST-VINTAGE total, not the final one.
    # A lender writes the covenant against the figures on the table, and drawing
    # it from the revised total would put look-ahead into the generator of a
    # task about look-ahead -- the threshold would know which way the revisions
    # went. Close on purpose: a bar nobody is near flips on no revision at all
    # and would make the whole measurement report zero for the wrong reason.
    threshold = round(first_total * r.uniform(0.94, 1.06), 2)
    # Spans the regime where filings are still arriving (first filings land at
    # +30..+75d) as well as the one where they have all landed. A range starting
    # after the last first-filing would only ever exercise the REVISION half of
    # look-ahead, and revision turns out to be the smaller half by a factor of
    # five -- see the finding.
    decision_date = _day(r.randint(45, 190))

    ents = {m: Entity(m, types=("actor",),
                      facets={"economy.actor": Facet("economy.actor",
                                                     {"name": m})})
            for m in members}
    claims: list[Claim] = [
        Claim("owns", {"parent": EntityRef(group), "child": EntityRef(s)})
        for s in subs]
    for m, v, known in filings:
        claims.append(Claim(
            "revenue", {"of": EntityRef(m), "value": Quantity(v, "USD")},
            valid_time=Interval(PERIOD, PERIOD),
            transaction_time=Interval(known, known)))

    return SolvencyCase(
        seed=seed, world=WorldSnapshot(entities=ents, claims=tuple(claims)),
        group=group, members=members, threshold=threshold,
        decision_date=decision_date, filings=tuple(filings),
        meta={"n_filings": len(filings), "n_revised": len(filings) - len(members),
              "first_total": round(first_total, 2),
              "final_total": round(final_total, 2)})


def decide(case: SolvencyCase, *, as_of: str) -> tuple[bool, float, bool]:
    """``(cleared, total, complete)`` for the covenant, as known on ``as_of``.

    Computed here by direct search over the filings so it is **independent of
    the kernel** it is used to check — an oracle that shared the kernel's code
    would agree with it by construction.
    """
    total = 0.0
    complete = True
    for m in case.members:
        seen = [(v, k) for e, v, k in case.filings if e == m and k <= as_of]
        if not seen:
            complete = False
            continue
        total += max(seen, key=lambda p: p[1])[0]
    return total >= case.threshold, round(total, 2), complete


# ---------------------------------------------------------------------------
# controlled corruption, to ask whether the flood task's mechanism transfers
# ---------------------------------------------------------------------------
CORRUPTIONS = ("drop_owns", "drop_filing", "misread_value", "drop_period",
               "drop_publication_date")


def corrupt(case: "SolvencyCase", *, seed: int, rate: float,
            kind: str) -> WorldSnapshot:
    """Damage one channel of the world, leaving the others intact.

    The flood task's finding was that a pipeline's fragility sits in the facts
    that define the answer's **domain** rather than in the ones that constrain
    it, and that recall errors therefore hurt more than precision errors. This
    is the same knob on a structurally different task, so the claim can be tested
    rather than generalised by assertion.

    * ``drop_owns`` removes a member from the consolidation -- a domain deletion.
    * ``drop_filing`` removes one vintage -- domain if it was the only one, a
      recall error either way.
    * ``misread_value`` keeps every filing and corrupts the number -- precision.
    * ``drop_period`` / ``drop_publication_date`` strip a time, which the
      economy projection discards by name.
    """
    if kind not in CORRUPTIONS:
        raise ValueError(f"unknown corruption {kind!r}; have {CORRUPTIONS}")
    r = random.Random(int.from_bytes(
        hashlib.blake2b(f"corrupt|{seed}|{rate}|{kind}".encode(),
                        digest_size=8).digest(), "big"))
    out = []
    for c in case.world.claims:
        if kind == "drop_owns" and c.predicate == "owns" and r.random() < rate:
            continue
        if c.predicate != "revenue":
            out.append(c)
            continue
        if kind == "drop_filing" and r.random() < rate:
            continue
        if kind == "misread_value" and r.random() < rate:
            q = c.roles["value"]
            out.append(_replace_claim(c, value=Quantity(
                max(1.0, round(q.value * _slip(r), 2)), q.unit, q.stderr)))
            continue
        if kind == "drop_period" and r.random() < rate:
            out.append(_replace_claim(c, valid_time=Interval()))
            continue
        if kind == "drop_publication_date" and r.random() < rate:
            out.append(_replace_claim(c, transaction_time=Interval()))
            continue
        out.append(c)
    return WorldSnapshot(entities=case.world.entities, claims=tuple(out),
                         alignments=case.world.alignments)


def _slip(r: random.Random) -> float:
    """A misreading: a digit slip, a units confusion, or a percentage error.

    Digit-level rather than Gaussian, because that is what a reader of a filing
    actually gets wrong.
    """
    return r.choice((0.1, 10.0, 0.9, 1.1, 0.75, 1.25))


def _replace_claim(c: Claim, **kw: Any) -> Claim:
    from dataclasses import replace as _r
    if "value" in kw:
        roles = dict(c.roles)
        roles["value"] = kw.pop("value")
        kw["roles"] = roles
    return _r(c, **kw)
