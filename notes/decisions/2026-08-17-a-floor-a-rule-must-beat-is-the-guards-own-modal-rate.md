---
date: 2026-08-17
author: lead
status: preregistration
related: [2026-08-17-the-channel-is-walked-and-it-took-a-conjunction-of-three,
          2026-08-17-i-keep-blaming-a-pipeline-stage-for-a-property-of-the-objective,
          2026-08-15-a-floor-outside-the-models-hypothesis-class]
---

# A rule should have to beat the guard it lives under, not a constant chosen for the whole lattice

## The weakness this closes

`frontier-007` walks the derivability channel at 0.989 and it does so with
`min_precision = 0.2` — a number I chose **after** logging that 0.5 excluded the
rule the derived fills need. No value was selected by the derived-bucket score
and none was searched over it, but the choice was *informed* by an evaluation-seed
measurement, which is weaker than a value settled on the development split and
weaker again than a value that needs no choosing.

The mechanism the logging exposed says what the fix is:

> One global precision floor cannot serve both ends of a guard lattice. It is
> generous at a narrow guard and prohibitive at a broad one — and the phenomena
> that live at broad guards are exactly the ones no narrow guard names.

A constant is the wrong shape for that. The floor should be a property of the
**population the guard admits**.

## The proposal

A rule at guard `g` must beat **`g`'s own out-of-fold modal rate** — the
precision the `const` resolver achieves there, which is exactly "answer every
fill under this guard with its commonest label". That is the do-nothing baseline
*for that guard*, and requiring a rule to beat it is the same discipline this
repo applies to models: a score is meaningless without the floor it is measured
against, and the floor has to be in the same population.

It behaves correctly at both ends by construction:

* **narrow guard, `const` at 0.99** — almost nothing is admitted, which is right;
  if the modal answer is nearly always correct there is nothing to add.
* **broad guard, `const` at 0.04** (the measured value at `[slot=1, nsib=2]`) —
  a resolver at 0.2 is five times the baseline and is admitted, where a constant
  0.5 threw it away.

`const` itself is admitted against a small absolute floor instead, since it
cannot be asked to beat itself.

## Predictions, before the numbers

1. **`frontier-008` reaches `acc | derived, not copyable` ≥ 0.95** on
   `derive:wordnet` *without* the hand-chosen 0.2 — i.e. the relative floor
   admits the same rule for a reason rather than by a coincidence of value.
2. **The control stays at its blind marginal**, ≤ 0.20 on `derive:wordnet-perm`.
   A relative floor is more permissive at broad guards, so admitting noise is the
   live risk and this is the number that would show it.
3. **`-shuffled` ties the treatment**, as it does for all twenty-odd models.
4. **Pooled `label_acc` ≥ `frontier-007`'s 0.4376**, or the permissiveness is
   costing more elsewhere than it buys here.

## What refutes it

- **The bucket lands below 0.90.** The relative floor does not admit the rule and
  0.2 was doing something a principled floor does not.
- **The control rises above 0.25.** The floor is admitting rules that fit noise,
  and then the treatment number is not readable at all — this is the void
  condition and it outranks every other outcome.
- **Pooled accuracy falls materially** (say below 0.42). Being generous at broad
  guards costs the rest of the curriculum more than the derived slot is worth,
  and the global constant was a crude but real regulariser.

## The knob that remains, and where it gets settled

`margin` — how much a rule must beat the modal rate by — and the small absolute
floor for `const`. Both default to the least tunable values available (1.0, i.e.
strictly better; and 0.02). **If either needs moving it gets moved on the
development split through `scripts/rsi_loop.py` and never on the derived
bucket**, which is an evaluation-seed measurement. That is the rule
`configs/rsi_dev.toml` exists to make enforceable, and this note is the place it
gets committed to in advance.
