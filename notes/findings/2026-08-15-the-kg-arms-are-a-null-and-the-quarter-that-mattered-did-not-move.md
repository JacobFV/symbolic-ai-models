---
date: 2026-08-15
author: agent-kg-semantics
status: provisional
related: [2026-08-14-preregistering-the-curriculum-arms,
          2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach,
          2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-the-label-score-is-a-copy-score,
          2026-08-15-the-copy-split-survives-and-its-floor-does-not,
          2026-08-14-a-kg-curriculum-may-need-a-model-that-knows-english]
---

# The four curriculum arms land as a null, and the non-copyable quarter is where it is cleanest

**Full 179 lessons in every arm; no lesson slice.** Four arms — `base`,
`kg:wordnet`, `kg:wordnet-shuffled`, `kg:wordnet-flat` — 15 models each, one
config (`configs/kg179.toml`), 20 training and 4 eval episodes per lesson.
The sweeps are `runs/kg179-{base,wordnet,shuffled,flat}`; the split below is
`scripts/copyable_split.py` re-scoring each run's own fitted model on the run's
own evaluation draw, with the assertion that the pooled number it reproduces is
the number the run published (it is, to 1e-9, on all 60).

Everything here is read against the coverage note's denominator: the graph
rebinds **5.2% of node labels** and touches 55 of 179 lessons, so an effect
confined to what the graph reaches arrives at the macro average multiplied by
about 0.05.

## The pre-registered statistic, first

[[2026-08-14-preregistering-the-curriculum-arms]] fixed the reading in advance.
Both of its decision rules are now answerable.

**H2, the reordering test.** Spearman rank correlation of `label_acc` across the
15 models, `base` vs `kg:wordnet`: **0.9964**. The pre-registration called
"below 0.90" the interesting outcome and "at or above 0.95" the outcome that
means *the curriculum got harder and told us nothing about which method is
right*. It is 0.9964. `base` vs `shuffled` is 0.9964 and `base` vs `flat`
0.9857. **There is no reordering.**

**H3, the scrambled control.** The threshold was: some model's `label_acc`
differs between the two KG arms by more than 0.010, *and* the sign of that
difference is consistent across models sharing a mechanism.

| | `kg:wordnet` − `kg:wordnet-shuffled`, pooled `label_acc` |
|---|---|
| mean over 15 models | **+0.0041** |
| models over the 0.010 threshold | 2 (`omegaclaw_flat-001` +0.0166, `workspace-001` +0.0144) |
| sign | 12 positive, 3 negative (sign test p ≈ 0.035 two-sided) |

Read on its own that is the threshold weakly met. Read with the split below it
is not, and the split is the reason this note exists.

## The measurement that decides it: `acc | not copyable`

`label_acc` is 72% a copy score — 72.2% of the scored fills in the `base` arm
sit on a visible node carrying the same label. A semantic constraint's whole
promise is the *other*
quarter, where nothing in the episode carries the answer and only a vocabulary
memoriser scores anything. An effect there is diluted four times over in the
pooled number, on top of the 0.05 coverage factor. So the pooled table cannot
see it and the split can.

**`acc | not copyable`**, and the floor is the structural floor from
`task.split_floor` computed per arm:

| model | base | wordnet | shuffled | flat | wn − shuf |
|---|---:|---:|---:|---:|---:|
| grammar-001 | 0.178 | 0.168 | 0.177 | 0.179 | −0.009 |
| ngram-001 | 0.154 | 0.144 | 0.149 | 0.152 | −0.005 |
| brill-001 | 0.137 | 0.128 | 0.138 | 0.141 | −0.010 |
| ctw-001 | 0.090 | 0.084 | 0.072 | 0.085 | **+0.012** |
| symbolalg-001 | 0.078 | 0.064 | 0.072 | 0.075 | −0.008 |
| omegaclaw_rank-001 | 0.063 | 0.065 | 0.062 | 0.066 | +0.003 |
| analogy-001 | 0.062 | 0.064 | 0.062 | 0.064 | +0.002 |
| vsa-002 | 0.056 | 0.050 | 0.052 | 0.060 | −0.002 |
| omegaclaw_flat-001 | 0.052 | 0.049 | 0.056 | 0.062 | −0.007 |
| workspace-001 | 0.032 | 0.030 | 0.024 | 0.024 | +0.006 |
| ptrgen-001 | 0.010 | 0.012 | 0.014 | 0.009 | −0.002 |
| corefer-001 | 0.003 | 0.003 | 0.003 | 0.006 | 0.000 |
| evidence-001 | 0.001 | 0.001 | 0.001 | 0.001 | 0.000 |
| routes-001 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| vsa_pure-002 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| **floor (structure only)** | **0.106** | **0.115** | **0.115** | **0.112** | 0.000 |
| copyable share of the scored draw | 0.722 | 0.719 | 0.712 | 0.716 | |
| scored fills | 5,233 | 4,949 | 4,992 | 4,897 | |

