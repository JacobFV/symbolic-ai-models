---
title: The gap was not lexical — a thesaurus is worse than no words at all
date: 2026-08-19
status: measured
arm: wordnet-expansion
---

## What this was supposed to do

[[2026-08-19-the-empty-cell-is-filled-by-five-words-of-flooding]] measured a
**0.382** gap between what a hand-declared anchor vocabulary achieves (1.000) and
what it achieves against phrasings written to evade it (0.618, exactly its
no-vocabulary floor). That gap is the value of having the right word, and it was
recorded as the justification for a lexical resource: *"WordNet or a
distributional resource would be earning its place against a number rather than
being reached for first."*

So WordNet was installed and the expansion procedure fixed **before** scoring it,
in `predictions.jsonl`: every synset of every anchor, plus direct hyponyms,
direct hypernyms and derivationally related forms. No hand curation.

| role | tokens before | after |
|---|---:|---:|
| depot | 6 | 507 |
| flooded | 6 | 224 |
| needs | 5 | 593 |

## What happened

| phrasings | vocabulary | grouped | interleaved |
|---|---|---:|---:|
| original | empty | 0.765 | 0.618 |
| original | **tight (17 tokens)** | **1.000** | **1.000** |
| original | wordnet (1,324) | 0.882 | **0.735** |
| adversarial | empty | 0.765 | 0.618 |
| adversarial | tight | 0.765 | 0.618 |
| adversarial | wordnet | 0.676 | **0.588** |

**It recovers nothing and breaks what worked.** Of the 0.382 available it
recovers **−0.029** — it is *worse* than having no vocabulary at all on the
phrasings it was brought in to handle — and it costs **−0.265** on the wording
the seventeen hand-declared tokens handled perfectly.

Filtering does not rescue it. Dropping every token appearing under more than one
role (14, 39 and 23 pairwise overlaps) gives:

| vocabulary | original | adversarial |
|---|---:|---:|
| tight | **1.000** | 0.618 |
| wordnet | 0.735 | 0.588 |
| wordnet, shared dropped | 0.794 | **0.412** |

Filtering helps the original set slightly and makes the adversarial set **much
worse**, because dropping shared tokens removes the ambiguity that was acting as
a brake: a sentence matching two roles returns "" and falls through to
elimination, where a sentence matching one *wrong* role is assigned confidently.

## Why, and this is the part that generalises

**The tight vocabulary's value was precision, not coverage.** With six words a
match is almost certainly right. With five hundred, most matches are spurious,
and a confident wrong role is worse than no role — it pre-empts the elimination
that would otherwise have got it right.

The earlier adversarial test found the tight vocabulary degrades to *exactly* its
floor and never below, and named that as the arm's virtue: **its failure mode is
silence, not error.** Automatic lexical expansion trades precisely that away. For
a component feeding a symbolic pipeline, where a wrong claim propagates and a
missing one merely fails to help, **precision dominates coverage** and a bigger
lexicon is a worse one.

**And the gap was never lexical.** The adversarial phrasings name the roles by
*consequence and function*:

> flooding as *"nothing gets through"*, *"written off"*, *"traffic has ceased"*
> a depot as *"where the fleet sleeps"*, *"the yard"*, *"crews sign on"*
> a need as *"called in an order"*, *"an appeal"*, *"they are out"*

A thesaurus bridges *flood → inundate*. It does not bridge *flood → nothing gets
through*, because that is not a fact about words. What settles these is knowledge
of **what a role does** — a depot is where vehicles are kept, flooding is what
makes a region unroutable — which is the *kernel's* semantics, not a
dictionary's.

## Where this points

The front moves from "get a better lexicon" — now closed by measurement, in the
strong form that more words are actively harmful — to **letting the reader emit
consequences and the kernel bind them**. The reader can see that a sentence says
something about a region being unusable without knowing the word *flooded*; the
routing kernel already knows that an unusable region is what `flooded` means to
it. Binding those is a different mechanism from matching words, and it is the one
the evidence now points at.

That also rhymes with the ambiguity machinery already built and with directive
19: emit what is known, let the kernel decide, rather than collapsing to a role
name the text never used.

## What would refute this

- A distributional resource (embeddings) rather than a taxonomic one might bridge
  *flood → nothing gets through* where WordNet cannot, since the relation is
  situational rather than taxonomic. That is a real and untested alternative, and
  it is the one thing this finding does **not** rule out. It should be measured
  before the lexical route is called closed in full generality.
- A precision-weighted expansion — keep an expanded token only if it is rare in
  the corpus outside its role's sentences — would test whether precision alone is
  the fixable part. Untried.

---

## Correction, 2026-08-19: the 0.618 baseline is 0.710 at 400 seeds

Every row above quoting **0.618** is an n=34 reading of the all-adversarial
interleaved cell, which is **0.710** at 400 seeds (grouped stable, 0.765 →
0.758). The comparisons in this note are all *against* that baseline and all use
the same 60 seeds, so the **rankings and the conclusion are unaffected** — but
the absolute figures are 0.09 low, and the "exactly its no-vocabulary floor"
identity is guaranteed by `_verify_adversarial` rather than measured.

The thesaurus result is unchanged and is now better explained: a vocabulary that
reaches a sentence it was not written for costs **−0.290** against having no
vocabulary at all (`2026-08-19-a-vocabulary-is-worse-than-none-when-it-is-confidently-wrong.md`).
"Worse than no words" is the general case, not a quirk of WordNet.
