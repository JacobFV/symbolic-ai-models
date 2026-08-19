---
title: A vocabulary is worse than none when it is confidently wrong
date: 2026-08-19
status: measured
arm: can-a-vocabulary-be-worse-than-none
---

## The control that could not fail

`scripts/adversarial_variants.py` names two questions and says the second matters
more:

> whether a declared vocabulary can be **worse than none**, by *misfiring* -- an
> anchor hitting a sentence it was not written for assigns a confident wrong role
> where an empty vocabulary would have left it to elimination.

It cannot answer it. Its `_verify_adversarial` asserts that no adversarial
phrasing contains a declared anchor, using `t.startswith(w)` over
`re.findall(r"[a-z]+", s.lower())` — **the same predicate `_anchor_role`
computes**. So `_anchor_role` returns `""` on every adversarial sentence *by
construction*, and the arm reduces to the emptied-anchor arm.

Measured rather than argued: the two agree **case by case**, 252 of 252 at 400
seeds and 34 of 34 at 60, in both arrangements.

| | grouped | interleaved |
|---|---:|---:|
| no vocabulary (anchors emptied) | 0.758 | 0.710 |
| declared, phrasings evade it | 0.758 | 0.710 |

The published reading of that coincidence — *"landing **exactly** on the
emptied-anchor floor, to three decimals… so the anchors never **misfire**, so its
failure mode is silence rather than error"* — is implied by the verification
step. It is one computation reported as two agreeing measurements.

## The inversion

`scripts/misfiring_vocabulary.py` writes phrasings that **do** trip an anchor,
for the **wrong** role, and for exactly one role so the reader gets a confident
wrong answer rather than silence. A depot sentence tripping `require`; a flooding
sentence tripping `origin`; a needs sentence tripping `water`. `_verify_misfires`
asserts the misfire **exists** — the honest inversion of a verification that
asserted it away.

| vocabulary | grouped | interleaved |
|---|---:|---:|
| none (anchors emptied) | 0.758 | 0.710 |
| declared, phrasings evade it | 0.758 | 0.710 |
| **declared, phrasings misfire** | **0.468** | **0.421** |

**−0.290 in both arrangements**, 252 non-empty cases at 400 seeds. The answer to
the original question is **yes, and by a lot**: a vocabulary that misfires costs
more than the whole distance between having one and not.

## The mechanism was already written in the code

Elimination only assigns into a role that is still **open**:

> An unresolved region must NEVER default to flooded while depot or needs is
> still open: marking a region impassable cuts the network and destroys the
> answer, where leaving it unassigned merely fails to help. The first version of
> this defaulted to flooded and scored 0.000 for that reason.

A misfire takes the slot. A flooded region misfiring as the depot both occupies
`depot` and pushes the true depot down into `flooded`, which is exactly the
failure that comment records. Silence leaves the slot open for elimination to
fill correctly; confidence closes it wrongly.

## The asymmetry that says which failure is which

**The misfire penalty is arrangement-independent — 0.290 in both cells — and the
silence penalty is not**: 0.242 grouped against 0.290 interleaved. Silence hands
the decision to elimination, which reads document order, so destroying the order
costs more. A confident wrong role does not consult the order at all.

So the two failure modes are separable by an experiment that changes only the
arrangement, without knowing which anchors fired.

## What this changes

- **The 0.290 gap is the case for lexical generalisation, and it is also the
  ceiling on what a bad one costs.** Enlarging a hand-declared anchor list has
  a downside of the same magnitude as its upside, realised whenever a new word
  reaches a sentence it was not written for. That is a stronger argument against
  growing the list than "it memorises the generator one variant later".
- The pairing with the emission result is the practical statement: **silence is
  recoverable and confidence is not.** Emission detects every role error the
  reader makes when it stays silent (0 wrong at 0.361 coverage); nothing detects
  a misfire, because a misfired role is `forced` and enumerates to one world.

## What would refute this

- Three misfiring phrasing families, hand-written by me, on one domain. They are
  natural-sounding but they are mine, and a real vocabulary's misfire rate is a
  property of the corpus rather than of a designer.
- The penalty is measured with **every** lone-region sentence misfiring. A real
  vocabulary misfires on a minority; the interesting quantity is the rate at
  which the penalty accrues, which is not measured here.
