---
date: 2026-08-14
author: lead
status: measured
related: [2026-08-14-label_bits-drifted-on-master-while-every-accuracy-held,
          2026-08-14-a-boundary-optimum-is-not-a-fitted-value,
          2026-08-13-the-harness-moves-more-than-the-models]
---

# A fitted parameter that is never written down turns a discrepancy into an investigation

## The mechanism

A parameter is fitted at training time, applied to every reported number, and
recorded nowhere. Later a published number moves. Nobody can subtract the
parameter's contribution, because nobody knows what it was — so the only way to
attribute a four-decimal drift is to check out old commits and refit the model
to find out.

The cost is not the drift. It is that **the cheapest possible check is
unavailable**, and a subtraction becomes a bisect.

## What happened

`corefer-001`'s `label_bits` moved 6.951829 -> 6.954734 on `master` while
`label_acc` stayed **identical to nine decimal places**, along with `type_acc`,
`type_bits`, `copy_acc`, `label_floor` and `copy_floor`. `ngram-001` moved too,
by +0.0004.

Accuracies holding while bits move is a sharp signature: it is what a **post-hoc
monotone rescaling** does. Dividing log-probabilities by a positive constant
cannot reorder them, so every stated probability moves and no prediction does.
`_fit_temperature` is exactly such a transform and was the obvious suspect.

It could not be checked, because the temperature was not in `summary.json` — and
the published run's `model.pt` had been deleted by an earlier and otherwise
correct cleanup ("Keep the evidence, drop the weights"). So the parameter was
unrecoverable from the artefacts and had to be re-derived by refitting.

**And the guess was wrong in its specifics.** Refitting showed the current run at
`T = 1.1`, and forcing `T = 1.0` reads 7.050756 — a hundred times the observed
drift. So the published run was *also* near 1.1 and **the temperature did not
step**. Something smaller moved: the back-off or the masking draw. The reasoning
was right in kind (a monotone transform is implicated) and wrong about which one,
which is only knowable because somebody spent the afternoon.

## Why it matters more than 0.04% suggests

It changes no ranking. What it damages is the claim a versioned name is supposed
to make. `symbolic_ai_core/registry.py` exists because editing a model in place
silently redefines every published number carrying its name, and that had already
happened twice. Here `corefer-001` published one `label_bits` and now produces
another **with no commit anywhere saying so** — the same failure, arriving
through the harness instead of through the model.

## The guards

1. **`train.py` now writes `"temperature"` into every summary.** One float, the
   only parameter that moves every `*_bits` and no `*_acc`. The next drift is a
   subtraction rather than a bisect.
2. **The rule that came out of it, and it applies to every table in the repo:**
   `label_bits` is not stable to four decimals across unrelated harness changes
   and `label_acc` is. **Quote bits to three decimals, and treat a change below
   ~0.005 as noise rather than as a result.**
3. **Any parameter fitted from data belongs in the summary next to the numbers it
   moved** — with its search grid, per
   [[2026-08-14-a-boundary-optimum-is-not-a-fitted-value]]. The mixture weight
   `c`, the gate share, `top_k` and the floors are the standing candidates; only
   the temperature has been fixed so far. That makes this entry a **live hazard**,
   not a closed one.

## The general form, for the next one

An artefact that records outputs but not the parameters that produced them
cannot support the claim that a name pins a number. **If a value was fitted, it
is part of the result** — the run directory should be enough to explain any
future disagreement without checking out a commit or refitting a model.
