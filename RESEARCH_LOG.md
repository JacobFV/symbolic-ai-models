# Research log

Where this repo actually is, for someone arriving cold. `README.md` documents
the harness and the models; `ROADMAP.md` holds the task list and the working
rules; this file says what is *known*, what is *shaky*, and what is *wrong that
used to be believed*.

**Model names carry a version.** Every model is registered as `name-001`, and a
bare `name` resolves to the highest version, so `--models corefer` still works
and means "the current one" while `corefer-001` pins a specific thing. A number
in this file is attached to a versioned name because it has to be: `corefer`'s
type head went 0.174 -> 0.612 in one commit and `workspace` moved from eighth to
joint first when a cap was raised, and both silently redefined what an earlier
row meant. A variant is now `corefer-002` or `corefer-noprose`, a separate row in
the same sweep.

Numbers here are from `runs/full179`: all 179 generatable lessons, 20 training
episodes each, evaluation seeds a million away, CPU. The sweep is the authority;
nothing in this file was measured by a scratch script.

## The question

Two tasks on the same harness. Next-token prediction, and **masked-node
prediction** — hide nodes in the typed term graph an episode was rendered from,
predict each one's *label* (which symbol) and *type* (what kind of node). The
graph is not a parse of the text; it is the thing the text was generated from,
so the answers are exact and unannotated.

Nineteen models, two families. Rule-based ones are the subject; six neural ones
exist as a control and are off by default.

## What is established

**Every ranking this repo has published is an accuracy ranking, and the models
rank close to inversely by bits.** `label_bits` has been in every
`summary.json` from the beginning and was never given a lift, so it was never
compared. On the full curriculum:

| model | lbl acc | rank | lbl bits | rank |
|---|---:|---:|---:|---:|
| `grammar` | 0.187 | 14 | **6.09** | **1** |
| `evidence` | 0.219 | 12 | 6.26 | 3 |
| `ngram` | 0.170 | 17 | 6.41 | 4 |
| `corefer` | **0.357** | **1** | 6.95 | 6 |
| `omegaclaw_rank` | 0.356 | 2 | 8.09 | 11 |
| `brill` | 0.244 | 10 | 9.08 | 19 |

The cause is the shared mixture, `(1-c)*backoff + c*votes`. A model that knows
the answer is one of ten and no more has argmax accuracy 0.1, and `c` was fitted
as an argmax accuracy, so it kept 0.1 of the mass and gave 0.9 back to a unigram.
Deciding well and estimating well were made to pull against each other by the
interface, not by the reasoning. **A ranking is a property of a metric and never
of a set of models**; both columns are now printed by `compare`.

**Fitting the mixture weight as a mixture weight is worth +0.017 lift and 0.58
bits.** `ptrgen-001` and `ptrgen-argmax` are the same pointer, the same
features, the same decision procedure, differing in one method: whether the gate
is fitted by maximising held-out likelihood or by measuring argmax accuracy.

| | lbl acc | lbl lift | bits |
|---|---:|---:|---:|
| `ptrgen-001` (likelihood) | 0.336 | +0.225 | **5.91** |
| `ptrgen-argmax` (accuracy) | 0.321 | +0.208 | 6.49 |

The accuracy gain was not predicted and has a mechanism: raising `c` cannot
reorder the votes, but it does move the boundary between a voted symbol and the
structural prior, and the votes win that comparison more often than they lost it.

**An ensemble pays in bits only when the members are actually diverse, and the
control proves it.** `ensemble-001` is `ptrgen` x `grammar`, chosen on the
renaming column — one loses 0.003 accuracy when every symbol is permuted, the
other 0.159. `ensemble-pointers` is `ptrgen` x `corefer`, two pointers over the
same features, registered as the control.

| | lbl acc | bits | bits vs best member |
|---|---:|---:|---:|
| `ptrgen-001` alone | 0.336 | 5.91 | — |
| `ensemble-001` (diverse) | 0.336 | **4.77** | **-1.14** |
| `ensemble-pointers` (correlated) | 0.340 | 5.91 | -0.00 |

4.77 bits is the best in the repo by a wide margin, and the correlated pair
gains *exactly nothing*. The fitted weight is 0.55 — an interior optimum, so
neither member is carrying it. `ROADMAP` rejected ensembling on a measured
ceiling for the **copy head** and that rejection stands; this is the label head,
and every ensemble previously considered was pointer-with-pointer, which the
control now shows is the case that does not work.

