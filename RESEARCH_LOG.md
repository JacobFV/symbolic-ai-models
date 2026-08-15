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

## Parsing text back into the graph: `symbolic_ai_parsers`

A second, separate package, because the parser layer in `symbolic_ai_models`
answers a different question. There a `Parser` is `text -> ParseResult` — word
classes, brackets, facts — scored by pairwise class agreement. Here a parser is
`str -> Graph` and has to produce the term the text was rendered from: nodes,
types, labels, parents. The old layer is not deleted and its four reasoners keep
using it; it is **superseded for this objective, not wrapped**, because a
`ParseResult` cannot be turned into a `Graph` without inventing the structure it
declined to commit to. One bridge is registered as a control (`legacy-001`,
lifting the old `regex` parser's `facts`), and it loses — see the table.

Numbers below are from `runs/parsers_full179.json`: all 179 generatable lessons,
16 training episodes each, 8 eval episodes each at seeds a million away, macro
averaged over lessons, four rendering languages. `symbolic-ai-parsers sweep` is
the authority.

### A tree alignment cannot be used to score attachment

Written first, and it read as a strong result. Comparing a predicted graph to
the true one needs an alignment, and the natural one is the top-down /
isolated-subtree mapping: roots align, and the children of two aligned nodes are
aligned to each other. That mapping only ever adds a pair once the pair's
parents are paired — so **every aligned node has a correct head by
construction**, and the UAS computed over it is identically 1 wherever it is
defined. It reported 0.95 for a parser that copies a remembered graph and does
no parsing at all. What it measures is how many nodes were *alignable*.

`uas` and `las` now use a content alignment — the k-th node carrying a label is
the k-th gold node carrying it, which is the exact analogue of dependency
parsing comparing two analyses token index by token index. The tree alignment is
kept for `type_acc`, where identifying a node by where it sits is what makes
agreeing about its type a real question. Both degeneracies are pinned by tests.

A smaller one, caught by a test rather than by reading: counting occurrences is
a statement about node numbering, so scoring canonicalises both graphs
breadth-first before anything else.

### A floor for every metric, fitted per metric

`bracket_f1` is PARSEVAL over `(type, label, leaf yield)` and `label_f1` is the
multiset of labels with structure ignored; the full set of ten is below. Five of
them never call an aligner, deliberately, so a result resting on the alignment
has a witness that does not. Each gets its own text-blind constant floor, fitted
by search over training graphs held out against each other — per metric, because
the constant maximising `label_f1` is not the one maximising `bracket_f1`.

The floor search itself was checked rather than trusted: quadrupling it to 200
candidates against 120 targets moves the floor by at most 0.013, so the lifts
above it are not an artefact of a thin search. The larger setting is the
default.

English, 179 lessons:

| parser | uas | las | type_acc | bracket_f1 | label_f1 | exact |
|---|---:|---:|---:|---:|---:|---:|
| **floor** (text-blind constant) | 0.075 | 0.051 | **0.548** | 0.004 | 0.123 | 0.000 |
| `prior-001` (one constant graph) | 0.028 | 0.020 | 0.502 | 0.004 | 0.033 | 0.000 |
| `legacy-001` (the old layer's facts) | 0.065 | 0.041 | **0.410** | 0.067 | 0.382 | 0.000 |
| `bracket-001` (layout, written down) | 0.145 | 0.084 | 0.644 | 0.020 | 0.455 | 0.000 |
| `retrieve-001` (memorise, no parsing) | 0.568 | 0.511 | 0.943 | 0.228 | 0.758 | 0.008 |
| `template-001` | 0.576 | 0.515 | 0.958 | 0.234 | **0.832** | **0.016** |
| `template-002` | 0.545 | 0.487 | 0.935 | 0.214 | 0.798 | 0.008 |
| `template-seeded` | 0.575 | 0.512 | 0.939 | **0.241** | 0.839 | 0.015 |

Three things to read off it, none of them the ranking:

- **`type_acc` has a floor of 0.548 and `bracket_f1` has one of 0.004.** They
  are not comparable numbers and a parser quoted on one of them without the
  other is being quoted selectively. `legacy-001` sits *below* the type floor
  (lift **-0.307**) while clearing the bracket floor (+0.063); `bracket-001` is
  the reverse shape. This is the same pattern the model half of the repo has —
  seven rule-based models below the type floor while clearing the label floor.
- **Exact graph recovery is essentially unachieved.** The best row is 0.016.
  Whatever these parsers are doing, it is not parsing in the sense of getting
  the answer right.
- **Memorisation gets most of it.** `retrieve-001` does no parsing whatsoever —
  nearest training prompt by word overlap, emit its graph — and reaches 0.758
  label F1. `template-001`'s refill step is worth **+0.074 label F1 and +0.008
  exact** over that, and nothing at all on `bracket_f1` (0.234 vs 0.228). On a
  templated corpus, recall is most of the score, and any parser number here that
  is not read against `retrieve-001` is unreadable.

### Ten metrics, because six were already disagreeing

`exact`, `uas`, `las`, `type_acc`, `bracket_f1`, `label_f1`, and then four
graph-level ones: `edge_f1` (Smatch's triple set, exact here because a label
plus a type names a node, so no hill climbing is needed), `path_f1` (root-to-node
lineages), `wl_f1` (Weisfeiler-Lehman subtree kernel, two rounds — the only
score here that is about neighbourhoods rather than trees, and the only one that
would survive these graphs ceasing to be trees), and `ted_sim` (an upper bound
on tree edit distance, from the constrained mapping). Five of the ten never call
the aligner.

They were added because the first six already ranked parsers differently and one
number was hiding it. On the full curriculum, `cky-001` against `bracket-001`:

| | uas | type_acc | bracket_f1 | edge_f1 | label_f1 |
|---|---:|---:|---:|---:|---:|
| `bracket-001` | 0.145 | **0.644** | 0.020 | 0.080 | 0.455 |
| `cky-001` | **0.299** | 0.594 | **0.168** | **0.261** | **0.527** |
| floor | 0.075 | 0.548 | 0.004 | 0.039 | 0.123 |

An induced grammar is worth **eight times** the layout baseline's bracket F1 and
loses to it on node type. Both are true, they are not reconcilable into one
ordering, and this is the ordinary case rather than a curiosity — a table with
one column would have reported whichever was written first.

### Classical parsers: a treebank the corpus does not have

The three parsers that *compose* an answer rather than retrieving one, which was
the standing open question in this file. They need spans, and the generator
records none — it hands over the term and the string and nothing about which
characters a subterm produced. `symbolic_ai_parsers/treebank.py` recovers them
from two facts about the curriculum: arguments are copied into the prose
verbatim in every language, and a predicate renders as one punctuation-delimited
clause. Nodes are assigned to clauses greedily by argument overlap.

**79% of clause-shaped graph nodes find a clause** (22,844 of 28,899 at 16
episodes per lesson), which is the honest ceiling on everything built from it.
The scaffolding above the clause — record, field, list — is not recovered at all
and is assembled from block layout, so the classical parsers are grammars *of
clauses* with a hand-built document skeleton. That cap is in the code.

The induced grammar is 4,487 productions over two preterminals — `ARG` and the
literal word — with `P(ARG | token)` from training counts and the unseen-token
rate estimated on hapaxes rather than written down (it comes out at **0.716**:
a token never seen in training is usually a nonce symbol, and usually an
argument). Surface order and graph slot are stored separately, which is the one
piece of linguistics in the file and is what lets Turkish's verb-final rendering
be one extra production over the same head rather than a new predicate. A test
asserts exactly that.

Productions are flat, so the LR(0) item-set automaton of this grammar *is* the
trie of right-hand sides. All three parsers walk the same automaton:

| | size | uas | type_acc | bracket_f1 | edge_f1 | label_f1 | ted_sim |
|---|---:|---:|---:|---:|---:|---:|---:|
| floor | | 0.075 | 0.548 | 0.004 | 0.039 | 0.123 | 0.313 |
| `bracket-001` (written down) | 1.91 | 0.145 | **0.644** | 0.020 | 0.080 | 0.455 | 0.401 |
| `lr-001` (deterministic) | 2.34 | 0.175 | 0.547 | 0.062 | 0.129 | 0.369 | 0.326 |
| `cky-001` (exhaustive chart) | 1.52 | 0.299 | 0.594 | **0.168** | 0.261 | 0.527 | 0.472 |
| `shiftreduce-001` (perceptron) | 1.09 | **0.309** | 0.556 | 0.164 | **0.267** | **0.528** | **0.515** |
| `retrieve-001` (no parsing) | 1.00 | **0.568** | **0.943** | **0.228** | **0.697** | **0.758** | **0.768** |

Three things, and the third is the one that matters:

- **The chart earns its search.** `cky-001` is 2.7x `lr-001` on bracket F1 and
  2x on edges, on the same grammar and the same lexicon. The pre-registered
  alternative — that a deterministic maximal-munch pass would match the chart,
  making the search wasted work — is refuted: these productions share prefixes
  and differ later, which is exactly the case a chart exists for.
- **A learned greedy oracle recovers what the chart gets by searching.**
  `shiftreduce-001` matches `cky-001` within noise on every metric, beats it on
  `uas`, `ted_sim` and `edge_f1`, and does it in one left-to-right pass. It also
  over-generates far less: **1.09 nodes per gold node against the chart's 1.52**,
  which is where the `ted_sim` gap comes from. This is transition-based parsing's
  standing claim, and it reproduces here.
- **All three still lose to memorising.** `retrieve-001` does no parsing at all
  and beats the best of them by +0.06 bracket F1, +0.43 edge F1 and +0.23 label
  F1. Composing an answer is not yet competitive with recognising which of 179
  lessons the text is.

### The compositional parsers are the *most* vocabulary-bound

Share of the English score kept, on `bracket_f1`:

| parser | zh | tr | sw |
|---|---:|---:|---:|
| `cky-001` | 0.06 | 0.07 | 0.27 |
| `lr-001` | 0.05 | 0.06 | 0.08 |
| `shiftreduce-001` | 0.08 | 0.11 | 0.29 |
| `retrieve-001` | 0.40 | 0.86 | 0.87 |
| `template-002` | **0.46** | **0.72** | **0.73** |

This was not expected and is the opposite of the usual story about grammars
versus lookup tables. The reason is structural: a production's right-hand side is
keyed on **literal words**, so translating the frame words invalidates every
rule at once, while a template lookup can be keyed on punctuation and line
structure and never needs to read a word. A grammar over word classes rather
than word forms would be the obvious repair and has not been built.

### Cross-language: the clean test, and my prediction was wrong

`langcurriculum` takes a language when it renders and takes none when it
structures, so the same seed gives a different string in every language and a
**byte-identical graph**. For the masked-node task that is a disappointment
(`tests/test_language.py`). For a parser it is the ideal experiment: the target
is fixed, the input is translated, nothing else changed.

The pre-registered prediction, written into `parsers/template.py` and committed
before the sweep ran, was that a dictionary-seeded parser would collapse in
Chinese and a grammar-learning one would not. **The opposite happened.** Share
of the English score kept:

| parser | lookup signal | zh retrieval | zh label F1 kept | tr | sw |
|---|---|---:|---:|---:|---:|
| `template-001` | "layout" | **0.02** | **0.16** | 0.29 | 0.87 |
| `retrieve-001` | word identity | 0.34 | 0.47 | 0.89 | 0.90 |
| `template-seeded` | word identity | 0.34 | 0.38 | 0.79 | 0.80 |
| `template-002` | punctuation and lines | **0.74** | **0.60** | 0.82 | 0.84 |

The parser designed to be language-independent was the one that collapsed
hardest, and word identity — the thing translation is supposed to destroy —
transferred better than it did. The cause is worth writing down because it is
not about parsing at all:

**`layout_features` was not measuring layout.** It counted tokens, measured
their mean length, and counted how many were ASCII. Every one of those is a fact
about the *tokenisation*, and Chinese retokenises the same document into far
more, far shorter, non-ASCII pieces. The feature vector moved wholesale and the
nearest-neighbour lookup went to the wrong lesson 98% of the time.

`template-002` is registered beside `-001` rather than replacing it, and uses
punctuation counts and line structure only. Settled on **held-out training
episodes** rendered in each language (seeds 200-201) before it was ever run on
eval:

| feature set | en | zh | tr | sw |
|---|---:|---:|---:|---:|
| `layout_features` (token shape included) | 0.983 | 0.014 | 0.084 | 0.966 |
| `shape_features` (punctuation and lines) | 0.933 | **0.690** | 0.860 | 0.860 |

Two more from the same measurement:

- **NFKC is not enough for CJK punctuation.** It folds `：` and `；`, which are
  compatibility forms, and leaves `、` and `。` alone, which are not. The
  ideographic comma is the list separator in the Chinese rendering, so without
  an explicit fold the document reads as having no separators: Chinese lesson
  identification is **0.212 unfolded and 0.690 folded**.
- **Counting identifiers looks language-independent and is not.** Adding "how
  many ASCII identifier tokens" took English to 0.969 and Chinese to 0.159,
  because in English that count includes every English word and in Chinese only
  the untranslated symbols. It is a vocabulary-size feature wearing a shape
  feature's name. Not used.

The honest summary of the language axis is that **script and tokenisation
dominate it, not grammar versus vocabulary**. Swahili costs almost nothing to
anything (0.80-0.90 kept across the board, and 0.87 even for the broken
`template-001`), because it keeps the Latin script, the layout and a good deal
of untranslated English. Chinese costs everything that touched a token. A
cross-language claim in this repo should say which of those two it is testing.

### Dictionary seeding: a null that shrinks to zero

The knob is `Lexicon.from_curriculum` — build the frame/content judgement from
the whole curriculum's vocabulary instead of estimating it from the training
episodes. It is registered as `template-lex` with `template-001` as the
unseeded control on the identical lookup, and the bare name `template` resolves
over numbered versions only, so nothing can ask for "the template parser" and
get the seeded one.

| training episodes per lesson | `template-001` label F1 | `template-lex` label F1 |
|---:|---:|---:|
| 2 | 0.787 | 0.798 |
| 16 | 0.832 | 0.832 |

**+0.011 at two episodes per lesson, and identical to three decimals at
sixteen** — on every metric and in every language. The judgement it seeds
saturates almost immediately: a template constant appears in *all* of a lesson's
episodes, so two draws already separate it from a content word most of the time.
A curriculum-wide dictionary buys nothing a handful of examples does not, and
`FRAME_THRESHOLD` was not swept to rescue it.

## The VSA was not unbinding anything, and permutation fixed it

`runs/vsa_reach`, all 179 lessons, same config, floors and evaluation seeds as
every other row. The `vsa-002` and `corefer-001` rows reproduce their published
numbers to three decimals, so the two runs are directly comparable.

**The diagnosis, which is a fact about the algebra rather than a measurement.**
`VSAModel._trace` superposes only nodes that have a label, and the masked node's
label is `None`. Its binding was never in the trace, so `role(i) * trace` is not
a recall — it is the crosstalk, and the score of candidate `s` collapses to
`sum over {j : label_j = s} of <role(i), role(j)>`. A role is a *product* of four
independent bipolar atoms, so that inner product is `d` when the two role tuples
are identical and a zero-mean random walk otherwise: measured at `d = 4096`,
**4096 ± 0 on a match against 4 ± 60 on a mismatch**. Sixty-eight standard
deviations. `vsa-002` is a **hard partition** — "the commonest symbol among the
visible nodes sharing my exact `(ptype, slot, depth, arity)`" — which is a table
lookup, and a worse one than the floor's, since it has one key and no back-off.

On a five-lesson diagnostic slice a visible node with the query's exact role
tuple exists for only **37.5%** of scored nodes, and where none exists the model's
label accuracy is **0.000**. The copy head's -0.115 was never a readout defect on
top of a working retrieval. The retrieval had no reach.

**The fix is the operator the family never had.** The copy floor keys on the
relative *node-index* offset `i - source`, and no role atom encodes position.
Permutation is the standard third VSA operator and is exactly what binds order:
`seq = sum_j rho^j(cb[label_j])`, probed at `sum_k w_k rho^{k-i}(seq)` with `w`
counted per structural context on **training** episodes, keyed on the head of the
same ladder the floor keys on. Two things differ from the floor and both are
priced below: it superposes the top six routes where the floor takes the arg-max
over them, and it has a back-off ladder where the floor has one key and a global
fallback.

| model | lbl acc | lbl lift | bits | bits lift | copy acc | copy lift | rename | secs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `vsa-002` | 0.219 | +0.089 | 6.80 | +0.275 | 0.181 | -0.115 | 0.029 | 35 |
| `vsa_pure-002` | 0.200 | +0.066 | 6.94 | +0.259 | 0.181 | -0.115 | 0.002 | 35 |
| `vsa_addr-002` | 0.219 | +0.089 | 6.80 | +0.275 | 0.210 | -0.076 | 0.029 | 44 |
| `vsa_addr_pure-002` | 0.200 | +0.066 | 6.94 | +0.259 | 0.210 | -0.076 | 0.002 | 43 |
| `vsa_transform-002` | 0.242 | +0.116 | 6.69 | +0.286 | 0.254 | -0.016 | 0.021 | 44 |
| `vsa_perm_one-002` | 0.295 | +0.178 | 6.64 | +0.292 | 0.301 | +0.048 | 0.006 | 44 |
| `vsa_perm-002` | 0.326 | +0.213 | 6.49 | +0.307 | **0.310** | **+0.060** | 0.010 | 41 |
| `vsa_perm_pure-002` | **0.337** | **+0.227** | 6.62 | +0.293 | **0.310** | **+0.060** | **-0.003** | 40 |
| `vsa_full-002` | 0.325 | +0.212 | 6.42 | +0.314 | 0.300 | +0.047 | 0.010 | 45 |
| `vsa_full_gated-002` | 0.327 | +0.215 | 6.41 | **+0.316** | 0.299 | +0.045 | 0.008 | 56 |
| `vsa_full_pure-002` | 0.328 | +0.216 | 6.56 | +0.300 | 0.300 | +0.047 | -0.000 | 46 |
| `corefer-001` | **0.357** | +0.250 | 6.95 | +0.258 | **0.336** | **+0.096** | 0.003 | 197 |

Floors: label 0.143, type 0.860, copy 0.266, copy ceiling 0.722. The type head was
not touched and every row sits at -0.486, which is where `vsa-002` already was;
design rule 1 says the two heads do not share machinery and nothing here does.

- **The copy head crosses its floor**, -0.115 to +0.060: a swing of 0.175, larger
  than the entire spread between the four pointers this repo already had.
- **The label head moves further than the copy head did**, +0.089 to +0.213,
  because in this model they are one computation — reaching for a source *is*
  reaching for a symbol. The family was near-last on accuracy and its best row is
  now 0.337 against `corefer`'s 0.357, without giving up its bits. That ranking
  is against the rows in this sweep and the established table above, not a fresh
  nineteen-model run.
- **The control does not carry it, and is not nothing.** `vsa_addr-002` changes
  only the pointer *readout* — a node scores by its address, `<Q(i), role(j)>`,
  rather than by the mass its label received — and recovers +0.039 of the copy
  deficit while leaving the label head identical to three decimals. So a third of
  the pointer's problem was that it was the label head read twice, and two thirds
  was that it could not reach.
- **The analogical transform is the weaker half.** Learning per context which
  roles the answer occupies and superposing them into one query vector (`a:b::c:?`
  in one multiply) is worth +0.027 label lift and +0.099 copy — real, and a third
  of what permutation buys.
- **Superposing both channels is worse than the better one alone, and weighting
  them does not rescue it.** `vsa_full` loses 0.013 copy lift against `vsa_perm`
  and gains 0.007 bits. The obvious defence is that an equal share is too much
  for the weaker channel, so `vsa_full_gated-002` fits the share on held-out
  *training* episodes by held-out likelihood — design rule 4, the mass on
  whichever symbol turned out to be right rather than whether the argmax was it.
  It lands **interior at 1.25** and the row still trails `vsa_perm-002` on the
  head the channel was added for. Pre-registered and refuted: the role transform
  is subsumed once relative position is available, not mis-weighted.

  The first attempt at this answered nothing and is recorded so the mistake is
  not repeated: the grid stopped at 1.0, the fit landed on 1.0, and the model came
  out bit-identical to `vsa_full-002`. A boundary optimum cannot distinguish "this
  is the best balance" from "the grid was too narrow", and reporting it as a null
  would have been wrong.
- **Superposing the *routes* is worth less than it looks, and the control says
  so.** `vsa_perm_one-002` pins `top_k = 1`, which makes it the copy floor's own
  rule — same key, arg-max offset — expressed in hypervectors. It scores **+0.048
  copy lift**, so four fifths of the gain is there before a single route is
  superposed, and the mixture over six routes adds +0.012 copy and +0.035 label
  on top. The honest reading is that the *positional channel* is what was
  missing; the superposition is a real but secondary refinement. Note the
  single-route row still clears the floor it is a copy of, because it inherits a
  back-off ladder the floor does not have, a graded cleanup and a calibrated
  gate — so +0.048 is not "the floor scored above itself", it is what those three
  are worth on top of the same rule.
- **The memorising fallback stops being worth anything — it starts costing.** For
  `vsa-002` the shared `structural_fallback` was +0.019 accuracy and all of its
  renaming sensitivity. For the reaching variants it is **negative**:
  `vsa_perm_pure-002` scores 0.337 against `vsa_perm-002`'s 0.326, and
  `vsa_full_pure-002` 0.328 against 0.325. The fallback was compensating for a
  retrieval that could not find anything, and charging the family its one
  distinguishing property for the service.
- **The best row in the family is now the exactly equivariant one.**
  `vsa_perm_pure-002`: label lift **+0.227**, bits lift +0.293, copy lift +0.060,
  renaming drop **-0.003** over a permutation of all 2,105 symbols, in 40
  seconds. It is within 0.023 label lift of `corefer-001` at a fifth of the
  runtime, and unlike `corefer` its equivariance is a property of the algebra
  rather than a measurement that came out well.
- Still 0.310 of a 0.722 ceiling, and still behind `corefer` on the copy head.

**A seventh small-sample artefact, caught this time before it was written up.**
The first equivariance measurement of the permutation variants used the module's
24-episode test fixture and read **+0.051** against `vsa_pure-002`'s 0.000 —
which says the new channel bought its accuracy by memorising. The obvious
mechanism, superposition crosstalk (the sequence trace is loaded by *every* node
where the role trace is not), was checked and refuted: raising `d` from 4096 to
16384 moved the drop the wrong way. Re-measured with more episodes:

| eval episodes | `vsa_pure` | `vsa_perm_pure` | `vsa_full_pure` |
|---:|---:|---:|---:|
| 24 | +0.000 | +0.051 | +0.051 |
| 72 | +0.010 | +0.005 | +0.010 |
| 192 | -0.002 | +0.008 | +0.008 |

It was sampling noise, and the full curriculum agrees: `vsa_perm-002` is +0.010
against `vsa-002`'s +0.029 — *less* renaming-sensitive, not more. The lesson is
the one this repo keeps paying for, with one difference worth recording: this is
the first time the artefact was caught by re-measuring at a larger sample rather
than by a later sweep contradicting a published claim.

## The readout is worth more than the model, and it survived an independent attack

`runs/agent-sweep/` and `runs/agents-readout179/`, all 179 lessons, 716
evaluation episodes, 2,632 scored fills, `repair`. **The floor is `context`
0.2025 in every row below**, which is what makes them one table.

The same fitted `corefer-001` — same model, same episodes, same prior, same
calibrator — read two ways:

| agent | reads the output as | candidates | `label_acc` | lift |
|---|---|---:|---:|---:|
| `graphread` | **a move** | 24 | **0.5080** | **+0.383** |
| `graphread-capped` | a move | 8 | 0.3609 | +0.199 |
| **floor** (`context`) | — | | *0.2025* | *0* |
| `abstain` | nothing at all | — | 0.0866 | −0.145 |
| `wrap` | **text** | 8 | 0.0851 | −0.147 |
| `wrap` | text | 24 | 0.0767 | −0.158 |
| `wrap-envcal` | text | 24 | 0.0760 | −0.159 |
| `random` | — | — | 0.0543 | −0.186 |

**This is the largest effect in the repo and it is not a model difference.**
Models span about 0.1 of lift. One readout swap spans 0.43 — and `corefer-001`
was registered and sweeping the whole time, able to do this, with no way for the
harness to ask.

**It was attacked by an agent that did not write it, and the gap grew.** The
author named two confounds and ran neither; both were run, with thresholds
committed 22 minutes before the first number landed.

- **The candidate cap is real, asymmetric, and runs backwards.** `wrap` sees 8 of
  `repair`'s 24 candidates and `graphread` sees all 24, so part of the gap was
  truncation. Capping `graphread` to 8 costs it 0.147 — so the cap was worth a
  third of the published gap. But the direct control says `wrap` at **24** scores
  **0.0767, *lower* than its 0.0851 at 8**: the extra candidates cost `wrap`
  nothing because it was never using them. On equal candidate sets the gap is
  **0.4312, larger than the 0.4229 published.**
- **The calibrator was a third difference nobody had named** — `wrap` fitted on a
  freshly built `choice`, `graphread` on the run's own environments. Equalising
  it is worth 0.0007. Equalising all three differences leaves **0.4320**, the
  largest of the four framings. A gap that grows as its confounds are removed is
  the opposite of a confounded result.

**And the comparison row turns out to be silence, which corrects the finding's
own interpretation.** `wrap` 0.0851 against `abstain` 0.0866 — four fills of
2,632, and *identical on `success` to sixteen figures* over 716 episodes. So the
claim that "reading this model as text is actively bad" is unearned. The honest
statement is cleaner and stronger: **reading these models as text is
indistinguishable from saying nothing at all**, and eleven of nineteen models
cannot emit a token anyway.

**A slice finding died on the way.** "Abstention on `repair` is below chance" was
measured on six lessons and inverts at 179: `abstain` 0.0866 against `random`
0.0543 is **0.032 above** chance, not 0.060 below. Both rows moved, in opposite
directions, and no mechanism for either move has been measured. The note named
this as its own live risk and was right to.

## `005`: the type head is saturated, not unattacked

`runs/metta005`, 19 rows, all 179 lessons, same floors as every other row: label
0.143, type 0.860, copy 0.266, copy ceiling 0.722. The IR-as-a-knob line's first
candidate — **AtomSpace/MeTTa, whose native operation is match and rewrite**.

**The type head moved for the first time, and it still lost.**

| | type acc | type lift | type bits lift |
|---|---:|---:|---:|
| every other VSA-family row | 0.7922 | −0.4855 | +0.4931 |
| **`metta_type-005`** | **0.8203** | **−0.2849** | **+0.5660** |

That is **+0.201 of type lift**, the largest movement any row in this family has
shown on the head this log called "the last one nothing has attacked" — and it is
still **0.285 below the floor**. Both halves are the result. The reframe is what
to take away: **the type column was saturated, not unattacked.** A six-level
backed-off ladder over tree shape is simply very good, and reading what a node
*contains* — a direction no key in this repo had ever had — is worth a fifth of
the gap and loses anyway.

Design rule 1 held, and was checked in the arithmetic rather than asserted:
against `metta-005`, the `metta_type-005` row moves type lift by +0.201 while
`label_lift`, `label_bits_lift` and `copy_lift` are **identical to four
decimals**. The type gain did not come from the label route, which is the mistake
`corefer` paid 0.174 -> 0.004 for.

**Expressiveness is not the binding constraint — third independent
confirmation.** The pre-registration predicted the label null and named the
reason: `omegaclaw_reach-001` added `ilp`'s best discovered operator and lost;
candidate recall climbing 82.7% -> 98.7% moved accuracy by 0.000. Confirmed wide,
0.274 against `corefer`'s 0.357. MeTTa *can* express things `CLAWS` cannot — the
typed slot-selected sibling, the downward direction, arbitrary-length joins,
bounded transitive closure — and it does not help the head this repo leads with.

**A structural bits gain that survives renaming.** +0.011 bits lift at a **+0.001**
renaming drop, all 2,105 symbols permuted without refitting — against
`ensemble-001`'s +1.14 that collapsed 0.467 -> 0.038 on the same test. A tenth
the size, keeping essentially all of it. Accuracy is flat (0.213 vs 0.214), so an
"atomspace roles win" headline and an "atomspace roles are a null" headline are
both available from this table and both misreport it.

**A `Graph` cannot be content-addressed into an atomspace.** The
pre-registration's own proposed encoding would have collapsed **42.3% of all
nodes** (26,351 of 62,253, affecting 97.1% of graphs), because a `Graph` is a tree
of *occurrences* and an atomspace is a set of *values*. Caught by the round-trip
test covering all 179 lessons rather than sampling a fixture — the
`test_encoding_is_lossless` failure mode, caught before it could publish
anything. An outside `hyperon 0.2.10` agrees on 1,575 bindings with 0
disagreements, with a self-test proving the check can fail.

**Cost fired, and the absolute rate is refused.** The IR alone is 2.6x, the full
schedule 9.5x. The calibration control read `vsa_sum-004` at 0.50x its published
throughput, so no absolute rate from that pass is quotable and none is quoted.
For context `vsa_sum-004` at d=4,096 is already 15x below `APPROACH.md`'s target
before any atomspace exists, and **a `005` row at d=256 was never run** — the
cheap experiment this line skipped.

**The copy result survives an independent attack, and shrinks by two thirds.**
`metta_perm_pure-005` reaches **+0.1091** copy lift against `corefer-001`'s
+0.0959 — the first thing in this repo's history to lead the pointer. A refuter
who did not write it eliminated the three artefact hypotheses that would have
killed it:

- **Same question.** The scored `(batch, row, node)` key lists are *identical*
  across all four models on every draw; pads and self excluded symmetrically.
- **Not the shared back-off.** `structural_fallback` reaches `symbol_logits`
  only, never the pointer. Decisively: the flat pointer back-off scores **0.0000**
  and coverage is **1.000** for every model, so on this head abstention is
  punished rather than subsidised and the "back-off wearing the model's name"
  mechanism cannot operate.
- **Not one lucky mask.** Paired McNemar plus a lesson-cluster bootstrap over
  five draws, including 716 **fresh** episodes: `metta` leads 5/5 and the order
  never flips.

**But the improvement was quoted against the wrong baseline, and the honest
number is a third of it.** The finding compared to `vsa_perm_pure-002` (+0.060)
and omitted `vsa_perm_hks_wide_pure-004` at **+0.0926** — which this same log
names the second-best pointer. Decomposed properly: **+0.0327 for graph-derived
roles at all, and +0.0165 for the atomspace specifically.** That increment is
significant on all five draws; the headline +0.049 was never the atomspace's.

And **on the published draw alone the lead over `corefer` is not significant** —
56 items in 5,785, McNemar p = 0.057. Replication carries it, not that mask. Two
further honest notes: second place is a coin flip (`corefer` vs `hks_wide`
changes sign across draws), and the lead is bought on questions with 3+
coreferent sources and given back on two-source questions.

One thing the leading row has outright: **its pointer is bit-identical under a
permutation of all 2,105 symbols**, where `corefer`'s moves because
`_pair_features` reads prompt mention counts. It reads strictly less and wins.

**Correction to a number quoted throughout this file.** `copy_ceiling` is
computed over `label_n` = 5,233 and quoted against `copy_acc`, which is scored
over 5,785. On its own denominator the ceiling is **0.7305**, not 0.7216. Every
"0.722 copy ceiling" here is that mismatch; the conclusion it supports — that
more than half the reachable signal is untouched — is unaffected, since 0.346 of
0.7305 is if anything further from the ceiling.

## Roles derived from the graph, and a bandwidth nobody had fitted

`runs/vsa_role`, 27 rows, all 179 lessons, same floors as every other row: label
0.143, type 0.860, copy 0.266, copy ceiling 0.722. Attacked by an agent that did
not write it; **all four load-bearing conclusions survive and the headline was
0.053 too low.**

A role in `vsa-002` is the product of four random atoms indexed by
`(ptype, slot, depth, arity)`, and because the codebook is bipolar the candidate
score reduces exactly to the **role Gram matrix**. Swapping the role construction
and touching nothing else is therefore a controlled experiment by arithmetic.

`_pure` rows — no shared memorising fallback, so the algebra is what is measured:

| model | role Gram | lbl lift | bits lift | copy lift | rename |
|---|---|---:|---:|---:|---:|
| `vsa_null_pure-004` | i.i.d. — **the bottom row** | −0.125 | 0.201 | −0.320 | +0.003 |
| `vsa_hks_shuf_wide_pure-004` | signature **shuffled**, matched | −0.075 | 0.166 | −0.264 | +0.000 |
| `vsa_spec_shuf16_pure-004` | eigenmap shuffled, matched | −0.070 | 0.192 | −0.259 | −0.003 |
| `vsa_spec_pure-004` | Laplacian eigenmap | −0.044 | 0.212 | −0.232 | −0.001 |
| `vsa_pure-002` | product of atoms | +0.066 | 0.259 | −0.115 | +0.002 |
| `vsa_sum_pure-004` | **sum** of the same atoms | +0.083 | 0.282 | −0.097 | −0.000 |
| `vsa_hks_wide_pure-004` | **heat-kernel signature, fitted** | **+0.160** | 0.292 | −0.014 | +0.006 |
| `vsa_perm_hks_wide_pure-004` | signature + permutation | +0.187 | **0.316** | **+0.093** | −0.002 |
| `vsa_perm_pure-002` | partition + permutation | **+0.227** | 0.293 | +0.060 | −0.003 |

**The graph beats the hand-built coordinates, and by twice what was published.**
`vsa_hks_wide_pure-004` uses **no hand-built coordinate of any kind** — no parent
type, no slot, no depth, no arity. Each node's role is its heat-kernel signature,
a spectral quantity invariant under graph automorphism. At **+0.160** against the
hand-built partition's +0.066 and the hand-built graded ladder's +0.083.

**The published +0.107 was measured at a bandwidth the data does not want.** All
four `vsa_hks*` rows fitted `knob = 0.5` — the **bottom** of their grid. Extended,
the fit lands **interior at 0.25** and gains +0.053. This repo wrote a lesson that
same day saying a boundary fit is a failed fit until re-run wider; **the lesson
was invoked on the arm that lost and skipped on the arm that won**, and on the
losing arm it gave the wrong reading. That is now its own lesson,
`notes/lessons/2026-08-14-a-guard-applied-only-to-the-arm-that-lost.md`.

**The shuffled control is load-bearing and the effect is bigger than claimed.**
Permuting the signature rows across nodes preserves the Gram's value multiset and
destroys only the correspondence to the graph: +0.160 → −0.075. But the family had
no *bottom* row, so "gradedness contributes nothing on its own" had nothing to be
nothing against. `vsa_null_pure-004` (i.i.d. roles) supplies it at −0.125, so
gradedness alone is worth **+0.051**, and two unrelated shuffled embeddings agree
on that to 0.001. The corrected split is **82% correspondence, 18% gradedness** —
not 100/0.

**The pre-registered eigenmap is refuted**, at −0.044, below the floor, beating
its own matched control by only 0.026. Extending the diffusion grid 64x leaves it
**bit-identical**, so `t = 16` was an interior optimum all along and "a wider grid
cannot rescue it" has gone from an argument to a measurement. The mechanism given
for it — a term tree alternates functor and argument levels, so a label-carrying
node is always an even number of hops away — was a three-lesson slice and does not
survive: "always even" is **91.2%** at 179 lessons, and "the nearest visible node
never carries the answer" is 0.022, not 0.000. **The direction survives, the
absolutes do not.**

**`*` → `+` is still the cheapest result here.** Superposing the four atoms
instead of binding them is +0.017 label lift on the `_pure` pair and halves the
renaming drop, with no graph at all — and without it, a win for any graph
embedding would be unattributable between "graded helps" and "graph-derived
helps".

**The three heads still disagree, and that is the strongest thing in the work.**
Redrawn at the fitted bandwidth, `vsa_perm_pure-002` leads on label (+0.227), the
signature leads on bits (0.316) and on copy (+0.093). `vsa_perm_hks` is the
**second-best pointer in the repo**, behind `corefer-001`'s +0.0959. There is no
single ranking of these two models; which is better is a property of the metric.

**And every row in the family sits 0.486 *below* the type floor.** The work quotes
that floor and never returns to it. Nothing here has attacked the type head.

## `006`: the Lean gate closes, and the kernel loses to an arity check

The IR-as-a-knob line's second candidate was **Lean — a representation that can
*refuse* an answer** rather than score it low. It was pre-registered with a
gating diagnostic designed to kill it before a model was ever written, because
the pointer's constraint is measured to be discrimination rather than recall:
candidate recall climbing 82.7% -> 98.7% moved dev copy accuracy by 0.000. So a
typechecker helps only if it prunes candidates *without* pruning the gold one.

All 179 lessons, 537 held-out **training** episodes (eval's seeds untouched),
4,443 scored holes, median 55 candidates each. Reproduced on an independent draw
of 895 episodes at different seeds; nothing moves by 0.01.

| filter | prune (median) | gold survival | matched random |
|---|---:|---:|---:|
| `open` — the sound kernel | 0.286 | 0.988 | 0.634 |
| `declared` — Lean's own rule | **0.355** | **0.984** | 0.486 |
| `closed` — the committing arm | 0.797 | 0.797 | 0.256 |
| **`arity` — the floor** | **0.370** | **0.988** | 0.506 |
| `shifted` — the must-fail control | 0.286 | **0.578** | 0.663 |

**One arm cleared the pre-registered thresholds and it is dominated on both axes
by the floor.** The floor is: *reject a candidate iff no visible occurrence of it
has the hole's number of children.* No types, no unification, no intermediate
representation — any of the nineteen registered models could compute it from the
`Graph` it already reads. The pre-registration's own row-one language applies
exactly: **the IR is a re-encoding with no filter.** No threshold was moved; the
number cleared its threshold and failed its floor.

The two are not nested — the kernel rejects 3,659 candidates the floor keeps and
keeps 5,468 the floor rejects — so taking both prunes 0.388 against the floor's
0.370. **+0.018 of prune for an entire intermediate representation**, against a
measured baseline where sixteen points of candidate recall bought 0.000.

**The instrument works, which is what makes the null readable.** `shifted` — the
same kernel pointed at a different hole of the same episode — holds its prune
rate at 0.286 while gold survival collapses 0.988 -> 0.578, *below* its own
matched-random. The filter reads the hole. And it is not "right but
unaffordable", the failure mode the pre-registration worried about: 291,000
candidate checks per second, about 1.1 s for a full sweep.

**Why there was nothing left for a type system.** Every entity symbol in an
episode collapses into one metavariable component — `alice`, `apple` and
`manipulate` share a type, because the generator never made them differ. Only
`Nat/Str/Chr/Prop` are rigid and all come from literals. What remains is kind and
arity, and arity is free.

**No `lean-006` was registered and no sweep was run.** Phase 2 was never entered.
That is the gate doing its job, and it is the cheapest death any line here has
had.

This is promoted despite its controls being author-designed, and the reason is
worth stating: the failure mode that makes an author's controls untrustworthy is
constructing them to *pass*. Here they killed the author's own line, and the
must-fail control failed as required. A null from the agent that built the thing
runs against its own incentive; a win does not.

## Awaiting independent challenge — the promotion queue

`notes/` promotes into this file **only once something independent has tried to
break the finding**, because this repo has had author-designed controls pass
while being hollow. Four results are currently strong, measured on the full
curriculum, and **not yet in this file on purpose**. They are listed here so the
queue is visible rather than implicit — a finding nobody knows is waiting is a
finding that never gets challenged.

| finding | what it claims | what would promote it |
|---|---|---|
| ~~graph-derived roles~~ | — | **PROMOTED**, above. All four load-bearing conclusions survived an independent attack; the headline moved *up* 0.053 once the bandwidth was fitted rather than pinned at its grid's edge. Four of the refuter's five written predictions were refuted, all in the finding's favour. |
| the dimension / throughput curve, same note | quality saturates at **d = 1,024** for every construction and the last 64x buys nothing; `vsa_sum-004` at d = 256 matches `vsa-002` at d = 4,096 on accuracy at **17x the throughput** | **still queued, and it needs a quiet machine.** The quality half survived: one arithmetic claim, "all three decline slightly", is wrong — `vsa-002` *rises* 0.2146 → 0.2180 from 1k to 64k. The right statement is that all three move by ≤0.004 in either direction, which is the saturation the section claims. The throughput half was not re-measured: the box was at load 35 and a contaminated pass read `vsa_sum-004` at 1,391 tok/s against a published 18,995 |
| ~~the action readout~~ | — | **PROMOTED**, above. Attacked by an agent that did not write it; both named confounds run, plus a third nobody had named; the gap grew from 0.4229 to 0.4320 as they were removed. Its own interpretation was corrected in the process and a slice finding it rested on was refuted. |
| `notes/findings/2026-08-13-one-parser-over-word-classes-transfers-the-class-identities-do-not.md` | over 46 WALS-coded languages, abstraction transfers and the induced class *identities* are a liability held out; `Treebank.coverage` predicts held-out transfer at **r = +0.886** and survives partialling out script and untranslated share | a second, independent handle on coverage — the one intervention tried moved bracket F1 by +0.002, which is not enough to call a +0.886 correlate a passenger. See `notes/questions/2026-08-14-a-second-handle-on-treebank-coverage.md` |

| ~~the copy lead~~ | — | **PROMOTED**, above. Survived an independent attack that eliminated three artefact hypotheses — same scored key lists, back-off provably absent from the pointer, leads 5/5 draws including fresh episodes. The *improvement* did not survive: quoted against the wrong baseline, the atomspace-specific increment is **+0.0165**, not +0.049. The attack also found a denominator mismatch in `copy_ceiling` affecting every copy number in this file. |

The one thing the queue must not become is a parking lot for results nobody
intends to challenge. A finding that sits here unchallenged is not "pending"; it
is unverified, and should be read that way.

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
  +0.078 copy lift against `corefer`'s +0.096. The first thing that *did* move
  a pointer a long way is `vsa_perm-002`, and it moved it from far below the
  floor to +0.060 — still third of the pointers, so the ceiling is untouched.

  **Update: something is now first, and the ceiling still stands.**
  `metta_perm_pure-005` reads **+0.1091** against `corefer-001`'s +0.0959, which
  is the first time in this repo's history anything has led the pointer. It is
  0.346 of a reachable 0.722, so **more than half the signal is still untouched**
  and the question is unchanged in substance; what died is only "nothing has ever
  been first". Not promoted — it was not pre-registered and is under challenge.
- ~~**The type head is the last one nothing has attacked.**~~ **Attacked, and the
  finding is that it was saturated rather than unattacked.** `metta_type-005`
  reads what a node *contains* — a direction no key here has ever had — and moves
  type lift from −0.486 to **−0.285**, the largest movement any VSA-family row has
  shown, while still sitting 0.285 *below* the floor. Design rule 1 held: label,
  label-bits and copy are identical to four decimals across that move. A
  six-level backed-off ladder over tree shape is simply very good, and the open
  question is now the sharper one — **is anything except tree shape worth
  anything on this head at all?** Two of nineteen models are positive on type.
  The original text follows, because it is what the attack was aimed at:
  every VSA row sits at
  -0.486, unchanged since `vsa-002`, because the family's type vote is a
  four-feature lookup and the floor is a six-level backed-off ladder. Two of
  nineteen models are positive on type. Design rule 1 says the heads do not share
  machinery, so the fix cannot be "point the label pointer at it" — `corefer`
  already tried that and paid 0.174 -> 0.004.
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
- **Can anything beat `retrieve-001` by more than the refill step does?** On the
  `str -> Graph` task a lookup with no parsing in it reaches 0.758 label F1 and
  the best parser reaches 0.832. Until something opens that gap, "parsing this
  curriculum" and "recognising which of 179 lessons this is" are the same
  measurement, and the second one is not interesting.
- **Exact graph recovery is 0.016 at best.** Every other number in the parser
  table is partial credit. Nothing here has actually parsed an episode.
- **Is `template-002`'s Chinese score grammar or is it punctuation?** It keeps
  0.60 of its English label F1 across a full script change, on punctuation
  counts and line structure alone. That is either a real structural signal or a
  fingerprint of 179 distinct document layouts, and the two are distinguishable:
  render with the layout perturbed — bullets to numbers, semicolons to newlines —
  and see whether identification survives. It has not been run.
- ~~Nothing has tried to *build* a graph rather than retrieve one.~~ Done:
  `cky-001`, `lr-001` and `shiftreduce-001` compose one from an induced grammar,
  and all three lose to `retrieve-001`. The open question it turns into is
  sharper: **can a compositional parser beat a lookup on this corpus at all, or
  is 179 templates simply a corpus where recall is the right algorithm?**
- **A grammar over word classes, not word forms.** The compositional parsers are
  the most language-bound things in the package — `cky-001` keeps 0.06 of its
  English bracket F1 in Chinese where `template-002` keeps 0.46 — because a
  production's right-hand side is keyed on literal words. Replacing those with
  induced classes (which is what `symbolic_ai_models/parsers/` produces, and the
  one place the two packages might genuinely meet) is the obvious repair and has
  not been built.
- **The treebank's 21% miss is unexamined.** Clause alignment finds a span for
  79% of clause-shaped nodes. Nothing has looked at which fifth it loses or
  whether they are systematically one kind of lesson, and every classical score
  is capped by it.
