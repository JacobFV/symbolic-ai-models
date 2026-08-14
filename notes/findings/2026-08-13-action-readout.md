---
date: 2026-08-13
author: agent-action-readout
status: provisional
related: [2026-08-13-readout-is-a-knob]
---

# The third readout: the same graph emission, read as an action

**Slice warning, first sentence as the rules require:** every number below comes
from `configs/agents-small.toml` — six lessons, 64 training and 16 evaluation
episodes per lesson, `vocab_size=2048`, `max_nodes=128`. That is 3% of the
curriculum and the README already records a six-lesson slice ranking this repo's
models close to backwards against the full 179. **Nothing here is a ranking of
models.** It is a measurement of whether a readout *can* rank them differently,
run at the size that fits in the time available.

## What was built

`symbolic_ai_agents/readouts/action.py` registers `action-001` in the shared
`symbolic_ai_core.readout` registry. It turns a `RuleBasedModel`'s graph-valued
emission — `node_votes(view)` and `source_votes(view)` — into a `Preference`
over an `Observation`'s legal action strings. `symbolic_ai_agents/agents/graphread`
is the agent that acts through it, registered beside `wrap` rather than in place
of it.

The channel is a knob (`extra.channel` ∈ `symbol` | `node` | `both`), which is
the entire point: two rows differing only in the channel measure the readout,
not the models.

## Hypothesis, written before any number landed

Stated in advance so the reading cannot drift toward whatever the table says.

1. **`graphread` on `choice` IS the prior.** `choice` carries no graph, so
   `graphread` abstains at 100% there by construction and lands exactly on the
   shared prior. Its `choice` row is therefore not a score of anything. If it
   ever differs from a mute agent's `choice` row, the abstention path is broken.
2. **`graphread` beats `wrap` on `repair`.** `wrap` reads the rendered
   s-expression as text and is truncated to `max_actions=8` of `repair`'s 24
   candidates; `graphread` reads the graph head the model was actually fitted
   for and sees all 24. I expect a clear gap on `repair` `label_acc`.
   *Refuted if* `graphread` is at or below `wrap` on `repair` — which would say
   the graph head carries less about the answer than the text rendering does,
   and would be a much more interesting result than the one I expect.
3. **The channel knob moves things more than the model choice does.** The
   repo's standing lesson is that harness decisions span 0.15–2.0 and models
   span ~0.1. *Refuted if* the `symbol`/`node`/`both` spread on one model is
   smaller than the model spread within one channel.
4. **The question the exercise is for — does the action readout rank models the
   same way the symbol readout does?** My prediction is: **the `symbol` channel
   agrees, the `node` channel disagrees.** The `symbol` channel reads the same
   `node_votes` the vocabulary readout reads, merely restricted to a 24-way
   legal set, so agreement there would be unsurprising. The `node` channel reads
   `source_votes` — a head that only eight of the registry emit and that
   `label_acc` never sees — so a model whose vocabulary head is weak and whose
   pointer head is strong (`ptrgen-001` is exactly that shape) should climb.
   *The design in `notes/decisions/2026-08-13-readout-is-a-knob.md` is refuted
   if both channels rank the models the same way the symbol readout does*: then
   reading the graph as an action bought nothing and the agent-side pressure was
   not pressure.

## The floor

`reference_floor` from `symbolic_ai_agents/envs/base.py`, reused rather than
re-derived — the best of `random`, `shortcut` and `context`, **fitted on the
training episodes and run in the environment**, with `floor_by` naming the
winner. The readout's own `floor()` calls the same function and namespaces the
result under `action_*`; there is deliberately no second floor for the readout,
because a near-copy of a floor is how a lift over a baseline 0.065 too low got
published here once already.

## Results

All rows: `symbolic-ai-agents run --config configs/agents-small.toml --envs
choice,repair`, 96 evaluation episodes (seeds from 1,000,000), **116 scored
fills** on `repair`. The symbol/node readout columns are
`symbolic-ai-models sweep --config configs/small.toml --tasks node --n-train 64
--n-eval 16` — the same six lessons and the same per-lesson episode counts, so
the two harnesses are looking at the same world.

`repair` `label_acc` (per filled node). Floor **0.3966**, `floor_by: context`.
`choice` return floor 0.3958, `floor_by: random`.

