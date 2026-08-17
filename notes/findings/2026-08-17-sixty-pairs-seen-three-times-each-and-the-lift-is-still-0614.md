---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-pair-count-curve-and-a-correction-to-yesterdays-block,
          2026-08-17-the-per-guard-floor-keeps-the-channel-and-drops-the-chosen-constant,
          2026-08-17-the-channel-is-walked-and-it-took-a-conjunction-of-three,
          2026-08-14-record-the-curve-not-the-argmax]
---

# The derivability result is not about table size, and two of my four predictions were too pessimistic

The headline's biggest named threat was that six planted pairs is a small map and
the result might be about **table size** rather than induction. This is the curve
that separates them, pre-registered in
[[2026-08-17-the-pair-count-curve-and-a-correction-to-yesterdays-block]] before
any score.

`-kN` widens the **pool** the episode's six kinds are drawn from; the per-episode
map stays six wide. The kind→value assignment is the pool's and fixed
corpus-wide, so the only thing that varies with `k` is how often each pair is
seen.

## The curve

`frontier-008`, `acc | derived, not copyable`, each rung against **its own**
control and its own blind marginal:

| k | instances per pair | treatment | control `-perm` | blind (treatment) | **lift over control** |
|---:|---:|---:|---:|---:|---:|
| 6 | ~30 | 0.989 | 0.143 | 0.167 | **0.846** |
| 12 | ~15 | **1.000** | 0.092 | 0.115 | **0.908** |
| 24 | ~7.7 | 0.896 | 0.072 | 0.039 | **0.824** |
| 60 | ~3 | 0.641 | 0.027 | 0.016 | **0.614** |

The derivation floor — a lookup *told* the premise — is **1.000 at every rung**,
so the ceiling does not move and the comparison is honest across `k`.

**At k=60 the model holds sixty corpus-wide pairs, each seen about three times
in training, and answers 64% of the bucket against a blind marginal of 1.6%.**
That is forty times chance. The lift is roughly flat from k=6 to k=24 and only
falls at k=60.

## Against the predictions

| # | predicted | measured | |
|---|---|---:|---|
| 1 | k=12 stays ≥ 0.90 | **1.000** | held, and stronger |
| 2 | k=24 falls to 0.4–0.8 | **0.896** | **too pessimistic** |
| 3 | k=60 collapses toward the blind marginal (0.016) | **0.641** | **refuted** |
| 4 | the control falls as 1/k; lift is the readable quantity | 0.143 → 0.027 | held |

Two of four wrong, both in the same direction: **I expected the two-fold
cross-fit to fail on a pair seen three times, and it does not.** A pair seen
three times is often absent from one fold entirely, and I predicted the `map`
would then decline. What evidently happens instead is that the *other* pairs
carry the rule and the thin ones are answered by whichever fold does hold them —
the cross-fit is per key, not per rule, so a table's rare keys degrade
individually rather than sinking the rule that owns them.

No rung's control rose with its treatment, so the void condition never fired and
every row is readable.

## What this settles

**The "it is about table size" threat is dead.** Six pairs was not doing the
work; the same machinery holds sixty. The derivability result should be stated as
what it is — a model that induces a corpus-wide correspondence between symbols
and applies it — and not hedged down to "a six-pair correspondence".

**And it is a data curve, not a capacity curve**, which the pre-registration
insisted on saying before the numbers arrived and which the numbers now support.
The fall from 0.896 to 0.641 tracks instances-per-pair (7.7 → 3), not pool width
per se. Whether k=60 recovers at `n_train = 40` is the direct test of that and has
not been run; if it does, the curve is entirely about supervision and nothing
here is a statement about how many pairs the model can hold.

## The correction this note also carries

Earlier today I marked the parked question **blocked**, having implemented the
naive reading — widen the *map* — hit the trap that reading deserves, and
attributed the trap to the note. The note had specified the pool design
correctly. The guard shipped for the naive reading is still worth having and the
lesson still stands; my characterisation of the note was a misreading, and
"the parked experiment was unrunnable" and "I ran a different experiment from the
parked one" are different claims. I published the first.

## What would still make this hollow

The population is the same 11 carrying lessons and ~1,330 fills at every rung, so
this is the whole derived slot and not a slice of it — but it is still **0.20% of
graph positions in 11 of 179 lessons**, and nothing here says anything about the
rest of the curriculum. The `-shuffled` check was run only at k=6; the k rungs
have treatment and control but no third arm, which is a weaker configuration than
the base family has.