**And the entire 1.14-bit gain is vocabulary memorisation.** Run the renaming
test on it — permute all 340 symbols, do not refit — and it is the least
equivariant model ever measured here:

| model | plain | renamed | drop |
|---|---:|---:|---:|
| `ptrgen-001` | 0.390 | 0.392 | **-0.002** |
| `ensemble-pointers` | 0.392 | 0.396 | **-0.004** |
| `omegaclaw_em-001` | 0.450 | 0.423 | +0.027 |
| `grammar-001` | 0.290 | 0.008 | +0.282 |
| `ensemble-001` | 0.467 | **0.038** | **+0.429** |

So the finding stands and its sign is the opposite of what it looked like.
Diversity *is* what an ensemble buys, and the diversity available here is
"one member reads structure and the other memorises the corpus" — which is why
the correlated control gains nothing and why the gain does not survive a
renaming. `ensemble-001` is the best density estimator in the repo and it is not
a symbolic model; `ensemble-pointers` keeps the equivariance and buys nothing.

The honest summary is that **on this task, bits and equivariance are in
tension**, not that an ensemble helps. Which makes the next line the important
one:

**A symbolic model can still win on bits — `ptrgen` already does.** At 5.91 it
beats `grammar`'s 6.09, the previous best, while dropping 0.002 under renaming
against `grammar`'s 0.282. The 1.14 bits on top of that are memorisation and the
0.18 below it are not. Those are different quantities and only the second is
what this repo is trying to measure.

**The label task is a binding problem being scored as classification.** 71.9% of
scored answers already sit on a *visible* node of the same episode, so the real
question is "which node do I corefer with", not "which of 8,192 symbols is this".
The best model reaches 0.357 accuracy against a **0.722 copy ceiling**. More than
half the reachable signal is untouched by every model here.

**Node type is very nearly determined by tree shape.** A content-blind
backed-off lookup reaches 0.860. That is the floor now, and on it only two of
nineteen models are positive: `corefer` (+0.612) and `rgt` (+0.395, a network).
Every other model that looked good at type was reproducing a lookup table.

**Capacity spent on symbol identity is wasted.** `ilp` reaches +0.198 label lift
with 74 counts; `ctw` reaches -0.040 with 819,990. The task re-randomises which
symbol fills which slot every episode, so parameters attached to symbol identity
have to be unlearned at test time.

**Renaming separates models the score cannot.** Permute all 2,105 symbols,
without refitting. Every rule-based model, sorted by what it loses:

| equivariant (≤0.03) | mostly structural | vocabulary-dependent |
|---|---|---|
| `routes` -0.000 | `syllogism` -0.024 | `symbolalg` -0.041 |
| `corefer` -0.003 | `ruleinduce` -0.027 | `ctw` -0.088 |
| `evidence` -0.003 | `omegaclaw_flat` -0.030 | `brill` **-0.130** |
| `omegaclaw_rank` -0.017 | | `workspace` **-0.130** |
| `omegaclaw_ctx` -0.018 | | `ngram` **-0.143** |
| `analogy` -0.019 | | `grammar` **-0.159** |
| `ilp` -0.021 | | |

Thirteen of sixteen lose under 0.05 — the symbolic models really are mostly
reading structure, which is the thesis of the repo and had never been measured
across the board. The exceptions are informative: `grammar` and `ngram` are
vocabulary methods by construction and behave that way, while `brill` and
`workspace` were not expected to and do.

`corefer` and `workspace` tie at 0.357 label accuracy and sit at -0.003 and
-0.130. The score cannot tell them apart; this can.

## Nulls and near-nulls worth not repeating

All four were built expecting a win, all four were pre-registered with what
would refute them, and all four came back small. Same sweep, same floors,
`runs/ptrgen`.

**Joint decoding helps the model that gains candidates, not the model that
gains reach — the opposite of the prediction.** Masked nodes are hidden 15% at a
time, so a claw reaching for a coreferent node lands on `None` whenever the
harness hid the evidence and the question together. Filling the surest nodes
first and re-reading the graph fixes that, and was predicted to help
`omegaclaw_ctx` most because its claws name specific structural positions.

