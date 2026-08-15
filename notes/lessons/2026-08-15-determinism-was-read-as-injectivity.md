---
date: 2026-08-15
author: agent-r090
status: measured
related: [2026-08-15-rung-fours-bound-points-the-other-way,
          2026-08-13-the-renderer-is-deterministic,
          2026-08-14-generation-is-parse-tree-infilling,
          2026-08-15-a-floor-outside-the-models-hypothesis-class]
---

# A bound was quoted in the direction that closed the question

## The mistake

Rung 4 of the infilling ladder — render the completed graph and score
`exact_match` — was never run, on this reasoning:

> The render is a deterministic function of the term, so
> `exact_match <= graph exact-match`, and the cheap side of that inequality is
> enough to answer the ladder's refutation condition.

Determinism gives the **other** implication. A function maps equal inputs to
equal outputs, so a graph that is exactly right renders to text that is exactly
right, and `exact_match >= graph exact-match`. The bound as written needs the
render to be **injective**, which nothing had measured and which the note it
cited — `the-renderer-is-deterministic` — does not claim; that note establishes
that no random draw happens on the render path, which is a different property.

## What it cost

The ladder recorded its last rung as answered when it was open, and the number it
recorded was wrong by more than 4x in the direction that made the conclusion
comfortable. A third of all scored fills have symbols that never appear in the
prompt at all, so `corefer-001`'s rung-4 number is somewhere in **[0.038, 0.15]**
at `mask_rate=0.15`, not "at most 0.038". The published gloss — *exact generation
is essentially unachieved* — is safe at `mask_rate=0.90`, where both ends are
about zero, and not established at the rate every other number in this repo is
measured at.

The shape is familiar: `audit-the-floor-before-quoting-a-lift` is the same error
one object over. There a comparison was quoted against a bound nobody had
checked; here a *bound itself* was quoted in the direction that made the question
go away.

## The guard

**A bound has two directions and only one of them follows from your argument.
Write the implication out before writing the inequality.**

- "f is deterministic" gives `x = y  ⇒  f(x) = f(y)`, so *sameness upstream
  bounds sameness downstream from below*.
- "f is injective" gives `f(x) = f(y)  ⇒  x = y`, which is what an upper bound
  needs, and it is a separate property that has to be argued or measured.

And the practical half, which is what actually catches it: **when a bound is used
to skip an experiment, ask which observation would sit between the bound and the
truth.** Here it was one question — *does every hidden symbol reach the page?* —
answerable with the prompt strings already carried in `batch.meta` and no new
run. A bound that closes a question deserves the same scepticism as a result that
closes one, and this repo already applies that to floors.

## Still open

The proxy that produced the upper end — *a symbol reaches the text only if its
own string is a word of the prompt* — has failure modes in both directions and
neither has been measured. So the interval's upper end is an estimate; the lower
end is the part that needs no assumption, and it is the one that contradicts what
was published.
