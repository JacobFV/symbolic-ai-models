---
date: 2026-08-13
author: lead
status: open
related: [2026-08-13-language-id-above-the-parser]
---

# Condition rules on language, do not bucket parsers by it

Supersedes the one-parser-per-language reading in
[[2026-08-13-language-id-above-the-parser]]. Bucketing throws away what the
languages share, and they share a great deal — composition, consolidation,
abstraction and association rules held in common through descent. The design is
**one rule set, selectively applied**, conditioned on context, on the structure
parsed so far, and on which language this is.

## The substrate already exists

`OmegaClaw.weigh(name, ctx, claim)` is exactly this shape: claws are rules,
`perceive` builds the context, `weigh` is the conditional gate with per-context
reliability fitted from data. The family has already measured that this is where
the value is — **+0.107 lift for learning which rule to trust in which context,
and ~0 for widening the rule set** (`omegaclaw_reach-001` added the most reliable
single claw ever measured here and still lost).

So the experiment is cheap: extend `perceive` to carry language (and later
partial parse state), let `weigh` learn per-language reliability, and register it
beside the existing model.

## The prediction that makes it falsifiable

A rule reliable across *all* languages is universal; one reliable only in a
subset is family-specific. So: **cluster the languages by their per-rule
reliability vectors and check the clustering against known genealogy.**

- If it recovers real language families, the system learned grammar structure
  rather than N lookup tables — and the shared-descent intuition is measured
  rather than asserted.
- If the clustering is arbitrary, rules are being fitted per language
  independently and the conditioning bought nothing that bucketing would not.

Refuted if per-language reliability vectors cluster no better than a control
pairing (shuffle the language labels and re-cluster).

## Caveat that does not go away

Language arrives as ground truth now and should eventually be an in-context
signal from higher mechanisms. Either way it must be **measured as its own head
with its own floor** — a supplied signal that is never scored is a subproblem
assumed away rather than factored out.
