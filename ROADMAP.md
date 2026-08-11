# Roadmap

State for autonomous continuation. Read `git log --oneline | head -20` first;
this file says what the work *is*, the log says how far it got.

## Done: parsing is decoupled from reasoning. Almost nothing uses it.

The split was built and works:

- `parsers/` — a `Parser` is `text -> ParseResult` (tokens, classes, brackets,
  facts). Registered by name, fitted on training episodes only.
- `models/` — a reasoner declares `extra.parser` and gets whatever it names.
  Reasoners must work with *any* parser, including `none`.

Four reasoners consume one: `ngram`, `grammar`, `syllogism`, `symbolalg`. All
four sit in the bottom half of the label table, and the parser matrix bought
about 1% of a bit. That is the honest state of the abstraction: it is correct,
it is tested, and it has not yet paid.

**The interesting gap.** The one model that reads prose usefully — `corefer`,
whose `said` feature is worth +0.010 copy lift — does not use a parser at all.
It counts regex occurrences of a candidate's symbol in the prompt. A parser
would give it word *classes* instead of raw counts, which is exactly the
abstraction the layer exists to provide, and nobody has tried it.

That is the natural next experiment on the parser layer, and it is a real test
rather than a tidy one: if induced classes beat a regex count inside the only
model where prose demonstrably helps, the abstraction has paid for itself; if
they do not, "parsers buy ~1% of a bit" stands as the summary of this whole
direction and should be said plainly at the top of the README.

## Why parsers can be scored exactly here

`langcurriculum` renders every episode from a typed term it also hands over, so
for each text there is a true structure. A parser's classes can be scored
against the roles the generator actually used — no annotation, no judge, and an
unbounded supply of fresh episodes, so a parser cannot be tuned to a test set.

Metric: pairwise clustering F1 between "same induced class" and "same true
role", where a word's true role is the multiset of (parent label, slot) it
occupies in the term graph.

## Measured, so nobody re-derives it

- **The parser metric has headroom.** A concern was raised that scoring two
  words as role-sharing when their role sets merely *intersect* is too loose a
  quotient, putting the one-big-class floor above F1 0.82 and leaving no room to
  measure in. Measured instead of argued: role-share base rate is **0.074** over
  all lessons (2354 words) and **0.131** on a two-lesson slice; the one-class
  floor is **0.078** and **0.232**. The quotient is tight, not loose. The
  concern was reasonable and did not hold.
- **The rule-based models are stable across processes.** Sets and frozensets
  iterate in an order that depends on hash randomisation, which is fixed within
  a process and differs between them, so a tie-break resting on iteration order
  would flap every number while looking reproducible in a single-process test.
  Checked under `PYTHONHASHSEED=1` vs `999`: all eight are bit-identical.
  `test_fitting_is_stable_across_processes` keeps it that way.

- **`rgt`'s type win is uniform across node types, not one class carrying it.**
  A +0.587 type lift against a next-best +0.295 is large enough to suspect a
  degenerate cause -- one dominant class predicted well, or a skew the floor
  handles badly. It is not. Per-type accuracy for the trained `rgt`, over 6,422
  scored nodes:

  | type | n | acc | share |
  |---|---:|---:|---:|
  | `ident` | 2552 | 0.930 | 0.397 |
  | `pred` | 1794 | 0.939 | 0.279 |
  | `num` | 818 | 0.813 | 0.127 |
  | `list` | 423 | 0.856 | 0.066 |
  | `field` | 400 | 0.985 | 0.062 |
  | `token` | 149 | 0.960 | 0.023 |
  | `record` | 123 | 0.935 | 0.019 |
  | `char` | 110 | 0.991 | 0.017 |
  | `str` | 53 | 0.774 | 0.008 |

  Every class lands between 0.774 and 0.991, and the two that make up two thirds
  of the nodes are near the middle of that range. The model is not winning by
  being excellent at one frequent thing.

  This is a diagnostic, not a headline: it draws its own masks, so it scores
  6,422 nodes where the sweep scored 6,344, and gets 0.9168 against the sweep's
  0.915. The sweep remains the authority for the number.

- **Three models score bit-identically on type, and it is not a bug.**
  `evidence`, `routes` and `symbolalg` all report type_acc
  **0.6990857503152585** over the same 6,344 nodes on the full curriculum. Two
  identical numbers is a coincidence; three to sixteen digits is a shared cause,
  so I went looking for one, expecting a broken fallback.

  It is not that. All three emit type votes on 85-89% of nodes rather than
  abstaining, their predictions are not constant (three distinct types), and on
  a sample they agree node for node. The cause is that their type heuristics are
  *equivalent*: each copies the type of a structural neighbour, and on a tree
  whose node types are nearly determined by shape, sibling-copying and
  peer-copying and best-match-copying return the same answer almost everywhere.
  Three models, one method, arrived at independently.

  They sit below the type floor because the floor is a lookup on
  `(parent type, slot, depth, has children)` -- strictly more context than any
  neighbour-copy uses -- so on 179 lessons the table wins. That is a result
  about the task, not a defect in the models. `ilp` and `workspace` differ
  slightly (0.6687, 0.6695) and are doing something marginally their own.

  One real asymmetry was found on the way and left alone deliberately:
  `symbol_backoff` receives a structural `context_prior` at inference and
  `type_backoff` does not, so an abstaining model falls back to the global type
  marginal rather than the structural one. That is worth fixing, but it cannot
  be the explanation here -- it only reaches the 10-15% of nodes where these
  models abstain, and it would not produce identical predictions on the rest.

- **Prose frequency predicts the copy source, weakly, and my first measurement
  of it had the sign backwards.** All four pointers key on tree shape alone and
  none reads the text, so the question is whether the text would help.

  Measured on **training** episodes only: for each masked node, compare the
  prompt-frequency of a correct source against one randomly drawn wrong
  candidate. Correct is more frequent **56.2%**, less **32.0%**, tied 11.8% —
  an AUC of **0.621** against 0.5 for no signal. Real, and modest.

  The first version of this measurement compared the *maximum* frequency over
  all correct candidates against the maximum over all wrong ones and reported
  that the correct source was less frequent 73.9% of the time. That is an
  artefact: the wrong-candidate set is far larger, and a maximum over more draws
  is larger for that reason alone. The bias produced a confident result with the
  wrong sign, from data that actually says the opposite.

- **The prompt does not leak hidden node labels; prose is admissible.** Asked
  and answered by `shortcuts.node_text_leak`, before anything was built on it.
  Over 12,201 masked labels:

  | | |
  |---|---:|
  | answer already on a visible node | 0.711 |
  | answer not in the graph at all | 0.289 |
  | of those, prompt contains the answer | 0.567 |
  | of those, **uniquely determined by the prompt** | **0.000** |
  | expected accuracy of the cheat, when absent | 0.025 |
  | **expected accuracy of the cheat, overall** | **0.007** |
  | structure-only label floor, for comparison | 0.105 |

  The text carries the symbol without carrying its *position*, which is exactly
  the distinction this task rests on: the question is which node, not which
  symbol. Not once in 12,201 draws does the prompt pin the answer down, and a
  text-only cheat scores an order of magnitude below the floor it would have to
  beat. `test_the_prompt_does_not_leak_hidden_node_labels` keeps it that way and
  will fail if the margin ever closes.

  So the prose pointer is unblocked.

## Open questions

- [x] **Re-rank the pointer's own candidates. Do not ensemble the pointers.**
      Done: `corefer` is two-stage, copy lift +0.063 -> +0.096. Widening the
      candidate pool afterwards bought nothing (recall 83% -> 99%, accuracy
      flat), so stage two's discrimination is the constraint, not its input.
      Both options measured before building either, which is the only reason the
      cheaper-looking one was rejected.

      An ensemble is the obvious move — four pointers, different mechanisms —
      and its ceiling is low. A *perfect* selector over all four reaches
      **0.397** against `corefer` alone at 0.306, and the pair that combines
      best is `corefer`+`evidence` (either-correct 0.379) even though `evidence`
      is the weakest of the four. Diversity, not strength, is what an ensemble
      buys, and it buys about +0.09.

      Re-ranking has more than twice the headroom, because the signal is already
      there and only the order is wrong. Where `corefer` puts the correct node,
      as a share of the positions that have one:

      | | eval | train |
      |---|---:|---:|
      | top-1 (what it scores) | 43.7% | 48.1% |
      | top-3 | 59.1% | 59.6% |
      | top-5 | 67.3% | 67.3% |
      | top-10 | **78.1%** | **78.7%** |

      The right answer is in its top ten roughly four times in five and gets
      picked out of them fewer than half those times. Confirmed on training
      episodes so the decision does not rest on eval. As a share of *all* scored
      positions that is 0.549 reachable by re-ranking `corefer` alone, against
      0.397 for a perfect ensemble of all four.

      So: keep the naive-Bayes score as a **candidate generator**, take its top
      k, and score those few with features too expensive or too sparse to apply
      to every node — full joint contexts, agreement between the other three
      pointers, whether the candidate's symbol fits the query's type. Sparse
      features that ruined the first-pass model are affordable over ten
      candidates and were not over a hundred.

