---
date: 2026-08-13
author: lead
status: open
related: [2026-08-13-is-the-chinese-score-grammar-or-a-fingerprint, 2026-08-13-compositional-parser]
---

# Route on language instead of asking one parser to be multilingual

Language identity is a fact about the *situation*, not about the string. Put it
above the parser: the reasoning engine determines which language it is in, and
the parser is a specialist that gets told. Each language gets its own parser.

## Why this is not just a convenience

The curriculum's **graph is byte-identical across languages** — same seed, same
term, different rendering. So per-language parsers are trained on *the same
terms* with different surfaces: an exact, unlimited parallel corpus, which almost
no real setting has.

That changes what "learned grammar, not words" can mean.

- **Now:** train English, parse Chinese, report the drop. `cky-001` keeps 0.06 of
  its bracket F1, `template-002` keeps 0.46.
- **Under routing:** ask whether the seven induced grammars are **the same object
  up to relabeling**. That is a structural comparison of the learned artifacts
  rather than a score drop, and it is a much stronger claim.

Two more things become available:

**The invariant becomes learnable, not only testable.** One term parsed in seven
languages gives seven derivations; what is common across all seven *is* the term
structure and what differs is realization. Direct supervision for the
grammar/surface split, which no monolingual setup provides.

**The real generalization test moves to a held-out language.** An eighth language,
never seen: can the system notice it is new, and bootstrap a parser from the
shared grammar plus a small lexicon? That is closer to what a learner does than
transfer is.

## What it costs, and the trap

Routing makes the *current* cross-language diagnostic vacuous — a Chinese parser
trained on Chinese will of course score well, and the thing that made
`cky-001`'s 0.06 informative is gone. Routing relocates the question; it does not
answer it. The replacement (grammar alignment) needs machinery that does not
exist yet.

**The trap:** supplying language as ground truth hides a failure mode. You never
find out that the parser would not have noticed it was in the wrong language, and
deployment has no oracle. So **language ID must be measured as its own head with
its own floor**, even when it is supplied at parse time. That is the difference
between factoring a subproblem out and assuming it away.

## The trap, priced

`scripts/language_id_head.py` scores language ID as its own head, since this note
insists it must be. Character-trigram nearest centroid, fitted on training seeds,
2,506 evaluation prompts: **0.8388 against a 0.1429 majority floor, +0.8119
lift.** Chinese, `symbols`, Spanish, Turkish and Swahili are 0.96-1.00; english
and english_synonym are 0.377 and 0.578, and 342 of the 404 errors are those two
confused with each other, because they render 511 of 537 prompts byte-identically.

So supplying language as ground truth is nearly free for five packs and is a
genuine oracle for one distinction — the system could not acquire it from the
surface at any quality. Any result that leans on separating english from
english_synonym is leaning on information that is not there.

## What would settle it

Induce a grammar per language on the same terms, then score the *alignment*
between grammars: is there a bijection on nonterminals under which the production
sets agree? If English and Turkish align at high rate while English and a
shuffled-control grammar do not, the grammar is genuinely shared and only the
lexicon is not. `symbolic_ai_parsers/treebank.py` already recovers spans, and
surface order is already stored separately from graph slot — the agent noted
Turkish's verb-final rendering is one extra production, not a new predicate,
which is exactly the evidence this would quantify.

Refuted if per-language grammars align no better than a control pairing.