| | lbl lift | bits | typ lift |
|---|---:|---:|---:|
| `omegaclaw_ctx-001` | +0.234 | 7.87 | -0.071 |
| `omegaclaw_joint-001` | +0.233 | 7.89 | -0.091 |
| `ptrgen-001` | +0.225 | 5.91 | +0.565 |
| `ptrgen_joint-001` | +0.230 | 5.87 | **+0.681** |

`omegaclaw` does not move at all; `ptrgen` gains a little on labels and a lot on
type. The interpretation was fixed in advance — *if only one moves, the effect
is about reach rather than about decoding* — and it applies: a committed node is
one more candidate for a model that scores every visible node, and mostly
nothing for a claw that wanted one particular position. **Sequential decoding is
not what helped.** The teacher-forcing boundary is worth less on the prediction
side than the scope note implied.

**Widening the claw set with a route the search discovered makes accuracy
slightly worse.** `ilp` is the one model here whose hypothesis space is not a
list somebody wrote down, and it does use that freedom: 38% of its clause
firings land where no claw reaches, and it is right there 82% of the time. Its
strongest clause is a *typed, slot-selected sibling*, which `CLAWS` cannot
express — it has `sibling0` and `prev_sibling` and no way to say which sibling.
Added as `omegaclaw_reach-001`, `sibling_pred` fires at **0.803** reliability
against 0.232 for `mirror` and 0.163 for `peer`, the two the base class calls
the strongest operator every model here agrees on.

It still loses: +0.226 against `omegaclaw_ctx`'s +0.234, with bits slightly
better (7.72 against 7.87). The number that predicted this was already in the
diagnostic — `ilp` is uniquely right on only **2.2%** of nodes, because the claw
set reaches the same answer by another route nearly everywhere. **Reach was
never the constraint**, and the family's "control beats reach" claim comes out
of this stronger than it went in: the best single operator anyone has found here
does not pay for itself once eleven worse ones are already voting.

**EM credit assignment is worth +0.006 lift, and re-ranks the claws sharply.**
`omegaclaw_em-001` splits one unit of credit among the claws that were right
instead of giving each a whole hit — `peer` and `mirror` are two routes to the
same coreferent node and agree constantly, so counting records several
independent solutions to one problem. It reads +0.240 against `omegaclaw_ctx`'s
+0.234, second-best in the sweep: a real but small gain in score.

The *diagnostic* value is larger than the score change. Which claws keep their
reputation once the double count is removed, on all 179 lessons:

| claw | counted | EM | kept |
|---|---:|---:|---:|
| `prev_sibling` | 0.361 | **0.196** | 54% |
| `mirror` | 0.177 | 0.109 | 62% |
| `sibling0` | 0.255 | 0.107 | 42% |
| `slotmate` | 0.181 | 0.064 | 35% |
| `echo` | 0.200 | 0.043 | 21% |
| `prev` | **0.243** | 0.042 | 17% |
| `peer` | 0.100 | 0.026 | 26% |

The prediction written down before running it was that the vague aggregates —
`echo`, `slotmate`, `prev` — would lose most and the sharp structural claws
would keep theirs. That is what happened. `prev` falls from first to sixth: "the
nearest labelled node before this one" is right largely in the company of a claw
that had a reason, and hard counting cannot see it. `prev_sibling` and `mirror`
are what survive.

**A three-lesson slice said something else and it was wrong.** On that slice
`peer` collapsed from 0.141 to 0.005, which read as a clean discovery that
`peer` is subsumed by `mirror`. On 179 lessons `peer` keeps 26%, loses less than
`prev` or `echo`, and is not singled out. Fourth time a small slice has produced
a confident wrong answer here.

## The text surface, and a harness bug that made it unmeasurable

**Eleven of nineteen models cannot emit a single token of text.** `ptrgen`,
`corefer`, the whole `omegaclaw` family and both ensembles implement
`node_votes` and not `text_votes`, so they abstain to the unigram back-off and
all score identically: **8.51 bits/token, `answer_acc` 0.000**. The leaderboard
this repo optimises is masked-node only, and masked-node accuracy is disjoint
from generation. Of the models that *can* generate, only the counting ones are
any good — `ngram` 2.35 bits, `grammar` 2.43, `ctw` 4.30, against
`ruleinduce` 7.69 and `syllogism` 7.71, barely distinguishable from saying
nothing.

