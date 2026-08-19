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

__all__ = ["stale_by_tense", "stale_by_cancellation", "stale_by_verb",
           "filter_stale", "TENSE", "CANCELLING", "CANCELLING_V1",
           "TRANSITION_ROOTS"]

#: Past-tense and perfect auxiliaries. A sentence in the past, nothing more.
TENSE = ("was", "were", "had", "used to", "did")

#: Cues that a sentence **withdraws** what it asserts: the state is over or the
#: item is off the list. Declared from what these words mean, not fitted to a
#: corpus -- the fitting version of this experiment is what the
#: misfiring-vocabulary result is about.
#:
#: **Corrected against 36,223 sentences of real scientific prose** (`data/sources/
#: openalex-prose`, `scripts/gate_on_real_prose.py`). The first list carried four
#: more cues, and on English nobody here wrote they were **temporal ordering**
#: rather than withdrawal -- *"before the reaction"*, *"previously reported"*,
#: *"once-weekly"*, *"until the endpoint"*. A sentence may say "before the war X
#: was Y" while X is still Y. They accounted for **40%** of all fires on real
#: text and nothing in any generated surface here depends on them, every
#: distractor carrying a second, genuinely cancelling cue.
#: A second genre corrected it again, and differently. On 75,555 sentences of
#: public-domain narrative (`scripts/gate_on_narrative.py`) the dominant fire was
#: **`struck`** at 29.9% -- the verb *strike*, "struck him", "was struck by" --
#: where the abstracts corpus fired it twice. The cancelling sense always carries
#: a particle: *struck from*, *struck off*. **Each genre surfaced a different
#: dominant false positive and neither was predictable from the other.**
CANCELLING = ("disused", "former", "formerly", "no longer", "struck from",
              "struck off", "cancelled", "withdrawn", "ceased",
              "since removed", "came off")

#: ``used to`` is two constructions and only one of them cancels. The habitual
#: past -- *"job_0 used to cut"* -- says the state is over. The passive of *use*
#: -- *"is used to obtain"*, *"have been widely used to examine"* -- says nothing
#: of the kind, and it is **53.5% of every fire on real prose**, 439 of 443 of
#: them as the only cue in the sentence. That is not a temporal/cancelling
#: confusion, it is an ambiguity between two grammars, and it separates on one
#: observable: the passive is preceded by a form of *be*.
_BE = frozenset({"is", "are", "was", "were", "be", "been", "being"})
#: How far back to look for the auxiliary. Three tokens, because an adverb or two
#: routinely intervenes -- *"are then used to"*, *"have been widely used to"* --
#: and an approximation is what is available without a parser.
#:
#: **Bounded by the clause.** Measured on narrative, an unbounded three-token
#: window suppressed **22.0%** of *used to*, and the samples showed it reaching
#: across a comma into a different clause: *"this May that we have been having,
#: I used to run down"*. Stopping at a comma or semicolon is the clause boundary
#: a parser would supply. What survives suppression is the third construction,
#: *be used to* meaning **accustomed** -- *"he had been used to look"*, *"you have
#: been lately used to"* -- which is a state that may well still hold and so is
#: correctly not a cancellation.
_LOOKBACK = 3
_CLAUSE_END = re.compile(r"[,;:]")


def _habitual_past(low: str) -> bool:
    """``used to`` in the habitual reading -- not the passive of *use*."""
    for m in re.finditer(r"\bused to\b", low):
        head = low[:m.start()]
        cut = max(head.rfind(c) for c in ",;:")
        clause = head[cut + 1:] if cut >= 0 else head
        before = re.findall(r"[a-z0-9_]+", clause)[-_LOOKBACK:]
        if not (_BE & set(before)):
            return True
    return False

#: The first list, kept so a published number can be reproduced rather than
#: silently redefined. Nothing measured here moved when the four were dropped.
CANCELLING_V1 = CANCELLING + ("once", "previously", "before the", "until the")


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


def stale_by_cancellation(sentence: str, *, cues=CANCELLING) -> bool:
    """The sentence withdraws what it asserts."""
    return _has(sentence, cues) or _habitual_past(sentence.lower())


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


#: Taxonomic ancestors that denote cessation, departure or loss of possession.
#: Chosen from WordNet's own hypernym closure -- not from the supersenses, which
#: classify by **subject matter** rather than by aspect and cannot separate a
#: verb that asserts a relation from one that ends it (``cease`` is
#: *verb.stative*, ``divest`` is *verb.possession*, exactly like ``own``).
TRANSITION_ROOTS = frozenset({"change", "end", "discontinue", "leave", "exit",
                              "deprive", "transfer", "remove"})


def stale_by_verb(sentence: str) -> bool:
    """A token whose WordNet hypernym chain reaches a cessation ancestor.

    The signal the cue lists cannot reach: *"sub_98 left the group in April"* is
    stale because of what **leave** means, not because of any word on a list.

    **It has no part-of-speech knowledge and that is the binding limit.** Every
    token is tested as a verb, so *"the end of the study"* and *"a change in
    protocol"* fire on their nouns. Measured on real prose the false-positive
    rate is what decides whether this is usable, and it is reported beside the
    recall rather than left out.

    **Measured and NOT usable as a gate.** Kept because a dead end that is not
    written down gets re-derived. On verbs held out from the set used to choose
    the roots: recall **0.42** at 0.08 false positives with all eight roots,
    **0.33** at **0.00** with the deep six. The design set read 0.86 and 0.64, so
    a fifteen-verb negative class inflated it about twofold.

    At the **sentence** level it fires on **0.522** of real scientific prose with
    all eight roots and **0.058** with the deep six, against 0.003 for
    `stale_by_cancellation`. And end to end on solvency it lifts the uncued floor
    0.485 -> 0.635 while taking the clean surface **1.000 -> 0.650**, on one
    word: ``dated``, a participial modifier in every filing sentence whose first
    WordNet sense is the romantic one and whose chain reaches *leave*.

    Two failure modes at once, and the diagnostic separates them: a nominal
    filter (skip a token after *the*, *of*, *in*...) moves 0.522 -> 0.426 and
    0.058 -> 0.045, so **part of speech is not the dominant problem -- ancestor
    depth is**. ``change`` accounts for 6,899 token fires and ``transfer`` 2,191,
    against ``leave`` 315, ``end`` 271, ``remove`` 91, ``exit`` 12, ``deprive``
    5. See `scripts/verb_class_staleness.py`.
    """
    from .wordnet import hypernym_closure, is_verb_lemma
    for token in re.findall(r"[A-Za-z][a-z]+", sentence):
        low = token.lower()
        if not is_verb_lemma(low):
            continue
        if TRANSITION_ROOTS & hypernym_closure(low):
            return True
    return False
