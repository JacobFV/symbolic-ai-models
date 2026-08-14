---
date: 2026-08-13
author: lead
status: measured
---

# Accuracy and bits rank these models close to inversely

`label_acc` and `label_bits` have been in every `summary.json` since the
beginning. Only accuracy was ever quoted, and no published ranking said so.

| model | lbl acc | rank | lbl bits | rank |
|---|---:|---:|---:|---:|
| `grammar` | 0.187 | 14 | **6.09** | **1** |
| `ngram` | 0.170 | 17 | 6.41 | 4 |
| `corefer` | **0.357** | **1** | 6.95 | 6 |
| `omegaclaw_rank` | 0.356 | 2 | 8.09 | 11 |
| `brill` | 0.244 | 10 | 9.08 | 19 |

**The mechanism is the interface, not the reasoning.** Every rule-based model
spends its confidence as `c` in `(1-c)·backoff + c·votes`, and `c` was fitted as
an *argmax accuracy*. A model that knows the answer is one of ten and no more has
argmax accuracy 0.1, so it keeps a tenth of the mass and hands the rest to a
unigram — discarding about 3.3 bits of real information. Deciding well and
estimating well were made to trade off by the contract.

Fitting `c` as the mixture weight it actually is (`MassCalibrator`, by held-out
likelihood) is worth **+0.017 lift and 0.58 bits** on otherwise identical models.

**The third axis is renaming.** `ensemble-001` leads on bits and collapses
0.467 → 0.038 under a symbol permutation; `ptrgen` reaches 5.91 bits at −0.002.
Those are different capabilities and only one is what this repo is measuring.

**The rule:** quote accuracy, bits **and** renaming together, or say which one
you chose and why. Where two defensible metrics disagree, the disagreement *is*
the finding — report it rather than picking the flattering one.
