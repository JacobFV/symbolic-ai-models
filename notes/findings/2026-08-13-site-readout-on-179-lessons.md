---
date: 2026-08-13
author: agent-readout
status: provisional
related: [readout-is-a-knob, action-readout]
---

# Attachment on the text surface: the `site` readout, on all 179 lessons

**Full curriculum.** `configs/full179_site.toml`, which is `configs/full179.toml`
with a different `out` and nothing else; 179 lessons x 20 train / 4 eval; 3,580
training and 716 evaluation episodes; **30,748 scored site positions**. Not a
slice.

## The hypothesis, and what would have refuted it

Written before the numbers landed, in
`notes/decisions/2026-08-13-readout-is-a-knob.md`:

> `site` is not measurable above its floor by anything that is not the oracle.
> Then the text surface carries no attachment signal a parser can reach, and the
> readout is a ceiling with no system under it.

and

> The oracle row is not exactly 1.000. Then the target and the prefix
> restriction disagree and one of them is wrong.

## What the readout asks

For each word of the rendering that realises a labelled node of the true term:
**which already-read word is the head it hangs under?** The answer is a token
position, and correctness is word equality with the true attachment site, never
index equality — the rule `_pointer_counts` established for the other pointer.

The ground truth is free: `prefix.availability` already says which word reveals
which node, so walking up to the nearest ancestor already realised gives the
site. It is a *target*, computed task-side from `meta["graphs"]`, and no model
is handed it.

## The floor

Best of three structure-free rules, fitted on train, scored on eval. On the full
curriculum:

| rule | what it does | wins? |
|---|---|---|
| `start` | attach at ROOT, always | **yes, 0.2056** |
| `previous` | attach under the immediately preceding word | no |
| `offset` | commonest word offset per positional context, applied blind | no |

That `start` wins is itself worth recording. On a three-lesson slice `offset`
won at 0.3495 and `start` was nowhere — the eighth time a slice has pointed the
opposite way in this repo, and it took ninety seconds of full-curriculum compute
to find out. **Attachment on this corpus is not right-branching**: pointing at
the previous word is worse than pointing at nothing.

## The numbers

`runs/full179-site/`. One reasoner, five registrations differing **only** in the
prefix parser, so the spread is a measurement of parsing.

| row | parser | site acc | site lift | site bits |
|---|---|---:|---:|---:|
| floor (`start`) | — | 0.2056 | 0 | — |
| `gsite-none` | none | *unscored* | — | — |
| `gsite-flat` | flat | 0.2056 | +0.0000 | 5.591 |
| `gsite-001` | `template-002` | **0.2200** | **+0.0181** | 5.783 |
| `gsite-oracle` | oracle | 0.9979 | +0.9974 | 1.668 |

`corefer-001` (0.357 label, 0.336 copy) and `ptrgen-001` (0.336 / 0.323) ran
under the identical config and have **no site column at all**.

## What it means, stated against the refutation conditions

**"Not measurable above its floor by anything that is not the oracle" — not
refuted, but only just.** `gsite-001` clears the floor by 0.0181 of the
headroom, 1.4 accuracy points, on 30,748 positions. That is a real,
full-curriculum, non-oracle number and it is small.

**`gsite-flat` *is* the floor's `start` rule, to four decimals.** Not a
coincidence and a good control: a flat parse is one unlabelled root with the
words under it, so every word attaches at ROOT and the honest zero turns out to
be literally the floor. A design in which the zero row and the floor were
supposed to coincide and did not would have meant one of them was wrong.

**The oracle row cannot separate reasoner from parser, and must not be read as
though it did.** `gsite` walks up to the nearest labelled available ancestor,
which on the oracle parse is a re-implementation of the target, so 0.998 is the
target agreeing with itself. The **defensible** comparison is the one between
two real parsers: `flat` -> `template-002` is +0.0144 accuracy. The 78-point gap
to the oracle is inflated by the tautology and is not evidence about parsing.

**0 of 19 existing models can answer a site.** The repo already knew that 11 of
19 cannot emit a token; not one can emit a text-surface pointer. The readout
reports that as an **empty cell** rather than as zero, which is the contract
working: "cannot point" and "points badly" now occupy different cells.

**The accuracy/bits inversion reappears on a brand-new channel.** `gsite-flat`
has *worse* accuracy (0.2056 vs 0.2200) and *better* bits (5.591 vs 5.783) than
`gsite-001`. This repo's signature disagreement — `label_acc` and `label_bits`
ranking models close to inversely — was attributed to the one shared symbol
mixture `(1-c)*backoff + c*votes`. Here it shows up on a pointer channel with a
**flat** back-off, no `context_prior` and no temperature: the mechanism is not
that particular mixture, it is that a confident-and-sometimes-wrong reader trades
bits for decisions wherever a confidence exists at all. Splitting *where* from
*what* did not dissolve it. Recorded as
`notes/questions/2026-08-13-the-inversion-is-not-the-symbol-mixture.md`.

## Which readout each model can answer *at all*

Static, not measured: does the class override the hook, or inherit the
abstaining default. No episodes, no fitting, so this one cannot be a slice
artifact. Over the **90 registered rule-based models**:

| readout | models that can answer it |
|---|---|
| `symbol` | 79 / 90 |
| `node` | 41 / 90 |
| `site` | **5 / 90** — and all five are the `gsite` family added here. Before this work: **0**. |
| next token | 14 / 90 |

**Read the first row carefully — I got it wrong first.** The eleven that cannot
answer `symbol` are exactly the six `gparse` and five `gsite` rows, which are
text-surface models and abstain on the graph task *by design, in their own
docstrings*. There is nothing hidden there, and my first reading of it ("eleven
models cannot answer the readout the repo is scored on") drifted toward the more
dramatic version before I checked which eleven. Recorded in
`notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-the-models-name.md`.

What the table actually says is in the other three rows: **two thirds of the
registry has no pointer, six sevenths cannot emit a token, and until this work
nothing at all could answer a question about the structure of the text surface.**
That last one is the readout being new rather than the models being deficient —
which is the honest form of "one readout is an assumption".

The hidden version of the problem is a *runtime* fact this table cannot see, and
the agents-side `action` readout caught it independently: `synth-001` implements
`node_votes`, publishes 0.2500, and contributes nothing
(`notes/findings/2026-08-13-action-readout.md`).

## What this does not show

* It is one reasoner. `gsite` walks up to the nearest labelled ancestor of the
  node its parser found and points at the most recent mention of it. A scored
  candidate set with fitted feature weights — what `gparse-003` does for the
  symbol readout — has not been tried, and the reasoner is at least as likely to
  be the bottleneck as the parser.
* `site_bits` is charged against the *stated* site, not against the equivalence
  class, so a reader that spread its mass over six spellings of the right word
  is punished in bits and forgiven in accuracy. The two columns therefore do not
  have to agree, and where they disagree the accuracy is the lenient one.
* Nothing here says attachment helps the label task. That is a separate
  measurement and it has not been made.
