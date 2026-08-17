---
date: 2026-08-16
author: lead
status: idea
related: [2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name]
---

# SoftReason: the interface complaint this repo already has, answered by an architecture

[arXiv:2607.20402](https://arxiv.org/abs/2607.20402), AbdAlmageed, 2026-07-22.
Facts carry soft truth values, and logical closure becomes a differentiable
analogue of the immediate-consequence operator `T_P`, iterated to a fixpoint over
predicate embeddings and latent composition channels.

Ignore the differentiability — the neural half is a control here and stays off.
The part worth taking is that **the output of a soft `T_P` fixpoint is a
distribution over conclusions, natively.** Every rule-based model in this repo
emits an answer plus a scalar `c` and spends it as `(1-c)·backoff + c·votes`, and
[[2026-08-13-a-ranking-is-a-property-of-a-metric]] is the bill: a model that
knows the answer is one of ten has argmax accuracy 0.1, hands 90% of its mass to
a unigram, and throws away about 3.3 bits. Accuracy and bits then rank the models
close to inversely, and every published ranking was an accuracy ranking.

A soft-`T_P` model would be the first here whose *native* output is the quantity
the bits metric asks for. Concretely and on CPU: weighted facts, a rule set with
per-rule reliability, iterate `T_P` to a fixpoint under a t-norm, read the
conclusion masses off directly instead of picking an argmax and inventing a
confidence for it.

**The prediction worth writing down before anyone runs it:** this should be the
best `label_bits` model in the repo and should *not* be near the top on
`label_acc`, because the fixpoint spreads mass over everything derivable rather
than committing. If it wins on both, suspect the harness before believing it. If
it wins on neither, the interface was not the constraint and the 3.3-bit
argument above is wrong — which would itself be worth knowing, since that
argument is currently load-bearing in `RESEARCH_LOG.md`.

`frontier-001`'s rule set is a plausible source for the rules: it already emits
guarded implications with verified precisions, which is a rule base with
reliabilities attached.
