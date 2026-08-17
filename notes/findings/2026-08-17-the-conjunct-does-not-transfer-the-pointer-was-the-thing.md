---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-corefers-entire-type-advantage-is-one-conjunct,
          2026-08-17-type-bits-was-never-compared-and-it-inverts-the-type-ranking,
          2026-08-13-a-control-that-could-fail]
---

# The conjunct does not transfer: `corefer`'s type advantage is the pointer, not the column it enters through

The previous finding priced `corefer-001`'s pointed-at-type conjunct at **+0.095
accuracy and 0.48 bits** — the whole of its +0.612 type lift, on a model that is
otherwise below the floor. It ended with a caveat written defensively:

> the pointed type is the output of a fitted coreference pointer, so "one
> conjunct" understates the machinery behind the term.

`frontier-typepoint` tests that caveat, and the caveat is the finding.

## The result

The ninth atom is the type of whatever visible node carries the symbol
`frontier`'s own **label** head predicts — the coreferent under its own
hypothesis, derived rather than fitted, and measured earlier at **0.4936** type
accuracy alone on the 62% of fills where such a node exists.

| | type acc | type bits | type lift | label acc / bits |
|---|---:|---:|---:|---|
| `frontier-typemass` | 0.8666 | 0.9342 | +0.046 | 0.4414 / 7.141 |
| **`frontier-typepoint`** | **0.8686** | **0.9070** | +0.062 | 0.4414 / 7.141 |
| `corefer-001` | 0.9458 | 0.3479 | +0.612 | — |
| `corefer-nopoint` | 0.8514 | 0.8300 | −0.065 | — |

| # | predicted | measured | |
|---|---|---:|---|
| 1 | `type_acc` into **0.88–0.92** | **0.8686** | **refuted** |
| 2 | `type_bits` improves on 0.9342 | 0.9070 | held, small |
| 3 | every label number bit-identical | 0.4414 / 7.141 | held |

**+0.002 of accuracy where `corefer` gets +0.095.** The same conjunct, in the
same position, in a model that already has every other atom of `corefer`'s
ladder — and it is worth a fiftieth as much.

## What this settles

**The value is in the pointer, and the conjunct is only where it enters.**
`corefer`'s pointer is a fitted coreference model — naive Bayes over pairwise
relational features, with a reranking stage, and it is the thing that model
*is*. Frontier's is a by-product of a label rule. Feeding the same column from a
0.49 pointer instead of `corefer`'s buys essentially nothing.

So the previous note's headline needs reading with its caveat promoted: *"one
conjunct"* is true of the arithmetic and false as an explanation. The honest
statement is **"the type head's ceiling is set by the quality of the pointer
behind its pointed-type conjunct"**, and both rows are now on the record — 0.49
pointer → +0.002, `corefer`'s pointer → +0.095.

It also closes the line I have been pushing for several rounds. Four variants
gave `frontier`'s type head its own knobs, its own atoms, a fitted gate and now a
pointer conjunct, moving it 0.8633 → 0.8686 in accuracy and 1.0316 → 0.9070 in
bits. **It needs a coreference model, not another column**, and building one
inside `frontier` would be building `corefer` inside it.

## What would make this wrong

The derived pointer takes the *lowest-indexed* visible node carrying the
predicted symbol, with no ranking among candidates. `corefer` chooses among them
with a fitted reranker. So this measures "a bad pointer's conjunct is worth
little", which is the intended claim — but it does not separate *bad pointer*
from *no ranking among equally-labelled nodes*, and a cheap reranker on the same
candidates would. That is unrun and is the honest limit of the result.
