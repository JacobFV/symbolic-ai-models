"""``text -> WorldSnapshot`` for the works order, by type signature.

Third domain for the same mechanism. The signatures separate every claim kind
outright, with **no coreference at all**, because entity prefixes carry the type:

    (machine, quantity)          -> capacity
    (job,     quantity)          -> duration
    (machine, capability word)   -> has_capability
    (job,     capability word)   -> needs_capability

The one piece of external knowledge is the **capability vocabulary** -- the
lexical counterpart of flood's numeric value registry, and the second instance of
the same architectural need. It also does the distractor rejection for free: the
withdrawn machine and the cancelled job carry no capability and no quantity, and
"no machine is set up for anodising" names a capability outside the vocabulary.
"""

from __future__ import annotations

import re

from symbolic_ai_core.world import (Claim, Entity, EntityRef, Quantity,
                                    WorldSnapshot)

from .surface import CAPABILITIES

__all__ = ["read_signature", "read_signature_accumulating"]

_MACHINE = re.compile(r"\bmachine_\d+\b")
_JOB = re.compile(r"\bjob_\d+\b")
_NUM = re.compile(r"\b(\d+\.\d{2})\b")


def read_signature_accumulating(text: str, *, capabilities=CAPABILITIES
                                ) -> WorldSnapshot:
    """Every claim in a sentence, not one branch per sentence.

    `read_signature` uses an ``elif`` chain, so *"machine_0 is set up for cut and
    has 5.51 hours available"* matches the capacity branch and the capability is
    **silently dropped** -- seed 0 loses two of four capabilities and the whole
    surface falls to its floor.

    Same claims, same signatures; the only difference is that a machine sentence
    yields its quantity **and** its capability words rather than one of them.
    """
    return _scan(text, capabilities, accumulate=True)


def read_signature(text: str, *, capabilities=CAPABILITIES) -> WorldSnapshot:
    """Type every sentence by its shape, one branch per sentence."""
    return _scan(text, capabilities, accumulate=False)


def _scan(text: str, capabilities, *, accumulate: bool) -> WorldSnapshot:
    machines: dict[str, float] = {}
    jobs: dict[str, float] = {}
    has: list[tuple[str, str]] = []
    needs: list[tuple[str, str]] = []
    for sent in re.split(r"(?<=[.?])\s+", text.replace("\n\n", " ")):
        ms = list(dict.fromkeys(_MACHINE.findall(sent)))
        js = list(dict.fromkeys(_JOB.findall(sent)))
        ns = [float(x) for x in _NUM.findall(sent)]
        caps = [c for c in capabilities if re.search(rf"\b{c}\b", sent)]
        if accumulate:
            if len(ms) == 1 and not js:
                if ns:
                    machines[ms[0]] = ns[0]
                for c in caps:
                    if (ms[0], c) not in has:
                        has.append((ms[0], c))
            elif len(js) == 1 and not ms:
                if ns:
                    jobs[js[0]] = ns[0]
                for c in caps:
                    if (js[0], c) not in needs:
                        needs.append((js[0], c))
        elif len(ms) == 1 and ns and not js:
            machines[ms[0]] = ns[0]
        elif len(js) == 1 and ns and not ms:
            jobs[js[0]] = ns[0]
        elif len(ms) == 1 and caps and not js:
            for c in caps:
                if (ms[0], c) not in has:
                    has.append((ms[0], c))
        elif len(js) == 1 and caps and not ms:
            for c in caps:
                if (js[0], c) not in needs:
                    needs.append((js[0], c))

    entities: dict[str, Entity] = {}
    claims: list[Claim] = []
    for m in sorted(set(machines) | {a for a, _ in has}):
        entities[m] = Entity(m, types=("machine",))
    for j in sorted(set(jobs) | {a for a, _ in needs}):
        entities[j] = Entity(j, types=("job",))
    for j in sorted(jobs):
        claims.append(Claim("duration", {"of": EntityRef(j),
                                         "value": Quantity(jobs[j], "h")}))
    for j, c in sorted(needs):
        claims.append(Claim("needs_capability", {"job": EntityRef(j),
                                                 "capability": c}))
    for m, c in sorted(has):
        claims.append(Claim("has_capability", {"machine": EntityRef(m),
                                               "capability": c}))
    for m in sorted(machines):
        claims.append(Claim("capacity", {"of": EntityRef(m),
                                         "value": Quantity(machines[m], "h")}))
    return WorldSnapshot(entities=entities, claims=tuple(claims))
