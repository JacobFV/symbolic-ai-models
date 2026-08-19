---
title: I inferred a capability boundary from a missing branch in my own code, and published it twice
date: 2026-08-19
author: lead
status: provisional
tags: [lesson, diagnosis, boundaries]
---

## The mistake

A reader failed on exactly one claim kind. The diagnosis looked clean: the
antecedent is named by a **superlative** — *"X is the lightest of them"* — and a
rule for *"lightest"* dies under paraphrase, so this must be where structural
methods stop and meaning begins. I wrote that up as a boundary:

> This is the first place in the front where a lexical resource or a learned
> component is not a shortcut but the only mechanism available.

Then I built a milestone table on top of it and published **reader loss 0.682
exceeds every kernel loss**.

The real cause was a **missing `elif`**. The naming sentence has signature
(1 vehicle, 0 quantities); my reader's quantities-paragraph branch handled three
other signatures and let that one fall through. One clause fixed it, consulting
no lexicon, and the reader went to **1.000 at every phrasing setting**.

## Why the wrong diagnosis was so convincing

Because it was **consistent with every number I had**. Capacity was the only
failing kind. The failing sentence really did contain a superlative. The
generalisation argument really is true of a *"lightest"* rule. Everything fit —
and the fit was to a story about the domain rather than to the code that
produced the numbers.

**A failure localised to one mechanism is evidence about my implementation before
it is evidence about the world.** I had the ablation that localised it and never
asked the cheaper question: *does my code have a branch for that case?*

## The guard

Before claiming a **capability boundary** — "this needs learning", "structure
cannot reach here", "the mechanism stops at X" — do the implementation audit
first:

1. **Enumerate the input shapes the failing path can see**, and check the code
   handles each. Here: four signatures in one paragraph, three handled.
2. **Ask what the fix would cost** if the boundary were *not* real. A one-clause
   fix is cheap enough to try before writing a boundary claim, and trying it is
   strictly faster than defending the claim later.
3. **A boundary claim is a negative existential** — *no structural method can do
   this* — and this repo has a standing rule that those are not established by
   checking the places you expected the thing to be. That rule was written for
   data files; it applies to mechanisms too.

Related: `notes/lessons/2026-08-18-i-searched-for-the-mechanism-and-the-file-was-named-after-its-purpose.md`
— the same shape, one level up: a negative existential asserted from an
incomplete search.