- **Two episode-local candidate features, both slightly harmful.** After the
  cross-episode symbol prior failed, the remaining idea was episode-local
  evidence — something the structure-only floor cannot compute. Measured per
  question on training episodes, then tested on the held-out train slice:

  | feature | AUC | dev copy accuracy |
  |---|---:|---:|
  | baseline (no such feature) | — | **0.4036** |
  | `same_ctx_count` / `echo`: symbol already fills the query's role here | 0.581 | 0.3984 |
  | `in_episode_count`: how often the symbol occurs at all | 0.442 | not built |

  A feature at AUC 0.581 did not survive contact with the model, which is now
  the third candidate-level feature in a row to fail. Prose at AUC 0.621 was
  worth +0.010 copy lift; the returns below that appear to be negative, and the
  likely reason is that naive Bayes adds a weak correlated signal to features
  that already carry it rather than absorbing what is new.

- **The symbol-plausibility feature the error analysis called for does not
  help, and the first version of it was reading its own target.** The diagnosis
  below said two candidates of the same type in similar positions are separated
  only by which symbol they carry, so stage two got a feature: where the
  candidate's symbol ranks among symbols seen in this query context, counted
  from training answers, keyed exactly as the structure-only floor keys its
  lookup.

  | | dev copy accuracy |
  |---|---:|
  | no symbol prior | **0.4036** |
  | prior fitted on the reranker's own episodes | 0.3614 |
  | prior cross-fitted, 2 folds | 0.3968 |

  The first number to distrust was the *drop*. A useless feature costs a little;
  losing 0.042 means the feature was actively misleading, and it was: the prior
  was built from the same episodes that supply stage two's training examples, so
  the gold symbol had contributed to the very counts it was being ranked
  against. `fits == 0` meant "correct" while fitting and meant much less at
  prediction time. Cross-fitting the prior — count it on the folds an example
  did *not* come from — recovers 0.035 of the 0.042, which is the size of the
  leak.

  The residue is the real answer: even leak-free, the feature is slightly
  harmful. Reverted. The diagnosis that produced it may still be right about
  *what* distinguishes the candidates while being wrong that a context-keyed
  symbol frequency is how to express it — the floor already computes that
  quantity and the pointer is meant to add what the floor lacks.

  Measured on a held-out slice of training episodes throughout; eval untouched.

- **Candidate recall is not the pointer's constraint; discrimination is.** The
  obvious next move after the two-stage pointer was to widen stage one's top-k,
  since stage two can only pick from what it is shown. Measured on a held-out
  slice of *training* episodes, fitting on 3,000 and scoring on 580, so the
  choice of k never touched eval:

  | top_k | stage-1 recall (train) | dev copy accuracy |
  |---:|---:|---:|
  | 10 | 82.7% | 0.4036 |
  | 20 | 93.1% | 0.4043 |
  | 40 | 98.7% | 0.4012 |

  Recall climbs 16 points and accuracy does not move. Every candidate added is
  found by stage two and then not chosen, so precision loss cancels the recall
  gain exactly. Keeping k=10; the wider pools cost counts and buy nothing.

  **What it confuses instead.** Over 3,821 errors where the answer *was* in the
  candidate set: it picks `same_head_same_slot` 61% of the time and `sibling`
  31%, while the correct node is `same_grandparent` 25% and `same_depth` 11% —
  it reaches for the structurally nearest candidate when the answer is often one
  step further out. And **86.2% of the time the node it picked has the same type
  as the one it should have picked**, so node type carries almost no
  discriminating information at the point of the mistake.

  That is the shape of a *missing feature*, not a mis-weighted one. Two
  candidates of the same type in similar structural positions are separated by
  which *symbol* each carries and whether that symbol is plausible in this query
  context — precisely the information the pointer was built to avoid using, and
  precisely what the structure-only floor's lookup table already estimates. The
  pointer knows where to look and not what is plausible; the label head knows
  what is plausible and not where to look.

- **The copy floor resists the treatment that fixed the type floor, and the
  reason generalises.** The type floor went 0.795 -> 0.860 by replacing one
  four-feature key with a backed-off ladder of richer structural contexts. The
  copy floor is a single fixed relative offset per context at 0.266, so the same
  move looked obviously right. It is not:

  | content-blind copy baseline | accuracy |
  |---|---:|
  | **commonest offset per context** (kept) | **0.266** |
  | signature: sibling, slot, depth delta, type | 0.253 |
  | the same signature with the offset added back | 0.250 |

  Adding structure made it worse, and adding *more* structure made it worse
  again. The type question has about nine answers and thousands of observations
  per key, so a specific key is both sharp and well-supported. The pointing
  question has a median of 55 candidates and a signature space in the thousands,
  so specific keys are seen a handful of times and the argmax over candidates
  turns to noise. Exact relative position generalises where a conjunction of
  five structural facts does not.

  This is the same sparsity boundary that killed the reranker's `(query, said)`
  feature over a hundred candidates and left it useful over ten. Richer keys pay
  when the answer space is small and the data per key is large, and cost when
  either fails. Neither the type floor's success nor this failure is about the
  features being right; both are about that ratio.

  The copy floor stays at 0.266 and `corefer`'s +0.096 stands.

## Naming

Models are registered as `name-001`. A bare name resolves to the highest
version, so every existing config, script and command keeps working; a versioned
name pins a specific model and never moves. Variants go beside their predecessor
rather than replacing it — `corefer-002`, or `corefer-noprose` when the point is
what changed rather than when.

Register the new one, leave the old one registered, and let `sweep --models
corefer-001,corefer-002` print both rows. That is the comparison this repo keeps
wanting and has so far only been able to describe in commit messages.

## Design rules, learned the expensive way

1. **The label head and the type head do not share machinery.** Discovered four
   times now, each time by paying for it:

   | what was shared | cost |
   |---|---|
   | omegaclaw's calibrator, priced the type head with the label head's confidence | **-1.96 type lift**, on three models at once |
   | `corefer` abstained on type, falling through to the global marginal | **-1.950**, identical to a model with no type opinion |
   | `corefer` pointed both heads with one prose-informed pointer | **0.174 -> 0.004** |
   | seven rule-based models below the type floor while clearing the label floor | the standing shape of the table |

   The reason is not incidental. The label question is *which thing is this* and
   the type question is *what kind of thing sits here*; evidence for one is
   routinely evidence against the other. Prompt frequency is a fact about a
   symbol's identity, so it helps the label head and actively misleads the type
   head. Anything shared between them — a calibrator, a confidence, a pointer —
   should be justified before it is written, not after it costs a lift.

2. **Pool by question, never by candidate.** Twice now a pooled average has
   produced a confident conclusion with the wrong sign, and both times the
   broken version was the one that looked like a finding.

   | measurement | pooled | per question |
   |---|---:|---:|
   | prose frequency picks the right source | "less frequent 73.9%" | **AUC 0.621** |
   | in-episode symbol count picks it | **AUC 0.823** | **AUC 0.442** |

   The mechanism is the same both times and is not subtle once seen. A question
   with many correct candidates contributes many positive rows, so any feature
   correlated with *having many correct candidates* — which frequency is, by
   construction — looks predictive when rows are pooled. A maximum over the
   larger set does the same thing. The fix is always the same: one positive
   against one negative, drawn per question.

   `in_episode_count` is the sharpest case. Pooled it reads 0.823, which would
   have been the strongest feature ever measured here. Per question it is 0.442,
   *below chance*.

3. **A technique that worked once is not a technique that works.** Interacting a
   feature with the query context took `corefer` from -0.036 to +0.053. The same
   move applied to the prose feature made every head worse. `(query, rel)` is
   dense and `(query, said)` is sparse, and naive Bayes has nothing to smooth
   the second with.

## Scope

The **symbolic models are the subject**. The neural half exists as a control and
is no longer registered by default: it is the only part of this repo that wants
a GPU, and on a shared machine that means competing with real training for no
benefit to the question being asked. `SYMBOLIC_AI_MODELS_NEURAL=1` brings it
back for a run where the cross-family comparison is the point. Nothing was
deleted and its tests still run under that flag.

Everything defaults to CPU now, including `TrainConfig.device`, which used to be
`auto` and took an accelerator whenever one existed.

## Task list

- [x] **Finish the full-curriculum sweep and rewrite the conclusions.** Eleven
      of thirteen are in and the conclusion reversed completely; README
      rewritten. `synth` and `workspace` are resuming.
