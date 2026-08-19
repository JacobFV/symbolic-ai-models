"""Does a sentence **cancel** the claim it makes?

The one channel that matters in both domains measured on 2026-08-19 is
**multi-valued**: flood's ``flooded`` and scheduling's ``has_capability`` admit
any number of regions or machines, so no arity constraint checks them, and in
both domains that is where the damage is -- 0.655 and 0.790 accuracy against
detectors that fire 0.000 of the time.

Nothing else in either document *knows* those facts, so there is no second
**source** to corroborate them. What is available is a second **reading of the
same sentence**: not what it says, but whether it takes it back.

Two gates are declared here rather than one, because the generator has confounded
two signals -- every real phrasing in both domains is present tense and every
distractor is past tense **with** a cancelling clause:

    A disused track once ran from region_0 to region_3.
    machine_0 was set up to paint last shift, before the head came off.
    job_0 used to cut as well, until the drawing was revised.
    job_90 was cancelled by the customer and has been struck from the list.

`stale_by_tense` keys on the past; `stale_by_cancellation` keys on the taking
back. They agree on every sentence the generators currently produce, and the
claim that they are different is only worth anything against real claims phrased
in the past. That arm is `scripts/staleness_gate.py`.

Both lists are **closed-class and domain-independent**, which is the property
that makes this different from a role vocabulary: adding a domain does not add
words. It does not make either gate safe -- a misfiring gate deletes true claims
where a misfiring anchor merely mislabels them -- but it bounds how the risk
grows.
"""

from __future__ import annotations

import re

__all__ = ["stale_by_tense", "stale_by_cancellation", "filter_stale",
           "TENSE", "CANCELLING"]

#: Past-tense and perfect auxiliaries. A sentence in the past, nothing more.
TENSE = ("was", "were", "had", "used to", "did")

#: Cues that a sentence **withdraws** what it asserts: the state is over, the
#: item is off the list, or a clause bounds it in the past. Declared from what
#: these words mean, not fitted to the corpus -- the fitting version of this
#: experiment is what the misfiring-vocabulary result is about.
CANCELLING = ("disused", "former", "formerly", "no longer", "used to", "once",
              "previously", "struck", "cancelled", "withdrawn", "ceased",
              "before the", "until the", "since removed", "came off")


def _has(sentence: str, cues) -> bool:
    low = sentence.lower()
    tokens = set(re.findall(r"[a-z]+", low))
    for cue in cues:
        if " " in cue:
            if cue in low:
                return True
        elif cue in tokens:
            return True
    return False


def stale_by_tense(sentence: str) -> bool:
    """The sentence is in the past. Says nothing about whether it still holds."""
    return _has(sentence, TENSE)


def stale_by_cancellation(sentence: str) -> bool:
    """The sentence withdraws what it asserts."""
    return _has(sentence, CANCELLING)


def filter_stale(text: str, gate) -> str:
    """Drop every sentence the gate marks, keeping paragraph structure.

    Reader-agnostic on purpose: this is the first component here meant to be
    shared across domains unchanged, so it operates on the text rather than on
    anything a particular reader builds.
    """
    out = []
    for para in text.split("\n\n"):
        sents = [s for s in re.split(r"(?<=[.?])\s+", para) if s.strip()]
        kept = [s for s in sents if not gate(s)]
        out.append(" ".join(kept))
    return "\n\n".join(out)
