# Research log

Where this repo actually is, for someone arriving cold. `README.md` documents
the harness and the models; `ROADMAP.md` holds the task list and the working
rules; this file says what is *known*, what is *shaky*, and what is *wrong that
used to be believed*.

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

## Open questions

- Can anything reach the 0.722 copy ceiling? Four candidate-level features in a
  row have failed, and a discriminative re-ranker was worse than counting.
- Does a parser beat a regex? `corefer` reads prose by counting regex matches,
  and the parser layer — built, tested, scored — has never been tried inside the
  one model where prose demonstrably helps.
- What budget would settle the neural comparison? Parked; it is a control.
