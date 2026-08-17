---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-17-two-thirds-of-softreasons-headline-is-the-gate-and-the-same-gate-pays-twice,
          2026-08-13-the-harness-moves-more-than-the-models,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# If the gate's fitting method is worth half a bit wherever it is applied, `corefer-001` has half a bit on the table

## The claim being tested

Two architectures with nothing in common price the same method change almost
identically:

| model | mass-fitted gate | argmax-fitted gate | difference |
|---|---:|---:|---:|
| `ptrgen` | 5.91 | 6.49 | **0.58** |
| `softreason` | 6.148 | 6.680 | **0.53** |

Two points is a coincidence until it is three. `corefer-001` is the third and the
sharpest available: it is the repo's most-cited rule-based model — best
`label_acc` before the frontier line, the only model with a large positive type
lift (+0.612), and the most renaming-invariant thing here at −0.003 — and its
gate is neither calibrator. It is a **hand formula**, `min(0.15 + 0.8·top, 0.9)`,
written before either calibrator existed.

## Predictions, before the numbers

1. **`label_bits` improves from 6.952 by 0.35–0.55**, i.e. lands in **6.40–6.60**.
   That is the interval the two existing points imply, widened downward because a
   hand formula is not the same baseline as an argmax fit and could already be
   accidentally well calibrated.
2. **`label_acc` moves by less than 0.02**, in either direction. `ptrgen`, also a
   pointer, moved 0.015 on this change; `softreason` moved 0.061 because a
   closure spreads mass over more candidates than a pointer does, and `corefer`
   is a pointer.
3. **`type_acc` is unchanged at 0.9458.** The type head has its own estimator and
   its own confidence — this is the control that says only the gate moved, and it
   is the one that decides whether the row is readable.
4. **The renaming drop stays ≈ −0.003.** A gate cannot add vocabulary dependence.

## What refutes what

- **Bits do not improve.** The half-bit pattern does not generalise; it is
  specific to models whose gate was *already* a fitted calibrator, and the
  "fitting method is worth ~0.5 bits wherever applied" sentence in
  [[2026-08-17-two-thirds-of-softreasons-headline-is-the-gate-and-the-same-gate-pays-twice]]
  must be narrowed to those.
- **Bits improve by much more than 0.6.** The hand formula was worse than an
  argmax fit, which would make `corefer`'s published bits an artefact of a
  formula nobody had revisited — a bigger claim than the one being tested and one
  that would need its own check.
- **`type_acc` moves.** Something other than the gate changed and the run is not
  the experiment.

## The thing to be careful about

`corefer-001` is published and heavily cited. Extracting the formula into an
overridable method **must be a no-op**, and the regression row is the proof: the
unchanged model has to reproduce 0.3572 / 6.952 / 0.9458 exactly. Three defects
today came from edits whose intent was innocuous
([[2026-08-17-a-default-computed-in-init-captures-the-base-classs-values]],
[[2026-08-17-str-replace-hits-every-occurrence-including-the-subclass]]), and all
three were invisible to the suite and visible in one control row.
