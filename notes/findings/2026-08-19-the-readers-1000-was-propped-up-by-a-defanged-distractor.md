---
title: The reader's 1.000 was propped up by a defanged distractor
date: 2026-08-19
status: measured
arm: adversarial-distractor
---

## What the instrument said, and what it was worth

`audit_surface(prose=True)` flagged that flood's *"A disused track once ran from
X to Z; it has not carried traffic for years."* carries **exactly** the `link`
signature — two regions, no number — and that the reader admits it as a road in
every one of 20 cases. That flag was validation at the time: the audit had
rediscovered, unaided, a defect previously found by hand.

But it was recorded as a defect whose *cost* had not been measured. It has now.

## The defect was masked by the generator, not prevented by the reader

The distractor's endpoints are drawn from `_OUTSIDE = (region_88, region_91,
region_94)` — regions that appear nowhere else in the world. The phantom edge
therefore connects nothing and cannot change any answer.

Point the same sentence at two **real** regions with no road between them,
changing nothing else — same claims, same phrasings, same answer, same span
alignment for every claim:

| distractor | surface | accuracy | spurious links/case |
|---|---|---:|---:|
| as published (`_OUTSIDE`) | grouped | **1.000** | 1.00 |
| as published | interleaved | **1.000** | 2.00 |
| **adversarial (real ids)** | grouped | **0.367** | 1.00 |
| **adversarial** | interleaved | **0.383** | 2.00 |

**Two region ids in one sentence are worth −0.633.**

The interleaved rows are the sharper embarrassment: they admit **twice** the
spurious links — interleaving destroys the paragraph grouping that picks the
network paragraph, so the "districts lie outside" distractor gets in too — and
still score 1.000 published, because both phantom edges are inert. The reader was
being scored on a surface where its false claims could not matter.

## This corrects a headline

[[2026-08-19-the-empty-cell-is-filled-by-five-words-of-flooding]] reports
`signature+content` at **1.000 in all four cells** of phrasing × arrangement, and
calls it the first reader here invariant to both. That number is real but it is
measured against a distractor that cannot bite. Against one that can, the same
reader scores **0.333**.

The adversarial-phrasing test already showed that 1.000 was a *ceiling* rather
than a capability. This shows the ceiling was also resting on a second prop, and
an unrelated one: not what the reader knows, but what the generator declined to
ask.

## Why the reader cannot fix this without content

By the audit's own logic the sentence is unreachable. It has exactly the `link`
signature, so **no content-free observable separates a disused track from a
road** — the same closure that holds for depot vs flooded, arrived at from a
completely different direction.

That unifies two things previously treated as separate problems. Distractor
rejection is not a different task from role assignment; both are cases of the
signature failing to fix the predicate, and both need content. It also explains
cleanly why scheduling's capability vocabulary works as a distractor filter,
noted earlier as a curiosity: **it is content**, and content is what the job
requires.

## What changed in the repo

`render_observation(..., hard_distractors=True)` points the sentence at two real,
currently-unlinked regions, preferring the depot-to-site pair — the phantom edge
most able to change the answer, because a distractor that cannot matter is not a
distractor.

**Default `False`, deliberately.** Every published flood number was measured with
the easy distractor, and changing it in place would silently redefine all of
them. `True` is the honest setting and the one new work should use.

## What would refute this

- A reader rejecting the phantom edge without content. The closure argument says
  it cannot, but that argument covers the observable the audit computes; a richer
  content-free observable would need its own collision test.
- The flow absorbing phantom edges. It does not — a phantom edge creates routes
  that are then legitimately checked against flooding and bridge limits and pass,
  because the edge itself is the lie. That was the alternative written into the
  prediction, and the measurement rejected it.
