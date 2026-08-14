# symbolic-ai-models

**Train and evaluate symbolic text model architectures on one harness: predict the next token, and predict a masked node in the graph.**

The premise is that these are the same question asked of two surfaces. The generator — [`langcurriculum`](https://jacobfv.github.io/formal-language-cirriculum/), vendored here as `symbolic_ai_data/` — builds every episode as a **typed term** and only then renders it as prose, so for each episode there is a graph that is not a parse of the text but the thing the text was generated *from*. That gives a rare pairing: running text and exact structure, describing the same world, generated from the same seed, in unbounded quantity.

An episode is a pure function of its seed, so a "dataset" here is only a cache and the train/eval split is a seed range rather than a file. That also means nothing on disk would change if generation drifted, which is why the corpus carries a checksum: `symbolic_ai_core/data/fingerprint.py` hashes 179 lessons × 5 seeds × 7 languages, and a test fails if any cell moves.

So every model here is asked both:

- **next-token prediction** over the episode as it is rendered;
- **masked-node prediction** over the term graph it was rendered from — hide a node, name its type and its label from the neighbourhood.

Both predict a hidden symbol out of **one shared vocabulary**, through **one shared output head**. That is what makes it meaningful to ask whether training on structure helps the text, whether an architecture that is good at one is good at the other, and whether a model that scores well on prose has internalised anything a term tree would recognise.

```bash
uv sync
uv run symbolic-ai-models models                       # 25 symbolic models
                                                       # (neural: opt-in, see below)
uv run symbolic-ai-models inspect unification --seed 2 # one episode, both surfaces
uv run symbolic-ai-models train --config configs/small.toml --model rgt       --out runs/rgt
uv run symbolic-ai-models train --config configs/small.toml --model ruleinduce --out runs/rules
uv run symbolic-ai-models sweep --config configs/small.toml --models all      --out runs/sweep
uv run symbolic-ai-models compare runs/sweep/*
```

`--models` also takes `neural` or `symbolic` to sweep one family. The symbolic
models are pure Python and run on CPU; nothing in them needs a GPU, and
`train` fits them in a single pass rather than taking gradient steps.

## The two surfaces

`symbolic_ai_models inspect` prints an episode as the harness sees it. This is `unification`, seed 2:

```
--- text (next-token task) ---
The fact is alice parent frank.
The pattern is alice parent A.
What is the unify A?

Answer with exactly one of: Alice | Bob | Carol | Dave | Erin | Frank
Reply with the answer only.
Frank

--- graph (12 nodes, masked-node task) ---
(record (fact (parent alice frank)) (pattern (parent alice A)) (query (unify A)))

--- node table ---
   i type      label                parent slot depth
   0 record                             -1    0     0
   1 field     fact                      0    0     1
   ...
   7 ident     alice                     4    0     3
   9 ident     alice                     5    0     3
  10 ident     A                         5    1     3
  11 ident     A                         6    0     3
```

Nodes 7 and 9 are the same constant; 10 and 11 are the same variable. The harness computes that as a `same_label` relation, alongside `parent`, `child_k`, `sibling` and `ancestor` — so the binding structure a lesson is *about* is present in the batch as an edge, and an architecture either uses it or does not.

## The harness

Every model consumes exactly one type, `SymbolicBatch`, and the tasks differ only in how it was filled in:

| | next-token | masked node |
|---|---|---|
| `tokens` | text pieces | node labels, some replaced by `<mask>` |
| `types` | all `text` | the term type of each node |
| `rel` | `None` — positions are a chain, so relative position serves | the relation between every pair of nodes |
| `causal` | `True` | `False` |
| `target_*` | the next token | the hidden label and the hidden type |

A neural architecture implements one method:

```python
@register("mine", doc="what it does differently")
class MyModel(NeuralModel):
    def build_encoder(self, cfg: ModelConfig) -> nn.Module:
        return MyEncoder(cfg)          # forward(h[B,L,D], batch) -> h[B,L,D]
```

A rule-based one implements two, and never sees a tensor:

```python
@register("mine", doc="what it reasons with")
class MyModel(RuleBasedModel):
    def learn(self, episodes, tok): ...            # fitted once, on train only
    def node_votes(self, view: GraphView):         # view.labels[i] is None where hidden
        return {i: (({symbol: 1.0}, 0.7), ABSTAIN) for i in view.hidden}
```

Embeddings, heads, initialisation, optimiser, schedule, the back-off and both losses are defined once and are identical within each family — so a difference in the results is a difference between the architectures, not between two people's recipes.

## The architectures

Two families, one interface. Both answer `forward(batch) -> logits`, so both are scored by the same cross-entropy against the same floors and land in the same table.

**Neural** — trained by gradient descent, and **off by default**. They are not
the subject of this repo and they are the only thing in it that wants a GPU,
which on a shared machine means competing with real training. Nothing is
deleted; set `SYMBOLIC_AI_MODELS_NEURAL=1` to register them for a run where the
cross-family comparison is the point and the device is free. Everything else —
including `--device`, which now defaults to `cpu` rather than grabbing whatever
accelerator exists — runs on CPU:

| id | what it is | what it is there to show |
|---|---|---|
| `gru` | a GRU over the linearisation, causal or bidirectional | the floor. If structure-aware models don't beat it, the structure wasn't doing the work |
| `transformer` | plain pre-LN transformer; a graph is its pre-order linearisation | the control — no edge ever reaches it |
| `rgt` | attention biased by edge type, values marked by edge type | the value of being *told* the structure rather than inferring it |
| `tpr` | [tensor product representations](https://doi.org/10.1016/0004-3702(90)90007-M): role ⊗ filler binding, with a learned role-remapping matrix per edge type | explicit binding. `f(a,b)` and `f(b,a)` have identical neighbour sets and must not be the same state |
| `hrr` | [holographic reduced representations](https://doi.org/10.1109/72.377968): circular-convolution binding, superposition, and a cleanup memory | fixed-width symbolic capacity — and its limits, which are the interesting part |
| `ndr` | [neural data router](https://arxiv.org/abs/2110.07732): one shared layer run `T` times, copy gate, geometric attention | depth of computation untied from depth of network; `set_steps()` raises it at eval time |

`rgt` versus `transformer` is the cleanest contrast among these — same depth, same width, same initialisation, differing only in whether the edges are visible.

**Rule-based** — fitted in one pass, pure Python, CPU only. Five are ported from [`symbolic-ai`](../symbolic-ai); each keeps its original algorithm and gains a predictive head:

| id | ported from | the algorithm |
|---|---|---|
| `ngram` | — | variable-order back-off counting. The floor for this family: everything else has to beat counting |
| `syllogism` | `symbolic_ai_001` | parses a fragment of English into categorical statements, saturates them under conversion, subalternation and the four valid figures. On graphs it aligns subtrees — the operation under unification |
| `symbolalg` | `base_symbolic_002` | the deliberately weak, ambiguity-preserving parser: keeps *both* readings of a clause and predicts by template analogy within the episode |
| `synth` | `seq_synth_001` | enumerative program synthesis with observational-equivalence pruning, run online over token ids. The hypothesis is a program, refitted whenever it is refuted |
| `ruleinduce` | `rule_induce_001` | CN2/RIPPER-style decision-list induction with MDL stopping. Its rules predict *pointers* (`copy:peer`, `copy:parent`), not symbols — so they survive the curriculum's per-episode invented vocabulary |
| `evidence` | `symcontrol_001` | retrieval by weighted concept overlap, with the source's evidence threshold intact — below it the model **abstains** |

And four drawn from the wider history of symbolic AI, chosen to fill the gaps the
ported set left — nothing above learns clauses with variables, mixes over model
orders, corrects its own errors, or reasons by structural analogy:

| id | after | the algorithm |
|---|---|---|
| `ctw` | Willems, Shtarkov & Tjalkens 1995 | **Context Tree Weighting** — a Bayesian mixture over *every* context tree at once, KT estimators, the ½/½ recursion. Where `ngram` picks the longest context it has seen and calls that a confidence, CTW never chooses; the two see identical counts and differ only in how they combine them |
| `ilp` | Quinlan's FOIL | **First-order clause induction.** Everything else here is propositional. A hypothesis is `answer(X,L) :- peer(X,V), label(V,L)` — the relational *chain* is learned, not enumerated, and the head binds a variable rather than naming a symbol, so a clause induced over `o0`/`o1` episodes applies unchanged where everything is called `w7` |
| `brill` | Brill 1995 | **Transformation-based error-driven learning.** A weak baseline plus an ordered list of corrections, each chosen to repair more than it breaks *on the output of every rule before it*. The hypothesis is a program over its own predictions, and reads as a narrative about what the baseline got wrong |
| `grammar` | Harris 1954; ADIOS; SEQUITUR | **Grammar induction — the only parser here that was learned.** Symbols sharing enough contexts are merged into equivalence classes by union-find, then frequent class digrams are promoted to nonterminals. Prediction happens at the class level, so a context never seen with a given word still resolves if the *kind* was seen there |
| `workspace` | Hofstadter & Mitchell's Copycat; Hearsay-II; SOAR | **Infers its own objective, partitions memory to fit, then runs competing codelets.** Derives a goal signature from the tree, carves the episode's top-level fields into regions, and lets operators (mirror a parallel region, copy a peer, echo the frame) compete; agreement lowers a temperature that governs commitment. What it learns is a *policy over strategies*, keyed by problems it discovered for itself |
| `analogy` | Gentner's structure mapping; Forbus's MAC/FAC | **Retrieve an isomorphic case and transfer the route to its answer.** A symbol-free structural signature filters the case base, a greedy alignment grows a node correspondence, and what crosses is the *path* the remembered answer stood at rather than the symbol itself. Verified equivariant under renaming — which it was not when first written; see the findings below |

### No cheating

The symbolic models are held to the same bar as the networks, and the bar is enforced rather than promised:

- **They emit distributions, not answers.** Each returns *votes* plus a confidence in `[0,1]`, and the base class mixes that against a smoothed unigram back-off: `p = (1-c)·backoff + c·votes`. Nothing can assign zero probability, so cross-entropy is finite and a confidently wrong model is punished for it. There is no separate multiple-choice path.
- **Abstention is real and costs the prior.** Confidence zero lands exactly on the back-off — the honest reading of "I don't know". `evidence` reports its `abstention_rate` because that is a result, not an excuse.
- **They cannot see the answer.** Rule-based models receive a `GraphView` in which hidden labels and types are literally `None`; there is no field holding the value being predicted.
- **Two leak tests run against all twelve models.** Perturbing later tokens must leave earlier predictions bit-identical, and rewriting a masked node's true label must not move the prediction. A model that fails either is reading its own answer.
- **The back-off is shared**, exactly as the embeddings and heads are shared on the neural side, so differences between symbolic models come from their machinery.

### The parser is a parameter — and one of them is an oracle

`collate_text` sets `rel=None`, so the text surface hands a model a flat token
chain while `collate_graph` hands it the true term graph. Every model that scores
well here scores on the graph, which leaves "is the text-surface failure a
*parsing* failure or a *reasoning* failure" unanswerable — the two are welded
together inside each model.

`symbolic_ai_models/prefix.py` unwelds them. A `PrefixParser` maps every prefix
of a token sequence to a `Graph`; a rule-based model names the one it wants in
`extra.text_parser` and reads `view.graph(t)`. `TextPrefix` adapts any parser
registered in `symbolic_ai_parsers`, so a reasoner is measured against a real
parser without either being rewritten. `gparse-003` is the first reasoner written
against the seam and is registered five times — `-003` (`template-002`),
`-retrieve`, `-flat`, `-none`, `-oracle` — differing in nothing but the reader,
so the spread between its rows measures parsing rather than models.

**`gparse-oracle` is a CEILING, not a system.** It is handed the episode's true
term graph. On real text there is no oracle, and on any batch built from ids
rather than episodes — `decode`, the agent evaluation — it returns nothing and
the model abstains. It is a word-suffixed name on purpose: `--models gparse`
resolves to `gparse-003`, never to the ceiling.

**The leak, and why the number is not worthless.** 85.3% of answers are literally
the label of a node of that episode's graph, so an unrestricted oracle would read
the answer off it. The oracle is therefore restricted to *the nodes whose symbol
the reader has already read* — the r-th node carrying a symbol waits for the r-th
occurrence of that symbol as a complete word in `decode(ids[:t+1])`; symbol-free
nodes wait for their first available descendant; the rest are deleted and their
children re-attached. **It can never name a symbol the model has not read**: it
supplies relations among seen symbols, which is what a parser supplies, and not
vocabulary, which is what a leak is. Audited on all 179 lessons at eval seeds,
11,198 positions, 424,550 revealed nodes: **zero** suffix violations and **zero**
unseen-symbol violations, against a `none` reader that passes both by revealing
nothing.

Note that the two existing leak tests would *not* have caught a leak here — both
perturb tokens, and the graph does not move when the tokens do. The guard that
would is `tests/test_prefix_parser.py`: adding graph nodes labelled with symbols
the text never contains must leave every logit bit-identical.

### The readout is a parameter too

The parser seam answers *what does the model read*. The mirror-image seam —
*what is the model's output read as* — was welded shut until now, and one
readout is an assumption rather than a neutral choice. Three measurements say so:
**71.9%** of scored answers already sit on a visible node, so the label task is
binding scored as classification; `gparse-003` abstains everywhere outside the
answer span and 11 of 19 models cannot emit a token at all; and `label_acc` and
`label_bits` rank the models close to *inversely*, because one shared mixture
`(1-c)·backoff + c·votes` pushes deciding and estimating through the same scalar.

`symbolic_ai_core/readout.py` unwelds it. A `Readout` is
`(model output, batch) -> counts`, plus `summarize` and — non-negotiably —
`floor`; `ModelOutput` carries a `channels` mapping and each readout names the
one it consumes. `source_logits` **became** `channels["node"]` rather than
staying a special case beside a second mechanism, and one assembler
(`_pointer_logits`) builds both pointer channels. `symbolic-ai-models readouts`
lists them.

| readout | channel | the question | floor |
|---|---|---|---|
| `symbol-001` | `symbol` | name the hidden symbol out of 8,192 | the masked-node structural table |
| `node-001` | `node` | which visible node of this episode says it | commonest offset to a same-label node |
| `site-001` | `site` | which already-read *word* is the head this token attaches under | best of `start` / `previous` / `offset` |
| `action-001` | `symbol`/`node` | the same emission read as a move in an environment | the environment's `reference_floor` |

**A model that emits nothing on a channel is unscored, never scored zero.**
"Cannot point" and "points badly" are different facts and one cell cannot hold
both — `gsite-none` has no `site` column at all, which is the correct row for a
reasoner handed nothing to read.

**`site` is the new question, and the corpus is privileged for it.** A token may
attach to the phrase before it or the one after, at different depths of the
tree, and the curriculum ships the true term *and* its rendering from one seed —
so the correct site has ground truth at every position, for free. `availability`
already says which word reveals which node; walking up to the nearest ancestor
already realised gives the site, and the word that spelled it is a position.
Correctness is *word* equality with the true site, never index equality, which
is the rule the copy head already followed and is what makes the readout
scorable for any parser — including `flat`, which has no term nodes at all.

The target is computed task-side from `meta["graphs"]`, exactly as
`target_tokens` is computed from the episode, and no model is handed it. The
guard is the one the causality test cannot be, because that test perturbs tokens
and the graph does not move when tokens do: **adding graph nodes labelled with
symbols the text never contains must leave every logit on every channel
bit-identical** (`tests/test_readouts.py`).

A symbolic run's artifact is legible: `runs/<name>/rules.txt` is the induced decision list in full, and you can read it and argue with it.

```
IF slot(1) AND parent_head(parent) THEN copy:peer   [41/44]
ELSE IF parent_type(record) THEN const:query        [30/38]
```

## What is actually graded

Everything is **open-vocabulary** and **teacher-forced**. A model outputs a
distribution over the whole vocabulary at every position; nothing is ever a
true/false question and nothing is confined to a list of options.

| | what it predicts | over | reported |
|---|---|---|---|
| `lm` | the next token, given the true prefix | the full vocabulary | `token_*` (all positions) and `answer_*` (the answer span only) |
| `node` | a masked node's label and type | the same vocabulary; 17 types | `label_*`, `type_*`, `label_coverage` |
| `--curriculum` | which option is right | the episode's own answer set | per-lesson acc / floor / lift |

The third is a *report*, not a separate path: each option is scored as a
continuation with the same LM head and the best one wins. Nothing in the repo
has a classifier over choices.

**Read `answer_*`, not `token_*`.** Across the curriculum only **1.4%** of
scored language-modelling positions are the answer; the other 98.6% is the
question and the fixed scaffolding around it. The gap is not subtle — a
back-off n-gram scores `token_lift` **0.77** and `answer_lift` **0.05** on the
same run, and every network in the sweep holds `token_lift` above 0.65 while
scoring *negative* `answer_lift`. Undifferentiated, the LM metric measures how well a model reproduces
"Answer with exactly one of:".

Every *number* is teacher-forced scoring, which is how language models are
trained and evaluated. Free-running generation exists but is deliberately
**outside** the evaluation path — see below.

## Sampling, for reading rather than scoring

A model with a respectable cross-entropy can still produce nonsense the moment
it stands on its own output, and no aggregate will show you that. So there is a
decoder, and it feeds no metric:

```bash
symbolic-ai-models sample runs/rgt --per-lesson 2 --max-new-tokens 12
symbolic-ai-models sample runs/rgt --sample --temperature 0.8 --json out.json
scripts/qualitative-sample.sh runs/both        # every run, transcripts + JSON
```

Greedy by default, with temperature / top-k / top-p available; it stops at
`<eos>` or the end of the line. The prompt is fed exactly as training saw it
(`<bos> prompt \n`), the answer never enters the input, and because both
families answer the same `forward`, the same sampler decodes a decision list and
a transformer alike. There is no KV cache — each step re-runs the whole prefix,
which is quadratic and entirely fine at review volumes, and keeps the decoder on
the same forward pass the metrics use.

The script writes a transcript per model, flat JSON records for a reviewing
model to read, and a `review.md` explaining what a reviewer is actually for.
Nothing it produces has a floor, and none of it should be compared against the
numbers in `summary.json`.

It is immediately useful. At 400 steps `rgt` scores `token_lift` 0.67 — and
samples like this:

```
gold      : 'o1'
generated : 'Reply with exactly one of: o1'
```

which is the same finding as the negative `answer_lift`, in a form you cannot
misread.

## Where the vocabulary comes from

Fitted on the **training episodes only** (seeds 0…n), by frequency, with
nothing external and nothing pretrained:

- 6 specials, 256 byte tokens, then the most frequent pieces;
- 70% of the budget goes to text pieces, 30% is reserved for whole node labels,
  because a label has to land on a single id or the masked-node head cannot ask
  for it;
- anything out of vocabulary falls back to its UTF-8 bytes, so encoding is
  lossless in every language the curriculum renders — an English-fitted
  vocabulary still round-trips Chinese, Turkish and Swahili exactly.

It is neither character-level nor synthetic: it is empirical counts over real
curriculum text. Two consequences follow from the curriculum inventing
vocabulary per episode, and both are measured rather than assumed:

- **24.5%** of evaluation text tokens fall back to bytes;
- **16.2%** of evaluation node labels are out of vocabulary and are **excluded
  from the label score** — so `label_acc` is an accuracy over the nameable 84%,
  and the excluded ones are systematically the interesting cases. That share is
  reported as `label_coverage`. The real fix is a copy/pointer head; `ruleinduce`
  already has one in effect, since its rules predict pointers rather than
  symbols.

## Floors

`langcurriculum` refuses to report an accuracy without a floor, and the same argument applies harder here: masked-node accuracy is dominated by how often the answer was `ident`, and a number that doesn't say so isn't telling you anything. So every metric comes with the score of the best thing that knows only the training distribution, and:

```
lift = (score - floor) / (1 - floor)
```

`lift` is the number to compare. Zero is the prior; one is perfect. Floors are **fitted on train and scored on eval** — a floor that gets to look at the answers isn't a floor.

Type and label are reported separately and never averaged. Type is the structural question (what kind of thing sits here); label is the symbolic one (*which* predicate, *which* variable) and the harder of the two.

**One correction worth reading before the rest.** This README claimed for a long time that label is hard *because the curriculum invents its vocabulary per episode*, so the answer is usually a name the model has never seen. Measured across all 179 lessons: **100.0% of scored labels are symbols that appear in training.** The generator varies which name fills a slot, not the pool it draws from. Label is hard because choosing among familiar symbols is hard — not because the symbols are unfamiliar.

That premise was load-bearing for several design decisions here, and they should be read in its light: `analogy` gave up 0.463 accuracy for 0.186 to become renaming-equivariant, and `ruleinduce` predicts pointers rather than symbols. Equivariance is a real robustness property and those models genuinely have it. It is simply not what this task rewards, and on this curriculum robustness and accuracy pull in opposite directions.

The masked-node floor is a **structure-only baseline**, not a majority-class one, and the difference matters more than it sounds. Node type is very nearly a function of tree shape — a `field` is always a record's child, a `char` always a string's — and a lookup table keyed on nothing but `(parent type, slot, depth, has children)` scores **0.96** on the curriculum's graphs. Against a majority-class floor of 0.33, a model that had learned strictly *less* than that table would still report a lift near 0.9. So the floor is the table. What remains above it is the part of the score that is actually about reference rather than about shape.

The practical consequence: treat **label lift** as the number that separates architectures, and read a high type score as confirmation the model parses the tree, not as evidence it understands it.

## Contamination

There is none, by construction. An episode is a pure function of its seed, so training draws from seeds at 0 and evaluation from seeds at 1,000,000: the split is a property of the seeds, not of a file that could be regenerated wrongly. An evaluation set did not exist until it was asked for.

```python
import symbolic_ai_models as sm
sm.TrainConfig(lessons="tag:mathematics", n_train=512)   # 179 lessons, or a slice
```

Data can be generated live or cached first — cache it for a sweep, since generation is pure Python and would otherwise be repeated identically per architecture:

```bash
uv run symbolic-ai-models data --out data/full --n-train 256 --n-eval 32   # ~46k episodes
uv run symbolic-ai-models sweep --config configs/full.toml --data data/full
```

## Scoring against the curriculum's own question

Perplexity isn't what the curriculum asks. It asks whether the right answer was chosen out of a stated set. A trained model answers by scoring each option as a continuation and taking the best, normalised per token so long options aren't penalised:

```bash
uv run symbolic-ai-models eval runs/rgt --curriculum
```

```
lesson                                    n     acc   floor    lift
-------------------------------------------------------------------
context_free_language                    40   0.550   0.550   0.000
palindrome                               40   0.525   0.525   0.000
center_embedding                         40   0.300   0.327  -0.040
unification                              40   0.175   0.275  -0.138
-------------------------------------------------------------------
macro-average                           240   0.367   0.412  -0.078
```

That output is real, and it is what a 400-step wiring check actually produces: a model that has learned the shape of the prose and cannot yet answer anything. Negative lift is the report working. Nothing in this repo ships with a result — `configs/full.toml` is where a run that could support one starts.

`symbolic_ai_models.agent.as_text_agent(model, tok)` returns a `Callable[[str], str]` for `langcurriculum.evaluate` directly, if you want the library's own report instead.

## Layout

```
symbolic-ai-models/
  configs/
    small.toml            # finishes in minutes; checks the wiring
    full.toml             # a slice, with the shape knobs pinned
    full179.toml          # all 179 lessons: the config a result comes from
    agents-small.toml     # the same two, for the interactive half
    agents-full.toml
  symbolic_ai_data/       # the generator, vendored verbatim from langcurriculum
    lessons/ generators/  #   180 registered, 179 that generate; one seed = one
                          #   episode, in both surfaces
    grammar/ languages/   #   deterministic realization, seven language packs
    _vendor.py            #   provenance, and the rule for changing any of it
  symbolic_ai_core/       # what every package here shares; depends on nothing
    data/                 #   above it
      curriculum.py       # symbolic_ai_data -> Episode (text + graph, one seed)
      fingerprint.py      # a checksum of the corpus; the generator cannot move
                          #   without a test saying so
      graph.py            # term JSON -> flat node array + parent pointer
      tokenizer.py        # one vocabulary, byte fallback, lossless
      batch.py            # SymbolicBatch + the relation algebra  <- the harness
    registry.py           # the versioned-name rule, written once for everyone
    floors.py             # empirical_floor, lift, and exact per-head counting
    shortcuts.py          # what an unthinking cheat scores: a floor and an audit
    calibration.py        # is the confidence worth anything
    invariance.py         # rename every symbol and see who notices
    asymptotics.py        # I(d) and effective rank: observables of the corpus
  symbolic_ai_models/
    data/ calibration.py  # re-export shims at the pre-split import paths
    invariance.py shortcuts.py asymptotics.py
    models/
      base.py             # Model (the interface) + NeuralModel (embeddings, heads)
      symbolic.py         # RuleBasedModel: votes -> distribution, redacted views
      registry.py
      gparse_003/         # the -003 generation: the parser is a *parameter*
      transformer_001/ rgt_001/ tpr_001/           # neural, one dir each,
      hrr_001/ ndr_001/ gru_001/                   #   named for what it registers
      ngram_001/ syllogism_001/ symbolalg_001/     # rule-based, one dir each,
      synth_001/ ruleinduce_001/ evidence_001/     #   carrying the ported source
    tasks/
      base.py             # Task protocol, floors, lift
      lm.py               # next-token
      masked_node.py      # masked node: type head + label head
    prefix.py             # ids -> one Graph per *prefix*: the parser seam, the
                          #   prefix-restricted oracle, and its leak audit
    train.py              # data, tasks, budget -> model.fit(); no learning here
    decode.py             # sampling, for reading; feeds no metric
    agent.py              # trained model -> multiple-choice answerer
    report.py cli.py
  symbolic_ai_parsers/    # text -> Graph, the inverse of the generator
    scoring.py floors.py  #   ten metrics, each with its own fitted floor
    treebank.py grammar.py#   spans recovered from the corpus; induced productions
    align.py              #   content alignment (a tree alignment cannot score
                          #   attachment -- it scored 0.95 for a non-parser)
    parsers/              #   one directory per registered row, version and all
      bracket_001/ prior_001/ retrieve_001/
      template_001/ template_002/ template_lex/ template_seeded/
      cky_001/ lr_001/ shiftreduce_001/   # chart, SLR(1), learned oracle
  symbolic_ai_agents/     # the interactive half: what happens when errors stay
    envs/                 #   choice, retry, repair, probe
    agents/               #   random, shortcut, context (floors); recall, careful
    train.py trace.py     #   rollouts; trajectories, for reading, not a metric
  notes/                  # the lab notebook; one file per note (worktrees merge)
    questions/            #   the parking lot: ideas, whether or not chased
    findings/ decisions/
  scripts/
    qualitative-sample.sh # decode every run; transcripts + JSON for a reviewer
  tests/
```

`APPROACH.md` says what the whole thing is *for* and why it is a portfolio rather
than a bet; `RESEARCH_LOG.md` says what is known.

## What the models are actually good at

**Read this before the numbers below it.** Every result in earlier versions of
this README was measured on six lessons out of 179, chosen early and never
revisited. Run on the whole curriculum, the central claim reverses.

Masked-node task, all 179 generatable lessons, 20 training episodes each,
evaluation seeds a million away, CPU:

```
model          family        params  lbl acc lbl lift typ lift    copy  rename
corefer        rule-based     4,115    0.357   +0.250   +0.612  +0.096  -0.003
workspace      rule-based    10,472    0.357   +0.249   -0.576       -  -0.130
omegaclaw_rank rule-based       872    0.356   +0.248   -0.016       -  -0.017
omegaclaw_ctx  rule-based       872    0.344   +0.234   -0.071       -  -0.018
analogy        rule-based     6,000    0.334   +0.222   -0.351       -  -0.019
ruleinduce     rule-based        80    0.329   +0.217   -0.377  +0.032  -0.027
routes         rule-based       599    0.324   +0.210   -1.152  +0.051  -0.000
ilp            rule-based        73    0.312   +0.198   -1.037       -  -0.021
brill          rule-based     1,200    0.290   +0.172   -0.026       -  -0.130
rgt            neural     1,125,053    0.241   +0.115   +0.395       -       -  *
omegaclaw_flat rule-based       872    0.234   +0.106   -0.282       -  -0.030
evidence       rule-based     5,819    0.219   +0.089   -1.152  +0.023  -0.003
grammar        rule-based    65,125    0.187   +0.051   -0.442       -  -0.159
gru            neural       995,537    0.176   +0.038   -0.390       -       -  *
ngram          rule-based   358,167    0.170   +0.031   -1.029       -  -0.143
symbolalg      rule-based   157,793    0.149   +0.007   -1.152       -  -0.041
syllogism      rule-based        26    0.146   +0.003   -1.486       -  -0.024
tpr            neural     1,159,085    0.145   +0.002   -0.505       -       -  *
transformer    neural     1,089,917    0.145   +0.002   -0.582       -       -  *
ctw            rule-based   819,990    0.109   -0.040   -0.291       -  -0.088
synth          rule-based         6    0.077   -0.077   -3.326       -       -
hrr            neural     1,272,305    0.057   -0.100   -0.959       -       -  *
ndr            neural       939,893    0.048   -0.112   -1.070       -       -  *
```

**Rename every symbol and the table reorders.** Models are fitted on the
original episodes and scored on episodes where every symbol has been permuted, so
a model reading structure keeps its accuracy and a model reading vocabulary loses
it. 2,105 symbols permuted:

| model | original | renamed | change |
|---|---:|---:|---:|
| `corefer` | 0.353 | **0.350** | **-0.003** |
| `omegaclaw_rank` | 0.352 | 0.335 | -0.017 |
| `ilp` | 0.313 | 0.291 | -0.021 |
| `workspace` | 0.352 | 0.221 | **-0.130** |

`corefer` and `workspace` are tied on the headline table and are not close here:
one is equivariant to three decimal places, the other loses 37% of its accuracy.

Worse, and this is a caveat on a change made deliberately: raising `workspace`'s
example cap lifted its original accuracy 0.273 -> 0.352 and its renamed accuracy
only 0.214 -> 0.221. **About 91% of what the extra data bought is symbol
memorisation that a renaming erases.** The cap is still set from runtime rather
than from either number — choosing it by robustness would be as much a
post-hoc choice as choosing it by accuracy — but the headline gain should be read
as mostly vocabulary, not mostly reasoning.

Memorising is not cheating here: the curriculum draws from a fixed symbol pool,
100% of scored labels recur in training, and the floor memorises too. It is
simply a different capability from the one this repo is trying to measure, and
the two are only distinguishable by testing.

`copy lift` is the pointer head, over the structure-only floor of 0.266; a dash
means the model states no bindings and is not scored on copying. `lbl cov` is
0.82 for every row and is dropped from the table for space. Rows marked `*` are
the neural control, whose lift is recomputed from its stored accuracy against
the current floor rather than re-run — accuracy does not depend on the floor, so
that is exact, not an estimate.

**All lifts here are against the strengthened floor** (label 0.143, type 0.860),
which replaced a four-feature lookup that a counting model beat by 15 points.
Every published number in this repo before that change was measured against a
floor 0.065 too low on type and 0.038 too low on labels. Two claims did not
survive it:

- **"Every rule-based model clears the label floor" is no longer true.** `ctw`
  (-0.040) and `synth` (-0.077) fall below it. Fifteen of seventeen still clear
  it.
- **The type column is almost entirely negative.** Against the old floor eight
  models were positive on type; against this one, two are: `corefer` at +0.612
  and `rgt` at +0.395. `omegaclaw_rank` goes +0.308 -> **-0.016** and `brill`
  +0.295 -> **-0.034**. Neither model changed. What changed is that a
  content-blind lookup now does what they were being credited for.

  That is the real result about node type on this curriculum: it is almost
  entirely determined by tree shape, and nearly every model that looked good at
  it was reproducing a lookup table. The two exceptions read something else —
  `corefer` a learned binding, `rgt` a learned attention over typed edges.

- **Fifteen of seventeen rule-based models clear the label floor.** On the
  six-lesson slice not
  one of them did, and this README said so repeatedly. The claim was an artifact
  of which lessons were picked.
- **The ranking reverses too, not just the level.** `ruleinduce` was *last* on
  the slice at −0.206 lift and is second here at +0.250. A comparison drawn from
  3% of a curriculum ranked the models close to backwards.
- **The compact models win — on accuracy.** The top four carry 74 to 6,000
  discrete parameters; the bottom three carry 158k to 820k. `ctw`, the largest,
  is last. Whatever is working here is not memorisation of contexts.

  **That claim inverts on bits, and this table is an accuracy table.** See the
  next section: `label_bits` has been recorded in every run from the beginning
  and was never compared, and by it the 65k-parameter `grammar` is first and
  `corefer` sixth. The sentence above is true and it is not the whole truth,
  which is the sharpest example of the general point that a ranking is a
  property of a metric.
- **Type and label come apart.** `brill` is fifth on labels and first on types;
  `ilp` is fourth on labels and last but one on types. Averaging them would
  describe neither, which is why they are never averaged here.

### The ranking depends on which column you read

Every number above is an accuracy. Cross-entropy is in every `summary.json` too,
and had no lift attached to it, so it was never in a table. It is now, and it
does not agree:

| model | lbl acc | rank | lbl bits | rank |
|---|---:|---:|---:|---:|
| `grammar` | 0.187 | 14 | **6.09** | **1** |
| `ngram` | 0.170 | 17 | 6.41 | 4 |
| `corefer` | **0.357** | **1** | 6.95 | 6 |
| `omegaclaw_rank` | 0.356 | 2 | 8.09 | 11 |
| `brill` | 0.244 | 10 | 9.08 | 19 |

The cause is the shared mixture, `p = (1-c)·backoff + c·votes`. A model that
knows the answer is one of ten and nothing more has argmax accuracy 0.1 — and
`c` was fitted *as* an argmax accuracy, so it kept a tenth of the mass and
handed the rest back to a unigram. "It is one of these ten" is worth about 3.3
bits against 8,192 symbols and the interface priced it at nothing. Deciding well
and estimating well were made to pull against each other by the contract, not by
the reasoning.

`compare` now prints both columns. Neither is the real one — and the split is
partly a *symbolic-versus-statistical* one, which is the uncomfortable half.
The models at the top of the bits ranking, `grammar` and `ngram`, are the two
that lose most under renaming; the models at the top of the accuracy ranking are
the pointer-valued ones that lose nothing. Cross-entropy rewards knowing which
symbols are common, and this curriculum re-randomises which symbol fills which
slot every episode.

That is not a reason to go back to quoting accuracy alone. `ptrgen` reaches
**5.91 bits while dropping 0.002 under renaming**, beating `grammar`'s 6.09 at
0.282 — so better density estimation is available without memorising. It is a
reason to read the bits column next to the renaming column, always.

### The models that came out of noticing that

Same harness, same floors, all 179 lessons, `runs/ptrgen`:

```
model                   params  lbl acc  lbl lift   bits  bits lift  typ lift  copy lift
corefer-001               4115    0.357    +0.250   6.95     +0.258    +0.612     +0.096
omegaclaw_em-001           872    0.349    +0.240   7.85     +0.162    -0.091          -
omegaclaw_ctx-001          872    0.344    +0.234   7.87     +0.160    -0.071          -
ptrgen_joint-001          3696    0.340    +0.230   5.87     +0.374    +0.681     +0.078
ensemble-pointers         7812    0.340    +0.230   5.91     +0.370    +0.668     +0.078
omegaclaw_reach-001       1310    0.337    +0.226   7.72     +0.176    -0.093          -
ptrgen-001                3696    0.336    +0.225   5.91     +0.369    +0.565     +0.078
ensemble-001             68822    0.336    +0.225   4.77     +0.491    +0.545     +0.078
ptrgen-argmax             3696    0.321    +0.208   6.49     +0.307    +0.565     +0.078
```

- **`ptrgen`** states copying and generating as one distribution —
  `p(v) = g·Σ_{j: label(j)=v} p(j) + (1-g)·backoff` — with `g` fitted by
  maximising held-out likelihood rather than inferred from an argmax accuracy,
  and a pointer trained on the marginal likelihood of landing on *any* correct
  antecedent. `ptrgen-argmax` is the same model with the old gate: the pair
  isolates the calibrator at **+0.017 lift and 0.58 bits**.
- **`ensemble-001`** is `ptrgen × grammar` as a geometric mixture, the pair
  chosen on the renaming column rather than the leaderboard. At **4.77 bits** it
  is the best in the repo by a wide margin, gains no accuracy at all, and
  **is not a symbolic model**: permute every symbol without refitting and it
  falls 0.467 → 0.038, the largest drop ever measured here. The whole 1.14-bit
  gain over `ptrgen` alone is vocabulary memorisation. `ensemble-pointers`, two
  pointers over identical features, keeps the equivariance (-0.004) and gains
  **exactly zero** bits. Diversity is what an ensemble buys and the only
  diversity available here is structure-versus-memorisation, so on this task
  **bits and equivariance are in tension.** Read it as a measurement of the
  metric, not as a model worth using.
- **`omegaclaw_em`** fits claw reliabilities by EM instead of hard counting, so
  four claws that agree stop recording four independent solutions to one
  problem. Worth +0.006 lift, and it re-ranks the claws hard: `prev` falls from
  first to sixth.
- **`omegaclaw_reach`** adds the typed, slot-selected sibling that `ilp`'s
  first-order search turns out to find and `CLAWS` cannot express. It is the
  most reliable single claw in the set (0.803, against `peer`'s 0.163) and the
  model still **loses** to `omegaclaw_ctx`. Reach was never the constraint.
- **`ptrgen_joint`** decodes masked nodes in confidence order, committing the
  surest and re-reading the graph — the teacher-forcing boundary closed on the
  prediction side. It helps `ptrgen` (type +0.565 → **+0.681**) and does nothing
  for `omegaclaw`, which is the opposite of the prediction; the gain is extra
  candidates, not sequential conditioning.

`RESEARCH_LOG.md` has the pre-registered refutation criteria and what each one
actually did.

### Is the text surface a parsing failure or a reasoning failure? — `gparse-003`

All 179 lessons, `configs/full179.toml`, `runs/full179-gparse`. One reasoner,
five readers, plus one declared ablation of the reasoner. `answer_*` only: every
`gparse` row abstains outside the answer span by construction, so its
`token_lift` sits at −0.001 to −0.007 and says nothing.

```
row               reader                    params   ans acc  ans lift   ans bits  bits lift
gparse-oracle     oracle -- CEILING           4740     0.387    +0.349      7.169     +0.098
gparse-retrieve   retrieve-001             1838708     0.322    +0.281      7.804     +0.019
gparse-003        template-002              112277     0.305    +0.263      7.985     -0.004
gparse-nolex      oracle, symbol-free          148     0.299    +0.256      8.081     -0.016
ngram-001         (no parser; counts)       358019     0.143    +0.090      6.137     +0.228
ctw-001           (no parser; CTW mixture)  819616     0.047    -0.012      8.646     -0.087
gparse-flat       prefix words, no structure    55     0.030    -0.030     10.368     -0.304
gparse-none       nothing                        1     0.000    -0.062     10.608     -0.334
```

- **Structure is the difference between working and not.** The same reasoner on
  the prefix's *words* scores 0.030 — below its own floor — and on any
  structured parse 0.30–0.39.
- **A perfect parse leaves most of the task undone.** At most 84.5% of eval
  answers can be produced by pointing at a node at all, so even where the right
  node exists the ceiling picks it under half the time. **The bottleneck this
  finds is node selection, not parsing** — the opposite of what motivated
  building the oracle.
- **The best "parser" does no parsing.** `retrieve-001` hands back the nearest
  *training* graph verbatim and is indistinguishable from `template-002`
  (0.017, ≈1 SE at n=1,346). Whatever the parser column buys is recognition of
  the lesson template. The audit agrees from the other side: 47% of the nodes
  `retrieve-001` emits, and 37% of `template-002`'s, name symbols absent from
  the document.
- **A quarter of the ceiling is vocabulary.** Two of the ten node features read
  a symbol — the parent's and grandparent's labels. Drop them (`gparse-nolex`,
  exactly renaming-invariant) and the ceiling falls 0.387 → 0.299, a drop the
  size of the whole oracle-versus-real-parser gap, landing *level with*
  `template-002`. The renaming-invariant ceiling is worth no more than what a
  real parser already delivers by reading words.
- **And 148 symbol-free features get within 0.006 of a 112k-parameter
  parser-plus-model** and within 0.023 of a 1.8M-parameter memoriser.
- **The metrics disagree, again.** By `answer_acc` the ceiling leads. By
  `answer_bits` **`ngram-001` is the best row in the table** (6.14 against the
  ceiling's 7.17) and `template-002` sits exactly at the floor. `gparse`
  decides; `ngram` estimates. `token_*` settles what `gparse` is not: `ngram`
  scores 0.580 / 3.21 bits against `gparse`'s 0.05 / 8.47. **`gparse` is not a
  language model** — it is an answer predictor sharing the LM head, and it does
  nothing about prose. `ctw-001` is the same trap from the other end: `token_lift`
  **+0.280** and `answer_lift` **−0.012**, below the floor on the 1.4% of
  positions that carry the reasoning while looking respectable on the rest.

`notes/findings/2026-08-13-a-perfect-parser-does-not-rescue-the-text-surface.md`
carries the refutation conditions, the uncontrolled confound (the readers do not
present equal numbers of candidates) and the caveats.

### Does an ABC make new symbolic models cheap? — `omegaclaw`

`symbolic_ai_models/models/omegaclaw/` is a base class rather than a model: it
fixes the skeleton six of the reasoners above share — reach into a few
structurally-defined places, decide what each is worth here, commit — and leaves
subclasses one method, `weigh`. Three of them are registered, differing only in
that method (`omegaclaw_flat`, `omegaclaw_ctx`) and in aggregation
(`omegaclaw_rank`).

Twelve lessons, taken as every fifteenth lesson id so the slice could not be
chosen to flatter anything; 50 train / 10 eval episodes each; `runs/omegaclaw`:

```
model            params   lbl acc  lbl lift   typ lift
omegaclaw_ctx       749     0.418    +0.245     +0.048
omegaclaw_rank      749     0.409    +0.233     +0.041
workspace           720     0.398    +0.219     -1.086
routes              320     0.388    +0.206     -0.823
ilp                  66     0.387    +0.205     -0.526
brill               179     0.384    +0.201     -0.289
ruleinduce           82     0.377    +0.192     +0.311
omegaclaw_flat      749     0.335    +0.138     -0.060
```

- **Cheap, measurably.** A new member is 10 lines of code against 186–293 for
  the standalone models it is being compared with, and it arrives with masked
  training views, held-out calibration, a proper distribution and the abstention
  contract already correct.
- **Control beats reach.** `flat` and `ctx` run the same eleven operators over
  the same evidence and differ in one line; learning which to trust in which
  context is worth **+0.107 lift**. Mixing versus committing to the single best
  operator is worth +0.012, which on twelve lessons is not a difference.
- **The abstraction's own failure mode, measured.** The first sweep scored the
  family at −1.96 to −0.78 type lift, because one shared convenience method
  priced the type head with the label head's confidence. One mistake in the base
  class was three models wrong at once — the cost of sharing, and the mirror
  image of the benefit. Repaired by giving the type head its own calibrator
  (fitted on training episodes; the label numbers are unchanged to three
  decimals) and written up in `OmegaClaw._type_votes`.
- **Read the ranking with the caution this README earned above.** Twelve lessons
  is 7% of the curriculum, and 3% of it once ranked these models backwards. The
  within-family contrasts are what this table supports.

**What is not established: the family comparison.** Earlier versions of this
README said all neural models were above the label floor and no rule-based model
was. The second half is now known to be wrong. The first half is *not* retested
here, and the one attempt at it does not count:

```
gru          neural  995,537   0.061    -0.050    (300 steps ~ 1.3 passes)
```

That is below the floor, and it would be cheap and wrong to report it as the
separation inverting. The neural models were given 300 steps at batch 16 against
3,580 training episodes — barely more than one pass. It is an undertrained
model, not a beaten one.

**Earlier versions of this paragraph finished "…while every rule-based model
sees the training set in full". That is false**, and it was the load-bearing
half of the fairness argument. Those 3,580 episodes yield about **130,800**
masked-node training examples, and five rule-based models cap how many they
learn from:

| model | cap | share of available |
|---|---:|---:|
| `ilp` | 1,500 | **1.1%** |
| `brill` | 3,000 | 2.3% |
| `ruleinduce` | 4,000 | 3.1% |
| `workspace` | 4,000 | 3.1% |
| `analogy` | `max_cases` | varies |

The caps stride rather than truncate, so the sample is spread across the
curriculum instead of stopping at the early lessons — that bug was found and
fixed earlier. But `ilp` reaching fourth place on 1.1% of the data is a
different and more interesting claim than the one this README was making, and
it means the budget asymmetry ran in *both* directions at once. They are
defaults in `extra`, not constants; nobody has measured what these models do
when raised.

**Four networks were re-run at 2000 steps. All four clear the label floor;
none had converged.**

| model | 300 steps | 2000 steps | gain over last 500 | type lift | train time |
|---|---:|---:|---:|---:|---:|
| `rgt` | -0.058 | **+0.152** | +0.019 | **+0.587** | 11 min |
| `gru` | -0.050 | **+0.079** | +0.030 | +0.052 | 60 min |
| `tpr` | -0.048 | **+0.045** | +0.022 | -0.026 | 47 min |
| `transformer` | -0.065 | **+0.044** | +0.015 | -0.079 | 9 min |

`hrr` and `ndr` were **deliberately not re-run** and their rows are still
300-step runs. Four architectures spanning recurrence, attention, the relation
algebra and the role algebra were enough to answer the question the re-run
existed for, and the symbolic models are what this repo is about. `compare`
flags the mixed budget rather than hiding it.

The 300-step figures were artefacts of the budget. Nothing that rested on them
survives, in either direction — including any reading of the rule-based models
as beating the neural half.

**`rgt` is first of nineteen on node type, by a factor of two.** Its +0.587
against `brill`'s +0.295 is the largest margin anywhere in this table, and it is
the one architecture here built to read the relation algebra rather than a
linearisation — it aggregates over parent/child/sibling/ancestor edges directly.
The structure-aware model being the one that predicts structure is the least
surprising result in the repo and the first time it has actually been measured.
On *labels* it is seventh at +0.152, below `analogy`, `ruleinduce`, `routes`,
`ilp`, `workspace` and a hair under `brill`.

These are **lower bounds, not converged scores** — all three were still gaining
more than +0.01 over their last 500 steps when the budget ran out, though
`transformer` is decelerating hard (+0.0096 then +0.0049 over its last two
intervals) where `gru` was not.

The heads come apart by architecture, sharply. On identical data and budget the
type lift runs `rgt` +0.587, `gru` +0.052, `tpr` -0.026, `transformer` -0.079 —
and note that `tpr` carries an explicit role algebra too, so reading the graph
is not by itself what `rgt` is being paid for. Averaging the
two heads would erase exactly this, which is why they are never averaged here.

The cost is also wildly uneven: 9, 11 and 60 minutes for models within 15% on
parameter count. A recurrence cannot be parallelised over the sequence and an
attention stack can, and on a CPU that dominates everything else.

`hrr` and `ndr` are still at 300 steps and **must not be read as results**.
`compare` says so itself, and refusing to read those rows is the whole point of
the warning:

```
!! these rows were NOT produced under one config, so the comparison is not like-for-like:
  steps: 2000=gru, rgt, tpr, transformer; 300=hrr, ndr
```

**The rest of the comparison is still running**, at 2000 steps (8.9 passes) on CPU — it
did not need a GPU, only the patience to let it finish, and `train --resume` so
an interrupted run resumes instead of restarting. One model takes about an hour.

The interpretation of each endpoint was written into `ROADMAP.md` before the
numbers arrived, deliberately: an earlier reading of this same curve as "flat"
was wrong in the direction that flattered the write-up. Numbers here are
replaced as each model completes, not before.

## Notes

- `synth` is by far the slowest model here — it enumerates programs at every
  position it has not already explained. Its budget (`max_size`, `max_refits`,
  `window`) is in `extra`; lower it if a sweep is dragging.
- `tpr` and `hrr` sum over edge types, so they cost roughly `N_RELATIONS` times a transformer's aggregation. That's the price of an explicit role algebra; it's stated here so nobody has to discover it from a training curve.
- Episodes render in any language `langcurriculum` supports (`--language
  chinese`), and the graph is byte-identical across all of them — which makes a
  cross-language *node* experiment vacuous rather than probing, since the model
  is handed the same graphs it trained on. This README previously offered
  train-on-one-evaluate-on-another as a structure-versus-surface probe; on the
  node task it is not one, and `tests/test_language.py` pins the property so
  nobody builds on the misreading.

  On the text surface it is a real question, and measured, nothing transfers.
  An English-fitted model spends 1.4 bits/token on English and **23.5 on
  Chinese** — the byte fallback keeps encoding lossless but not affordable.
  Choice accuracy sits below floor in *all three* languages including English,
  so there is no transfer to measure yet: you cannot lose what you never had.
- The one lesson of the 180 that the curriculum's author declined to grade is excluded rather than left to fail a run halfway through.
