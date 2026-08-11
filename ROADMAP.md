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

## Task list

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
- [ ] **Calibration.** `RuleBasedModel` already emits a confidence in [0,1].
      Bucket by it, report accuracy per bucket and ECE. Free.
- [ ] **Cross-language transfer.** Fit on English, evaluate on Chinese/Turkish;
      the graph is identical across renderings. The README claims the data
      supports this and nothing measures it.
- [ ] **Held-out-slice selection.** Any reasoner that fits parameters and then
      selects among them on the same episodes is selecting on its own training
      signal. Affects `synth`, `ruleinduce`, `grammar`, `analogy`.
- [ ] **Per-episode parameter fitting.** Induce the hypothesis *family* across
      training episodes, then choose the member per episode by consistency with
      what that episode states. This is the direct answer to the curriculum
      inventing vocabulary per episode, which is what holds `label_coverage` at
      0.92 and label lift near the floor.
- [ ] **Anchor-relative features.** Re-express structural features relative to
      the masked node or the query subtree — relative depth, sibling offset,
      path-from-query — so a hypothesis learned on one episode is *identical*
      rather than merely similar on another.
- [ ] **Cap the counting models' memory.** The source work reports a
      count-based model taking the host down at 40M tokens. `ngram`, `ctw` and
      `grammar` grow with distinct contexts and have no bound.

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
