---
date: 2026-08-13
author: agent-polyglot
status: measured
related: [2026-08-13-the-language-representation-is-orthographic]
---

# One parser, many languages: what is being changed, and what would refute it

Written **before** any of it was run. The numbers land in
`notes/findings/2026-08-13-*`; this file is the pre-registration.

## The problem, restated from the measurement that produced it

`cky-001` keeps **0.06** of its English bracket F1 in Chinese; `template-002`,
a lookup keyed on punctuation, keeps 0.46. The known cause is that a
production's RHS is keyed on **literal words**
(`ClauseSample.categories()` emits the word itself at every non-argument
position), so translating the frame invalidates every rule at once.

## The four factors, separated on purpose

A single "multilingual parser" that changed all of these at once would be
unreadable. Each is registered as its own arm so the sweep prints them side by
side against the same floors.

| factor | off | on |
|---|---|---|
| **segmentation** | `split_words`, the repo's shared splitter | script-aware splitter (CJK/kana/Thai one char per token, combining marks kept on their base letter) |
| **abstraction** | literal words in the RHS | induced word classes |
| **training mixture** | English only | N languages at once |
| **conditioning** | one global rule weight | per-language rule weights, backing off to global |

## Hypotheses, and what refutes each

**H0 (the one I actually expect to dominate — harness, not architecture).**
The shared word splitter is orthographic. `[^\W\d_]+` runs over CJK without a
break, so `alice和面包` is *one* token and the argument cannot be found; Tamil
combining marks are not `\w`, so Tamil shatters into graphemes. Predicted:
treebank clause coverage is much lower for CJK than for English, script-aware
segmentation raises it, and **that single change moves cross-language parser
scores more than class induction and conditioning combined**.
*Refuted if* script-aware segmentation leaves coverage and cross-language
bracket F1 essentially unchanged, or if it is smaller than the abstraction
effect.

**H1 (abstraction).** With frame words replaced by induced classes and an
open wildcard for unseen frame tokens, a chart parser keeps materially more of
its score on a language it was **not** fitted on.
*Refuted if* `polycky-001` does not beat `polycky-literal` (same everything,
literal RHS) on held-out languages.

**H2 (the class induction is doing work).** The induced classes beat the
degenerate one-class grammar.
*Refuted if* `polycky-1class` matches `polycky-001`. That would say the gain is
"ignore the frame words entirely", i.e. a positional template, not a grammar
over classes — which is `template-002`'s mechanism wearing a chart parser's
name, and would have to be reported as such.

**H3 (conditioning).** Per-language rule weights beat the unconditioned mixture
**net of a same-cardinality nonsense split**. `polycky-crc` buckets episodes by
`crc32(instance_id) % K` — same K, same per-bucket sample size, no information.
*Refuted if* `polycky-crc` gains as much as `polycky-002`. This has already
happened once in this repo on the reasoner side, so it is the expected outcome
rather than the feared one.

**H4 (script is the confound).** If the abstraction is really doing
orthography, held-out-language retention concentrates in languages whose script
is represented in training.
*Refuted if* retention is flat across the in-training-script / novel-script
split.

## Protocol

- 46 WALS-coded languages from `configs/full179_wals46.toml`, all 179 lessons.
  The graph is byte-identical across all of them, so nothing but the input
  changes and every drop is attributable.
- Train seeds from 0; eval seeds from 1,000,000, never touched during fitting.
- **Leave-one-language-out**: 46 fits, each on the other 45, scored on the
  held-out one. One JSON per language, written the moment it finishes, because
  a single long process gets killed at ~20 min and takes its process group.
- Every metric against `symbolic_ai_parsers.floors.fit_floor`, which is
  text-blind and therefore the same number in every language.
- The language label at eval is an **oracle**. It is measured as its own head
  with its own floor (nearest-centroid on `shape_features`, floor = 1/46), per
  the standing rule that a supplied signal must not assume away a subproblem.

## What was rejected

- **One parser per language.** It is the thing the objective is against, and it
  cannot answer the held-out-language question at all.
- **Editing `split_words`.** It is shared with the graph side and with the
  tokenizer, and `tests/test_curriculum_fingerprint.py` exists to stop exactly
  that silent redefinition. The new splitter lives in the parser package and is
  registered beside the old one.
- **Editing `cky-001`.** Every arm is a new registration; `cky-001`,
  `lr-001` and `shiftreduce-001` are untouched and stay in the table.
- **Clustering frame words by embedding similarity.** The parallel corpus makes
  a translation-equivalence class directly countable from the supervision the
  grammar already has; a similarity threshold would be a free parameter on top
  of that.