- [x] **Re-run the neural half with a step budget matched to the data.** Done
      for four of six; `hrr` and `ndr` deliberately left at 300 steps. Every
      network re-run cleared the label floor, so the -0.050 that the family
      claim rested on was an artefact. `rgt` is first of nineteen on node type
      at +0.587. All four were still climbing at 2000, so every neural number
      here is a lower bound. **The neural half is a control and this item is
      closed**; further budget work on it is parked below and should stay
      parked unless the symbolic side needs it. A
      first attempt on CPU gave the networks 300 steps at batch 16 against 3,580
      training episodes — about 1.3 passes — while every rule-based model sees
      the training set in full. `gru` came out at -0.050 lift, which is an
      undertrained model rather than a beaten one and must not be reported as
      the family separation inverting.

      **The confound is real and does not account for the gap.** `gru` at four
      times the steps, everything else held fixed:

      | steps | passes | label acc | label lift |
      |------:|-------:|----------:|-----------:|
      |   300 |    1.3 |     0.061 |     -0.050 |
      |  1200 |    5.4 |     0.092 |     -0.015 |

      So the budget was indeed doing damage — 4x the steps closes about 70% of
      the distance to the floor — and it is still below it at 5.4 passes. That
      is one model and does not settle the family question, but it does mean the
      answer is not simply "they were undertrained".

      `runs/full179` currently holds all 19 summaries, and **the six neural ones
      are the 300-step runs**, while every rule-based entry carries the config's
      intended 2000. The table is complete and not yet comparable. Re-running
      the six at 2000 steps (8.9 passes) on CPU, `--resume` so it can be
      assembled across interruptions; ~50 min per model, no GPU taken.

      **What each outcome licenses, written down before the number lands.**
      This repo has twice had a measurement drift toward flattering the write-up,
      so the interpretation is fixed in advance rather than chosen afterwards.
      The in-flight `gru` curve (label lift by step) is:

      | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 1000 |
      |----:|----:|----:|----:|----:|----:|----:|----:|----:|-----:|
      | -0.101 | -0.051 | -0.045 | -0.041 | -0.035 | -0.031 | -0.023 | -0.011 | -0.011 | -0.002 |

      It reproduces the old 300-step figure of -0.050 at step 300, so the re-run
      is measuring the same thing the baseline did.

      **Correction.** At step 600 the per-100 gains looked flat at about +0.005
      and I recorded them that way. They were not: +0.006, +0.004, +0.006,
      +0.004, +0.008, +0.012, +0.000, +0.009. The last four are the largest
      since the opening hundred. Six points of a noisy curve were not enough to
      call its shape, and the reading that fitted them was the one that agreed
      with the result already written up.

      Over the last 500 steps (500 -> 1000) label lift moved +0.033, which is
      three times the +0.01 threshold set below for "still climbing". The type
      head crossed the floor at step 700 and has stayed there (+0.007, +0.008,
      +0.009, +0.006), and the label head is at -0.002 -- level with a
      structure-only lookup at 4.5 passes, having been -0.050 at 1.3.

      So the third branch below is the live one, and the first is now plausible
      too. What is already settled: **-0.050 at 300 steps was an undertraining
      artefact**, and no claim resting on it survives.

      - If the 2000-step lift is **>= 0**: the 300-step number was an
        undertraining artefact. Every claim about the families separating comes
        out of the README, and the table is rebuilt from the new rows.
      - If it **plateaus below 0** (under +0.01 gained over the last 500 steps):
        more budget does not rescue it. The honest claim is then bounded and
        must be stated as bounded -- a ~1M-parameter network, 8.9 passes over
        3,580 episodes, scores below a structure-only lookup table on this task.
        That is not "networks cannot do this", and must not be written as if it
        were.
      - If it is **still climbing at 2000** (over +0.01 over the last 500): the
        budget is still the binding constraint and the comparison remains
        unsettled. Say so and stop, rather than reporting the endpoint as if the
        curve had converged.

      Report the curve either way, not just the endpoint. `history.json` is
      written on the evaluation cadence, so it survives an interrupted run, and
      `compare --history` prints it.

      **`sweep --resume` would not do this and said nothing.** Its completeness
      test was "a `summary.json` exists", so raising `--steps` over a directory
      of finished 300-step runs skipped all six and reprinted the stale table.
      A no-op that looks like a successful re-run is the most expensive kind of
      wrong answer here, and the only reason it was caught is that the sweep
      returned in seconds instead of hours. Fixed: a run counts as complete only
      if it ran at least the budget being asked for, and a rule-based model
      (0 steps, fits in one pass) is always complete.
- [ ] (parked — neural, not the subject) **Run two networks past 2000 steps to
      find where the curve flattens.**
      Every network that has finished the re-run is a *lower bound*: all three
      gained more than the +0.01/500 threshold across their last 500 steps. So
      even when all six land, the pre-registered answer is "the budget is still
      binding and the comparison is unsettled", and 2000 was chosen as 8.9
      passes over the data, not because anything converges there.

      They are not even failing to converge in the same direction. Last four
      100-step gains:

      | model | gains | shape |
      |---|---|---|
      | `gru` | .0058 .0064 .0036 .0070 | flat |
      | `transformer` | .0049 .0032 .0043 .0006 | decelerating |
      | `rgt` | .0011 .0013 .0060 .0066 | **accelerating** |

      `rgt` is speeding up at the point the budget ends, so its +0.152 label and
      +0.587 type are underestimates by an unknown margin, and it is the model
      the headline type result rests on. A number that is still moving is not a
      result, it is a snapshot.

      Run `rgt` and `transformer` to 8000 steps — the two cheapest at 11 and 9
      minutes per 2000, so roughly 45 minutes each, and between them they cover
      the accelerating and decelerating cases. `gru` is excluded at 60 minutes
      per 2000; it is flat and the least informative. Stop when the 500-step
      gain is under +0.01 twice consecutively, and report the budget that took.

      Written in advance: if `rgt` keeps climbing to 8000, the honest headline is
      that **the structure-aware network was never given enough budget to
      measure**, and every neural row in this repo is a lower bound of unknown
      tightness. That is a worse-looking result than the current table and is
      the one to report if it happens.

      Blocked behind the current sweep, which owns the CPU.

- [x] **A data-budget curve for the rule-based models.** Done. The caps bind for
      two of four and cost nothing for the other two, and the split changes the
      leaderboard.

      | model | baseline | 6,000 | 24,000 | 96,000 |
      |---|---:|---:|---:|---:|
      | `ilp` | +0.231 (1,500) | +0.224 | +0.232 | — |
      | `ruleinduce` | +0.250 (4,000) | +0.247 | +0.250 | — |
      | `brill` | +0.155 (3,000) | +0.179 | +0.198 | +0.205 |
      | `workspace` | +0.191 (4,000) | +0.200 | +0.267 | **+0.280** |

      Both pre-registered outcomes happened, to different models. `ilp` is flat
      across a 16x increase, so **it really does reach fourth place on 1.1% of
      the data** and that is the headline it earns. `ruleinduce` likewise.

      `workspace` at +0.280 is **first of nineteen**, above `analogy` at +0.256,
      and it was fifth at its default cap. The published ranking was partly an
      artefact of an arbitrary constant. `brill` gains +0.05 and is decelerating.

      The sharpest part is the cost: `workspace` takes **21 seconds at 96,000
      examples against 17 at 4,000**. The cap was not buying speed. It was a
      default nobody had measured.

      **Do not pick the cap by eval lift** -- that is tuning on the evaluation
      set, and this table is a sensitivity analysis, not a search. The defensible
      change is to drop the caps to whatever runtime allows, chosen on runtime
      grounds alone, and re-run the affected models. Recorded as the next item.