**The tokenizer was deleting underscores.** `_PIECE_RE` was an alternation of
four cases and `re.findall` drops whatever matches none of them; `_` matched
none. `'foo_bar_baz'` round-tripped to `'foobarbaz'`. On a twelve-lesson slice,
**9 of 85 answer strings and 17 of 60 episode texts did not survive a round
trip** — and a string the tokenizer cannot represent cannot be emitted by any
model, so those lessons' `exact_match` was pinned at zero for reasons unrelated
to any model. Both patterns are now total; after the fix, 0/85 and 0/60.

`test_encoding_is_lossless` existed, passed, and missed it: its fixture drew
episodes containing no underscore. **That is the six-lesson-slice error in a
different costume** — sampling the world rather than covering it — and it is now
the fifth time that shape of mistake has produced a confident wrong reading
here. The replacement tests assert on the alphabet, not on a fixture.

**Refuted: the degenerate generation is not a decoding-rule artefact.**
`symbolic-ai-old-A` found a 0.00 → 0.40 swing on a gridworld from sampling
instead of arg-max, with no parameter change, and this repo's
`'Reply with exactly one of: o1'` output has the same signature. It does not
replicate:

| | greedy | T=1.0 | T=0.7 top-50 |
|---|---:|---:|---:|
| `ngram` in-answer-set | 0.000 | 0.050 | 0.050 |
| `ctw` | 0.000 | 0.017 | 0.000 |
| `grammar` | 0.000 | 0.050 | 0.033 |

`exact_match` stays 0.000 everywhere. Sampling from a broad distribution is
worse to read than its mode, not better. The useful part was the greedy output
itself — gold `'opt_c'`, generated `'optd'`, the right shape with the underscore
missing — which is what led to the bug above.

## The transfer question, measured

