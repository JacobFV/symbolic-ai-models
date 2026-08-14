---
date: 2026-08-13
author: agent-readout
status: provisional
related: [2026-08-13-site-readout-numbers]
---

# The readout becomes a knob, the way the parser did

## The fork

`symbolic_ai_parsers` made *text -> graph* a parameter, and the payoff was that
`gparse-003`'s six rows differ in one thing and are therefore a measurement of
parsing rather than a comparison of models. The mirror-image seam — *graph ->
scored prediction* — is still welded shut. There is exactly one readout in the
repo (argmax of `symbol_logits` over an 8,192-symbol vocabulary), plus a
half-generalised second one (`source_logits`, a pointer over nodes) that only
two models emit and only one metric consumes.

Three pieces of evidence say that is the wrong shape:

1. **71.9% of scored answers already sit on a visible node.** The label task is
   binding scored as classification. A vocabulary readout is the wrong codomain
   for two thirds of the questions asked.
2. **`gparse-003` abstains outside the answer span.** It is an answer predictor
   sharing an LM head, not a language model. 11 of 19 models cannot emit a token
   at all, and the harness has no way to say so except by scoring them as if
   they had tried and failed.
3. **`label_acc` and `label_bits` rank the models close to inversely.** One
   shared mixture `(1-c)*backoff + c*votes` forces *deciding* and *estimating*
   through the same parameter. Splitting **where** from **what** is the only
   structural fix; retuning the mixture is not one.

## What was chosen

**A readout is a named, registered component that turns a model's graph-valued
output into a scored prediction over a stated answer space, and it owns its own
floor.** `ModelOutput` grows a `channels` dict; `source_logits` becomes one
channel among several rather than a special case; the tasks ask the configured
readouts for counts instead of hard-coding three heads.

Three readouts, because one readout is an assumption:

| readout | channel | answer space | target |
|---|---|---|---|
| `symbol` | `symbol` | the vocabulary | `batch.target_tokens` |
| `site` | `site` | **positions of the batch** | the head a token attaches under |
| `action` | `symbol`/`node` | the environment's legal actions | the env's oracle |

### Why `site` points at *positions* and not at parse nodes

The obvious design — the model names a node of its own parse — cannot be scored,
because two parsers do not share an index space and one of them (`flat`) has no
term nodes at all. The repo already solved this for `source_logits`: **score a
pointer by what it picked, never by index** (`_pointer_counts` compares
`label_group`, not indices).

So `site` is `[B, L, L]` over the *token positions of the same batch* — "which
earlier word is the head this one attaches under" — and correctness is
**label-key equality with the true attachment site**, not index equality. That
makes it exactly the generalisation of `source_logits` (a pointer over the sites
of whatever surface the batch carries) rather than a second, parallel mechanism,
and it is scorable for any parser including none.

### Where the ground truth comes from, and why it is free

`prefix.availability` already computes, for every node of the true term, the
word index at which its label has been read. Inverting it gives *word -> the
node it realises*; walking up to the nearest already-available ancestor gives
*word -> the site it attaches under*; and the word that spelled that ancestor is
a token position. Nothing was annotated and nothing was estimated.

This is a **target**, computed task-side from `meta["graphs"]`, exactly as
`target_tokens` is. It is never handed to a model. The oracle prefix parser is
the one thing that can read the same object, which is why:

### The rejected alternatives, and why

* **A site over parse-node indices.** Rejected: not scorable across parsers, and
  it would have made the readout oracle-only, which is the failure mode the
  whole design is against.
* **A new `target_site` field on `SymbolicBatch`, filled by `collate_text`.**
  Rejected: it puts an availability computation into the hot path of every
  neural text batch for a metric most runs do not ask for, and it touches the
  collator that `test_curriculum_fingerprint.py` pins.
* **Replacing `label_acc` with the symbol readout's number.** Rejected. The
  symbol readout is required to reproduce `label_acc` *bit for bit* — that is
  the test that the refactor is behaviour-preserving — so it is added beside the
  existing counts, not in place of them. Register beside, never edit in place.
* **Unifying `FitContext` and `LearnContext`.** Rejected for now: they carry
  different fields (`tasks`/`task_weights` vs `envs`) and merging them would be
  a rename with no measurement attached. `GraphView`, `Votes`, `ABSTAIN` and
  `node_context` *are* unified into `symbolic_ai_core`, because
  `symbolic_ai_agents.envs.base` imports `GraphView` out of
  `symbolic_ai_models.models.symbolic` today, which is a package depending on
  its sibling for a pure data type.

## What would refute the design

* **`site` is not measurable above its floor by anything that is not the
  oracle.** Then the text surface carries no attachment signal a parser can
  reach, and the readout is a ceiling with no system under it.
* **The oracle row is not exactly 1.000.** Then the target and the prefix
  restriction disagree and one of them is wrong. This is asserted as a test, not
  reported as a result — a row that is 1.000 by construction is the definition
  of the target, not a finding.
* **The action readout ranks the models the same way the symbol readout does.**
  Then reading the graph as an action bought nothing and the pressure from the
  agents side was not pressure. The interesting outcome is disagreement.
* **Any readout moves a published number.** Then it is not a refactor.
  `tests/test_curriculum_fingerprint.py` at `68be4d098db17e28` and the
  reproduction of `label_acc` are the two guards.

## The leak guard

The causality test perturbs *tokens*, and the graph does not move when tokens
do, so it cannot catch a graph-side leak. The guard that works, and that every
new channel is held to: **adding graph nodes labelled with symbols the text
never contains must leave every logit bit-identical.** Kept live for `site` and
for anything else added to `channels`.
