---
date: 2026-08-14
author: agent-polyglot
status: open
related: [2026-08-13-one-parser-over-word-classes-transfers-the-class-identities-do-not]
---

Per-language `Treebank.coverage` predicts held-out parser transfer at **r =
+0.886** across 46 languages — better than untranslated share (+0.836) and far
better than script (−0.493), and it survives partialling the other two out
(+0.609). It is the strongest correlate in the whole multilingual run and it is
a property of a **span heuristic**, not of any parser.

And yet the one intervention on it did nothing. Script-aware segmentation raises
Chinese coverage 0.466 → 0.627 and Cantonese 0.491 → 0.685, and moves held-out
bracket F1 by +0.002 in 4 folds of 6.

One experiment is not enough to call a +0.886 correlate a passenger. What would
settle it is a **second, independent handle on coverage**:

- drop the greedy one-node-per-segment assignment in `Treebank._add` (a
  Hungarian solve, or simply allowing two predicates to claim one clause);
- score anchors by substring containment rather than whole-token equality,
  which is the failure mode for any language that agglutinates onto an argument;
- allow a node to align to a *pair* of adjacent segments.

Each moves coverage without touching the splitter. If the parse score stays flat
under all of them, "coverage is not causal" is solid and the interesting
question becomes what the shared upstream variable actually is. If any of them
moves the score, the segmentation arm was the odd one out and the null in
`notes/findings/2026-08-13-one-parser-over-word-classes-transfers-the-class-identities-do-not.md`
is about segmentation specifically rather than about coverage.

Worth doing before anything else in this area is built on the finding.
