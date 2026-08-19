---
title: Two readers, two axes, and an empty intersection
date: 2026-08-19
status: measured
arm: unsaturated-surface / interleaved-surface
---

## What was believed

`state.yml` recorded the flood surface as **saturated** — "a reader consulting no
content word reaches the oracle, so this benchmark no longer discriminates" — and
put the frontier at a surface without section headings and fixed paragraph
order, where "this same reader (position ablated) leaves 72 consistent worlds and
a bound deciding 0.0%".

Two halves of that were wrong, and the third is now measured properly.

## The headline was position, and it was worse than "position helps"

`read_signature` — the arm quoted at 1.000 with *zero reader loss* in the
milestone — branches on `pi == 0`, `pi == 1`, `pi == 2`, `pi == 3`. **Hard-coded
paragraph indices.** It knows the generator's five-paragraph template by
position.

`unsaturate()` drops the headings and shuffles paragraph order, remapping every
span offset so the alignment survives. Paragraph level *deliberately*: every
pronoun in this surface resolves inside its own paragraph, so reordering
paragraphs keeps every sentence **true**.

Non-empty accuracy, 60 cases:

| surface | signature/index | signature/roles | rules | lexical |
|---|---:|---:|---:|---:|
| as published | **1.000** | 1.000 | 1.000 | 0.088 |
| no headings | **1.000** | 1.000 | 1.000 | 0.088 |
| shuffled only | **0.000** | 1.000 | 1.000 | 0.088 |
| unsaturated | **0.000** | 1.000 | 1.000 | 0.088 |

- **The section headings are worth nothing.** No reader consulted them. They
  look like the giveaway and are not.
- **Paragraph order was worth everything** to the index reader: 1.000 → 0.000,
  claim recall 1.000 → 0.197.
- **Paragraph co-occurrence fully replaces it.** `read_signature_roles` reads
  paragraph *roles* off content — the paragraph carrying the masses owns the
  depot, the paragraph carrying the demand owns the needs site, every other lone
  region is flooded — and holds 1.000 while consulting no content word.

So the recorded "72 worlds, 0.0% decided" pessimism was an artefact: it came from
`signature_readings` flattening the document with `text.replace("\n\n", " ")`,
which discards paragraph **membership** along with paragraph **order**.
Membership is what carries the disambiguation, and it survives a reorder.

## The real frontier: grouping, and an empty intersection

Membership is still a template property. This generator puts every road in one
paragraph and every flood report in another; a real report does not.
`interleave()` destroys grouping too — every sentence in one paragraph, seeded
random order — keeping each pronoun glued to its antecedent so the document stays
true rather than merely hard.

Crossed with phrasing variation, non-empty accuracy:

| reader | V=1 grouped | V=1 interleaved | V=4 grouped | V=4 interleaved |
|---|---:|---:|---:|---:|
| rules (phrasings) | 1.000 | **1.000** | 0.000 | 0.000 |
| signature/roles | 1.000 | 0.000 | **1.000** | 0.000 |
| signature/index | 0.000 | 0.000 | 0.000 | 0.000 |
| lexical | 0.088 | 0.088 | 0.000 | 0.000 |

**The two mechanisms fail on orthogonal axes and their intersection is empty.**
The rules arm matches whole phrasings, so it does not care where a sentence sits
— and dies under paraphrase. The signature arm reads entity types, so it does not
care how a sentence is worded — and dies when structure goes. Neither is a reader;
each is one invariance without the other.

This is the honest statement of the front, and it is sharper than "the surface is
saturated": **what is missing is a reader invariant to phrasing *and*
arrangement at once.**

## What works in the empty cell: emitting, not collapsing

Directive 19 says do not collapse ambiguity merely to obtain a single world. In
the cell where every collapsing reader scores 0.000, the sound enumerating arm is
the only thing that does anything at all:

| arm | sound | decided | median worlds |
|---|---:|---:|---:|
| signature only | 1.000 | 0.000 | 72.0 |
| + value registry | 1.000 | 0.147 | 9.0 |
| + adjacency | **1.000** | **0.324** | **2.5** |

**Soundness is 1.000 on every rung** — the truth is always among the emitted
worlds — and the full arm decides 32.4% of cases where collapsing decides none.

One honest note on why adjacency still helps after interleaving, which I expected
it not to: the atom rule that keeps each pronoun with its antecedent — there to
keep the ground truth *true* — preserves exactly the adjacency that binds the
demand quantity to its site. The scramble cannot remove it without making the
document false, so this is a property of the task, not a leak in the experiment.

## What would refute this

- A reader scoring above ~0.1 in the V=4 interleaved cell would mean the surface
  is still saturated on both axes and the frontier is elsewhere.
- The alignment surviving both transforms is checked hard (20 tests): every claim
  span must quote the same text, no claim may be lost, no pronoun may be
  stranded, and claim kinds must actually stop clustering. If that machinery were
  wrong, every arm here would be scored against corrupted ground truth — the
  failure that has already cost this repo one withdrawn finding.
- The registry ablation is measured rather than assumed: emptying any one value
  vocabulary must damage `read_signature_roles`, which a test asserts.

## Correction to a published number

The emit table above first ran with `registry=None`, which means *no registry*,
and reported 72 worlds / 0.000 decided as though it were the arm's number. It is
the number with the arm's declared external knowledge switched off. The ladder is
now reported in full, which is the only honest form for an arm whose knowledge is
a declared input.
