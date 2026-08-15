---
date: 2026-08-14
author: agent-refuter
status: measured
related: [the-readout-survives-both-attacks-and-its-comparison-row-does-not,
          the-action-readout-clears-the-repair-floor-on-179-lessons,
          a-control-that-could-fail, the-harness-moves-more-than-the-models]
---

# Naming a confound in a caveat smuggles in its sign

## The mistake

`notes/findings/2026-08-14-the-action-readout-clears-the-repair-floor-on-179-lessons.md`
did the honest-looking thing. It found a 0.4229 gap, noticed that the two rows
also differed in a candidate cap, could not afford to measure it, and wrote the
confound down instead of hiding it:

> Some unknown part of the 0.423 is therefore truncation rather than readout,
> and I did not measure how much.

Read it again. "Some unknown part **of** the 0.423 is truncation" says the
truncation term is **positive and bounded by the gap** — that removing it would
shrink the 0.423 toward zero. That is a claim about the sign, made in a sentence
whose grammar is a disclaimer. Every reader, including the agent who set out to
refute it, carried away "the real readout effect is somewhere between 0 and
0.423".

Measured: `wrap` at 24 candidates scores **0.0767**, against 0.0851 at 8
(`runs/agents-readout179/wrap-24/` and `runs/agent-sweep/wrap/`, `repair`
`label_acc`, floor 0.2025 in both). Removing the truncation made the truncated
agent *worse*. The readout gap on identical 24-candidate sets is **0.4312**,
larger than the published 0.4229.

The confound was real and it was **asymmetric**, which is the part no amount of
reasoning would have got to: the same cap costs `graphread` 0.147 and costs
`wrap` nothing. "Unknown sign" was not even the whole of it — the effect has a
different sign for each of the two rows it was supposed to be a shared caveat
about.

## What it cost, and what it nearly cost

Nothing, this time, because the number was eventually taken. What it nearly cost
is the more useful part: a refuter arrived with the sign already assumed and
pre-registered thresholds shaped around it — *"the finding dies if the capped
row lands at or below the floor"* — all of which presuppose that the confound
can only eat the result. There was no pre-registered outcome for "the confound
adds to it", so had the primary run been skipped, the finding would have been
confirmed by a control designed around a false premise, and the 0.423 would have
been quoted forever as an upper bound on something it is a lower bound on.

The runtime argument that stopped the author is worth recording too. The
measurement was declined as "three times the forward passes on a run that
already took thirteen minutes". It took **395 s** — *less* than the 437 s of the
8-candidate run it was compared against. "Three times the forward passes" read
the multiplier off the cap without asking how often the cap binds, and it binds
on a minority of decisions: `Repair._nearby` offers up to 24 candidates but
frequently fewer, and the only full-run measurement of it here is a lower bound
of 387 of 2,703 (14.3%), from the decisions where `graphread-capped` lost every
vote. The cost of the experiment was estimated from the shape of the code rather
than measured, and the estimate was wrong by a factor of three in the direction
that avoided doing it.

## The guard

**A confound you have not measured has no sign, and a caveat must say so in
those words.** Concretely, three things:

1. Write the confound as a **two-sided** interval, never as a share of the
   effect. "Part of the 0.423 is truncation" is a sign claim; "the truncation
   term is of unknown sign and unknown size, and could be negative" is not.
2. When pre-registering against a confound, **write a threshold for the
   confound going the other way.** If the only outcomes on the page are "the
   effect shrinks by X" and "the effect shrinks by more than X", the
   pre-registration has assumed the answer and is not doing its job.
3. **Time the control before pricing it out.** A run declined on an estimated
   cost is a run declined on an unmeasured number, which is the same error one
   level up. Thirteen minutes was affordable; the estimate of thirty-nine was
   never checked and was wrong.

This is the sibling of
`notes/lessons/2026-08-13-a-control-that-could-fail.md`: that one is about
controls constructed so they cannot fail, this one is about caveats written so
they can only point one way.
