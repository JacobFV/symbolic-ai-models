# symbolic-ai-old-B: learning algorithms that are symbolic on the inside

*A design note and experiment on non-neural learners in the symbolic agent protocol.*
2026-08-06 · hardware: CPU only for every symbolic arm (1× NVIDIA GB10, shared, for the neural controls)

---

## 0. The correction this note responds to

`symbolic-ai-old-A` was symbolic at the *interface*: symbols crossed the
agent/environment boundary, but the agent's insides were a 13.97M-parameter
transformer. The intended target is stronger — **the algorithm itself is
symbolic**: a few dozen discrete parameters, plain code, no gradients, no
learned tensors, running on a CPU.

The bet being tested is that such a system generalizes where a network
memorizes, and does so for a rounding error of the compute.

Two secondary commitments, both from the project brief, shape the design:

* **Reasoning is not the point.** Symbol shuffling for its own sake is a trap.
  What matters is whether the system comes to operate inside the *conceptual
  schema of a world* — its objects, relations, laws, and what it counts as
  success. The centrepiece algorithm here therefore induces a world's schema and
  reasons inside it, rather than learning a stimulus→response map.
* **Importing knowledge is not cheating.** A system that can also *learn* loses
  nothing by being handed a lexicon or an ontology instead of mining it out of a
  terabyte of text. Knowledge enters through the same codec boundary as any
  other representation choice, and the experiments measure how much labelled
  data it replaces.

## 1. What "symbolic on the inside" means operationally

A learner qualifies here if all of the following hold:

| criterion | why it matters |
|---|---|
| no gradient computation anywhere | the compute claim |
| no learned real-valued tensor | rules out "small net in disguise" |
| all fitted structure is discrete and countable | the parameter count is honest |
| the fitted model is printable as a program a person can read | inspectable, editable, falsifiable |
| runs on a CPU | the energy/latency claim |
| tunable knobs are integers/thresholds fixed by hand, not fitted | "19 parameters and code" |

Every algorithm below satisfies all six. Where a real number appears (a
confidence, a discount) it is a *hand-set knob*, never something fitted by
descent.

## 2. The algorithms

All six plug into the existing protocol unchanged: they are `Agent`s that also
implement `update(trajectories)`. The environments, trajectories, evaluation and
provenance machinery are shared with the neural arm, so comparisons are like for
like.

### 2.1 `relational` — induce an ordered rule list

Flatten each observation into ground facts; optionally re-express numeric facts
relative to an **anchor entity**; generate a hypothesis language *from the
observed facts*; run greedy separate-and-conquer induction (CN2/RIPPER-flavoured)
with an MDL stopping rule.

Induced on MiniGrid in 11 s of CPU, from 800 episodes, it produces the entire
policy:

```
IF see(goal,_,_,>0) THEN forward      [1040/1040]
IF see(goal,_,<0,_) THEN left         [ 201/201 ]
ELSE right
```

Five parameters. 100% success on the configuration it was induced on, versus
0.70 for the 13.97M transformer trained on the same episodes.

Knobs: `max_conditions`, `min_support`, `min_confidence`, `max_rules`, `beam`,
`max_literals`, `frame`, `on_no_rule`. Eight.

### 2.2 `world_model` — induce the world's schema, then plan in it

The centrepiece, and the part that is not "reasoning as symbol manipulation".
Three inductions over the same fact language:

1. **Effects** — the difference between consecutive fact sets, lifted into the
   anchor's frame.
2. **Preconditions** — what distinguishes the cases where an action changed
   nothing, after the world's *bounds* have explained what they can.
3. **Goals** — what the environment rewards, read off the terminal states of
   successful episodes.

From 21,394 transitions in a 5×5 world it induces, in **0.14 s of CPU**, exactly
the laws of that world:

```
LEFT   : move(-1, 0)  unless wall(-1, 0)   within [0,size)
RIGHT  : move(+1, 0)  unless wall(+1, 0)   within [0,size)
UP     : move(0, -1)  unless wall(0, -1)   within [0,size)
DOWN   : move(0, +1)  unless wall(0, +1)   within [0,size)
PICKUP : add holds(agent,key); del holds(agent,nothing), at(key, 0, 0)
GOAL   : at(goal, 0, 0) ∧ holds(agent,key)
```

