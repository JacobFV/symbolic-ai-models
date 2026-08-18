---
title: Alignment-not-merge is load-bearing at 14.7% — and the composition I built to prove it is unpowered at n=3
date: 2026-08-18
status: provisional
tags: [federation, alignment, real-data, negative-result, composition]
---

## The question

Four real-data tasks, every one a single source. The architecture's central
claims are about **composition** — flow DAG, kernel ABI, alignment as uncertain
knowledge — and the only multi-kernel task ever run was on a world I generated.
So: **does the federation layer earn its complexity on real data, or is it
ceremony around a dict lookup?**

SEC EDGAR and GLEIF share no identifier: `kg:sec:cik:*` and `kg:lei:*` are
disjoint. The join has to go through names, which is exactly the case
`Alignment` was written for.

## Predictions

1. ~40% of SEC filers match at least one GLEIF entity.
2. ~25% of matched filers match more than one.
3. >60% of ambiguous filers have candidates with **different ultimate parents**,
   so collapsing the ambiguity corrupts the downstream answer.

## What I found — the part that holds

| | measured | predicted |
|---|---|---|
| filers matching ≥1 GLEIF entity | **50.8%** (4,076 / 8,021) | 40% — under-called |
| matched filers that are **ambiguous** | **14.7%** (598) | 25% — over-called |
| ambiguous matches spanning **>1 country** | **307 / 598 = 51.3%** | — |
| worst case | **HSBC HOLDINGS PLC → 35 candidates**, GB and JP | — |

The normaliser is the fitted one from `company_key`, which reaches 0.9998 held
out, so this ambiguity is a property of the **names**, not of a weak matcher.

**14.7% is load-bearing.** One filer in seven that matches at all matches
several things, half of those span jurisdictions, and a last-writer-wins merge
would pick one silently. That is a real answer to the architectural question:
`Alignment` earns its place, and it earns it on the first real cross-source join
this repo has ever run.

## What I found — the part that does not

Prediction 3 is **unmeasurable on this corpus**, and finding that out took
catching my own artifact first.

The first number I computed said **86.5%** of ambiguous filers have candidates
leading to different ultimate parents. It is meaningless: `closure_with_cycles`
returns the entity itself when it has no ownership edges, so *n* distinct
candidates give *n* distinct "roots" for free. The measurement was of the
candidates' distinctness, which was the premise.

Restricting to filers where at least one candidate has ownership data gives
46.7% on 152 — still inflated by the same self-root effect. Restricting to
filers where **every** candidate has ownership data gives:

> **n = 3, and all three agree.**

Which is not a measurement. The reason is sparsity, and it is stark:

| | |
|---|---|
| GLEIF entities | 3,348,427 |
| with any ownership edge | 137,686 (**4.11%**) |
| with a direct parent | 124,460 (**3.72%**) |

The composition "align a filer, then follow its ownership" needs a candidate to
be in the 3.7% that has an owner — and for the ambiguity to matter, it needs
*both* candidates of a pair to be. On 598 ambiguous filers that leaves three.

**So the two real-data tasks I built do not compose on this corpus.** Not because
the architecture cannot express the composition — it expresses it fine — but
because the populated subsets of the two sources barely intersect. That is a
fact about the corpus, and it is the second time today a capability claim has
turned on data density rather than on design.

## Bugs this found in the substrate

**`Alignment`'s namespace guard was wrong for every id in the corpus.** It read
the namespace as everything before the first colon, which suits `wn:dog.n.01`
and fails `kg:sec:cik:320193` versus `kg:lei:2138…` — a shared vendor prefix and
*then* the source. Both read as `kg`, so the guard refused **every genuine
cross-source alignment in 3.3 million entities.**

Fixed by taking the first two segments when there are three or more, and by
letting the caller state `left_source`/`right_source` explicitly. The heuristic
is documented as a guess, because it is one:

> `filesystem location is never identity` has a sibling: **a string prefix is
> never identity either.**

Nothing caught this before because every test used two-segment ids of my own
design. It took real bytes, which is the argument for real bytes.

## What would refute it

- The 50.8% coverage is a **name-equality** join. Real alignment would use
  country, entity type and filing history, and would both raise coverage and
  cut ambiguity. 14.7% is therefore an upper bound on ambiguity *for this
  method*, not for alignment in general — a better matcher makes the case for
  retaining alternatives weaker, not stronger.
- Precision is unmeasured. I know how many candidates a name attracts; I do not
  know how often the *right* one is among them, because there is no
  cross-source ground truth here. That is the honest limit of this finding.
- A denser ownership source (Orbis, Bureau van Dijk) would power prediction 3.
  Both are licensed, and this repo's `access: query_only_or_licensed` rule
  applies.
