# Roadmap

State for autonomous continuation. Read `git log --oneline | head -20` first;
this file says what the work *is*, the log says how far it got.

## Now: decouple parsing from reasoning

Every symbolic model currently has its parser welded on. `syllogism` owns a
categorical fragment, `symbolalg` a clause regex, `grammar` a class induction.
That makes "which parser" and "which reasoner" one choice when they are two, and
it means a better parser cannot be dropped under an existing reasoner.

The split:

- `parsers/` — a `Parser` is `text -> ParseResult` (tokens, classes, brackets,
  facts). Registered by name, fitted on training episodes only.
- `models/` — a reasoner declares `extra.parser` and gets whatever it names.
  Reasoners must work with *any* parser, including `none`.

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

- [x] **Re-run the full sweep and correct the README.** Done, and it refuted
      the claim that prompted it: three rule-based models did *not* clear the
      floor. Those measurements were taken at 50 training episodes per lesson
      and do not survive the sweep's 200 — see below.
- [ ] **Why do the rule-based models degrade with more data?** `workspace`
      scores 0.316 at n_train=50 and 0.291 at 200, while the floor rises 0.298
      -> 0.312. A model getting worse with four times the evidence is a defect,
      not a property, and it is the most likely reason none of them clears the
      floor at sweep scale.

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

## Open questions

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

1. Never commit with tests failing. `uv run pytest tests/ -q`.
2. One coherent change per commit, with a message saying what was learned.
3. Report negative results. A parser that does not help is a finding.
4. Do not tune against the evaluation set; seeds >= 1_000_000 are eval only.
