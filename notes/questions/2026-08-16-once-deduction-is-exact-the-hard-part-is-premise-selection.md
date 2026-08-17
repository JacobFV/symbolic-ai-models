---
date: 2026-08-16
author: lead
status: measured
answered_by: notes/findings/2026-08-16-premise-selection-is-free-inside-the-object-and-costs-0714-outside-it.md
related: [2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-15-a-floor-outside-the-models-hypothesis-class]
---

# CoTu's residual: when the solver is exact, what is left is choosing the premises

[arXiv:2607.14735](https://arxiv.org/abs/2607.14735), CoTu at EXACT 2026. A 4B
model writes Z3 or Python and a solver answers; they report that once deduction
is delegated, the remaining hard problem is **premise selection** — deciding
which facts, variables and constraints from the situation are the ones the
solver should be given.

This repo can measure that claim without an LLM and without a solver, because it
has both ends already. The derivation floor answers the derived bucket at
**1.000** while twenty models answer it at 0.000; the floor is not a better
reasoner, it is a lookup that was *told which sibling to read*. The gap between
those two numbers is entirely premise selection, and it is 1.000 wide.

The measurement: hold the deduction fixed at an exact table and vary only what
the table is allowed to look at.

| arm | given | expected |
|---|---|---|
| oracle premise | the kind sibling, named | 1.000 (the published floor) |
| self-selected | every visible sibling, must choose | ? |
| blind | no sibling | 0.167 (the published blind marginal) |

The middle row is the whole experiment and nobody has run it. Both its
endpoints are already published, so the arm is bounded on both sides before it
starts — which is unusual here and worth the cheapness.

If the middle row lands near 1.000, premise selection on this curriculum is
trivial and CoTu's residual does not reproduce here, which would say the derived
bucket is a *representation* problem and `frontier-001`'s map form is the whole
answer. If it lands near 0.167, then selection is the entire difficulty, the
hypothesis language was never the constraint, and the finding
[[2026-08-15-the-derivable-fill-is-worth-0833-to-a-lookup-and-nothing-takes-it]]
should be reread as a statement about search rather than about expressiveness.

Cheap, bounded, and the two readings point in opposite directions — which is
what makes it worth doing before anything more ambitious.

---

**Answered, and by neither of the two readings above.** The middle row is
**1.000** when the candidate set is the object's own siblings and **0.286** when
it is the whole visible graph — the scope decides, not the choosing. At the wide
scope the selector picks a *kind* label on 99.9% of positions and the *right
object's* kind on 23.3% of them, which is one over the number of objects in a
scene. The residual is argument binding, not relevance ranking. Control
(`-perm`) does not separate: 0.143–0.177 across all four rungs. See
`notes/findings/2026-08-16-premise-selection-is-free-inside-the-object-and-costs-0714-outside-it.md`.
