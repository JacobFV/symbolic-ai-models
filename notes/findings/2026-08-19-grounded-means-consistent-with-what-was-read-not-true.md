---
title: "\"Grounded\" means consistent with what was read, not true"
date: 2026-08-19
status: measured
arm: honest-milestone
---

## Re-running the north star with every prop removed

`scripts/milestone_end_to_end.py` is the programme's headline measurement — $ per
solved episode with the reader in front. It is measured on a surface that three
findings this week showed to be doing much of the work: it reads with
`read_signature` (whose 1.000 is hard-coded paragraph indices), on **grouped**
paragraphs with **section headings**, against a distractor whose phantom edge
joins regions appearing nowhere else.

`scripts/honest_milestone.py` re-runs it with all three props off — V=4,
interleaved, `hard_distractors=True` — and with the readers that now exist. The
old script is untouched; its numbers are published.

| system | claim R | task acc | $/correct | grounded |
|---|---:|---:|---:|---:|
| oracle world (ceiling) | 1.000 | 1.000 | 1.78e-08 | 1.000 |
| **signature+content** | **0.998** | **0.500** | 3.69e-08 | 1.000 |
| signature/roles | 0.861 | 0.000 | inf | 1.000 |
| signature/index (published) | 0.117 | 0.000 | inf | 1.000 |
| rules | 0.313 | 0.000 | inf | 1.000 |
| lexical cue routing | 0.313 | 0.000 | inf | 1.000 |
| oracle, no datalog | 1.000 | 0.818 | 3.32e-08 | 1.000 |
| oracle, no SMT | 1.000 | 0.500 | 2.57e-08 | 1.000 |
| oracle, no ASP search | 1.000 | 0.864 | 1.56e-08 | 1.000 |

Three results, in increasing order of how much they matter.

### 1. Reader loss now matches the largest kernel loss

| loss against the 1.000 ceiling | |
|---|---:|
| reader (signature+content) | **0.500** |
| kernel, no SMT load check | **0.500** |
| kernel, no datalog reachability | 0.182 |
| kernel, no ASP route search | 0.136 |

The published table concludes the opposite — reader loss **0.000**, kernel losses
up to 0.500 — and reaches it on the propped surface. $/correct rises to 2.1× the
oracle's: the spend is nearly identical, what changes is how many correct answers
it buys.

### 2. Claim recall is the wrong reader column

`signature+content` scores **0.998 claim recall and 0.500 accuracy**. Its failure
is a claim it **adds** — the phantom link — and recall cannot see a false
positive. The milestone reports recall as its reader-quality column, so on an
honest surface that column says "nearly perfect" about a reader getting half the
answers wrong.

### 3. "Grounded 1.000" certifies less than it sounds like

Grounding reads 1.000 in every row, including the rows that are half wrong. That
is not a bug in the check; it is its **scope**, and the scope had never been
stated.

`ungrounded()` builds its admissible edges from `report` — the routes the flow
computed **from the world it was given**. When that world came from a reader, a
route over a claim the reader *invented* is self-consistent and passes.

Demonstrated, seed 1 on the hard-distractor surface:

> **truth:** no vehicle can make the delivery — the correct answer is empty
> **rendered:** *"2 vehicles can make the delivery: truck_0, truck_1. … truck_0
> runs region_0 to region_3."*
> **`ungrounded()` returns `[]`.**

`region_0 to region_3` is a road that exists in no claim of the true world. A
false claim reaches the user as a **fully grounded sentence, over a non-existent
road.**

So the property is **internal consistency with the world as read**, not truth. It
catches renderer errors — invented numbers, false orderings, a paragraph
contradicting the structured answer — and it **cannot, by construction, catch
reader errors**. Quoting "grounded 1.000" as a safety property is quoting the
wrong thing unless the world is the oracle's.

That scope is now in `ungrounded`'s docstring and pinned by
`tests/test_grounding_scope.py`, which asserts **both** halves: that a grounded
paragraph can walk a non-existent road, and that a paragraph contradicting the
structured answer is still rejected. The second is what stops the first reading
as an excuse.

## Why this was worth finding rather than assuming

I nearly printed the opposite. The script's first draft ended with *"grounding
intact — a false claim does not reach the user as a grounded sentence"*, which is
exactly the reassuring line the number invites. It took reading `ungrounded`'s
edge construction to see that the guarantee runs against the read world, and one
demonstration to confirm it.

## What would refute this

- A grounding check that compared against the **true** world would catch this —
  but nothing downstream of a reader has access to the true world, which is the
  whole difficulty. A check that could would be a different and stronger
  component, and worth building only with that framing.
- The `test_grounding_scope` demonstration depends on the reader inventing a
  link. If the reader is strengthened so it no longer does, that test should be
  **replaced** rather than deleted — the scope claim survives the reader
  improving.
