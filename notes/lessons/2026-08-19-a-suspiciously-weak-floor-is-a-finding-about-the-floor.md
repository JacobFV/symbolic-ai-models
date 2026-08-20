---
title: A suspiciously weak floor is a bug report, not evidence that the task is hard
date: 2026-08-19
cost: would have published a +0.266 lift that is +0.065
---

## The mistake

I wrote a floor for open-vocabulary occupation reading: match *"is/was a/an"*,
then take the proposed candidate at that position. It scored **0.016** on a
corpus of biographies — text so formulaic that *"X (born 1953) is a British
politician"* is close to a template. I read 0.016 as "the pattern does not work
here" and moved on to quoting the learned reader's lift over it.

The floor was **built to fail**. The regex ended in a non-greedy modifier group,
`(?:[a-zA-Z][\w-]*\s+){0,2}?`, which prefers to match *nothing*, so the search
position landed immediately after *"is a"* — and then required a candidate to
start within two characters. *"is a British former professional racing cyclist"*
carries 34 characters of modifier before its head noun. The floor could only ever
fire on a bare *"is a cyclist"*.

Widening the window to 60 characters and taking the longest candidate inside it:
**0.016 → 0.223**, a factor of fourteen. Nothing about the model changed. The
headline lift went from **+0.266 to +0.065**.

## Why it nearly shipped

Because a low floor is *comfortable*. Every incentive in a write-up points the
same way: the floor is the thing the result is measured against, so a weak one
makes the result look strong, and the number arrives already agreeing with what
you wanted to say. `RESEARCH_LOG.md` has this failure twice already — `rgt`'s
"+0.587, first of nineteen" over a floor 0.065 too low, and the 0.722 copy
ceiling that every label lift should have been read against.

The existing guard — *audit the floor before quoting a lift* — is the right rule
and it did not fire, because I had **written** the floor and therefore believed I
had audited it. Authoring is not auditing.

## The guard

**When a floor scores near zero on a corpus where a human would score high, stop
and read the floor's code before reading anything else.** The question to ask is
not "is the model better than this?" but **"what is the largest score this code
could possibly produce?"** — run it against a handful of documents you have read
yourself and check it fires where you can see the answer.

Concretely, three cheap checks, in order of what they cost:

1. **Print what the floor matched on five documents.** Two minutes. It would have
   shown the window landing on *British* instead of *politician*.
2. **Ask whether the floor's ceiling is structural.** A pattern with a
   two-character window has a ceiling set by punctuation, not by the task.
3. **Build the floor to be embarrassing.** Give it the model's own candidate set,
   its own inventory, and the most generous decision rule you can defend. A floor
   you have tried to make win is a floor worth quoting.

## The reusable half

A floor is not a baseline you *report*; it is a hypothesis you are trying to
**refute** — the hypothesis that the task is trivial. A refutation attempt you
did not try to make succeed is not evidence. This generalises past floors to
every control in this repo: the permutation control, the copy ceiling, the
prior. If it did not cost you something to beat it, it did not test anything.

Related: [[audit-the-floor-before-quoting-a-lift]], and the five-times record in
`RESEARCH_LOG.md`'s believed-and-false table.