Curriculum against real English prose, same protocol, `symbolic_ai_models/asymptotics.py`.
Every curve carries two nulls: a within-sequence shuffle (destroys order, keeps
the sequence's own subject matter) and a global resample (destroys both, leaving
the plug-in estimator's floor). `order = raw - within`, `latent = within - global`.

```
CURRICULUM  1,074 episodes, 183k tokens        REAL ENGLISH  572 chunks, 97k tokens
   d    I(d)  within  global   order  latent      d    I(d)  within  global   order  latent
   1   4.136   1.676   1.357   2.461   0.319      1   4.122   2.461   2.315   1.661   0.146
   8   3.003   1.692   1.382   1.311   0.310      8   2.642   2.497   2.346   0.145   0.151
  32   2.402   1.746   1.456   0.656   0.291     32   2.628   2.603   2.455   0.025   0.148
 128   2.418   1.876   1.926   0.542  -0.050    128   3.365   3.414   3.275  -0.048   0.139

effective rank 333.7 / 2,323 contexts (14%)    effective rank 773.1 / 1,809 contexts (43%)
top-50 singular values 37.7%                    top-50 singular values 26.0%
```

**Correction to a number published in this log's first draft.** "`I(d)` plateaus
at ~2.35 bits at d=128, a constant-latent signature" was measured from the raw
plug-in curve with no control. Most of that 2.35 is estimator bias: the global
null alone reads 1.36–1.93 over the same range. The real latent term is **0.31
bits**, not 2.35 — a seventh of what was claimed. The plateau is real; its
magnitude was almost entirely an artefact of an uncontrolled estimator.

**The finding that matters for the programme.** The two corpora differ most in
*order* structure, and in the direction that is bad for transfer:

| | curriculum | real English |
|---|---:|---:|
| order structure at d=8 | 1.31 bits | 0.15 |
| order structure at d=32 | 0.66 | 0.03 |
| order structure at d=128 | **0.54** | **-0.05** |

Real prose's positional dependence is **gone by d≈16**. The curriculum's is
still worth half a bit at d=128, because a lesson renders one rigid template —
fact, then pattern, then query over the same symbols — so the token 128 places
back is genuinely informative about this one. **That is a property of the
generator, not of language**, and any method that earns its score by exploiting
long-range positional regularity will look far better here than on prose.

**The low-effective-rank claim holds, and by a wide margin.** 14% of contexts
against 43% for prose, with the spectrum more concentrated (37.7% vs 26.0% in
the top 50). A minimal sufficient statistic for prediction really is small on
this curriculum, which is what makes an exact symbolic machine affordable — the
premise of agenda item (A) survives.

**Caveats, stated because the proxy is weak.** The "real English" corpus is 97k
tokens of this repository's own technical prose, not a language corpus: small,
one register, one author. Values below about 0.05 bits are inside the
estimator's resolution here. What it can support is the *contrast* in order
structure, which is an order of magnitude and survives any reasonable correction;
what it cannot support is a claim about natural language in general.

## Vector-symbolic models: good at bits, weak at deciding, exactly equivariant

`runs/vsa`, all 179 lessons, same config and floors as every other row. An
episode is encoded as `trace = sum_j role(j) * filler(j)` over bipolar
hypervectors and a masked node is answered by unbinding at its role and cleaning
up against the candidates. No learned layers — elementwise multiply, add and
sign over one 4096-vector.

| model | lbl acc | lbl lift | bits | bits lift | typ lift | copy lift | rename | secs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `vsa-002` | 0.219 | +0.089 | 6.80 | +0.275 | -0.486 | -0.115 | 0.029 | 37 |
| `vsa_seeded-002` | 0.212 | +0.081 | 6.76 | +0.278 | -0.486 | -0.122 | 0.035 | 37 |
| `vsa_pure-002` | 0.200 | +0.066 | 6.94 | +0.259 | -0.486 | -0.115 | **0.002** | 38 |
| `corefer-001` | **0.357** | +0.250 | 6.95 | +0.258 | +0.612 | +0.096 | 0.003 | 208 |
| `ptrgen_joint-001` | 0.340 | +0.230 | **5.87** | **+0.374** | +0.681 | +0.078 | 0.004 | 156 |

- **Weak at deciding, respectable at estimating.** +0.089 label lift puts it near
  the bottom; +0.275 bits lift puts it fourth of everything measured, ahead of
  `corefer` and every `omegaclaw`. That is the graded-by-construction claim
  doing what it said: cleanup returns a similarity to every candidate, so the
  output is a distribution rather than a winner with a confidence attached.
- **Exactly equivariant, at full scale.** `vsa_pure-002` drops **0.002** under a
  permutation of every symbol. The proof holds: the winning cleanup score
  reduces to `sum(role_i * role_j)` because `cb[s]**2 == 1`, so it cannot depend
  on which symbol won. No other model here is equivariant *by construction*
  rather than by measurement.
- **The seed is a null.** `vsa_seeded-002` is -0.007 accuracy, +0.003 bits lift,
  and +0.006 renaming drop against the random codebook. Consistent with the
  codebook test: sign-quantising a random projection of sparse co-occurrence
  only doubles the average off-diagonal similarity, so the seed is weak by
  construction. A real pretrained table drops into the same interface and is the
  experiment this null is asking for, not a refutation of seeding.
- **The copy head is below its floor** (-0.115). Reading the cleanup as a
  pointer is worse than copying from a fixed relative offset. Reported rather
  than dropped; it is the sharpest thing wrong with the model.
- **Cheap.** 37s against `corefer`'s 208s, at 8,254 parameters (one hypervector
  per symbol plus 62 role atoms).

**Correction, and it is the sixth of its kind here.** On a three-lesson slice,
turning off the shared `structural_fallback` took `vsa-002` from 0.305 to 0.102
— two thirds of its accuracy — and that was written into a commit message and a
docstring before the sweep ran. On 179 lessons it is 0.219 to 0.200: **9%, not
67%.** The slice overstated it sevenfold.

What survives the correction is still worth having: the fallback is a memorising
component every rule-based model inherits, and it is where this model's renaming
sensitivity lives (+0.029 with it, +0.002 without). Separating mechanism from
shared floor is a harness change worth making for the whole table — but the
claim that it dominates any model's score is not supported.

## What is shaky

- **Every neural number is a lower bound.** All four re-run networks were still
  gaining more than +0.01 per 500 steps when the 2000-step budget ran out; `rgt`
  was accelerating. The family comparison is unsettled and says so.