- [x] **Give the label head a pointer, and score the labels it can reach.**
      Done. `target_source`, `label_group` and `source_logits` are in the
      harness; `copy_acc` is scored against a floor of 0.266 and a ceiling of
      0.722, over 5,785 positions including the 18% the label head censors.
      Four models point: `corefer` +0.096, `routes` +0.051, `ruleinduce` +0.032,
      `evidence` +0.023.
      The label task is a binding problem being scored as a classification
      problem, and the gap is most of the available signal.

      Measured on all 179 lessons: **71.9% of scored masked labels already
      appear on a visible node of the same episode**, so the answer is present
      in the graph and needs copying, not naming. The best model in the table,
      `workspace` at +0.280 lift, is at about **0.36 label accuracy against a
      0.72 copy ceiling**. Roughly half the reachable signal is untouched by
      every model here, and none of the nineteen has a pointer.

      The excluded 18% is the same story, sharper. Of 522 excluded labels, 462
      are `ident` nodes carrying invented names, and **80.7% of the excluded set
      is also copyable** — the metric drops exactly the positions where copying
      is the only route, which flatters vocabulary-based models and censors the
      capability this repo exists to study.

      **Scoring is in place (harness half done).** The copy head is now bracketed
      at both ends, measured on all 179 lessons through the sweep:

      | | copy accuracy |
      |---|---:|
      | random pointer | 0.048 |
      | **structure-only floor** (commonest offset per context) | **0.266** |
      | best label-head model today (`ilp`, as label acc) | 0.312 |
      | **oracle pointer** (the ceiling) | **0.722** |

      So a pointer has to clear 0.266 to have read anything, and there is 0.46
      of headroom above it. `label_group` gives label identity that survives
      being out of vocabulary — vocabulary ids collapse every invented name to
      `unk`, so two different invented names would compare equal and a pointer
      that copied the wrong one would score as correct.

      **First pointer measured, and it is a weak positive.** `evidence` already
      retrieved the best-supported node and then threw the node away, summing
      its overlap into a vote for that node's *label*. Kept as a node instead:

      | | value |
      |---|---:|
      | `evidence` copy accuracy | 0.283 |
      | structure-only floor | 0.266 |
      | **copy lift** | **+0.023** |
      | its own label accuracy | 0.219 |
      | positions scored (copy vs label) | 5,785 vs 5,233 |

      Two things worth separating. The same retrieval scores **better as a
      pointer than as a symbol** (0.283 vs 0.219) while answering 552 *more*
      questions, including the invented names the symbol head cannot express —
      so the projection to vocabulary was lossy, as predicted. But +0.023 over a
      fixed-offset rule means generic structural similarity is barely better
      than "copy from the usual place", and 0.44 of headroom to the 0.722
      ceiling is still untouched.

      **`corefer`: a pointer that clears the floor, after two wrong diagnoses.**
      Learns from training graphs which pairwise features predict that two nodes
      share a label, naive Bayes, 310 counts, 16 seconds.

      | version | copy acc | copy lift | label lift |
      |---|---:|---:|---:|
      | pairwise features only | 0.239 | **-0.036** | 0.188 |
      | redundant features collapsed | 0.239 | -0.036 | 0.188 |
      | **+ query context** | **0.305** | **+0.053** | **0.248** |

      First diagnosis, wrong: `siblings`, `same_grandparent`, `same_depth` and
      `same_ptype` are four views of one fact, naive Bayes added all four, and
      **99.3% of picks landed at the same depth as the query**. Collapsing them
      into one categorical changed copy accuracy by 0.001 and left the same-depth
      rate at 99.3%. The double count was real; it was not the constraint. Same
      depth is simply where most coreference lives.

      Second diagnosis, right: every feature was *pairwise*, so the model learned
      one global ranking function while the floor learns a separate offset per
      structural context. A global ranking loses to a conditioned one by
      construction. Adding the query's own context — its parent type and slot,
      interacted with the relation and the distance — moved copy lift from
      -0.036 to +0.053, more than double `evidence`'s +0.023, and label lift to
      +0.248, which is fourth of twenty.

      Still only 0.305 of a possible 0.722. The pointer works; it is not close to
      the ceiling.

      What that suggests: retrieval keyed on *generic* structural similarity is
      the wrong key. Coreference is the relation that matters, and the harness
      already computes `same_label` edges and withholds them for hidden nodes.
      A pointer keyed on what predicts coreference — shared parent head, same
      argument position across two occurrences of a predicate — is the next
      thing to try, not a better similarity metric.

      Two parts, and the second is the one that changes what is being measured:

      1. A vote over *nodes* rather than symbols, mixed with the existing
         symbol back-off and gated on first-mention vs subsequent. `ruleinduce`
         already predicts pointers and is second on labels at +0.250, so the
         mechanism is not speculative here.
      2. Score copy-style predictions against the excluded set, so
         `label_coverage` stops being a number that quietly removes the hard
         cases.

      Expect this to reorder the table, and expect the models built *not* to
      memorise — `analogy`, `ruleinduce` — to gain most, since the reason they
      were handicapped was a metric that never scored what they were built for.

- [x] **Strengthen the type floor.** Done. The floor is now a backed-off ladder
      of six structural contexts rather than one four-feature key, still
      content-blind — sibling *types* and child counts are structure, and no
      symbol appears anywhere in it.

      | floor | old | new |
      |---|---:|---:|
      | type | 0.795 | **0.860** |
      | label | 0.105 | **0.143** |
      | copy | 0.266 | 0.266 (separate rule, unchanged) |

      Every lift in the repo was measured against the old numbers and shrinks.
      `rgt`'s 0.915 type accuracy is +0.587 against the old floor and **+0.393**
      against this one; `corefer`'s 0.946 is +0.736 and **+0.613**. The ranking
      is unchanged, which is worth saying plainly — the floor was inflating all
      the type lifts by roughly the same amount rather than favouring anyone.

      What the model still has that the floor does not is the pointer: `corefer`
      reaches 0.946 where the same lookup without the pointed node's type as a
      conjunct reaches 0.860, so the binding is worth about 0.086 of type
      accuracy on top of the strongest content-blind baseline.

- [x] (superseded) Strengthen the type floor. It is now known to be weak.
      A backed-off conjunctive lookup inside `corefer` -- counting, no tensors,
      6 back-off levels, sibling types and arity added to the floor's four
      features -- reaches **type accuracy 0.946** where the floor reaches 0.795
      and `rgt`, the structure-aware network, reaches 0.915.

      So the headline of the neural control, `rgt` first of nineteen on node
      type at +0.587, is **below a counting baseline**. That does not make the
      neural number wrong, it makes the floor too low, and every type lift in
      the table is inflated by the same amount. The label floor has no such
      problem: it is 0.105 and the best model reaches 0.357.

      The fix is the one already written here -- fit the floor with the richer
      structural features, still content-blind so it stays a floor -- and it now
      has to happen before any type number is quoted again.

- [x] (superseded) Strengthen the type floor before trusting `rgt`'s +0.587. The floor is
      a lookup on four structural features and reaches 0.795; `rgt` reaches
      0.915. How much of that margin is the model and how much is a weak
      baseline is unknown, and the headline result of the neural control rests
      on it. Fit a decision tree or gradient boosting on the same structural
      features — still content-blind, so still a floor — and see what survives.

- [x] **Set the example caps from runtime, not from a guessed constant.** Done,
      and the choice was made from wall clock alone so that no cap was picked by
      the score it produced. Budget: the largest value fitting 300s on the full
      curriculum, well under `synth`'s 1,500s which the sweep already tolerates.

      | model | uncapped runtime | cap now | label lift |
      |---|---:|---:|---:|
      | `workspace` | 26s | none | +0.154 -> **+0.249** |
      | `brill` | 200s | none | +0.117 -> **+0.172** |
      | `ruleinduce` | 279s | none | +0.217 -> +0.217 |
      | `ilp` | **timed out past 900s** | 24,000 | +0.197 -> +0.198 |

      `workspace` moves from eighth to joint first on labels, and its old cap of
      4,000 was buying **four seconds**. `brill` gains 0.055 for 176s. The two
      whose curves were already flat do not move, exactly as the ladder
      predicted, which is the useful confirmation: raising a cap is not a free
      win, it is a win precisely where the curve was still climbing.

      `ilp` is the one model that cannot be uncapped at all — it ran past a 900s
      timeout, and 48,000 costs 462s. That is not a tuning decision, it is what
      its search costs.

      `analogy` uses `max_cases` rather than `max_examples` and was left alone;
      a different knob wants its own measurement.

- [x] (superseded) Set the example caps from runtime, not from a guessed constant, and
      re-run the four affected models.** The curve above says `workspace` and
      `brill` are held back by theirs and `ilp` and `ruleinduce` are not. The
      cap must be chosen *without* reference to eval lift, or the whole table
      becomes tuned on its own test set: pick the largest value each model can
      consume in a sensible wall-clock budget and use that. Runtimes measured
      above: `workspace` 21 s and `brill` 136 s at 96,000; `ilp` 240 s at 24,000
      and superlinear, `ruleinduce` 96 s. Then re-run those four in
      `runs/full179` so the published table is not a mix of policies -- the
      budget-drift warning will flag it until they all agree.