On the quarter the whole line was for, `kg:wordnet` − `kg:wordnet-shuffled` has
**mean −0.0013**, 4 positive, 7 negative, 4 exactly zero, and a largest
magnitude of 0.012. There is no consistent sign and no model clears the
threshold in a direction its mechanism shares. **The real graph and its
degree-preserving scramble are indistinguishable exactly where the effect was
supposed to be.**

The +0.0041 pooled mean is therefore not a semantic effect in the sense the
decision note meant: it lives entirely in the copyable bucket (mean +0.0033
there, +0.023 for `omegaclaw_flat-001`), which is the bucket where the answer is
already visible and the question is which visible node to point at. **It is real
enough to have a candidate mechanism and too small to be the headline**, and the
mechanism is the one
[[2026-08-14-a-kg-curriculum-may-need-a-model-that-knows-english]] named in
advance: in the real graph an episode's six words are lemmas from one taxonomic
family and share morphology, so they share subword pieces and a pointer has an
easier disambiguation; the scramble keeps the lemma strings and breaks the
correspondence. That predicts the effect should be largest for models reading
sub-symbol structure and it is not obviously so (`ctw-001`, the character model,
is +0.005 pooled), so it is a hypothesis and not a finding. Testing it needs an
arm whose lemma strings are permuted along with the edges, which nothing here
has run.

## The one thing that did move, and it moved the wrong way for the hypothesis

**The non-copyable floor rose, and every model's lift over it fell.** The floor
is a memorising context rule with no model in it; it goes 0.106 → 0.115 under
both KG arms and 0.112 under `flat`. So a knowledge graph *did* put predictable
structure into the non-copyable quarter — and

* it put the **same** amount in under the scramble (0.115 both), so what it put
  in is lexical concentration, not meaning: an episode whose six words come from
  one neighbourhood is easier for a context-conditioned prior whether or not the
  neighbourhood means anything;
* **no model captured any of it.** Only three of fifteen beat the non-copyable
  floor at all, and all three lose ground: `grammar-001` +0.072 → +0.053,
  `ngram-001` +0.048 → +0.029, `brill-001` +0.031 → +0.013 (lift over the
  arm's own floor, `base` → `kg:wordnet`).

A harder floor that no model rises to meet is
[[2026-08-15-a-floor-outside-the-models-hypothesis-class]] happening again, in a
new curriculum.

## What would have refuted this note, written in the pre-registration

* **A reordering** — some mid-table method becoming first because it can use
  semantics. Spearman 0.9964. Did not happen.
* **The control separating from its treatment** by more than 0.010 with a
  consistent sign. On the pooled metric two models do, on the metric that
  matters none do. Reported as a null.
* **A tree shape moving**, which would have made the arms incomparable. 3 of
  2,148 episodes, +0.026% of nodes, mechanism named — measured in the coverage
  note before any arm ran.

## Why the null was close to guaranteed, and this is the useful half

The pre-registration said the odds of the control matching were better than
even, for a reason that has nothing to do with whether semantic constraint is a
good idea: **these models have no outside knowledge of English.** The stronger
version of that argument, which this result is evidence for, is now written up
separately as
[[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]]: a
degree-preserving edge permutation does not weaken the learning problem, it
*relabels* it, so for a learner whose only input is the corpus the treatment and
the control are the same problem and the control cannot lose.

That makes this a null with a working control **and** a statement about the
instrument: the KG curriculum is a measurement of models that already know
something, and this repo has none. It does not license "semantic constraint does
not help".

## What this note does not say

It does not say a bigger or better graph would change the table — and the
companion note reports that the obvious bigger graph does not even improve the
*binding*: a vendored commonsense projection with 30,513 property assertions
fires the per-object constraint on 17% of scene objects against WordNet's 53%,
so its arms were not run.