| model | `wrap` (text) | `graphread` sym | node | both | coverage sym | symbol readout | node readout |
|---|---|---|---|---|---|---|---|
| ensemble-001 | 0.0259 | **0.5172** | 0.3534 | 0.4914 | 100% | 0.3279 | 0.2531 |
| corefer-001 | 0.0259 | **0.4052** | 0.4052 | 0.4052 | 100% | 0.2623 | 0.2612 |
| routes-001 | 0.0259 | 0.3879 | 0.3879 | 0.3879 | 90% | 0.1885 | 0.2041 |
| brill-001 | 0.0259 | 0.3793 | – | – | 52% | 0.2664 | – |
| ngram-001 | 0.0086 | 0.3621 | 0.0431 | – | 90% | 0.2500 | – |
| omegaclaw_ctx-001 | 0.0259 | 0.3621 | – | – | 100% | 0.2869 | – |
| ptrgen-001 | 0.0259 | 0.3103 | 0.3534 | 0.3448 | 100% | **0.3484** | 0.2531 |
| ilp-001 | 0.0259 | 0.2931 | – | – | 47% | 0.2582 | – |
| evidence-001 | 0.0259 | 0.2241 | 0.2241 | 0.2241 | 100% | 0.1967 | 0.2327 |
| analogy-001 | 0.0259 | 0.1983 | – | – | 84% | 0.2869 | – |
| vsa-002 | 0.0259 | 0.1552 | 0.1466 | 0.1552 | 100% | 0.2623 | 0.0735 |
| ruleinduce-001 | 0.0603 | 0.0690 | 0.0690 | 0.0690 | 82% | 0.2049 | 0.1347 |
| synth-001 | *(a)* | **0.0431** | – | – | **0%** | 0.2500 | – |
| gparse-003 | – | **0.0431** | – | – | **0%** | – | – |

*(a)* `wrap` on `synth-001` was killed at 50 minutes without finishing. One
forward pass per candidate per decision, with a program synthesiser behind it,
is not a thing this slice can afford — which is itself the cost side of the text
reading. `graphread` finished the same model in 82 seconds.

Coverage is `spoke / fills`, read off `policy.txt`. Every `choice` decision is an
abstention for every `graphread` row, so it is excluded from the rate.

### The controls

| row | `repair` label_acc |
|---|---|
| `graphread`, `gparse-003` — emits no `node_votes` at all | **0.0431** |
| `graphread`, `ngram-001`, `channel=node` — has no `source_votes` | **0.0431** |
| `random` (uniform, `use_prior=False`) | 0.1034 |
| `shortcut` | 0.1638 |
| `context` — **this is the floor** | 0.3966 |

Two abstain-everywhere rows agreeing to the last digit by two different routes is
the control working: the abstention path depends on the shared prior and on
nothing about the model that failed to speak. It also produced a second finding
big enough to need its own note — **abstaining on `repair` scores 0.0431, which
is below chance (0.1034) and 0.35 below the floor it is quoted against** — see
`notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md`.

## The four hypotheses, judged

**1. `choice` is the prior. Confirmed, and more than expected.** All fourteen
`graphread` rows return exactly 0.3645833 on `choice`, lift −0.0517. That row is
the shared prior and is not a score. What was *not* predicted: **every `wrap` row
returns the same 0.3645833**, so `wrap`'s `choice` column is the prior too at
this slice — the calibrated confidence on a rule-based model's text scores is low
enough that the mixture never moves the argmax. `tests/test_agent_wrap.py` pins
`wrap`'s *raw* ranking against `score_choices` and is right to; the acted column
is a different quantity and here it carries no model signal at all.

**2. `graphread` beats `wrap` on `repair`. Confirmed, 12 of 12.** The gap is not
marginal: `wrap` spans 0.0086–0.0603 across twelve architectures — a spread of
0.052 that **straddles the abstain-everywhere baseline of 0.0431** — while
`graphread` spans 0.0431–0.5172. Ten of the twelve `wrap` rows are *identical* at
0.0259. Reading these models as text on `repair` is indistinguishable from saying
nothing, and it is the same nothing for almost every model.

**3. The channel knob moves more than the model choice. Refuted, clearly.**
Models within `channel=symbol` span 0.4741. The largest within-model channel
spread is `ensemble-001` at 0.1638 (symbol 0.5172 → node 0.3534), then
`ptrgen-001` at 0.0431 (symbol 0.3103 → node **0.3534**, the pointer beating the
vocabulary head exactly as predicted), then `vsa-002` at 0.0086 — and **four of
seven are 0.0000 to four decimals** (`corefer`, `evidence`, `routes`,
`ruleinduce`). For those four the two channels are the same reading in two
coordinate systems: their label vote *is* their pointer, spelled. So the knob is
real but small for most models, and this is the first measurement in this repo
where the model spread is the larger one. (The caveat: the abstention machinery
under all of it is a ~0.35-wide harness effect, so "suspect the harness first"
survives; it is just not the *channel* that is the harness effect here.)

