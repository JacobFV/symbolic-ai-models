---
date: 2026-08-14
author: agent-005-atomspace
status: measured
related: [2026-08-14-a-boundary-optimum-is-not-a-fitted-value,
          2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable,
          2026-08-13-slices-have-inverted-results-eight-times]
---

# Record the whole grid, not the value it chose — the curve separates four worlds an argmax cannot

## The mechanism

A knob is fitted by search over a grid and the chosen value is written down. The
value alone is consistent with **four** different situations, which have
different implications and identical printouts:

1. a real optimum — the objective rises to it and falls after;
2. a **truncated grid** — the search wanted to keep going and you stopped it;
3. a **flat objective** — the argmax is picking noise between points that differ
   in the fourth decimal;
4. a **wrong-scale measurement** — the fit is real but was run somewhere the
   answer does not hold, e.g. on a slice.

`notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value.md` separates
(1) from (2) by looking at *where* in the grid the value landed. That is
necessary and it is not sufficient: it says nothing about (3) or (4), and an
interior value passes its check while still being noise.

**The curve distinguishes all four, costs one list, and can be printed into the
artefact the model already writes.**

## What happened

`metta_gated-005` fits `extra_weight` — how much of a node's role goes to the
signature groups only an atomspace can express — over
`(0, 0.25, 0.5, 1, 2, 4)`, where both ends are named degenerate models.

On a **six-lesson wiring check** it landed at `0.0`, the bottom of the grid.
Every existing guard passed cleanly: the value is at a grid end, so the boundary
lesson's rule fired and the model's own `rules.txt` printed `[BOUNDARY: bottom
of the grid; extras contribute nothing]`. The reading — "the likelihood switches
the treatment off" — was coherent, matched `omegaclaw_reach-001`'s prior, and was
reported upward as the headline finding.

On all **179 lessons** it lands **interior at 2.0**:

| `extra_weight` | 0.0 | 0.25 | 0.5 | 1.0 | **2.0** | 4.0 |
|---|---:|---:|---:|---:|---:|---:|
| held-out mixture LL | −4.1417 | −4.1145 | −4.0888 | −4.0676 | **−4.0639** | −4.0661 |

Monotone increasing across five points, then turning down. Identical to four
decimal places in the `_pure` row, which is an independent fit. So it is world
(1), and the slice had produced world (4) wearing world (2)'s clothes.

**The curve is what made that legible in one glance instead of an argument.** The
0.078 monotone rise rules out flatness; the turn at 4.0 rules out truncation; the
agreement between two independently fitted rows rules out noise. None of that is
visible in "the knob is 2.0", and none of it was visible in "the knob is 0.0".

## The cost of not having had it

The wrong reading was reported upward as a finding before the sweep finished.
It was labelled as coming from a slice, which is why it was caught rather than
believed — but it was still the headline of a status report, and the sweep would
have had to contradict it either way. Roughly one report cycle, and it is the
**tenth** slice inversion in this repo's history.

## The guard

- **A fitted scalar is reported with its curve or not reported.** One list, one
  line in `render()`, so it lands in `rules.txt` beside the value and survives
  into the run directory. `symbolic_ai_models/models/metta_005/model.py`'s
  `_fit_scalars` is the pattern.
- **Never quote a fitted hyperparameter from a smoke config.** A wiring check
  answers "does it run", never "what does it choose". Accuracy from a slice is
  already forbidden here; *fitted parameters* were not explicitly covered and
  now are.
- **If the objective is re-derived to record it, pin it with a test.** A curve
  reported for a knob that some other arithmetic actually chose is worse than no
  curve: it looks like evidence.
  `test_the_recorded_curve_picks_what_the_parent_fit_picks` runs both fits and
  requires the same answer.
