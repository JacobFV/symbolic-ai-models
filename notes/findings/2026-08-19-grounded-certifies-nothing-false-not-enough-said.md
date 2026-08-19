---
title: "\"Grounded\" certifies that nothing false was asserted, not that enough was said"
date: 2026-08-19
status: measured
arm: grounded-but-incomplete
---

## The question the stage accounting left

The renderers here format a fixed template, so nothing is ever omitted by choice
— which is why the last finding flagged that a renderer having to **select** what
to say would be a different problem. That raised a question no check in this repo
answers: `ungrounded` verifies that everything *asserted* is supported. What
about what is left **out**?

## Measured under a citation budget

Rendering flood's answer while citing only the first `k` supporting facts, with
**grounding measured by the real check** on real paragraphs:

| budget | cited | grounded | **decision-complete** |
|---:|---:|---:|---:|
| 0 | 0.0 | 1.000 | 0.000 |
| 4 | 4.0 | 1.000 | **0.000** |
| 8 | 8.0 | 1.000 | 0.000 |
| 16 | 16.0 | 1.000 | **0.529** |
| all | 28.5 | 1.000 | 1.000 |

**Grounding is flat at 1.000 across every budget.** A paragraph citing a strict
subset of true claims asserts nothing false, so there is nothing for the check to
catch. Decision-completeness — can a reader of the paragraph alone rebuild the
answer? — runs from 0.000 to 1.000 over the same range.

The axes are independent by construction: `ungrounded` inspects what is
**present**, and omission is a property of what is **absent**.

## And it is not hypothetical — the shipped renderer is at 0.000

| | |
|---|---:|
| claim citations per paragraph | **2.0 of 28.5** |
| grounded | **1.000** |
| decision-complete | **0.000** |

Every "grounded 1.000" figure in this repo describes a paragraph citing **7%** of
the claims, from which the answer cannot be reconstructed.

**This is not a defect in the renderer.** It is a summary and was never designed
to be reconstructible; a paragraph reciting 28 facts would be worse output. The
defect is in what the number was taken to mean. "Grounded" has been quoted as
though it certified the *explanation*, and it certifies only that nothing false
was said.

## What shipped

`incomplete(answer, case)` — the companion check. It rebuilds a world from the
claims the paragraph actually cites, re-solves, and reports the kinds whose
absence changes the answer. Two tests pin it: the shipped renderer is grounded on
every case and complete on none, and the check is satisfiable by citing
everything, so it is measuring something rather than always failing.

## The pattern, now three times

- `ungrounded` certifies consistency with the world **as read**, not truth.
- `role_assignment_forced` means the roles were not guessed, not that the answer
  is right — 0.664 on another surface.
- `ungrounded` certifies that nothing false was **said**, not that enough was.

Each time the check was correct and its **name** promised more. The recurring fix
is the same: name the thing computed, carry the counter-example in the docstring,
and write a test asserting the gap exists so it cannot quietly close.

## What would refute this

- Decision-completeness as defined is strict: it demands the answer be
  *rebuildable*, which is a higher bar than a human explanation usually meets. A
  weaker notion — "cites every claim whose deletion changes the answer" — would
  be more forgiving and is the version worth building if this is ever used as an
  objective rather than a diagnostic.
- The paragraph also carries `flow:` citations to computed routes, which
  `incomplete` does not count. A reader following those sees the route but still
  cannot check the bridge limits or the flooding, which is why the substantive
  conclusion stands.
