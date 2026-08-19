---
title: Two responses to a corrupt channel, and which one a domain allows
date: 2026-08-19
status: decision
---

## The synthesis, from numbers already on disk

Today's detection work and the older certificate work are answers to the same
question — *what do you do about a claim the reader may have got wrong?* — and
they are **not** alternatives on the same axis. There are exactly two responses,
each gated by a different property of the domain:

**(a) Detection.** Read the fact a second time and compare. Sound *and* complete
where it applies (the enumeration theorem), and gated by **evidence structure**:
the role's arity, and whether some companion sentence pins it. Measured across
three domains today: flood `needs` (single-valued + a quantity beside it) 0.774
and 0.976; flood `depot` (single-valued) 0.833; scheduling `needs_capability`
(exactly one per job) 1.000; and **0.000** for every multi-valued role —
flood `flooded`, scheduling `has_capability`, solvency `owns`.

**(b) Answer-insensitivity.** Do not decide whether the claim is true; prove the
answer does not depend on it. Sound but **lossy**, and gated by the shape of the
**decision** rather than of the evidence.

The second is where the older results already have the answer, and they say it
is available in inverse proportion to how much the decision aggregates:

| decision shape | insensitivity available? | on disk |
|---|---|---|
| reachability with redundancy (flood links) | **yes, free** | certificate fires 0 wrong at 48.8%; link deletion dependency 0.138 |
| NP-hard feasibility (scheduling) | **half** | monotone half worth 57%; the structural analogue is unsound on 8 of 9 |
| a **sum** against a threshold (solvency revenue) | **no** | revenue decides **0.000** — every filing moves the sum |

## The prediction I am recording rather than running

Building an insensitivity certificate for solvency's damaging channel would
produce **near-zero coverage**, because the decision is a sum and every term
moves it. That number is already on disk as the decidedness law's extreme case
(`revenue` decides 0.000 against `owns` at 1.000), computed on true worlds with
no reader involved. Running it would re-derive a number the law already gives,
which is the pattern `CLAUDE.md` names as the one to stop.

So it is written down as a prediction: **solvency admits neither response on its
revenue channel** — no second reading (multi-valued, no companion) and no
insensitivity (a sum). If a later experiment contradicts it, that contradiction
is the finding.

What *would* be worth running, and is not the same experiment: solvency's `owns`
channel is multi-valued **but** membership is not a sum — dropping one member
changes the total by that member's filing, which may or may not cross the
threshold. Insensitivity there is a real question with an unknown answer, and it
is the cheap version of the thing above.

## The rule this leaves

> **Before building a check, ask which of the two responses the domain permits.**
> Detection needs a second reading and is gated by arity; insensitivity needs a
> decision that ignores the claim and is gated by aggregation. A domain that
> aggregates everything and corroborates nothing — solvency's revenue — permits
> neither, and the honest move there is to fix the *reader*, which is what the
> consolidated reader and the staleness gate did.

## Related

- `notes/findings/2026-08-19-emitting-the-ambiguity-detects-every-error-and-recovers-none.md`
- `notes/findings/2026-08-19-the-detectable-error-is-the-harmless-one.md`
- the `decidedness` law and the certificate generality result in `state.yml`