**26 parameters.** Note `within [0,size)`: the bound is tied to a *scalar read
from the observation*, so the same operator is correct in a world of any size —
the law is stated in the world's terms, not in the training configuration's.

Planning is breadth-first search inside that schema, replanned every step
because an induced model is approximate.

### 2.3 `seq_synth` — enumerative program synthesis

Enumerate expressions over a tiny integer language in increasing size order (an
Occam prior), pruning by observational equivalence, and keep the shortest program
consistent with the sequence. There is no training phase and no training
distribution: the hypothesis is re-derived per episode in 1.6–43 ms.

### 2.4 `text_rules` — imported knowledge + induction

Lexical knowledge (Hu & Liu's opinion lexicon + VADER: 12,065 terms, 16,310
typed edges, ~100 kB) enters as facts through a `KnowledgeEncoder`, and rule
induction runs *over those facts as well as the words*. Three modes — `prior`
(zero labelled examples), `induce` (no knowledge), `both` — isolate what each
source contributes.

### 2.5 `vomm` — variable-order Markov modelling by counting

One pass of integer counting with absolute-discounting interpolation; four
knobs. Included as the honest attempt at symbolic *language* modelling, and it
is the clearest negative result in this note (§4.5).

### 2.6 `search` — the non-learning control

Best-first planning given the environment as its own model (`env.clone()`). It
learns nothing; it is here to separate "planning helps" from "learning the
schema helps".

## 3. Where the generalization actually comes from

Three distinct mechanisms, worth separating because they fail differently.

**Frames.** Re-expressing facts relative to an anchor (`at(agent,3,4)` +
`wall(4,4)` → `rel:wall(1,0)`) is the symbolic analogue of translation
equivariance. A hypothesis learned in a 5×5 world is *literally the same
hypothesis* in a 20×20 world — not approximately, identically. This is the
quotient/equivariance idea from `limiting-language-analysis`: choose the
equivalence relation deliberately, and what survives it is what transfers.

**Programs over parameters.** A synthesizer's competence is bounded by the
expressiveness of its language, not by the coverage of a training set. An unseen
rule family costs it nothing if the family is expressible.

**Schema over policy.** A policy answers "what do I do here?" and can only be
asked that question. A schema answers "what happens if?" and "what counts as
done?", so it can be re-aimed at goals nobody trained for.

## 4. Results

Every symbolic arm below ran on CPU. Neural controls are the `symbolic-ai-old-A`
checkpoint (13.97M parameters, 16 min on a GB10) and, where noted, a per-task
finetune of it.

### 4.1 Scaling a world 16× beyond the training configuration

Induced on 5×5 gridworlds with 3 walls; evaluated on worlds up to 20×20 with 24
walls, 25 episodes per cell, held-out seeds. Native metric: success rate.

| agent | params | 5×5 | 8×8 | 12×12 | 20×20 |
|---|---|---|---|---|---|
| **world_model** (teacher + exploration) | **26** | **1.00** | **1.00** | **1.00** | **1.00** |
| world_model (expert data only) | 21 | 0.64 | 0.40 | 0.32 | 0.24 |
| relational (rule list) | 42 | 0.84 | 0.72 | 0.56 | 0.56 |
| search (given the true model) | 0 | 0.80 | 0.24 | 0.12 | 0.00 |
| symbolic-ai-old-A (transformer) | 13,969,152 | 0.40 | 0.00 | 0.00 | 0.00 |
| random | 0 | 0.00 | 0.00 | 0.00 | 0.00 |

Three things in one table. The induced schema is *flat* across a 16× change in
state-space size. The transformer is at zero the moment the world stops looking
like its training data. And planning with the true model but a bounded search
budget (`search`) degrades faster than planning in the induced abstraction —
learning the schema is not just cheaper than search, it makes search tractable.

### 4.2 A goal that never appeared in training

The same induced model, re-aimed. No new data, no refitting.

| goal | achieved | mean steps | retrained? |
|---|---|---|---|
| induced goal (key, then goal square) | 1.00 | 11.6 | no |
| **new**: hold the key | **1.00** | 6.6 | **no** |
| **new**: stand on the goal square | **1.00** | 5.6 | **no** |
| **new**: stand where the key is | **1.00** | 5.6 | **no** |

