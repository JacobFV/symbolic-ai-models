---
date: 2026-08-14
author: lead
status: provisional
related: [2026-08-13-readout-is-a-knob,
          2026-08-13-action-readout,
          2026-08-13-the-renderer-is-deterministic,
          2026-08-14-semantic-constraint-from-a-knowledge-graph]
---

# Generation is in scope, and the repo has been doing it at a 15% mask rate while calling it something else

## The reframe

The masked-node task hides 15% of a term graph's nodes and asks for each one's
label and type. **That is parse-tree infilling.** Generation is the same
operation with the mask rate turned up, and the repo already owns every piece it
needs:

- the graph is the thing the text was *generated from*, so targets are exact and
  unannotated;
- **the renderer is deterministic and tested**
  (`notes/findings/2026-08-13-the-renderer-is-deterministic.md`), so `graph ->
  text` is exact and free;
- a readout already exists as a registered, floored component, and the pointer
  channel already scores "which node says it".

So **generation reduces to graph completion followed by an exact render.** The
missing piece is not a decoder. It is that nobody has raised the mask rate.

## Why the text surface has been failing, and why that is the wrong measurement

The `lm` task asks a model to emit tokens directly, and on it: **11 of 19 models
cannot emit a single token**, all of them scoring an identical 8.51 bits and
`answer_acc` 0.000; of those that can, only the counting models are any good
(`ngram` 2.35 bits) while the reasoners sit at 7.69–7.71, "barely
distinguishable from saying nothing"; and `exact_match` is **0.000 everywhere**.

The single largest effect ever measured in this repo says that is a readout
artefact rather than a capability fact. The **same fitted `corefer-001`**, same
episodes, same floor: **0.508** read as a move, **0.085** read as text — 0.423
apart, and the text reading is statistically indistinguishable from abstaining
entirely. A model with a real internal answer scores nothing when asked to spell
it, and scores well when asked to point.

**Generation should therefore be scored on the graph and rendered, not emitted
as text.** The `lm` task becomes the *control* — the thing you compare against to
show the readout is what changed — rather than the target.

## The ladder, cheapest first

Each rung is a knob that already exists (`mask_rate`) or a small task variant,
and each is a separate registered task so no published number moves.

1. **Raise `mask_rate`: 0.15 -> 0.35 -> 0.60 -> 0.90.** A curve, not a point.
   Pre-registered expectation: pointer models degrade *fastest*, because a
   pointer's candidates are the visible nodes and masking removes them —
   `omegaclaw`'s claws already land on `None` whenever the harness hid the
   evidence and the question together. If instead they hold up, the models are
   reconstructing rather than copying, which would be the most interesting result
   available here.
2. **Mask a whole subtree, not scattered nodes.** Scattered masking leaves
   siblings visible and is a fundamentally easier problem than generating a
   constituent. This is the honest "generate a phrase" task.
3. **Mask the entire answer subtree.** This is the curriculum's own question —
   fact, pattern, query, *answer* — asked on the graph instead of the text. It is
   directly comparable to `answer_acc`, which every rule-based model currently
   scores 0.000 on, and that comparison **is** the experiment.
4. **Render and score exact-match end to end.** Free, because the renderer is
   deterministic. This is the first `exact_match` number in this repo that would
   mean anything.

## Why this needs the KG work, and where it does not

Rungs 1–3 are buildable now and need nothing new.

Rung 4 is where semantic constraint starts to matter, and the reason is sharp:
**on the current curriculum you cannot score a generated phrase as wrong.**
Colour and shape are independent draws, so "purple rod" and "red cube" are
equally licensed and a model that emits either is equally right. Generation
scored on a curriculum with no selectional constraint measures template
conformance, not understanding. See
[[2026-08-14-semantic-constraint-from-a-knowledge-graph]].

## What would refute the reframe

- **Graph-side infilling is as bad as text emission.** If completing the answer
  subtree also scores ~0, then the 0.423 readout gap was about the `repair`
  environment specifically and generation is genuinely absent rather than
  mis-measured. This is the outcome that would hurt, and it is the first thing to
  check.
- **The mask-rate curve falls off a cliff at 0.35.** Then these models are
  interpolators inside a mostly-visible graph and "generation" is not a matter of
  degree from where they are.
- **`exact_match` stays 0.000 through the render.** Then the graph was never
  right enough to be worth rendering, and partial credit has been flattering
  every number in the file.

## The alternative framing, recorded rather than chosen

**Graph-to-token**: emit a linearisation directly, a seq2seq over the term. It is
the obvious other option and is deliberately not first, because it reintroduces
the exact coupling the readout work just showed to be worth 0.423 — the model has
to spell as well as decide. Worth trying **after** the infilling ladder gives a
number to compare it against, at which point it is a clean measurement of what
spelling costs.
