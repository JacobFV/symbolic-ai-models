# symbolic-ai-models

**Train and evaluate symbolic text model architectures on one harness: predict the next token, and predict a masked node in the graph.**

The premise is that these are the same question asked of two surfaces. [`langcurriculum`](https://jacobfv.github.io/formal-language-cirriculum/) builds every episode as a **typed term** and only then renders it as prose, so for each episode there is a graph that is not a parse of the text but the thing the text was generated *from*. That gives a rare pairing: running text and exact structure, describing the same world, generated from the same seed, in unbounded quantity.

So every model here is asked both:

- **next-token prediction** over the episode as it is rendered;
- **masked-node prediction** over the term graph it was rendered from — hide a node, name its type and its label from the neighbourhood.

Both predict a hidden symbol out of **one shared vocabulary**, through **one shared output head**. That is what makes it meaningful to ask whether training on structure helps the text, whether an architecture that is good at one is good at the other, and whether a model that scores well on prose has internalised anything a term tree would recognise.

```bash
uv sync
uv run symbolic-ai-models models                       # 12 architectures, two families
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

**Neural** — trained by gradient descent, GPU:

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

Type and label are reported separately and never averaged. Type is the structural question (what kind of thing sits here); label is the symbolic one (*which* predicate, *which* variable), and it is the hard one, because the curriculum invents its vocabulary per episode — the answer is very often a name the model has never seen and can only get from how the node sits among its neighbours.

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
    full.toml             # all 179 lessons
  symbolic_ai_models/
    data/
      curriculum.py       # langcurriculum -> Episode (text + graph, one seed)
      graph.py            # term JSON -> flat node array + parent pointer
      tokenizer.py        # one vocabulary, byte fallback, lossless
      batch.py            # SymbolicBatch + the relation algebra  <- the harness
    models/
      base.py             # Model (the interface) + NeuralModel (embeddings, heads)
      symbolic.py         # RuleBasedModel: votes -> distribution, redacted views
      registry.py
      transformer/ rgt/ tpr/ hrr/ ndr/ gru/        # neural, one dir each
      ngram/ syllogism/ symbolalg/ synth/          # rule-based, one dir each,
      ruleinduce/ evidence/                        #   carrying the ported source
    tasks/
      base.py             # Task protocol, floors, lift
      lm.py               # next-token
      masked_node.py      # masked node: type head + label head
    train.py              # data, tasks, budget -> model.fit(); no learning here
    decode.py             # sampling, for reading; feeds no metric
    agent.py              # trained model -> multiple-choice answerer
    report.py cli.py
  scripts/
    qualitative-sample.sh # decode every run; transcripts + JSON for a reviewer
  tests/
```

## What the two families are actually good at

From the smoke sweep (six lessons, 400 steps, tiny models — a wiring check, not
a result), three things are worth knowing before running anything big:

- **Nothing has learned to answer, and the old metric hid it completely.**
  Every network holds `token_lift` between 0.65 and 0.73 while scoring
  **negative** `answer_lift`; `ngram` reaches `token_lift` 0.77 on
  `answer_lift` 0.05. They reproduce the scaffolding and know essentially
  nothing. This is the single best argument for reading `answer_*`.
- **Most of a symbolic score can be memorisation, and only a renaming test
  finds it.** `analogy` was the best label predictor here — 0.463 accuracy,
  0.208 lift, beating every network — and this README said so. Then every
  symbol in the evaluation episodes was permuted: its accuracy fell to 0.036
  while `evidence` and `ilp` lost nothing. Its retrieval and alignment were
  always structural, but its *readout* returned the symbol remembered from the
  training case whenever no structural route applied.

  Fixed, it transfers a **route** — "the answer stood at my slot-0 sibling" —
  rather than a name, and is now exactly equivariant: 0.173 both before and
  after renaming. In the full sweep it scores **0.186 label accuracy, −0.200
  lift**: below the floor, where it had appeared to be the best thing in the
  repo. The honest ordering puts `hrr` first at 0.420 / 0.144.

  The general lesson is the uncomfortable one: on a curriculum that reinvents
  its vocabulary every episode, a method can look structural, *be* structural in
  its retrieval, and still have most of its score riding on remembered symbols.
  Accuracy alone cannot tell you; renaming can.
- **Induced rules beat networks on structure.** `ruleinduce` reaches 0.996
  node-type accuracy — 0.898 lift — on ~75 discrete parameters, against 1.78M
  for the best network, and the model is fourteen readable rules.
- **Counting and mixing are competitive language models.** `ctw` reaches 1.694
  bits/token against the best network's 1.722, on ~19k counts versus 495k
  weights — and `ngram` beats them both. On this data the neural models are not
  yet earning their parameters at the token level.
- **An induced grammar is the most parameter-efficient thing here.** `grammar`
  reaches 1.118 bits/token on **945** discrete parameters, against 1.722 on
  495k for the best network. It gets there by recovering the generator's own
  hidden categories from distribution alone — nothing was written down:

  ```
  { ' watched', ' avoided', ' praised', ' followed', ' chased', ' greeted' }
  { ' purple', ' green', ' blue', ' red', ' yellow', ' orange' }
  { ' prism', ' sphere', ' cone', ' cube', ' rod', ' disc' }
  ```

- **The workspace engine infers what it is being asked.** On `unification` it
  discovers unprompted that `fact` and `pattern` are structurally parallel
  regions and learns that mirroring between them is the strategy — arriving at
  the content of the lesson without the word appearing anywhere:

  ```
  ('fact',    field, slot=0, par=True, peer=False, n=3) -> mirror:0.89   [61x]
  ('pattern', field, slot=0, par=True, peer=False, n=3) -> mirror:0.86   [59x]
  ```

  Its accuracy is mid-pack; the artifact is the policy table, which is a
  readable account of how it decided to carve up the task.
- **The masked-node floor is brutal, and rightly so.** A structure-only lookup
  table scores 0.96 on types, and most models — both families — sit below it
  after a short run. Negative lift is the report working.

`synth` is bimodal by construction: strong where a short program generates the
sequence, useless on prose. Averaging those halves tells you nothing, so read
`symbolic-ai-models eval <run> --curriculum` per lesson.

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