**4. Does the action readout rank models the way the symbol readout does?
No — and that is the design's interesting outcome, not its refutation.**

Spearman ρ over the models each pair covers:

| comparison | ρ | n |
|---|---|---|
| action[symbol] vs the symbol readout | **+0.273** | 13 |
| action[node] vs the node readout | +0.745 | 7 |
| action[symbol] vs action[node] | +0.647 | 8 |
| action[symbol] vs action[both] | +1.000 | 7 |
| symbol readout vs node readout (both in the model harness) | +0.455 | 7 |
| `wrap` vs action[symbol] | **−0.385** | 12 |

The disagreements are large and specific, not noise at the margin:

* **`ptrgen-001` is 1st of thirteen under the symbol readout (0.3484) and 7th
  under the action readout (0.3103).**
* **`routes-001` is last under the symbol readout (0.1885) and 3rd under the
  action readout (0.3879).**
* `analogy-001`: 2nd= (0.2869) → 10th (0.1983). `vsa-002`: 5th= (0.2623) → 11th.
* **`synth-001` scores 0.2500 under the symbol readout and emits nothing at all
  on the graph channel** — 0% coverage, and a `repair` number exactly equal to
  the abstain-everywhere control.

### Why they disagree, and the confound that has to be stated

The action readout on `repair` differs from the symbol readout in **four** ways
at once, not one: a 24-way answer set instead of 8,192; a trajectory instead of
teacher forcing; the agent's prior mixture; and — the one that matters —
**no shared back-off**. `RuleBasedModel._forward_graph` mixes votes against
`structural_fallback` and the context prior *before* the symbol readout ever sees
them. The action readout deliberately has none (see its module docstring), so it
reads the model and only the model.

`synth-001` is the demonstration and it is not subtle: a published symbol-readout
`label_acc` of 0.2500 for a model whose `node_votes` abstains on essentially
every decision. Its number is the shared back-off wearing the model's name. The
same is true to a lesser degree of `gparse-003`, which cannot emit on the channel
at all.

**So the honest statement of the finding is not "the action readout ranks models
differently". It is: the action readout separates *the model spoke* from *the
back-off spoke*, and the symbol readout cannot, because the back-off is inside
the number.** That is what the agent-side pressure found, and it is a fact about
the model harness rather than about the agents package.

The cleaner isolation — `symbol` versus `node` with the environment, the prior,
the calibrator and the model all held fixed — is ρ = +0.647 over eight models,
with four of them identical. The channel knob alone reorders `ensemble` and
`ptrgen` against each other and leaves everyone else where they were.

## What did not work, and what is still open

* **`both` is currently indistinguishable from `symbol`** (ρ = +1.000, n = 7).
  Summing two unit-mass distributions with the arithmetic mean of their
  confidences is a defensible default and it is not obviously the right one; on
  the four models whose channels coincide it cannot differ by construction, and
  on the two where it could, it lands between them. A confidence-weighted sum is
  the obvious next thing and it was not tried.
* **Coverage and accuracy are mixed in every number above.** `ilp-001` speaks on
  47% of fills and `ensemble-001` on 100%, and what an abstention lands on scores
  0.0431 — so part of every gap in the table is coverage rather than reasoning.
  `ActionReadout.summarize` computes exactly this split (`action_acc`,
  `action_yield`, `action_speak`) and **nothing calls it**, because the counts
  need `Environment.oracle` and that is fitting-time only. Parked in
  `notes/questions/2026-08-13-coverage-versus-accuracy-in-an-agent-column.md`.
* **The slice.** Six lessons, 116 fills. A ρ of +0.273 over thirteen models is
  not precise enough to be quoted as a correlation; what it supports is the
  *qualitative* claim that two specific models move six or nine places, and
  the `synth-001` result, which is a coverage fact and does not depend on n.

## Refutation status

`status: provisional`. Every control above was designed by the same agent that
wrote the readout, which this repo has learned is exactly when a control passes
while being hollow. The two that an independent refuter should attack first:

1. **The abstain-everywhere baseline of 0.0431.** If that is wrong, every
   coverage-weighted reading in this note is wrong with it.
2. **`synth-001` emitting nothing.** The sweep says 0% coverage and a `repair`
   number exactly equal to the abstain control; a scratch check agreed
   (`node_votes` non-empty on 1 of 9 repair decisions), but a scratch check is
   not authority here. If it is real, a published `label_acc` in this repo is a
   back-off number, and that is worth someone else's time to break.