- [x] (superseded) A data-budget curve for the rule-based models, the mirror of the step
      curve for the networks.** Five of them cap their training examples:
      `ilp` 1,500, `brill` 3,000, `ruleinduce` 4,000, `workspace` 4,000, and
      `analogy` by `max_cases`. Measured against the ~130,800 masked-node
      examples the full curriculum yields, that is 1.1% for `ilp` and about 3%
      for the others. The README claimed the opposite -- "every rule-based model
      sees the training set in full" -- and that claim was the load-bearing half
      of the argument that the networks' 300 steps were unfair.

      So the asymmetry ran both ways and neither side was measured. Raise the
      caps in `extra` and plot lift against examples consumed, exactly as
      `history.json` now gives lift against steps. Two outcomes worth
      distinguishing in advance: if the curves are flat, the caps cost nothing
      and `ilp` reaching fourth on 1.1% of the data is the headline; if they
      climb, every rule-based number in the table is a lower bound and the
      family comparison has to be redone at matched data.

      Do not start this until the neural re-run finishes -- it owns the CPU.

- [x] (superseded) Finish the full-curriculum sweep and rewrite the conclusions. Running
      via `configs/full179.toml --tasks node`. Nothing in the README should be
      trusted until the complete table is in. Run it with `--resume` so an
      interruption costs one model rather than all of them. **Do not kill it**:
      `ctw` takes about two and a half minutes on its own and I mistook that for
      a hang twice, restarting from scratch both times.

- [x] **Re-run the full sweep and correct the README.** Done, and it refuted
      the claim that prompted it: three rule-based models did *not* clear the
      floor. Those measurements were taken at 50 training episodes per lesson
      and do not survive the sweep's 200 — see below.
- [x] **Why do the rule-based models degrade with more data?** They do not.
      The premise was noise from a 12-episode evaluation set; at 240 episodes
      every curve is flat. A real truncation bug was found and fixed on the way
      and changed nothing measurable. See below.

- [x] `parsers/base.py` — Parser, ParseResult, registry
- [x] `parsers/evaluate.py` — gold roles from the graph, clustering F1
- [x] parsers: `none`, `regex`, `categorical`, `induced`, `chunker`
- [x] `symbolic-ai-models parsers` and `parse-eval` CLI
- [x] reasoners accept `extra.parser`; `ngram` consumes one. Matrix swept:
      the abstraction level works and buys ~1% of a bit (see below)
- [x] scale test: parser quality vs number of training episodes (the curriculum
      is unbounded, so this curve is free and is the point of the exercise)
- [x] **Move the shared parsing primitives down into `parsers/`.** Done: the
      symbol algebra, clause splitter, lexicon and categorical fragment now live
      in `parsers/primitives/`, the model-side import is a plain top-level one,
      and `tests/test_layering.py` asserts no file under `parsers/` imports a
      model. The runtime version of that check does not work — the top-level
      package imports everything, so it measures the convenience surface rather
      than the layering — so the check reads the import statements instead.

### Next, from the design docs in `.old/docs` (ranked)

Cheap and high-value first; each is exactly measurable under this harness.

- [x] **Report shape, not the average.** `CurriculumReport` now leads with
      `solved` (lift >= 0.90) and `above_floor` (>= 0.15) over the lesson count;
      the macro-average is kept below them, labelled as describing neither mode.
      Still to do: the same treatment for the per-lesson breakdown of the `lm`
      and `node` tasks, which currently aggregate over all episodes at once and
      so cannot report a shape at all.
- [x] **Shortcut audits as extra floors.** Nine parameter-free cheats in
      `shortcuts.py`; the curriculum floor is now `max(uniform, majority, best
      cheat)` and the table names which cheat won. Audited all 179 lessons: no
      lesson is shortcut-solvable (nothing at or above 0.9), and the worst is
      `compiler_construction` at 0.467 against a uniform 0.250. This curriculum
      holds up better than the source work's did.
- [x] **Renaming invariance.** Done, and it refuted the repo's headline claim
      (see below). Note the test is for *equivariance*, not invariance: renaming
      moves the correct answer too, so accuracy is the quantity that must hold
      and logits are the wrong one to compare.
- [x] **Make `analogy`'s transfer structure-only.** It now carries a *route*
      ("the answer stood at my slot-0 sibling") instead of a symbol. Renaming
      delta is exactly 0.000, and the cost was most of the score: sweep label
      accuracy 0.463 -> 0.186, lift 0.208 -> -0.200, from best-in-repo to below
      the floor. `hrr` is the honest leader at 0.420 / 0.144.
- [x] **Calibration.** `calibration.py` buckets stated confidence against
      observed accuracy; ECE / MCE / signed overconfidence, wired into
      `eval --calibration`. Finding below.
- [x] **Replace the ad-hoc confidence formulas.** `ScoreCalibrator` fits an
      isotonic map from internal score to observed accuracy on held-out
      outcomes. `analogy` ECE 0.368 -> 0.051, `workspace` 0.320 -> 0.055, both
      now as well calibrated as `ngram` (0.048). Accuracy and the renaming
      delta are untouched, so this bought honesty and cost nothing.
      Bucket by it, report accuracy per bucket and ECE. Free.
- [x] **Cross-language transfer.** Measured, and the claim needed correcting
      rather than confirming — see below. The node task cannot test it at all;
      the text task can and shows nothing transferring.
- [x] **Held-out-slice selection.** Confirmed for `ruleinduce` and fixed
      (0.170 -> 0.099 ECE). Not confirmed for `brill`, where two attempts at the
      same fix made it strictly worse and were reverted — see below. `synth` and
      `grammar` do not select on training: `synth` fits each program on the
      prefix it is about to predict from, and `grammar`'s threshold is a fixed
      knob rather than a choice made against outcomes.
- [x] **Per-episode parameter fitting.** Built and ablated; it contributes
      exactly 0.000 here — see below. The route machinery it was built on was
      worth keeping and ships as the `routes` model; the per-episode refit is
      off by default with a knob to reproduce the null.
- [x] **Anchor-relative features.** Built, ablated, measured neutral-to-negative
      (-0.011 accuracy, worse calibration) and shipped off by default. Third
      null in a row, and the pattern is the real finding — see the note on
      priority below.
- [x] **PRIORITY: get any rule-based model above the label floor.** Done,
      barely: `analogy` at +0.008 lift, by pairing route transfer with a
      memorising fallback. See below — the margin is thin and the interesting
      part is what it took.
- [x] **Widen the margin.** The diagnostic run across all twelve found `ilp`
      answering 35% of nodes at 0.525 and `synth` 1% at 1.000 — mechanisms well
      above the floor, buried under abstention. The fallback moved into
      `RuleBasedModel`, so `ilp` is now the best rule-based model at +0.025 lift.
- [x] **`ruleinduce` loses 0.116 to the mixture.** Diagnosed wrongly in that
      note and fixed properly: the issue was not point-vs-probability but that
      an *abstaining* model fell back on the structural prior while a merely
      *unsure* one fell back on the unigram. The back-off is now structure-aware
      for both. `ruleinduce` 0.076 -> 0.297.
- [x] **Fit the confidence map against the final mixture.** Done via post-hoc
      temperature scaling on the graph output — and it selected **T = 1.0** for
      every model, i.e. there was nothing to rescale. The elevated ECE is a
      top-1 artifact, not a mis-scaled distribution; see below. The suspended
      assertion is replaced with a stronger one on the temperature itself.
- [x] (done, kept for the record) Anchor-relative: re-express features relative to
      the masked node or the query subtree — relative depth, sibling offset,
      path-from-query — so a hypothesis learned on one episode is *identical*
      rather than merely similar on another.
- [x] **Cap the counting models' memory.** Done, and the two models want
      opposite defaults — see below. `ngram` and `grammar` take a count cutoff
      and a hard cap; `ctw` has tree pruning available but off.

### Measured: the parser x reasoner matrix, first cut

`ngram` gained a class-context back-off level fed by whatever parser it is
given. Fitted on 240 episodes over four lessons, scored on disjoint seeds:

    parser        ctx  bits/tok  ans_acc
    none            0     1.269    0.227
    induced        36     1.256    0.227
    chunker      1013     1.265    0.227
    categorical    67     1.266    0.227
    regex          19     1.269    0.227

So the plumbing works and the payoff is ~1% of a bit, with answer accuracy
untouched. The likely reason is that at order 4 with this much data the literal
contexts nearly always hit, so the abstract level is seldom reached — the
abstraction is real but rarely needed. Worth retesting at small training sizes,
where literal contexts miss often and generalising the context should matter
most; that is the regime the parser scaling curve already showed `induced`
winning in.

### Measured: what the shortcut audit found, and what it did not

Nothing is shortcut-solvable. Across 179 lessons the strongest cheat anywhere is
0.467 (`compiler_construction`, "pick the longest option", uniform 0.250). The
source work found seven lessons solvable outright; this generator has none.

The first pass said otherwise and was wrong, which is the more useful result.
`compiler_construction` measured 0.867 and `grammar_induction` 0.783 — both
apparently decisive leaks — until the tie-breaking was fixed. Every shortcut
resolved ties on the option string, so with no signal they all chose the
lexicographically largest option, agreed with each other by accident, and posted
inflated scores that the `max` then picked up. Ties now fall to position, which
is neutral and uncorrelated across cheats. The "leaks" were mostly in the audit.