- **`workspace`'s joint-first label placement is mostly vocabulary.** Uncapping
  its training examples raised original accuracy 0.273 -> 0.352 and renamed
  accuracy only 0.214 -> 0.221. About 91% of that gain does not survive a
  renaming.
- **`corefer` is mine and it leads its own table.** It was built while the
  metrics it leads on were being built. Nothing in it reads eval, and the
  candidate-selection choices were made on a held-out slice of *training*
  episodes, but a reader should weight it accordingly.
- **The marginal-likelihood pointer did not beat naive Bayes at pointing.**
  `ptrgen` and `corefer` share stage-one features exactly, and `ptrgen` trains
  on the marginal likelihood of any correct antecedent where `corefer` asks a
  yes/no question of each pair. Copy lift: **+0.078 against +0.096**, label
  accuracy 0.336 against 0.357. The objective is better posed — several nodes
  usually carry the right label and nothing says which was meant — and it does
  not win on argmax. What it wins on is bits, by a full 1.04, and that is the
  gate and the summed label distribution rather than the pointer.
  `corefer` also has a second-stage reranker and `ptrgen` has none, which is the
  obvious confound and the obvious next experiment; until it is run, no claim
  should be made that the training objective is what separates them.

## What was believed and is false

Each of these was in the README as a result:

| claim | what it actually was |
|---|---|
| "The curriculum invents vocabulary per episode" | 100% of scored labels recur in training |
| "No rule-based model clears the floor" | an artefact of a six-lesson slice; on 179 nearly all do |
| "All neural models beat the label floor, no symbolic one does" | both halves wrong |
| "gru is beaten at -0.050" | it was undertrained at 1.3 passes; +0.079 at 8.9 |
| "rgt is first of nineteen on type at +0.587" | measured against a floor 0.065 too low; +0.395, and below a counting baseline |
| "Every rule-based model clears the label floor" | `ctw` and `synth` do not |
| "Every rule-based model sees the training set in full" | `ilp` saw 1.1% of available examples |

The pattern is worth naming: **six-lesson slices and weak floors both produce
confident results with the wrong sign.** Three separate conclusions inverted when
moved from six lessons to 179.

## How to add a variant

Register it beside its predecessor rather than editing in place:

```python
@register("corefer-002", doc="...")      # leave corefer-001 registered
```

Then `sweep --models corefer-001,corefer-002` prints both rows against the same
floors, and the difference is a measurement rather than a claim in a commit
message. Name the suffix for what changed when that reads better —
`corefer-noprose` says more than `corefer-003`.

This exists because the alternative was tried and cost real results. `corefer`'s
type head went 0.174 -> 0.612 in one commit and `workspace` moved from eighth to
joint first when a cap was raised; both were improvements, and both silently
redefined what an earlier published row had meant.

## Open questions

- Can anything reach the 0.722 copy ceiling? Four candidate-level features in a
  row have failed, and a discriminative re-ranker was worse than counting.
  `ptrgen`'s marginal-likelihood pointer is the fifth thing to not help, at
  +0.078 copy lift against `corefer`'s +0.096.
- **Put a reranker on `ptrgen`.** The cleanest open experiment in the sweep.
  `corefer` beats it on copy by +0.018 and has a second stage it does not; every
  other part of stage one is shared. Until that is run, "naive Bayes points
  better than marginal likelihood" is confounded with "two stages beat one".
- **Which metric should the repo lead with?** `ensemble-001` is first by bits
  and ninth by accuracy; `corefer` is the reverse. The two columns are now both
  printed and nothing decides between them. They are not interchangeable
  summaries of one quality — bits is a proper scoring rule and accuracy is what
  the curriculum's own multiple-choice question asks — so the answer is probably
  "both, always, and never one alone", which is what `compare` now does.
- Is the accuracy/bits frontier a property of the mixture or of the models? The
  interface forces a scalar `c` over a shared support. A model emitting a full
  distribution would not face the trade-off, and none exists here to check with.
- A probit link for `ScoreCalibrator`, as a data-efficiency variant rather than
  a multiple-truths one. See design rule 4 in `ROADMAP.md`.
- Does a parser beat a regex? `corefer` reads prose by counting regex matches,
  and the parser layer — built, tested, scored — has never been tried inside the
  one model where prose demonstrably helps.
- What budget would settle the neural comparison? Parked; it is a control.
