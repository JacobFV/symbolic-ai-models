---
date: 2026-08-14
author: agent-polyglot
status: idea
related: [2026-08-13-one-parser-over-word-classes-transfers-the-class-identities-do-not]
---

Conditioning the *rule weights* on language was a null (+0.003 in sample, +0.0001
held out, and the crc32 control lost 0.022). But the same run showed a clean
crossover that conditioning could actually exploit:

- in sample, the full class induction beats the one-class control (bracket
  0.130 vs 0.116) — the class identities are worth having when the language is
  in the mixture;
- held out, the one-class control beats it on every metric, 6 folds of 6 — the
  identities are a liability when it is not.

So the right conditioning variable may not be the rule weight at all. It may be
the **level of abstraction**: use the induced classes when the language is
known, collapse to the single frame class when it is not. The parser already
detects the novel case exactly (an unseen condition backs off to the global rule
set, and the out-of-vocabulary rate already switches on it), so the machinery
exists and costs one branch.

That would be "one rule set, selectively applied" in a stronger sense than
reweighting the same rules — the situation would choose *how coarse a rule to
apply*, which is nearer what `APPROACH.md` argues for than what was tested.

Register it as `polycky-003` beside `-002` and read it against `polycky-1class`
on held out and `polycky-001` in sample. It should be strictly better than both
if the crossover is real. What would refute it: matching `polycky-1class` held
out and `polycky-001` in sample is the *expected* result, so the finding is only
interesting if it also beats the crc32 control by more than the reweighting arm
did — otherwise it is another way of paying for a partition.