Three goals nobody trained for, satisfied on the first attempt by the same 26
parameters, because what was learned is the world's dynamics rather than a
mapping from states to actions. A policy — symbolic or neural — has no mechanism
for this: it would need new demonstrations for each new goal.

### 4.3 Rule families held out of training entirely

`seq_completion` generates sequences from a hidden rule. Five families
(`add, mul, alt, fib, repeat`) appear in training data; five structurally
analogous ones (`poly2, back2, double, minus, altstep`) are generated only at
evaluation. 40 episodes each, held-out seeds.

| agent | params | fitted on | TRAIN families | HELD-OUT families |
|---|---|---|---|---|
| **seq_synth** | **0** | nothing | **1.000** | **1.000** |
| neural specialist | 13,969,152 | train families | 0.975 | **0.000** |
| symbolic-ai-old-A | 13,969,152 | other tasks | 0.200 | 0.000 |
| random | 0 | — | 0.025 | 0.000 |

This is the cleanest separation in the project. The network reproduces its
training families almost perfectly and scores *exactly zero* on families it has
not seen. The synthesizer does not distinguish the two cases at all, because it
has no training distribution to be off.

### 4.4 Imported knowledge versus mined knowledge (SST-2)

200 held-out validation episodes.

| arm | params | labelled examples | imported knowledge | fit | accuracy |
|---|---|---|---|---|---|
| text_rules `prior` | **0** | **0** | 12,065 terms | 0 s | 0.600 |
| text_rules `induce` | 3 | 1500 | none | 0.3 s | 0.480 |
| **text_rules `both`** | **17** | 1500 | 12,065 terms | **0.7 s CPU** | **0.765** |
| symbolic-ai-old-A | 13,969,152 | 1500 | none | 16 min GPU | 0.585 |
| neural specialist (finetuned) | 13,969,152 | 1500 | none | +50 s GPU | 0.475 |

The ablation is the point: induction alone underperforms, the prior alone is
mediocre, and inducing *on top of* imported knowledge beats both — and beats the
transformer by a wide margin at ~10⁻⁶ of the parameters and ~10⁻³ of the fitting
time.

### 4.5 Language modelling: the negative result

Counting-based variable-order modelling on the same FineWeb-Edu tokens, same
BPE vocabulary, same held-out split:

| model | fit | fit cost | held-out ppl | next-token acc | peak RSS |
|---|---|---|---|---|---|
| VOMM order-4, 5M tokens | counting | 26 s CPU | 249.1 | 0.215 | 3.5 GB |
| VOMM order-6, 5M tokens | counting | 46 s CPU | 252.8 | 0.214 | 7.0 GB |
| VOMM order-5, 20M tokens | counting | 199 s CPU | 179.4 | 0.237 | 18.1 GB |
| VOMM order-6, 40M tokens | counting | — | — | — | **aborted: exhausted host memory** |
| symbolic-ai-old-A (mixture) | gradients | 16 min GPU | 89.1 | 0.250 | ~3.6 GB |
| baseline-lm-only | gradients | 22 min GPU | **51.9** | 0.125 | ~3.6 GB |

The counting model loses by 3.5× in perplexity and its memory grows with
*distinct contexts*, which is unbounded in a way a parameter budget is not — the
40M-token run took the machine down and the fitter now prunes under a hard
`max_entries` cap. Natural-language modelling is where the gradient-based method
is genuinely better, and no amount of framing changes that. What the symbolic
side wins on is everything that requires extrapolating a *structure* rather than
interpolating a *distribution*.

### 4.6 Cost

| arm | device | fit time | model size | per-decision latency |
|---|---|---|---|---|
| world_model (gridworld) | CPU | **0.14 s** | 26 discrete params | 0.2–140 ms (planning) |
| relational (MiniGrid) | CPU | 11 s | 5 discrete params | < 1 ms |
| seq_synth | CPU | none | 0 params | 1.6–43 ms |
| text_rules:both | CPU | **0.7 s** | 17 discrete params | < 1 ms |
| symbolic-ai-old-A | GB10 GPU | 16 min | 13,969,152 floats (55.9 MB) | ~10 ms/step |

