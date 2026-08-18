---
title: "This residual needs judgement" is what a residual looks like before you understand it
date: 2026-08-18
tags: [lesson, effort, measurement]
---

## The mistake

On a name-normalisation task I wrote a rule, scored 0.8870, inspected the
misses, and concluded the rest needed world knowledge about company names. It
did not: 68.9% of the residual was one pattern my rule structurally could not
see, because it stripped only trailing tokens and the data puts legal forms in
the middle.

I fixed that, scored 0.9479, inspected the misses, and concluded *again* that
the rest needed world knowledge — this time formalised as "the labels must be
inconsistent, so no method reading the name can exceed some ceiling below 1.0".

Measured it. **Zero tokens are treated inconsistently.** `trust` is kept 254
times out of 254, `inc` dropped 4,125 out of 4,125. The ceiling is 1.0, and
fitting the strip set from half the data scores **0.9998 on the other half**.

## What it cost

Nothing this time, because both hypotheses were checked before anything was
published. But the second one was about to become a finding titled *"the
symbolic method cannot reach the ceiling at the low-context end"*, and it would
have been false, load-bearing, and flattering to a conclusion I had gone looking
for.

## The mechanism

A residual is opaque by construction — it is exactly the part the current method
does not explain. Staring at it produces a story, and the story is always about
the *domain* ("company names need judgement") rather than about the *method*
("my rule only looks at the end of the string"), because the method is the thing
one has already thought hardest about and therefore trusts.

Worse, "this part needs judgement" is **unfalsifiable as usually stated** and
sounds like sophistication. It concedes a limit gracefully, which makes it feel
like intellectual honesty rather than what it is: an untested claim about one's
own most recent attempt.

## The guard

- **Never conclude "this needs judgement" from inspection. Measure the
  ceiling.** For a label-mapping task that is one pass: is any input token
  treated both ways? If not, the ceiling is 1.0 and the gap is yours.
- **Before attributing a residual to the domain, ask what the method structurally
  cannot represent.** Trailing-only stripping cannot see a medial token. That is
  a property of the code, findable in a minute, and it accounted for two thirds
  of the first residual.
- **Fit before concluding.** A hand-written list is a hypothesis about the data,
  not a symbolic method's best form. Fitting it — with a held-out split and a
  minimum-count guard — is cheap and it moved 0.9479 to 0.9998.
- **Distrust a limit you went looking for.** I chose this task expecting the
  symbolic side to lose. Both times the residual "needed judgement", it happened
  to confirm the thing I had set out to show.
