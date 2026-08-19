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
#:
#: ``change`` and ``transfer`` are **excluded** and that is the whole difference
#: between a usable feature and an unusable one: they sit near the root of the
#: verb hierarchy, so *increase*, *add*, *process* and *update* reach them, and
#: they account for 9,090 of the 9,584 token fires on real prose.
TRANSITION_ROOTS = frozenset({"end", "discontinue", "leave", "exit", "deprive",
                              "remove"})

#: A lemma counts as a transition verb when **more than this share of its senses**
#: reaches a root. Dominance rather than priority: taking the first sense fires on
#: ``dated`` -- "go on a date with" -- which appears in every solvency filing
#: sentence and cost that surface 1.000 -> 0.650.
#:
#: **This constant was set by one false positive** (``dated`` reaches a root on
#: 0.20 of its senses) and is labelled as fitted for that reason. What makes it
#: defensible rather than arbitrary is that it costs nothing: held-out recall is
#: 0.33 at this threshold and 0.33 for the first-sense rule it replaces, so the
#: fraction rule strictly dominates. The margin is also wide -- every genuine
#: transition verb measured sits at 0.27 or above and every relation verb at 0.00.
TRANSITION_SENSE_SHARE = 0.2


def stale_by_verb(sentence: str) -> bool:
    """A token whose WordNet senses **mostly** denote cessation or departure.

    The signal no cue list reaches: *"sub_98 left the group in April"* is stale
    because of what **leave** means. Measured on solvency's uncued arm, this takes
    accuracy **0.475 -> 1.000 with no cost on the clean surface** -- the first
    thing that moves that arm by reading rather than by refusing.

    Three findings are folded into the two constants above and neither is
    optional:

    - **supersenses cannot do this.** They classify by subject matter, so
      ``cease`` is *verb.stative* and ``divest`` is *verb.possession*, like
      ``own``.
    - **ancestor depth decides the false-positive rate.** With ``change`` and
      ``transfer`` included this fires on 0.522 of real scientific prose; without
      them, 0.057.
    - **sense dominance, not sense priority.** First-sense selection fires on
      ``dated`` and costs solvency's clean surface 0.350.

    **DOMAIN-SPECIFIC, AND NOT WIRED INTO ANY DEFAULT PATH.** It is not the
    counterpart of `stale_by_cancellation`, which is closed-class, fires on 0.004
    of real prose, and leaves all three generated surfaces byte-identical. This
    one draws on 11,529 open-class lemmas, fires on **0.156** of real prose, and
    end to end::

        solvency, uncued owns     0.475 -> 1.000     (clean surface unchanged)
        scheduling, hard machine  0.767 -> 0.675
        flood, hard distractors   0.589 -> 0.014

    **`can` is what kills flood.** WordNet has it as a verb -- *"terminate the
    employment of"* -- so one of its two senses reaches ``remove`` and the
    fraction is 0.5. It appears 90 times in thirty flood documents. Sense
    dominance protects against a **rare** wrong sense (``dated``, 1 of 5) and not
    against a **low-sense-count** word where one reading happens to be a
    transition. ``empty``, ``complete`` and ``laden`` fail the same way.

    The damage also scales with **claim density**: flood realises a claim in
    almost every sentence, so deleting 13% of them destroys the world, while
    solvency's ownership paragraph survives.

    Held-out recall is **0.33** besides -- a distractor built on *revoke*,
    *rescind*, *annul*, *forfeit* or *disband* is not caught -- so the 1.000 is a
    ceiling for the verbs it has, exactly as the declared anchors' 1.000 was. And
    it addresses **staleness** only: a claim that was never true, such as an
    unofficial figure, is a different failure and belongs to the insensitivity
    response.

    No part-of-speech tagger. One was tried, and removed: restricting to ``VB*``
    takes real-prose firing 0.057 -> 0.017 under the any-sense rule and buys
    **nothing** end to end once sense dominance is in place.
    """
    from .wordnet import sense_fraction_reaching
    for token in re.findall(r"[A-Za-z][a-z]+", sentence):
        if sense_fraction_reaching(token.lower(),
                                   TRANSITION_ROOTS) > TRANSITION_SENSE_SHARE:
            return True
    return False
