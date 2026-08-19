---
title: A correction to the correction — two numbers that agreed by accident
date: 2026-08-19
status: measured
arm: perturbation-dependency
---

## What went wrong, twice

Two turns ago I claimed *ambiguity is cheap to carry when the hypothesis about it
is small*. The curve experiment killed it: decidedness collapses at the first
bound, with no usable middle.

I replaced it with *carried ambiguity is cheap exactly when the ambiguous kind
has low **collision cost***, citing the audit's 0.000 for `bridge_on`/`link`
against 0.625 for `depot`/`flooded`/`needs`.

**That substitution was also wrong**, and setting up a test for it is what
exposed it.

Collision cost measures **permutation between two kinds** — the cost of not being
able to *type* a sentence. It is 0.000 for `bridge_on`/`link` because their role
signatures differ, so **nothing is permutable**. But what the link policy carries
is a **spurious claim**, explored by **deletion**. Two different quantities, both
low, for unrelated reasons. I read the coincidence as a prediction.

## The number that actually predicts

Dependency **under the perturbation being carried**:

| perturbation | dependency | carrying it |
|---|---:|---|
| flood: delete one link | **0.138** | free — 0.383 decided, gave up nothing |
| flood: reassign two lone-region roles | **0.467** | vacuous — 0.067 decided |
| solvency: delete one `owns` claim | **0.000** | inert — nothing to carry |

The separation is 3.4× and in the right direction. Roles are *not* always
load-bearing, as I assumed when explaining the earlier result — 0.467, not 1.0 —
but a link deletion is inert three times as often, because the network usually
has another path.

Solvency's `owns` is **exactly 0.000**: dropping every ownership sentence changes
no verdict and loses no member, because every member is recoverable from its own
revenue filing. Ownership in that domain is inert.

## What is and is not established

**Established:** the controlling variable is dependency under the carried
perturbation, not hypothesis size and not collision cost. Both earlier
formulations are withdrawn.

**Not established:** any functional form. There are still only **two real
carrying measurements** — link deletion and role reassignment — and `owns` adds
an extreme point with nothing to carry, so it anchors the variable without
testing the relationship. That is the same thinness that sank both previous
versions, and it is stated here rather than discovered next turn.

## The guard, in code

`collision_cost` and `deletion_dependency` now sit beside each other in
`symbolic_ai_generators/audit.py`, each documenting what it measures and that
**they are not the same number**, with the `bridge_on`/`link` case written out as
the worked example of them agreeing for unrelated reasons.
`test_deletion_dependency_is_not_collision_cost` asserts both — permutable
count 0, deletion dependency strictly between 0 and 0.4 — so the distinction
cannot quietly collapse again.

Which one applies is a property of the situation, not a choice: a reader that may
have **invented** a claim is carrying deletions; a reader that cannot **type** a
sentence is carrying permutations.

## A note on how this was caught

Not by a control and not by a refuter. I went looking for a third data point,
found that solvency's `owns` had zero dependency, and while writing the
experiment that would use it noticed that the quantity I had cited was not the
quantity being carried. **Building the next test on top of a claim is what
exposed the claim** — which is an argument for doing that promptly rather than
polishing the claim first.
