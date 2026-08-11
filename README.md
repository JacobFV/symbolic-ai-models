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
    train.py              # the loop; joint losses summed, not alternated
    agent.py              # trained model -> multiple-choice answerer
    report.py cli.py
  tests/
```

## What the two families are actually good at

From the smoke sweep (six lessons, 400 steps, tiny models — a wiring check, not a
result), two things showed up that are worth knowing before you run anything big:

- **Counting is a very strong language model here.** `ngram` reached **0.89
  bits/token** where the best network managed 1.72. Curriculum prose is
  generated from templates and repeats heavily within an episode, so a
  back-off model eats it. Any claim that a network "learned the language" has
  to clear this bar first.
- **The masked-node floor is brutal, and rightly so.** A structure-only lookup
  table scores 0.96 on types, and most models — both families — sit below it
  after a short run. Negative lift is the report working.

The symbolic models are also where the *shape* of a result is legible: `synth`
is bimodal by construction, strong where a short program generates the sequence
and useless on prose, and averaging those two halves into one number tells you
nothing. Read `symbolic_ai_models eval <run> --curriculum` per lesson.

## Notes

- `synth` is by far the slowest model here — it enumerates programs at every
  position it has not already explained. Its budget (`max_size`, `max_refits`,
  `window`) is in `extra`; lower it if a sweep is dragging.
- `tpr` and `hrr` sum over edge types, so they cost roughly `N_RELATIONS` times a transformer's aggregation. That's the price of an explicit role algebra; it's stated here so nobody has to discover it from a training curve.
- Episodes render in any language `langcurriculum` supports (`--language chinese`), and the graph is identical across all of them. Training on one and evaluating on another is a structure-versus-surface probe the data supports directly.
- The one lesson of the 180 that the curriculum's author declined to grade is excluded rather than left to fail a run halfway through.