Wall-clock and device are measured; **energy in Joules is not measured** and is
not claimed here — the GPU was shared with an unrelated job throughout, so any
power figure would be contaminated. The time and footprint ratios (≈10⁴ in fit
time, ≈10⁶ in parameters) are the defensible version of the efficiency claim.

## 4.7 The curriculum: language ability as a profile

Fourteen procedurally generated lessons, ordered by the capability they require
(reference → equivalence → discrimination → sequence memory → finite-state
syntax → recursion → structure → binding → unification → quantification →
compositional reference → acquiring a new language). Each is fitted on 60
episodes from seeds 0–59 and evaluated on 80 episodes from seeds ≥10,000, so the
evaluation is new worlds and new vocabularies rather than a held-out sample.
The grammar and ontology travel in `info["hidden"]`, which the evaluator reads
and the agent cannot.

| lesson | lvl | qsynth | relational | neural (trained on curriculum) | neural (zero-shot) | random |
|---|---|---|---|---|---|---|
| symbol_grounding | 1 | **1.00** | 0.34 | 0.40 | 0.26 | 0.24 |
| symbol_equivalence | 2 | **1.00** | **1.00** | 0.66 | 0.15 | 0.15 |
| symbol_discrimination | 3 | 0.88 | 0.65 | 0.56 | 0.44 | 0.44 |
| sequence_copy | 4 | **1.00** | 0.56 | 0.51 | 0.23 | 0.11 |
| next_symbol | 5 | **1.00** | 0.72 | 0.82 | 0.62 | 0.16 |
| finite_state_language | 6 | **0.91** | 0.53 | 0.49 | 0.51 | 0.47 |
| context_free_language | 7 | **1.00** | 0.55 | 0.70 | 0.45 | 0.55 |
| parse_depth | 8 | **1.00** | 0.00 | 0.40 | 0.12 | 0.00 |
| tree_to_sequence | 9 | **1.00** | **0.97** | 0.72 | 0.12 | 0.12 |
| variable_binding | 10 | **1.00** | 0.49 | 0.41 | 0.19 | 0.19 |
| unification | 11 | 0.59 | 0.34 | 0.47 | 0.23 | 0.12 |
| quantification | 12 | **0.99** | 0.72 | 0.69 | 0.78 | 0.21 |
| compositional_reference | 13 | 0.84 | 0.29 | 0.33 | 0.16 | 0.16 |
| lexicon_induction | 14 | **1.00** | 0.35 | 0.38 | 0.31 | 0.30 |
| **lessons solved (≥0.90)** | | **11** | 2 | **0** | 0 | 0 |
| **lessons above floor (+0.15)** | | **14** | 8 | 10 | 2 | 0 |

The shape of the two profiles differs more than their averages do. **Symbolic
induction is bimodal**: when the capability is inside the program space it is
exact (six lessons at 1.00, one at 0.99), and when it is not it sits at the
floor. **The network is uniformly mediocre**: it is above chance on ten of
fourteen lessons and masters none of them. A single "language score" would hide
precisely this.

What `qsynth` induces is readable, and is the correct answer rather than a
correlate:

```
symbol_grounding    arg0 of obj/5 where arg1=q1 ∧ arg2=q2
sequence_copy       arg1 of sequence_at/2 where arg0=q1
variable_binding    arg1 of bind/2 where arg0=q1
quantification      CASE(q1=none -> count(obj/5 where arg1=q2) eq0; q1=some -> ... )
lexicon_induction   arg0 of obj/5 where arg1 = [arg1 of says/2 where arg0=q1]
```

The last one is the interesting one. `lexicon_induction` invents three new words
per episode; nothing carries over. A program that says "find the object whose
colour is what this word means" acquires the language every time, and scores
1.00. A network scores 0.38, because there is no vocabulary to memorize.

### 4.7.1 A prediction, tested

The first version of this profile solved 6 of 14, and the eight failures were
all at the floor. Two explanations were available and they point at opposite
futures: the capability is **outside the program space** (write more
combinators, keep winning cheaply), or the program **exists and search cannot
find it** (enumeration is doomed, and a learned proposal distribution — a neural
model — becomes necessary). The prediction was coverage. It was testable, so it
was tested.

