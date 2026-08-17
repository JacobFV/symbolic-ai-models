---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-17-the-parked-experiment-was-a-null-by-construction-and-nothing-would-have-said-so,
          2026-08-17-the-per-guard-floor-keeps-the-channel-and-drops-the-chosen-constant,
          2026-08-15-how-many-pairs-can-a-model-here-hold,
          2026-08-14-record-the-curve-not-the-argmax]
---

# The curve is runnable, and I blocked it by misreading the note I was following

## The correction, first

Earlier today I marked
`notes/questions/2026-08-15-how-many-pairs-can-a-model-here-hold.md` **blocked**,
on the grounds that widening the derive map to 12 pairs makes
`DeriveBinder.vocabulary` fall back at every slot and derive nothing. That
measurement is right and the guard shipped for it is worth keeping.

**The conclusion drawn from it is wrong.** The question note does not ask for a
wider map. Its own words:

> register `derive:wordnet-k12`, `-k24`, `-k60` (an episode still draws six
> kinds, but **from a pool of k**, with the map fixed corpus-wide over the whole
> pool)

The pool is widened; the **per-episode map stays six wide**, which is exactly the
width the slots take. The design in the note never trips the binder. I
implemented the naive reading — widen the map — hit the trap that reading
deserves, and then attributed the trap to the note.

So: the lesson stands, the guard stands, and my characterisation of the *note*
was a misreading. Recording it here rather than quietly re-running, because
"the parked experiment was unrunnable" and "I ran a different experiment from
the parked one" are very different claims and I published the first.

## What is being run

`-kN` widens the **pool** the episode's six kinds are drawn from. The
kind→value assignment is the pool's and is fixed corpus-wide; restricting it to
a six-subset chosen by `(name, lesson_id, seed)` cannot change it. So the only
thing that varies with `k` is **how often each pair is seen**.

Structural check first, per the rule I wrote this morning — *before running a
parked experiment, check its treatment can move at all*:

| arm | distinct kinds | distinct pairs | per-pair appearances |
|---|---:|---:|---|
| `derive:wordnet` | 6 | 6 | 120–120 |
| `derive:wordnet-k12` | 12 | 12 | 54–67 |
| `derive:wordnet-k24` | 24 | 24 | 17–42 |
| `derive:wordnet-k60` | 60 | 60 | 3–19 |

Distinct pairs equals distinct kinds at every rung, so the correspondence is a
bijection throughout, and the appearance count falls the way the design intends.

## Predictions, before the numbers

`frontier-008` reaches **0.989** on `acc | derived, not copyable` at k=6 against
a 1.000 lookup floor. The training set holds ~184 derived fills, so each pair is
seen roughly `184·6/k` times: **~30 at k=6, ~15 at k=12, ~7.7 at k=24, ~3 at
k=60**.

1. **k=12 stays high, ≥ 0.90.** Fifteen instances per pair is thin but the
   cross-fit only needs the pair in both folds.
2. **k=24 falls but clears the blind marginal comfortably, 0.4–0.8.**
3. **k=60 collapses toward the blind marginal.** Three instances per pair cannot
   survive a two-fold cross-fit — a pair seen three times is often absent from
   one fold entirely, and `map` then declines.
4. **The control falls as 1/k, not to 1/6.** With `k` values in play the blind
   marginal itself drops, so **lift over the arm's own control is the readable
   quantity and the raw column is not** — this is the note's own warning and the
   reason each rung gets its own `-perm`.

## What refutes what

- **k=60 stays ≥ 0.9.** Then six pairs was never doing the work, the model holds
  arbitrary corpus-wide maps, and the "it is about table size" threat to the
  derivability headline is dead. That would be the strongest possible outcome and
  I do not expect it.
- **k=12 already collapses.** Then the headline is fragile and six was carrying
  it; the derivability result should be restated as "a six-pair correspondence",
  not "a corpus-wide correspondence".
- **A rung's control rises with its treatment.** Then that rung is admitting
  noise and nothing at that `k` is readable, whatever the treatment says.

The honest prior: this is a *data* curve, not a capacity curve. What it measures
is how many instances per pair the cross-fit needs, and the answer will be a
property of `n_train = 20` at least as much as of the model. That is worth saying
before the numbers so the write-up cannot quietly become a claim about capacity.
