---
title: The reader exists, and the surfaces that proved it are exhausted
date: 2026-08-19
kind: status
---

A programme-level assessment after the session that built the learned language
boundary. Every number is cited from a note under `notes/findings/`; this
introduces no measurements.

## Where we are

The critical path the user set has **steps 1–6 and 9 done**, and the thing they
were for exists: a reader with **no domain lexicon in its source**, fitted three
times from aligned `(sentence, claim)` pairs, that reads all three generated
domains at 1.000 claim F1 and 1.000 end-to-end — above every hand-written reader,
including the ones written while looking at these exact surfaces
[[learned-reader]]. That is the first time this repo has had a text→world
component that was not a person's pattern set.

Three claims are narrower than they sound.

**The 1.000 was a vocabulary measurement.** Renaming every entity to an unseen
form takes all three domains to 0.000. These corpora contain about ten distinct
names, so nothing in the fit could establish that `region_*` is a *kind* of name.
One augmentation fixes it — rename per document, the shape becomes productive,
renamed test recovers to 0.955 / 1.000 / 0.994 — and the union fit is the one
that holds both ends, because augmenting alone destroys the memory carrying
solvency's unnumbered `group`.

**The proposed reader objective is refuted as implemented.** `L_reader = Σ sᵢ Lᵢ`
now has measured weights: `sₚ` by intervention, spread 6.6x in flood, and
rate-matched `sₚ^eff` where the reader's own share is deleted rather than one
claim (flood's `link` 0.150 → 0.625, ratio 4.17). Spending them is negative — one
cell of nine improves end-to-end, three lose 0.075 to 0.200 — and the mechanism is
that a margin-scaled update **over-predicts the upweighted class**, so the
objective protects a critical claim by inventing it (`needs` precision 1.00 →
0.79). The objective survives; the per-example margin scale does not.

**The surfaces can no longer discriminate reader designs.** Six training
documents reach 1.000 F1 in all three domains. There is no regime here where this
reader makes graded errors: it is exact, or defeated by a phrasing it has never
seen.

## How things progressed, including what it cost

The session's route was ABI → learned reader → controls → sensitivity → objective
→ persistence, and three of those steps were only worth anything because a
control fired.

- The **renaming control** converted a headline into a diagnosis. Without it the
  repo would now claim a learned reader that reads three domains perfectly.
- The **observational estimate of `sᵢ` was impossible and looked merely weak** —
  AUC never above 0.63, and exactly 0.500 for the load-bearing claims, whose
  recall is 1.000 everywhere. No variance, no ranking information. Intervention
  was the only estimator, and it took an hour to see that.
- **Paragraph-granularity persistence measured nothing** and reported 1.000
  across the board. Every reference in these surfaces is paragraph-local.

Three implementation bugs cost real time and are recorded as mechanisms: an
averaged perceptron whose clock counted mistakes rather than examples (0.796 →
1.000 on one line); a mention history that advanced only on claim-bearing
sentences, losing precisely the antecedents the generator wrote as scaffolding;
and a renaming control implemented by string substitution, which shifted every
span offset and read as catastrophic reader failure.

## Trajectory

**Do:** take the reader to real text, where the errors are graded and the
objective can be tested properly. The persistence result says what the interface
needs and it is small — the entire cross-document state is the **mention
history**, which buys a claim-for-claim identical world at 8.3x less reading than
re-parsing per arrival, with minting surviving the split unaided.

**Stop:** fitting anything else on these generated surfaces. Six documents
saturate them. Any further reader comparison here measures the corpus.

## How this fits the narrative

Symbolic AI's post-mortem names the **knowledge-acquisition bottleneck** as the
thing that killed it: the world had to be entered by hand. This session's result
is a small, specific counter-example — a component that acquires the mapping from
text to a typed, n-ary, bitemporal world IR *from examples*, with the domain
inventory, the names, the role signatures, the units and the temporal envelope
all induced. It is not a refutation of the bottleneck; the supervision came from
a generator that knew the answer. But it locates the bottleneck precisely: the
expensive input is **aligned spans**, not rules, and alignment is the thing real
corpora might supply.

It also sharpens the brittleness charge rather than answering it. The renaming
collapse is brittleness of exactly the classic kind, and the fix was data
augmentation rather than a better representation — which is the neural
tradition's answer, arrived at from the symbolic side.

The claim that is genuinely new here is the persistence one. A neural LM rebuilds
its world from the prompt on every query; this maintains one, incrementally,
identically, and the state it needs to do so is a list of names.

## What should make an outside reader sceptical

- **n = 40–120 held-out documents** per arm, generated, one generator per domain.
- **Four phrasing variants.** Held-out phrasings are much harder: F1 0.850 /
  0.754 / 0.770 and end-to-end 0.567 / 0.583 / 0.333.
- **The repo has overturned its own headlines repeatedly**, and this session
  overturned one of its own within the hour.
- **The perceptron is not a scaling claim.** Whether these mechanisms hold with a
  neural encoder and calibrated scores is untested, and the sensitivity objective
  specifically needs calibration to be tested at all.
- **Nothing here is real text.** The real-text arms of the same session measured
  extraction at chance against critical error mass at 0.946, and no generated
  result touches that.