Adding three general mechanisms — none of them a solution to a particular
lesson — moved the profile from **6/14 to 11/14 solved**, with **14/14 above the
floor**, and fits stayed at 0.0–0.1 s. Search never exploded. The coverage
diagnosis was right.

| mechanism | what it is | lessons it unlocked |
|---|---|---|
| `Fold` | scan a sequence with a ±1 accumulator; *which* symbol increments, which decrements, and which summary is read out are all induced | context_free 0.55→**1.00**, parse_depth 0.00→**1.00** |
| `IndexAt` / `Extremum` / structural position | positions preserved for nested structure, indexing relative to either end, arg-extremum selection | tree_to_sequence 0.12→**1.00**, sequence_copy →**1.00** |
| `EpisodeFit` / `SuccessorLookup` | fit the *parameter* from the episode's own examples; the family is induced globally, the member per episode | symbol_discrimination 0.44→**0.88**, finite_state 0.51→**0.91**, next_symbol 0.16→**1.00** |

The third is the interesting one. Three lessons resisted everything because
their rule is *invented per episode* — the target symbol, the parity, the
category boundary are revealed only by the episode's own examples, so no
globally-induced program can encode them. What can be induced globally is the
family; the member is chosen by consistency with the few examples in front of
you. That is few-shot learning implemented as search, and it cost about eighty
lines.

What survives: `unification` (0.59) needs facts tagged by the *role* they play
(pattern versus fact) and a position-wise comparison template, and
`compositional_reference` (0.84) loses the cases where the one-hop program is
ambiguous. Both are coverage gaps of the same kind, and the same prediction
applies to them.

## 4.8 English surface forms, and what a dictionary is worth