### Measured: renaming refutes the repo's headline claim

Fitted on the original episodes, scored on episodes where every in-vocabulary
symbol is permuted (graph and prose together, a derangement, so nothing can pass
by accident). Masked-node label accuracy:

    model         orig  renamed    delta
    analogy      0.417    0.036   -0.381
    grammar      0.302    0.000   -0.302
    ngram        0.252    0.014   -0.237
    ctw          0.230    0.007   -0.223
    brill        0.266    0.086   -0.180
    ruleinduce   0.230    0.151   -0.079
    symbolalg    0.108    0.036   -0.072
    workspace    0.194    0.137   -0.058
    syllogism    0.043    0.036   -0.007
    evidence     0.151    0.151   +0.000
    ilp          0.129    0.129   +0.000

`analogy` was reported as the best label predictor in the repo and as the
strongest case that structure beats gradients. It loses more to a pure renaming
than any other model. Its retrieval and alignment are genuinely structural, but
its *readout* memorises, so most of that score was vocabulary. `evidence` and
`ilp` are the only models that lose nothing.

The measurement itself was wrong on the first attempt: it used `mask_all=True`,
which hides every label, so any model answering by copying a visible neighbour
scored 0.000 on both sides. Implausible baselines are what exposed it; the mask
rate is now the one evaluation uses.

### Measured: which confidences mean anything

Masked-node task, four lessons, fitted on training seeds and scored on disjoint
ones. `over` is signed, so a model that is systematically too sure reads
differently from one that is too shy:

    model            acc   stated    over     ECE     MCE
    analogy        0.219    0.586  +0.367   0.368   0.770
    workspace      0.216    0.534  +0.318   0.320   0.534
    ruleinduce     0.228    0.398  +0.170   0.170   0.779
    ctw            0.226    0.083  -0.143   0.143   0.194
    brill          0.272    0.352  +0.080   0.095   0.098
    grammar        0.271    0.262  -0.009   0.076   0.220
    ilp            0.165    0.207  +0.042   0.059   0.165
    ngram          0.217    0.258  +0.041   0.054   0.121

The split is not between good and bad models, it is between two ways of
building a confidence. `ngram` uses `m / (m + k)` on the observations behind a
context and `ctw` uses the posterior mass it put on the symbols it named —
both are estimates of *being right*, and both come out calibrated. `analogy`
uses `0.2 + 0.6 * alignment_score` and `workspace` uses `1 - temperature`; both
rise with how much structure was found rather than with how often that
structure was correct, and both are badly overconfident.

`analogy` is the sharpest case: in its most populated bucket it states 0.881 and
delivers 0.338. Note this is *after* the route fix — that repair made it
equivariant under renaming without making its confidence honest, so the two
defects were independent.

### Measured: cross-language transfer, and why the node task cannot test it

`Lesson.structured` takes no language, so the term graph is byte-identical
whatever the prose says. A cross-language masked-node experiment therefore hands
the model the graphs it trained on and would report perfect transfer while
measuring nothing. Pinned in `tests/test_language.py`.

On the text surface, fitting on English and evaluating elsewhere:

    model     lang       bits/tok  ans_acc  choice   floor    lift
    ngram     english       1.415    0.240   0.350   0.425  -0.130
    ngram     chinese      23.527    0.015   0.325   0.400  -0.125
    ngram     turkish      20.459    0.022   0.325   0.425  -0.174
    grammar   english       1.258    0.040   0.350   0.425  -0.130
    grammar   chinese      13.826    0.015   0.325   0.400  -0.125
    analogy   english       6.367    0.000   0.400   0.425  -0.043

Language modelling collapses -- 1.4 bits/token to 23.5 -- which is the byte
fallback doing its job of staying lossless without being affordable. Choice
accuracy barely moves, but it is *below floor in all three languages including
English*, so there is nothing to transfer and the small drop is noise around
chance. `analogy` abstains on text entirely, so its flat line across languages
is vacuous rather than impressive.

The honest reading: this experiment cannot say anything until some model is
above floor in its source language. Worth re-running once one is.

### Measured: whose stated confidence was training-inflated

`ruleinduce` reports each rule's confidence as its accuracy on the examples the
rule was induced from, and greedy separate-and-conquer fits rules until they are
nearly pure — so that number is near 1.0 by construction. Scored against
held-out episodes: weighted stated **0.953** against **0.627** delivered, with
individual rules claiming 1.000 and returning 0.364. Calibrating on a held-out
fifth took its ECE from 0.170 to 0.099.

`brill` was the negative result and the more useful one. Its confidence comes
from the same kind of training count (`fixed / (fixed + broke)` measured while
the rule was being chosen), so it looked like the same defect — but it was
already well calibrated at ECE 0.095, and both attempts to "fix" it made it
worse: 0.338, then 0.548. Reverted. The lesson is that an argument for why a
number *should* be inflated is not evidence that it is, and the measurement has
to come first.

The first `brill` attempt failed for a reason worth recording: it held out the
last fifth of the flat example list, which is not held out at all, because
examples come from repeated masked passes over the same episodes.

### Measured: per-episode fitting buys nothing on this task

The plan was to split the hypothesis *family* (which structural routes exist,
induced across training) from the *member* (which route is in force here, fitted
inside each episode from its own visible nodes). An episode carries dozens of
worked examples, so whichever route explains the five visible objects in a scene
ought to explain the sixth.

    use_episode_fit=True    acc 0.173   ECE 0.106
    use_episode_fit=False   acc 0.173   ECE 0.043

Identical accuracy, worse calibration. The likely reason is that the context
prior already conditions on `(parent type, slot, arity)` and episodes within a
lesson are structurally homogeneous, so what an episode demonstrates about its
own routes the prior already knew. Off by default; the knob stays so the null is
reproducible.

The first implementation counted route successes without counting failures,
making the endorsement uninformative for a stupider reason. Fixing it to a rate
moved the contribution from +0.007 to +0.000 — so the mechanism is genuinely
neutral here rather than merely mis-implemented, which is the version of the
result worth trusting.

What survived is the route vocabulary itself, now shared in `models/routes.py`
between `analogy` (which replays the route a remembered case used) and `routes`
(which follows the route its context expects). Both are exactly equivariant
under renaming.

### Measured: the family separation, and why the last three items were nulls

Sorted by label lift on the full sweep:

    hrr          neural       +0.144
    rgt          neural       +0.097
    tpr          neural       +0.069
    transformer  neural       +0.051
    gru          neural       +0.039
    ndr          neural       +0.029
    grammar      rule-based   -0.081
    ngram        rule-based   -0.116
    ...
    synth        rule-based   -0.475

The split is perfect and it is by family. Every neural model clears the
masked-node label floor; **no rule-based model does**, including the ones whose
mechanisms are demonstrably sound — `analogy` and `routes` are exactly
equivariant under renaming, `ilp` induces first-order clauses that fire, and all
of them are now well calibrated.

That reframes the last three roadmap items. Per-episode fitting (+0.000),
anchor-relative features (-0.011) and the parser abstraction (~1% of a bit) were
all refinements applied to models sitting at or below their floor, where there
is no headroom for a refinement to show up in. The mechanisms may be fine; the
experiment could not have detected it.

The productive question is not "which refinement helps" but "what would put any
rule-based model above the floor at all". Candidates worth trying before more
refinement:

- The floor is a structure-only lookup table conditioned on `(parent type, slot,
  depth, has children)`. The rule-based models mostly *are* structure-only
  lookups of one kind or another, so they are competing with the floor on its
  own terms and the tie is unsurprising. Something that reads content — a route
  chosen by what the episode *says*, not only by where the node sits — is the
  obvious missing ingredient.
- `label_coverage` is 0.92: the 8% excluded are out-of-vocabulary invented
  names, which is exactly where a pointer method should win and where it is
  currently not scored at all. Scoring copy-style predictions against the
  excluded set would change what the metric rewards.

### Measured: the floor was unfair, and fixing it made it harder

`MaskedNode.floor` read the **true** parent type off the unmasked graph and
scored every node in it, while a model reads `mask` wherever the parent is
hidden and is scored only where the mask fell. The floor was being computed with
information the models were denied, and the docstring claimed the opposite:
"exactly what a model can read off the relations".

Fixed: the mask is drawn at the evaluation rate, a hidden parent contributes
`mask` as it does in a `GraphView`, and only masked nodes are scored — averaged
over several draws at both fit and score time, since one 15% sample is a few
hundred nodes and this is the number every lift is measured against.

The hypothesis was that this had been depressing every model's lift. It had
not. On identical data:

    old floor (whole graph, every node)     label_acc 0.327
    new floor (masked view, masked nodes)   label_acc 0.372

