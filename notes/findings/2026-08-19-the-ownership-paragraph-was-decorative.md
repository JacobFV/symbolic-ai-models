---
title: The ownership paragraph was decorative, and no measurement could see it
date: 2026-08-19
status: measured
arm: solvency-hard-distractors
---

## Third domain, same defect, one level up

Flood's disused track was inert because the generator drew its endpoints from
**outside** the network. Scheduling's withdrawn machine was inert because it
carried **no capability**. Solvency's is *"A former subsidiary, sub_99, was
divested before the period and does not consolidate"* — and `sub_99` appears
**nowhere else**, so it is inert twice over: one entity, so it matches no reader
branch, and no filings, so admitting it would sum to nothing.

Pointing that distractor at something that matters found something bigger than a
distractor.

## `read_signature` never read the group structure

```python
elif len(ents) == 1 and money and dates:
    r.members.add(ents[0])          # <- a filing enrols its filer
```

So a **filing** makes you a member. Deleting the entire ownership paragraph — one
of the domain's two claim kinds — changes the answer on **0 of 200 cases**.

The reader was reported at **1.000 accuracy and 1.000 filing recall in all six
cells** of V × arrangement, and none of those cells could see this, because the
generator never files a figure for a non-member. The same inert-by-construction
pattern as the two distractors above, one level up: in the **reader's own logic**
rather than in the text.

`read_signature_consolidated` takes membership from the ownership claims alone,
and is registered beside the old one rather than replacing it.

## Neither fix works without the other

A divested subsidiary that **files**, plus a withdrawn figure dated at the
determination date. 200 cases, majority floor 0.550:

| arm | published | published + gate | consolidated | consolidated + gate |
|---|---:|---:|---:|---:|
| clean (default distractor) | 1.000 | 1.000 | 1.000 | 1.000 |
| hard, **cued** | 0.450 | 0.485 | 0.450 | **1.000** |
| hard, **uncued** | 0.450 | 0.450 | 0.450 | **0.450** |
| hard owns only, uncued | 0.485 | 0.485 | 0.485 | 0.485 |
| hard filing only, uncued | 0.515 | 0.515 | 0.515 | 0.515 |

**A strict conjunction.** The staleness gate alone buys 0.035; the consolidated
reader alone buys nothing; together they buy 0.550. The divested filer is
enrolled by *either* its filing (which only the reader fix removes) or its
ownership sentence (which only the gate removes), so removing one route leaves
the other open. Two channels, two checks, and the product is not the sum.

**And the uncued arm is unrepairable at 0.450** — *"sub_98 left the group in
April"* is semantically stale and carries no declared cue. That is the honest
floor of everything built today, asserted by a test so the 1.000 above cannot be
read as a solution.

## Quote the injection with the number

The spurious figure's **size** sets the damage, so 0.450 is a property of the
injection as much as of the reader. Dose-response, published reader, no gate:

| spurious figure ÷ threshold | accuracy | false TRUE | false FALSE |
|---:|---:|---:|---:|
| 0.05 | 0.630 | 4 | **70** |
| 0.10 | 0.665 | 33 | 34 |
| 0.25 | 0.515 | 97 | 0 |
| 0.50 | 0.450 | 110 | 0 |

**U-shaped, and for a reason.** The withdrawn-figure distractor is dated the
determination date, so it *replaces* the member's real filing under the
latest-by-date rule. A small spurious figure **lowers** the sum; a large one
raises it. That is the third instance in this repo of opposite-signed evidence
producing a U-shaped corruption curve, after scheduling's demand-vs-supply claims
— and the theory ledger already says a monotone form cannot fit one.

At 0.50 the reader answers **True on all 200 cases**, which is why the accuracy
lands exactly on the 0.450 true share. On the honest surface, the published
pipeline is **worse than answering "no" every time** (floor 0.550).

## What would refute this

- The distractors are two sentences written by me, and the uncued phrasings are
  the ones that matter and the ones I had the most freedom over.
- The 0/200 inertness of the ownership paragraph is parameter-free and is the
  claim to trust; everything downstream of the injection carries its size.
- `read_signature_consolidated` closes one enrolment route. It is not a safety
  property: an ownership sentence for a divested subsidiary still enrols it.