The same lessons, realized as English sentences ("which object is the purple
cube?", "some of the objects are green, true or false?"), with a third split
that swaps in synonyms the learner never saw ("which object is the **violet
block**?"). Parsing is a codec: `LexicalQueryEncoder` resolves each content word
against the vocabulary the world uses, consulting an imported WordNet synonym
index (111,910 lemmas, 347,094 edges, **6.7 s to import**) when the word is
unfamiliar. The ablation turns the dictionary off.

| lesson | arm | English | English with unseen synonyms |
|---|---|---|---|
| symbol_grounding | qsynth + dictionary | **1.00** | 0.29 |
| | qsynth, exact match only | **1.00** | 0.24 |
| | neural (curriculum-trained) | 0.21 | 0.19 |
| quantification | qsynth + dictionary | **0.99** | **0.85** |
| | qsynth, exact match only | 0.99 | 0.79 |
| | neural | 0.45 | 0.49 |
| sequence_copy | qsynth ± dictionary | **1.00** | **1.00** |
| | neural | 0.41 | 0.41 |
| variable_binding | qsynth ± dictionary | **0.86** | **0.86** |
| | neural | 0.30 | 0.30 |
| lexicon_induction | qsynth ± dictionary | **1.00** | **1.00** |
| | neural | 0.40 | 0.40 |

Two honest readings. The program induction is unaffected by moving from symbols
to English — it parses the sentence and induces the same program — while the
network stays near chance on the same lessons. But **the dictionary buys less
than it should**: +0.06 on quantification, +0.05 on grounding. The reason is
coverage, and it is checkable one pair at a time:

```
violet  -> purple   ✓        azure -> blue     ✗ (not in the same synset)
crimson -> red      ✓        ball  -> sphere   ✗
block   -> cube     ✓
```

`symbol_grounding` needs *both* the colour and the shape to resolve, so it
degrades multiplicatively and lands at 0.29. This is a coverage result, not a
mechanism result: where WordNet licenses the equivalence the substitution is
free, and where my synonym table asserted a link WordNet does not have, nothing
can rescue it. The fix is more or better knowledge (a colour ontology, a
domain lexicon), which is exactly the point — it is a data problem with a
lookup-shaped solution, not a training problem.

Three bugs the English interface exposed, all in the parsing layer and all
general: the WordNet import iterated nouns first and its lemma cap truncated the
import *before reaching the adjectives* where colour synonyms live; the
tokenizer dropped digits, so "position 3" lost its argument; and it dropped
single characters, so the variable "C" vanished. Fixing them moved
`sequence_copy` from 0.11 to 1.00 and `variable_binding` from 0.19 to 0.86 on
English input. Legible failures again: each was a one-line diagnosis.

## 4.9 The full curriculum: 180 lessons

The 14-lesson profile above was a pilot. The complete curriculum specified in
`docs/symbolic_ai_language_curriculum.md` — 170 environments from symbol
grounding to open-world research — is now implemented as procedural generators,
merged through one registry with a single admission test.

| | |
|---|---|
| lessons registered | **180** (170 from the doc + the 14 core pilot, minus overlaps, plus extras) |
| implemented and **verified** | **179** |
| honestly marked `spec` | 1 (`open_world_research_agent`) |
| profiling cost | **2 minutes**, 179 lessons × 3 arms, CPU only |

A lesson is only admissible if it passes: exact ground truth, answer in
vocabulary, uniform guesser near chance, constant (majority) guesser under
threshold, and determinism. The one `spec` lesson is a loop rather than a
question — the agent must choose interventions and be scored on a trajectory
functional — and its `note` specifies what a real implementation needs instead
of pretending.

### 4.9.1 Where the learner actually stands

| arm | solved (≥0.90) | above floor (+0.15) |
|---|---|---|
| **qsynth** | **19 / 179** | 42 / 179 |
| relational | 1 / 179 | 24 / 179 |
| random | 0 | 0 |

Nineteen of 179. That is the honest number, and it is the right shape for a
research programme: the curriculum is far ahead of the learner. The nineteen are
`symbol_grounding`, `symbol_equivalence`, `sequence_copy`, `next_symbol`,
`context_free_language`, `parse_depth`, `tree_to_sequence`, `variable_binding`,
`quantification`, `lexicon_induction`, `string_reversal`, `ellipsis`,
`implicature`, `event_semantics`, `symmetry_reasoning`, `negation`,
`finite_state_language`, `compositional_reference`, `instruction_following_micro`
— fifteen of them at exactly 1.00, which is the bimodality again at scale.

### 4.9.2 The capability map chooses the next primitive

Averaging each arm over the capabilities lessons declare turns "what should we
build?" into a measurement:

| reachable now (qsynth − floor) | | absent entirely (+0.00 over floor) |
|---|---|---|
| diagnosis +0.40 | | translation, unification, validity |
| sequence_memory +0.34 | | teaching, transfer, task_transfer |
| spatial_reasoning +0.30 | | taxonomy, symbolic_arithmetic |
| explanation +0.20, self_modeling +0.17 | | |
| recursive_syntax +0.15, temporal_reasoning +0.15 | | |

The absent column is not a list of hard problems; it is a list of *missing
mechanisms*, and they are the same three that the earlier sections predicted:
alignment between two independently generated symbol systems (translation,
transfer, taxonomy), position-wise structural matching (unification), and
executing a candidate derivation to check it (validity, symbolic_arithmetic).

### 4.9.3 What made the lessons trustworthy

Floor checks are necessary and nowhere near sufficient. What actually found the
defects was that nearly every generator was audited by an **independent oracle
that re-derives each answer from the observation alone**, plus explicit
*heuristic audits* that simulate the shortcut an unthinking agent would take and
measure it. Real defects caught this way:

* `grammar_induction` episodes that did not identify the grammar — two candidate
  strings each grammatical under a different consistent hypothesis;
* `latent_rule_discovery` trajectories consistent with several cellular automata;
* `curriculum_invention` **100% solvable from distractor name suffixes**;
* `symbolic_world_builder` 0.61 from "pick the candidate with most variables";
* `unknown_game` 0.47 from averaging payoffs under the *wrong* dimension — noise
  masquerading as signal;
* `representation_invention` 0.77 from "name the predicate built from the
  commonest relations";
* `cross_domain_unification` graphs whose isolated node was never written into
  the observation, making the answer unrecoverable from what the agent sees.

Two were mine. The verifier condemned `identity_continuity` on **sampling
noise** — a constant guesser's score is itself a random variable, and at n=120 a
perfectly balanced binary lesson trips a fixed threshold about one time in six;
borderline cases are now re-measured at 4× before being failed. And
`mechanism_design` solved for a unique pure Nash profile while its observation
*named* iterated elimination of weakly dominated bids; 2×2 games routinely have
several Nash equilibria, so it never produced a single episode.

### 4.9.4 Building what the map asked for

The capability map named three absent mechanisms. Each was implemented as a
general combinator whose parameters are induced, and the sweep was re-run.

| mechanism | what it does | effect |
|---|---|---|
| `PositionMatch` | match two structures of one shape and read off the position where they disagree | `unification` 0.53 → **1.00** |
| `Align` | put two independently generated symbol systems into correspondence | `translation` 0.07 → **1.00** |
| `PerCandidate` | compute a property of each candidate answer and select on it | `knowledge_refactoring` 0.25 → **1.00**, `value_learning` 0.10 → **0.88** |

Aggregate: **19 → 22 solved**, **42 → 47 above floor**, with ten lessons
improving by ≥0.10. The aggregate movement is modest; the mechanism-specific
movement is exact and large, which is what a targeted primitive should look
like. `PerCandidate` turned out to be the broadest of the three — generate-and-
test is how most "which of these is correct?" questions are actually decided.

Alignment was the instructive one. It failed three times before it worked, and
each failure was informative rather than incidental. Positional zip failed
because `translation` permutes word order; order-free intersection of
co-occurring words failed because the correspondence is not determined by
co-occurrence alone; what works is searching the (small) space of reorderings
and keeping those whose induced lexicon is consistent across every sentence
pair. So "alignment between symbol systems" is not one mechanism: it decomposes
into **lexical correspondence and structural reordering, which must be induced
jointly** because neither is identifiable without the other. The final program,
found in 0.2 s from four sentence pairs with no shared vocabulary:

```
align[paired_perm](pair -> pair) on q1[q2]
```

What still resists: `mechanism_design` needs a 2×2 game *solved* under iterated
weak dominance, and `theory_comparison` and `dimensional_analysis` need a
candidate *checked against a rule*. Aggregation cannot express either. The next
mechanism is therefore an evaluator — running a candidate through semantics
stated in the observation — which is the same capability `interpreter_learning`
and `procedural_language` demand, and it is the natural bridge to the modules
this repository already has (`world_model` plans, `seq_synth` executes).

### 4.9.5 The machine: stateful sequential execution

`TreeEval` evaluates an *expression*. The lessons that stayed at chance need the
same idea for *statements*, where the extra ingredient is mutable state: the
observation is not a scene to be queried but a program, and the answer is what
running it leaves behind. `Exec` (`symbolic/learn/execute.py`) is a small
abstract machine — a store, a sequencer, a loop, a branch — whose every
non-structural choice is induced:

| induced | from |
|---|---|
| which record field is the program | the rest is initial store and definitions |
| where the opcode sits — the node's head `(add u 3)` or its first argument `(step k 3)` | fit; both readings occur |
| what each opcode means | a table the observation states, `(prim p add 5)`; an assignment fitted once across episodes; or an assignment fitted **per episode** from worked examples the episode carries |
| the branch comparison, and the scalar every assignment is reduced modulo | fit |

The statement forms are read off arities, never names: `(H ident num)` is an
instruction, `(H num body…)` a loop, `(H ident num block block)` a branch, a
bare identifier a call.

| lesson | before | after |
|---|---|---|
| `procedural_language` | 0.10 | **1.00** |
| `interpreter_learning` | 0.12 | **1.00** |
| `compiler_construction` | 0.30 | **1.00** |

Aggregate **23 → 26 solved**, **47 → 50 above floor**, nothing regressed, sweep
cost +7 s. Two things had to be got right, and both are about *underdetermined
parameters* rather than about programs:

* `gt` and `ge` differ only where a branch variable sits exactly on its bound,
  which thirty episodes may never show. Left to sort alphabetically the fit
  picked `ge` and `procedural_language` scored 0.90 instead of 1.00. The fix is
  a declared order over parameter values charged to the program's size, so the
  existing Occam tie-break resolves it — while a held-out episode that *does*
  separate the two still wins on accuracy.
* Five episodes in sixty of `interpreter_learning` are genuinely ambiguous:
  several opcode assignments reproduce every demonstration and then disagree on
  the program. What removes the ambiguity is the constraint that two opcodes
  never mean the same thing — so *that* is a parameter too, induced from the
  training episodes like any other. With it, all sixty are uniquely determined.

The general lesson is that in-episode fitting needs its own priors. Fitting on
five demonstrations is not few-shot learning if the five do not identify the
hypothesis; what makes them sufficient is a structural constraint, and the
constraint has to be induced rather than assumed.

## 5. What went wrong, and what it taught

Kept deliberately, because the failures were more instructive than the wins.

**A competent teacher hides the world's laws.** The first world model never
learned that walls block movement — the rule-based teacher *avoids* walls, so
bumps almost never appear in expert data. Adding 400 episodes of random
exploration took the induced model from partially wrong (0.60 / 0.30 / 0.25) to
exactly right (1.00 / 1.00 / 1.00). Policy learners want *expert* data; model
learners want *diverse* data. Same interface, opposite data requirement.

**A competent teacher also hides preconditions entirely.** No amount of data
from a good teacher reveals that `PICKUP` requires a key, because a good teacher
never tries it. That precondition came from STRIPS semantics instead — a delete
list *is* a precondition, since you cannot remove a fact that is not there. Some
knowledge has to come from the form of the representation, not from the data.

**Reactive policies cannot explore.** The induced MiniGrid rule list is perfect
at 5×5 and 6×6 and scores 0.00 at 8×8 — because the goal leaves the 7×7 view and
the rule list has no rule for "goal not visible". One discrete knob
(`on_no_rule=random`) takes 8×8 from 0.00 to **0.96**. At 16×16 the goal is
never visible at reset (0/25 episodes) and no memoryless policy can solve it —
an architecture limit, not a scale limit, and the neural arm fails identically.

**Rule induction overfits in small ways.** The SST-2 rule list contains
`IF polarity(more_positive) ∧ word(=and) THEN positive` — the `and` is noise
that survived the MDL test. Legibility is what let this be *noticed*; a network
would have hidden the same artefact.

**Precondition induction is fragile.** Blockers had to be induced on the
*residual* after bounds explained what they could, with a discriminativeness
test rather than a frequency test. Two earlier versions learned confident
nonsense (`RIGHT unless at(goal,-4,0)`).

## 6. Limits

* Everything here is a small, fully observable, discrete world. The world-model
  learner assumes a single anchor entity with numeric coordinates and
  deterministic effects; it has no story for partial observability, stochastic
  transitions, or continuous quantities.
* The relational learner is propositional over a *generated* literal language,
  not full first-order ILP: no variable chaining, no recursion, no invented
  predicates.
* The synthesizer's language is fixed by hand. It is honest about scope — an
  inexpressible family costs it everything — but the language was not itself
  learned.
* SST-2 at 0.765 is well below what a tuned linear model on full SST-2 achieves;
  the comparison here is against a same-budget neural arm, not against the
  literature.
* One seed per cell; differences under ~0.1 on 25 episodes are not resolvable.

## 7. What would falsify the thesis

* A world whose laws are not expressible in the fact language, where the induced
  schema silently degrades instead of failing loudly.
* An environment where the anchor frame does not exist (no privileged entity),
  removing the equivariance that carries the size generalization.
* Scaling the neural arm until it generalizes off-distribution too — the
  comparison here is at a fixed 13.97M parameters and one hour of total compute.
* Any task where imported knowledge cannot be found in symbolic form, which is
  most perceptual tasks.

## 8. Reproduction

```bash
symbolic-agent collect --config configs/symbolic-ai-old-A.yaml     # teacher episodes
python -m symbolic.experiments.symbolic_suite                    # all four axes
pytest tests/test_symbolic_learners.py -q                        # 18 assertions on what is induced
```

Individual algorithms:

```bash
symbolic-agent run --env gridworld --agent world_model --episodes 20
symbolic-agent run --env minigrid  --agent relational  --agent-args on_no_rule=random
symbolic-agent run --env seq_completion --env-args families=test --agent seq_synth
symbolic-agent run --env hf/sst2 --agent text_rules --agent-args mode=both
```