The corrected floor is **harder**, not easier. Masking removes context from the
lookup too, and scoring only the masked subset changes the mix in the lookup's
favour. So the family separation is not an artifact of an unfair floor: the gap
between the neural and rule-based models on label prediction is real, and it is
now measured against a floor that is actually comparable.

### Measured: the repo's core premise about vocabulary is false

Across all 179 lessons, 537 evaluation episodes, 29,501 scored labels:

    seen in training:  29,494  (100.0%)
    genuinely novel:        7  (0.0%)

The claim that "the curriculum invents its vocabulary per episode, so the answer
is often a name the model has never seen" is false. The generator varies *which*
symbol fills a slot; the pool it draws from is fixed and small — alice/bob/carol,
o0..o9, the colours, the shapes. It appeared in the README, in
`tasks/masked_node.py`, and in the docstrings of `analogy`, `routes` and
`ruleinduce`, where it justified design decisions. All corrected.

The second recorded lead is dead too. `label_coverage` 0.92 was described as
excluding "precisely the invented names where a pointer method should win". The
excluded labels are six whole bracket strings — `'(()())'`, `'((())(()'` — the
un-exploded contents of `str` nodes. Not invented names; an artifact of a `str`
node carrying its whole content as a label while also exploding into char
children.

> **This refutation was itself a six-lesson artefact, and is withdrawn.** It was
> measured where `label_coverage` is 0.92; on all 179 lessons coverage is 0.82
> and the excluded set is completely different. Of 522 excluded masked labels,
> **462 (88.5%) are `ident` nodes** with values like `gvnt`, `vkgm`, `vlzk` —
> invented identifiers, precisely what the original lead claimed. Only 26 are
> `str` nodes. The lead is alive; see the pointer-head item in the task list.
> Third time a conclusion drawn from the six-lesson slice has inverted on the
> full curriculum.

**What this implies for the priority item.** The floor memorises the most common
label per structural context, and on a fixed symbol pool memorisation is a
winning strategy. Several rule-based models here were deliberately built not to
memorise — `analogy` paid 0.463 -> 0.186 for renaming equivariance, `ruleinduce`
predicts pointers rather than symbols — on the strength of a premise that does
not hold. Equivariance is real and worth having; it is simply not what this task
rewards. A rule-based model that clears the floor most likely has to do both:
memorise the recurring pool where it pays, and use structure where it does not.

### Measured: coverage, not reasoning, was the binding constraint

Splitting each model's accuracy into "where it commits" and "how often it
commits" changes the picture completely:

    model        argmax  voted%  acc where it voted
    analogy       0.221     63%              0.352
    grammar       0.267     94%              0.273
    ngram         0.250    100%              0.238
    routes        0.215    100%              0.233
    ctw           0.198    100%              0.221
    floor         0.332    100%              0.332

`analogy`'s mechanism was already **above the floor** — 0.352 against 0.332 —
and its overall score was being dragged down by abstaining on 37% of nodes,
where it fell back to the unigram prior. Nothing was wrong with the reasoning;
the model simply declined to answer a third of the questions.

Filling that gap with the floor's own strategy — memorise the commonest label
per structural context, used only where route transfer finds nothing — gives
0.221 -> 0.337, lift -0.166 -> +0.008. First rule-based model over the line.

This is a deliberate reversal of an earlier decision. `analogy` was rebuilt to
avoid memorising, on the premise that the curriculum reinvents its vocabulary;
that premise is measured false, so the memorisation it was refusing is free
accuracy. Equivariance is a real property and `routes` still has it — but it is
not what this task rewards, and `analogy` has been removed from the
structure-only list rather than pretending it can have both.

### Measured: abstention, not reasoning, was costing most of the score

Accuracy where a model commits, against coverage, floor 0.332:

    model        argmax  cover  acc|voted
    synth         0.006     1%      1.000
    ilp           0.186    35%      0.525
    analogy       0.337   100%      0.337
    grammar       0.267    94%      0.273
    ruleinduce    0.076   100%      0.192
    syllogism     0.070    41%      0.186

Two mechanisms are far above the floor and were scoring far below it purely by
declining to answer. So the fallback `analogy` was given last tick moved into
`RuleBasedModel`: an abstention now lands on the commonest label for the node's
structural context rather than on the unigram prior.

    model        before   after    lift
    ilp           0.186   0.349  +0.025
    syllogism     0.070   0.314  -0.027
    synth         0.006   0.302  -0.044
    grammar       0.267   0.297  -0.053
    symbolalg     0.134   0.244  -0.131
    ruleinduce    0.076   0.076  -0.384

`ilp` is now the best rule-based model in the repo and above the floor. Nothing
else clears it, but everything that abstained improved sharply.

Two costs, both real. Only rule-based models have a back-off, so strengthening
it moves them relative to the networks — the justification is that the old one
was needlessly weak, not that the families should be levelled. And the fallback
memorises, so it breaks renaming equivariance for every model that takes it;
`routes` opts out via `structural_fallback = False` and remains the model that
demonstrates the property.

### Measured: ECE and NLL disagree, and NLL is the one to believe

The previous tick left `analogy` and `workspace` under-confident by ~0.05 with
ECE up from ~0.09 to ~0.22, and queued "recalibrate against the final mixture"
as the fix. Post-hoc temperature scaling is the standard way to do that and has
the property that matters here: dividing log-probabilities by a constant cannot
reorder them, so no prediction and no accuracy changes.

Fitted on held-out episodes by minimising negative log-likelihood, it chose
**T = 1.0** for `analogy`, `workspace` and `ilp` alike. Confirmed on the
evaluation set as well — NLL 3.370 at T=1.0, rising to 3.376 at 0.9 and 3.454 at
1.2. The distributions are already properly scaled.

So the two measures genuinely disagree. The models are well calibrated in the
proper-scoring sense and under-confident specifically on their argmax, which is
what ECE reads. Sharpening to bring ECE down would raise NLL — trading the score
the repo reports for a diagnostic — so it is not done.

The machinery stays in place at T=1 as a no-op, because a future change that
genuinely mis-scales the output should be caught rather than argued about, and
the test now asserts the temperature rather than an ECE bound.

### Measured: pruning helps one counting model and hurts the other

Growth with data, all 179 lessons:

    episodes    tokens     ngram       ctw   grammar
         358    60,486   117,318   180,495    17,340
        1074   179,657   232,032   374,421    29,535
        3222   538,254   471,803   771,750    62,644

About 0.9 stored entries per token for `ngram` and 1.4 for `ctw`, so a 40M-token
corpus wants tens of millions and several gigabytes of Python dict — which is
the failure the source work reports and nothing here bounded.

The remedy is the standard count cutoff, and its effect splits:

    ngram  uncapped  232,032 entries  4.029 bits/token
    ngram  capped    170,318 entries  3.857 bits/token   <- better *and* smaller
    ctw    min_count=1  374,421       6.532
    ctw    min_count=2  256,547       6.951               <- 31% smaller, 0.4 worse

Pruning `ngram` improves it: a context seen once makes a confident claim on no
evidence, and dropping it lets the model back off to something better supported.
Pruning `ctw` costs real accuracy, because its deep nodes are not a noisy tail —
mixing over them *is* the algorithm. So the defaults differ: cutoff on by
default for `ngram`, off for `ctw` with the knob documented.

`grammar` needs neither at this scale (0.12 entries per token; the induced
classes are what compress it) but takes the same cap for safety.

CTW's pruning had to rebuild `log_w` and `child_logsum` bottom-up afterwards.
Those are maintained incrementally, so deleting a child leaves its parent
claiming mass from a subtree that no longer exists and the weighted values
quietly stop being probabilities — checked, and they still sum to 1.

### Measured: my "above the floor" claims were an artifact of training size

The last several commits reported `workspace` at +0.060, `ilp` at +0.051 and
`analogy` at +0.025 lift — three rule-based models above the label floor. Those
were measured at 50 training episodes per lesson with an ad-hoc harness. Run
through the committed sweep at 200, none of them clears it:

    workspace   n_train=50    acc 0.316   floor 0.298   lift +0.027
    workspace   n_train=200   acc 0.291   floor 0.312   lift -0.031

Both halves move the wrong way. The floor improves with data, as a lookup table
should. The model *degrades* — 0.316 to 0.291 on four times the evidence — which
is not a property of anything working correctly.

So the family separation stands: all six neural models above the label floor,
all twelve rule-based below, after a long run of work aimed squarely at closing
it. And the lesson about method is sharper than the lesson about models: an
ad-hoc measurement at a convenient scale agreed with what I wanted and was
reported as a result for several commits before the authoritative path
contradicted it.

### Measured: no degradation with data, and a real bug that did not matter

