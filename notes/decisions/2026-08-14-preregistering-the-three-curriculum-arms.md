---
date: 2026-08-14
author: agent-kg-seam
status: provisional
related: [2026-08-14-semantic-constraint-from-a-knowledge-graph,
          2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach,
          2026-08-13-a-control-that-could-fail,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# Pre-registering the three curriculum arms, before the sweep lands

Written while `runs/kg179-{base,wordnet,shuffled}` are still running, so the
reading cannot drift toward whatever the numbers turn out to be. That drift has
happened twice here — the `gru` curve was recorded as "flat" from six noisy
points because flat was the answer already written down.

## What is being compared

Three arms, **the same 179 lessons in each**, the same models, the same config
(`configs/kg179.toml`), the same 20 training and 4 eval episodes per lesson.

| arm | what differs |
|---|---|
| `base` | nothing. The curriculum every published number was measured on. |
| `kg:wordnet` | the closed word lists are bound under a vendored WordNet projection, under a dependency DAG |
| `kg:wordnet-shuffled` | the same, under a degree-preserving edge permutation of that graph |

The manipulation is **symbols only**: zero of 716 measured episodes changed tree
shape, arity, scene size, coordinates or which node carries the answer. Coverage
is 54 of 179 lessons and **5.3% of graph node labels** — see the coverage
finding. Everything below has to be read against that denominator.

## What I expect, and how confident

**The dominant expectation is that the macro effects are small.** 5.3% of nodes
is the multiplier. If the graph is worth 0.10 of label lift where it reaches, the
table moves 0.005 — which
[[2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable]] says is
inside the noise band for `label_bits` and near it for `label_acc`. I do not
expect a headline.

The interesting quantity is therefore **not** the mean. It is the **ordering**.

### H1 — every arm's score drops relative to `base`

Confidence: high, and it means nothing on its own. A larger effective vocabulary
(13,810 candidate words instead of 6) makes label prediction harder by
arithmetic. A drop that is uniform across models is a fact about vocabulary size,
not about semantics, and the decision note names it as the *uninteresting*
outcome.

### H2 — reordering, and this is the experiment

Under `base`, symbol identity carries no information: `alice` and `frank` are
interchangeable and a red cube and a purple rod are equiprobable. Under
`kg:wordnet` the episode's whole lexicon is one neighbourhood of English — the
kinds are taxonomic relatives, an object's attribute comes from its own kind's
parts and substances, the verbs are the ones WordNet's frames admit for that
animacy.

So I expect models that can exploit **lexical and co-occurrence structure**
(`ngram-001`, `ctw-001`, `grammar-001`, and the memorising fallback inside every
non-`_pure` rule-based row) to lose *less* than models that treat symbols as
atoms (`routes-001`, `omegaclaw_flat-001`, the `_pure` VSA variants).

**The pre-registered statistic is the Spearman rank correlation of `label_acc`
across the 24 models between `base` and `kg:wordnet`.** Prediction: below 0.90.
A correlation at or above 0.95 means the curriculum got harder and told us
nothing about which method is right — the decision note's second refutation
condition, and I would report it as such.

### H3 — the control, which is the cheapest death

If `kg:wordnet` and `kg:wordnet-shuffled` produce the **same** ranking and the
same lifts, the gain (or loss) is density and degree, the semantics never
mattered, and this is an expensive way to make the curriculum harder.

**Threshold, fixed now:** the idea survives only if some model's `label_acc`
differs between the two KG arms by more than **0.010**, and if the sign of that
difference is consistent across the models that share a mechanism. A difference
below that on every row is a null, and I will write it up as a null with a
working control, which the brief and `CLAUDE.md` both say is a complete result.

I put the odds of the control matching at better than even, and here is the
reason, stated in advance because it is the strongest argument against the whole
line: **these models have no outside knowledge of English.** They train on this
corpus alone. A degree-preserving permutation preserves every statistic a model
that starts from zero could learn *within* an episode. The remaining asymmetries
are real but thin — the real graph's lemma strings correlate with taxonomy
position (shared affixes, morphological families), and its co-occurrence
structure repeats across episodes drawn from the same family in a way the
scramble breaks differently. If those are worth less than 0.010 of label
accuracy, the honest answer is that a KG curriculum needs a *pretrained* model to
pay off, and that is a finding about the models, not about the curriculum.

### H4 — renaming, and it is the sharpest instrument here

Today a permutation of all symbols is nearly free for a structural model,
*because symbol identity carries no information*. Under a KG it carries real
information. So:

**Prediction: the renaming drop grows under `kg:wordnet` relative to `base`, and
grows less under `kg:wordnet-shuffled`.**

This is the one place I expect a clean, mechanistic signal, because it does not
require a model to have learned anything about English — only that the
information it *did* learn is now attached to symbols rather than to shapes.

And it comes with the warning the decision note wrote first: **the old and new
renaming numbers are not the same measurement.** Under `base` the column asks
"did it memorise the vocabulary"; under a KG it asks "did it use the semantics".
Better question, different question. They must not be tabulated together without
that sentence attached.

## Which metric

Both, and reported together, because
[[2026-08-13-a-ranking-is-a-property-of-a-metric]]: `label_acc` and `label_bits`
rank these models close to inversely and every published ranking here was an
accuracy ranking that never said so. The primary statistic is `label_acc` and
the rank correlation is computed on it; `label_bits` and the renaming delta are
reported beside it, and where they disagree the disagreement is the finding.

## Floors

**Refitted per arm, never carried across.** The floors and the copy ceiling are
properties of the curriculum, and a KG arm has a different label distribution by
construction. `train.py` fits them from each run's own episodes, so this is
automatic — but the note records it because the published `copy_ceiling` 0.7216
was computed over `label_n` and quoted against a head scored over
`copy_scored_n` (0.7305 on its own denominator), and a ceiling carried into the
wrong arm would be that mistake with a new way in.

The `base` arm is **re-run rather than compared against `runs/full179`**, for the
same reason: that run used a different budget and a differently fitted
temperature, and comparing across it would put a harness difference inside the
curriculum effect.

## What is a slice here and what is not

Every arm runs all **179 lessons**. What is subset is the *model registry* — 24
rows, chosen to span mechanisms, with the three neural rows omitted because they
are 7,000 of the 11,900 seconds of `runs/full179` and the symbolic models are the
subject. A model subset changes which rows the table has; it does not change what
any row measures. A lesson subset would, and thirteen wrong readings in this repo
came from one.

Any per-lesson breakdown — including the tempting "restrict to the 54 lessons the
graph touched" — is a **slice**, may form a hypothesis, and may not be reported
as a result. If the macro table is null and the 54-lesson view is not, that is a
hypothesis for a second sweep, not a finding.
