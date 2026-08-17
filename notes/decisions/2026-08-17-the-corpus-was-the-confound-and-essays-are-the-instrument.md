---
date: 2026-08-17
author: lead
status: decided
related: [2026-08-17-the-exchange-rate-is-not-fixed-it-spans-235x,
          2026-08-17-frontiers-paths-cap-at-0412-and-corefer-is-already-past-it,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The single-paragraph corpus is why vocabulary dominates every measurement, and the essay generator is the missing half of the instrument

Direction set by the user, 2026-08-17: move to synthesising complex
multi-paragraph text from graph-structured input, and stop re-verifying.
Recording the reasoning because the *why* is stronger than the instruction and
changes what gets built.

## What this repo has actually been studying

Across 51 scored models, every finding reduces to one of four:

1. The substrate — floors, calibrators, abstention fallback, tokenizer — moves
   numbers more than any architecture (0.15–2.0 against ~0.1 for the whole model
   spread).
2. Models leading on accuracy are memorising vocabulary. `frontier-floortype` is
   the most accurate model here at 0.4477 and scores **0.0469** renamed.
3. The mechanism that survives permutation is *pointing* — resolving a reference
   by relational features rather than symbol identity. That is the entire content
   of the `corefer` / `frontier-point` arc.
4. Metrics rank the models near-inversely, and every published ranking was
   secretly an accuracy ranking.

Together those are not four findings but one instrument: **this repo is a machine
for separating reference from vocabulary.** Renaming invariance operationalises
the split, pointing is what survives it, and the rest is bookkeeping.

## The accuracy/equivariance frontier is probably an artifact of bundling

Renaming invariance is a symmetry condition, `f(σ·x) = σ·f(x)` for σ ∈ S_n over
the vocabulary — ordinary equivariance. Everywhere else in machine learning, a
task with a real symmetry does not *trade* accuracy for equivariance; the
symmetry is built in and accuracy improves, because the symmetry is true of the
task.

This repo sees a trade because **the task is not equivariant**. The curriculum
carries real lexical content — `bread is a food` is a fact about English, not a
relational structure — and a perfectly equivariant model cannot represent it. So
the "frontier" measured this morning is not one task's efficiency limit; it is
two tasks (resolve references, know facts about words) sharing one number, and
the 235x "exchange rate" is the mixing ratio of two populations.

Reread that way: the first 0.20 of equivariance being nearly free is the region
where models stop being *bad at reference*, which costs nothing because it was
being left on the table. The expensive tail is where a model starts surrendering
lexical knowledge it cannot express relationally. Two regimes, one curve, written
up as a single convex trade.

The move this licenses is not walking further along the front. It is refusing the
bundling: a model factored into an equivariant relational core plus a
non-equivariant lexical memory with a gate, each half scored on its own
population. `corefer-mass` is accidentally close (pointer plus mass gate, drop
0.0019) and nobody built it deliberately.

## Why the corpus is the confound

A current episode is 985 characters, one paragraph, every candidate referent
simultaneously visible, answer chosen from four listed options. In that format
**reference is trivial** — the antecedent is never more than a few tokens away
and there is no competing distractor of the same type — so the only remaining
difficulty is vocabulary.

**The single-paragraph format is why vocabulary dominates every measurement
here.** We built an instrument to study reference and fed it data where reference
is free. The ceiling analysis said the same thing without being read that way:
`prev`, "nearest earlier visible node", does **0.288** of frontier's copy work,
more than any other path. A corpus in which the nearest noun phrase is usually
the right answer cannot tell pointing from proximity.

## The correction that shaped the build

The first generator averaged **104 words against the existing prompt's ~160** — it
made the data *smaller* while being described as more complex. Length was never
the axis. The axis is **referential distance**: how far a mention sits from its
antecedent, and how many same-type distractors lie between. `distractor_rate`,
not length, is therefore the difficulty knob, and it is the one the tests pin.

## What was built

`symbolic_ai_core/data/essay.py` — multi-paragraph essays realised from a
WordNet subgraph, deterministic in `(topic, seed)`, no language model involved so
every clause traces to a triple and can be ablated as a control.

The design decision everything follows from: **the graph is ground truth, the
essay is one surface realisation, and the alignment is recorded.** Every sentence
carries its triple and hop count; every mention carries its span, referent,
antecedent, distance in mentions/sentences/paragraphs, and whether the nearest
preceding noun phrase is a *different* entity (`lure`).

At 200 draws over 1,074 eligible topics: 152 essays, **147 with a genuine 2-hop
synthesis paragraph**, mean 127 words, 3.2 paragraphs, 21 mentions, **8.8 lures**,
3.1 cross-paragraph coreferences, antecedent distance out to 17 sentences.

Four bugs found while building, all silent in the output rather than loud:

- templates assumed `{S}` preceded `{O}`, so half the sentences realised with
  slots in the wrong order — spans still recorded, pointing at the wrong text;
- support templates mostly omitted `{S}`, collapsing the coreference chain to
  zero pronouns, which is the one thing the corpus exists to contain;
- the 2-hop paragraph fired **0/40** because it subtracted the hypernym's
  relation set from the topic's, and WordNet states these at the parent with the
  accessor inheriting *downward*, so that set is a subset by construction. The
  real 2-hop runs the other way — what the topic has only by inheritance;
- the body was drawn from the *inherited* sets, so the "unstated" 2-hop fact was
  stated two paragraphs earlier and the multi-hop item was solvable by copying.

The last is the one that would have mattered: it produces a corpus that looks
like it tests multi-hop reasoning and does not. `test_the_two_hop_fact_is_not_
stated_anywhere_else` exists for it.

## What this makes possible that the old corpus could not

- **A 2x2 typology instead of a ranking.** Every model currently gets one
  perturbation (permute symbols, keep structure). Essays make the orthogonal one
  natural — permute structure, keep symbols, by shuffling paragraph order. Cross
  them and models land in a coordinate system: relational, lexical, compositional,
  or surface-memorising. That dissolves the "which metric" wound rather than
  arguing about it.
- **Partial renaming.** Rename an entity in *some* paragraphs only, so nothing
  but coreference says the two names denote one individual. Not in any of the
  four source papers, and only posable because we control generation.
- **Lift as a curve over antecedent distance** instead of a pooled scalar. Given
  ten documented slice inversions here, a curve over the variable that drives
  difficulty beats any headline number.
- **Inversion: text → graph.** Exact ground truth makes semantic parsing
  scoreable, which is where symbolic models should win outright and which this
  repo has never measured.

## Dropped

The omegaclaw/Pareto census thread. It produces no new capability, and by the
program above it is decoration.
