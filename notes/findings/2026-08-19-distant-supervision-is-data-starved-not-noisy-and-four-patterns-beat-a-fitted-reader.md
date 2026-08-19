---
title: On real prose, distant supervision is data-starved rather than noisy — and four hand patterns beat a fitted reader 4x
date: 2026-08-19
status: measured
arm: real-text-reader
---

Every learned-reader number so far came from generated surfaces with **exact
span→claim alignment**, and the status note named that as the expensive input:
not rules, but aligned spans. This asks whether the alignment is necessary, on
168 Wikipedia company intros whose gold facts come from Wikidata and whose spans
nobody has ever marked.

Supervision is **string containment**: a sentence is labelled with relation `p`
if it contains a gold filler for `p`, and with nothing otherwise. No span, no
role, and the label is wrong whenever the string occurs for an unrelated reason.
That is what a real corpus can supply. Mentions are proposed by capitalised runs
joined across lowercase connectives — knowledge of English, the same category as
the tokenizer, because a name here is *Ministry of Communications*.

Three relations (`parent` P749, `country` P17, `headquarters` P159), 4-fold
cross-validation so every article is held out once, strict case-insensitive
equality against any gold filler. `runs/real_text_reader.json`.

## 1. It works, and it is four times worse than four hand-written patterns

| relation | coverage | correct | precision |
|---|---|---|---|
| `parent` | 0.411 | **0.101** | 0.246 |
| `headquarters` | 0.420 | 0.173 | 0.412 |
| `country` | 0.386 | 0.145 | 0.375 |
| `parent`, hand-written state-first reader | 0.601 | **0.393** | 0.653 |

**Predicted 0.30–0.45 for `parent`, and stated that below 0.15 would refute the
premise. It came in at 0.101.** On generated text with exact alignment the same
reader beat every hand-written reader; on real prose with distant labels it loses
to four patterns by 3.9x.

## 2. Where the loss is — three factors that multiply out

| relation | ceiling | gold string proposed | classifier recall | ranker \| label | product | measured |
|---|---|---|---|---|---|---|
| `parent` | 0.577 | 0.750 | **0.308** | 0.500 | 0.089 | 0.101 |
| `headquarters` | 0.452 | 0.882 | 0.360 | 0.667 | 0.109 | 0.173 |
| `country` | 0.482 | 0.879 | 0.187 | 0.643 | 0.058 | 0.145 |

- **The ceiling is 0.577.** Only 58% of articles contain a sentence with the
  gold parent string at all — distant supervision cannot see the rest, whatever
  the model. The hand reader's 0.393 is **68% of that ceiling**; this reader
  reaches 17%.
- **The classifier is the binding factor**, at 0.308 recall on sentences that
  *are* distantly supervised.
- The product reproduces the end-to-end numbers, so the decomposition is
  measuring the right three things.

## 3. Volume, not noise — tested and the test came back the unwelcome way

The learning curve is non-monotone (parent 0.282 → 0.179 → 0.308 at 31, 63, 126
training articles; `headquarters` *falls*, 0.560 → 0.560 → 0.360), which reads
like label noise: more articles bring more sentences where the string appears for
another reason.

So the noise hypothesis was tested directly with **multi-instance pruning** —
refit on the single highest-scoring sentence per (article, relation), the
standard at-least-one fix. There are 516 supervised sentences for 168 articles,
three per article for a fact stated once, so if noise were binding this should
help.

| relation | full distant supervision | multi-instance pruned |
|---|---|---|
| `parent` | 0.101 | **0.042** |
| `headquarters` | 0.173 | 0.123 |
| `country` | 0.145 | **0.042** |

Worse everywhere, and coverage collapses 0.411 → 0.214. **Discarding two thirds
of the positives starves it further, so the constraint is volume.** The
non-monotone curve was small-sample noise in a 42-article evaluation, not
evidence about the training labels — a reading I would have published had the
intervention not been available.

## 4. What this says about the bottleneck

The two halves of this repo now measure the same trade on the same task from
both sides:

- **generated text, exact alignment**: six training documents beat every
  hand-written reader.
- **real prose, distant labels**: 126 training articles lose to four hand
  patterns by 3.9x.

Hand-written patterns are a way of **injecting prior knowledge that substitutes
for data**, and on a 168-article corpus that substitution is worth 4x. This is
the knowledge-acquisition bottleneck restated as a quantity: it is not that rules
are unnecessary, it is that they are cheaper than data *below a corpus size this
work has not yet reached*. Where the crossover sits is the thing to measure, and
`data/artifacts/wikipedia_parents_scale.jsonl` is being built to find out.

Two things the patterns have that the classifier cannot find from 126 articles:
**relation words** (`subsidiary of`, `owned by`) as a tiny high-precision feature
set, and the knowledge that a state beats an event, which was itself a measured
finding rather than an intuition.

## What would have refuted this reading

Multi-instance pruning *helping*. It would have meant the positives were mostly
wrong and the corpus was adequate, which is the opposite prescription — clean the
labels rather than collect more. It hurt in all three relations.

## 5. WordNet does not substitute for the missing data either

If hand-written patterns win because they inject prior knowledge, an *external*
lexicon should be able to inject some of the same. The obvious candidate: a
corpus of 126 articles cannot learn that `subsidiary`, `division`, `unit` and
`arm` behave alike, but WordNet says all four are `noun.group`, and `owned` is
`verb.possession`. The module already on disk was extended to read the noun
tables — same archive, same three files — and every supersense present in a
sentence became a feature, with no list of relation words written down anywhere.

| relation | n-grams only | + WordNet supersenses |
|---|---|---|
| `parent` correct | 0.101 | **0.101** |
| `parent` coverage / precision | 0.411 / 0.246 | 0.500 / **0.202** |
| `parent` classifier recall | 0.308 | **0.231** |
| `headquarters` correct | 0.173 | 0.173 |
| `country` correct | 0.145 | 0.151 |

**Nothing.** Predicted 0.18–0.30 for `parent`; it did not move at all, and the
classifier's recall on supervised sentences *fell*. Coverage rose and precision
fell by the same amount, which is a classifier firing more and knowing less.

The mechanism is in the module's own docstring: there is no part-of-speech
tagging and no sense disambiguation, so a token contributes the **union** of
every sense it could carry. `company` is `noun.group` *and* `verb.stative`;
`unit` is `noun.Tops`, `noun.cognition` *and* `noun.group`. Every sentence in a
company article contains group nouns, so the feature fires everywhere and
discriminates nothing.

This is the **second** time supersenses have come out at the wrong granularity
here — the verb-class staleness arm found they could not separate a transition
from a state, because `divested` is `possession` and `ceased` is `stative`
exactly like the relation verbs they were meant to be told apart from. The
pattern across both: **WordNet supplies a category, and these tasks need a
frame.** What the hand reader knows is not that *subsidiary* is a group noun; it
is that *"X is a subsidiary of Y"* puts Y in a particular slot.

That narrows what would actually help, which is the useful half of a null: a
resource with **frames** (FrameNet, PropBank rolesets) rather than categories, or
enough text to learn the frames. The scale corpus tests the second.