The premise — `workspace` 0.316 at n_train=50 falling to 0.291 at 200 while the
floor rose — came from a 12-episode evaluation set. At 240 episodes:

    n_train   floor  workspace  analogy    ilp   ngram
         25   0.308      0.308    0.321  0.333   0.238
         50   0.321      0.329    0.340  0.336   0.267
        100   0.311      0.289    0.326  0.298   0.247
        200   0.316      0.326    0.338  0.332   0.259

Every column is flat. The floor does not improve with data and the models do not
degrade; the original two points were both inside the noise of a measurement
twenty times too small.

The investigation did find a real defect. `workspace` and `analogy` enforced
their example caps by *stopping* once the cap was reached, while `ruleinduce`
and `ilp` subsample with a stride. Episodes arrive grouped by lesson, so
truncation cut the later lessons out of the policy and the case base entirely,
and cut more of them the more data there was. Both now subsample.

It changed nothing at sweep scale: `workspace` 0.291 before and after,
`analogy` 0.286 -> 0.281. Worth fixing because order-dependence is a defect
whatever it scores, and worth recording that fixing it bought nothing.

### Partial: the six-lesson slice may have been unrepresentative

Every headline number in this repo was measured on six lessons chosen early and
never revisited, out of 179 available. The full sweep is running. Two models are
out of it so far, and both reverse:

    model      lessons  lbl acc  lbl lift  lbl cov
    analogy          6    0.281    -0.045     0.92
    analogy        179    0.334    +0.256     0.82
    brill            6    0.267    -0.065     0.92
    brill          179    0.244    +0.155     0.82

Both clear the label floor comfortably on the full curriculum and both sat below
it on the slice. If that holds across the remaining eleven, then "no rule-based
model clears the label floor" — reported here many times and written into the
README — is an artifact of lesson selection rather than a fact about the models.

Two of thirteen is not a result and this is recorded as a partial reading, not a
conclusion. But it is enough to stop quoting the six-lesson numbers.

Note `lbl cov` falls 0.92 -> 0.82: the wider curriculum has more
out-of-vocabulary labels, so the label score covers less of it. That is worth
holding in mind when the full table arrives — the two runs are not scoring quite
the same population of nodes.

### Fixed: models fitted on graphs four times bigger than they were scored on

`ModelConfig` had no node cap, so every model passed `cfg.max_len` — the *text*
length — as `max_nodes` when drawing training views. With the default
`max_len=512` that meant fitting on graphs truncated at 520 nodes and being
evaluated on graphs truncated at 128. Different data on the two sides, and four
times the work for the part that was then discarded. `ModelConfig.max_nodes`
now exists and the trainer passes the task's cap through; ten files were reading
the wrong field.

This was found while chasing what looked like a hang in `ctw`, and it was not
the cause. `ctw`'s forward really is about fifty times slower than `brill`'s —
53s to evaluate 716 episodes against 2s — which is a property of walking a
context path per candidate symbol, not a bug. Two full-curriculum sweeps were
killed on the mistaken belief it had stalled.

### Measured: the six-lesson slice inverted the result

All 179 lessons, masked-node task, 11 of 13 models complete:

    model        lbl lift (179)   lbl lift (6 lessons)
    analogy             +0.256                 -0.045
    ruleinduce          +0.250                 -0.206
    routes              +0.244                 -0.197
    ilp                 +0.231                 -0.093
    brill               +0.155                 -0.065
    ngram               +0.072                 -0.091
    ctw                 +0.004                 -0.040

Every model clears the floor on the full curriculum; not one did on the slice.
And the ordering is close to inverted — `ruleinduce` was last and is now second.

The lesson is about method rather than about models. Six lessons were chosen at
the start for speed, every subsequent conclusion was drawn from them, and the
sample was small enough to reverse both the level and the ranking. Several ticks
of work went into "why does no rule-based model clear the floor", which was a
question about the sample.

`lbl cov` is 0.82 here against 0.92 on the slice, so the two runs do not score
quite the same population of nodes; the effect is far too large to be explained
by that, but it is not a like-for-like comparison.

## Open questions

### Blocked: the neural comparison needs a GPU, and long CPU runs keep dying

The one remaining claim — whether the neural models clear the label floor on the
full curriculum — cannot be settled right now, and the reasons are worth
recording so the next attempt is planned rather than rediscovered.

**Cost, measured rather than guessed.** `gru` ran 300 steps in 455s on CPU:
**0.7 steps/s**. A budget large enough to matter is ~2000 steps, so ~51 minutes
per model and about five hours for the six. The GPU is occupied by other work
and must not be taken for this.

**Why 300 steps is not a usable data point.** 300 steps at batch 16 against
3,580 training episodes is ~1.3 passes, while every rule-based model sees the
training set in full. `gru`'s -0.050 lift is an undertrained model, not a beaten
one, and reporting it as the family separation inverting would be wrong.

**Operational problem.** Long background runs launched from a tick do not
survive it. Four attempts now — two full sweeps and a 1200-step `gru` — have
been killed part-way, twice leaving output directories with a tokenizer and no
summary. `sweep --resume` was added for exactly this and works; `train` has no
equivalent, so a single long run still loses everything.

**What would unblock it**, in preference order:

1. A free GPU: six models at 2000 steps is minutes, not hours.
2. ~~`train --resume`~~ — **done.** Training now checkpoints on the evaluation
   cadence and `--resume` continues from it, optimiser state included, so a
   five-hour CPU run can be assembled from tick-sized pieces. `sweep --resume`
   now resumes each model's partial training as well as skipping finished ones.
3. Failing both, state plainly in the README that the family comparison is
   untested on the full curriculum. That is already what it says.


- The design docs report counting losing to gradients by ~3.5x perplexity on
  real text, which is the opposite of what this repo's smoke sweep shows. The
  sweep is 400 steps on synthetic curriculum prose, so the disagreement is
  probably budget and domain rather than a contradiction — but no narrative
  should rest on the current LM column until a real budget has been run.
- The docs argue prediction is a special case of interaction and that their
  strongest results (state-space extrapolation, re-aiming induced parameters at
  new goals) need an environment to intervene in. This harness is teacher-forced
  scoring with no trajectories and no reward, so it cannot reproduce those. That
  is a scope boundary worth stating rather than quietly working around.

## Rules for autonomous work

-1. **`pgrep -f` matches the shell command running it.** Checking for a process
    with a pattern that appears in your own command line reports it as running
    forever. Match the interpreter path instead. This cost most of a tick and
    produced two confident, wrong readings about what was executing.

-0.5. **`nohup ... &` inside a tick does not outlive the tick.** The process
    group is cleaned up when the invoking call returns, so the detached job dies
    minutes later wherever it happens to be. A 2000-step `gru` launched this way
    reached step 51 and vanished without writing its first checkpoint; the log
    simply stops mid-run, which reads exactly like a hang and invites restarting
    it from scratch. Long jobs must be launched *as* the backgrounded command
    the harness tracks, not as a detached child of one. The runs that did
    survive several ticks were all launched the second way. This has now cost
    five attempts at the same experiment.

-0.4. **Check for a second copy before concluding a run is slow.** Two sweeps
    were once training into `runs/full179` at the same time, interleaving writes
    to the same `checkpoint.pt` and `summary.json` for the same model. The
    visible symptom was only that the first checkpoint took much longer than the
    arithmetic said it should, which is indistinguishable from an underpowered
    CPU. Read `ps -eo pid,ppid,...` and count the *process trees*, not the
    matching lines: `uv run` sits between the shell and the interpreter, so one
    launch always shows at least two rows and two rows prove nothing.

-0.3. **A subagent given "make a branch" shares your working tree.** Told to
    develop a new model family on a branch, one created it *in this checkout*,
    which moved my own HEAD onto it mid-tick. The next commit I made -- the
    config-drift detector, main-line work -- landed on the research fork and
    `master` was left two commits behind, with nothing to indicate it. Nothing
    was lost, but only because it was noticed within one tick.

    Give a parallel agent its own worktree (`isolation: "worktree"`), or accept
    that it owns the checkout and do your own work somewhere else. A shared tree
    also means the test suite imports the agent's half-written modules, so
    "tests pass" stops being a statement about your change. Recovering is a
    pointer move (`git branch -f master <sha>`), and the fork keeps its history.

0. **The sweep is the authority.** Ad-hoc measurement scripts have now
   contradicted `symbolic-ai-models sweep` twice, both times in the direction
   that flattered the result being written up. Quote sweep numbers; use scratch
   scripts to form hypotheses, never to report.

1. Never commit with tests failing. `uv run pytest tests/ -q`.
2. One coherent change per commit, with a message saying what was learned.
3. Report negative results. A parser that does not help is a finding.
4. Do not tune against the evaluation set; seeds >= 1_000_000 are eval only.
