---
date: 2026-08-13
author: lead
status: measured
---

# A slice is a different curriculum, and it has inverted results thirteen times

Every confident wrong result this repo has published came from measuring a
*sample* of the world rather than covering it. The count is **thirteen**, three of
them in one day.

*The filename says eight and is deliberately frozen there* — other notes,
`RESEARCH_LOG.md` and `CLAUDE.md` link to this slug, and renaming it to chase a
count that keeps rising would break every inbound link for no gain. The table is
the count.

| claim, from a slice | what the full run said |
|---|---|
| "no rule-based model clears the label floor" (6 lessons) | nearly all of them do |
| the 6-lesson slice ranked the models **close to backwards** | — |
| `peer` collapses 0.141 → 0.005 under EM, subsumed by `mirror` (3 lessons) | `peer` keeps 26%, loses less than `prev` or `echo` |
| turning off `structural_fallback` costs `vsa` **two thirds** of its accuracy (3 lessons) | 0.219 → 0.200, i.e. **9%** — overstated sevenfold, and already in a commit message |
| `I(d)` plateaus at **2.35 bits**, a constant-latent signature | mostly plug-in estimator bias; the controlled term is **0.31** |
| `test_encoding_is_lossless` passes | its fixture drew episodes with no underscore, so a tokenizer deleting `_` went unseen |
| the seeding 2x2's *positive* lifts (12 lessons) | every arm is **below** the label floor at 179; only the ordering survived |
| a +0.051 renaming drop for the permutation VSA (24 episodes) | +0.008 at 192 episodes, +0.010 on the full curriculum |
| Indo-European ranks at the median, Spanish nearest Chinese (7 packs) | at 46 languages a real, if weak, family signal appears |
| fitting the softmax temperature collapses held-out accuracy 0.126 → 0.040, so it must be held fixed (3 lessons) | at 179 the likelihood picks sharpness 12 unaided and the row is **bit-identical** to the fixed one; the trap does not exist at scale |
| abstention on `repair` scores **below chance** (6 lessons) | at 179 it is **0.032 above** chance — `abstain` 0.0866, `random` 0.0543. Both rows moved, in opposite directions, and no mechanism for either was measured |
| the eigenmap's mechanism: the graph-nearest labelled node carries the answer **0.000** of the time and a label-carrying node is **always** an even number of hops away (3 lessons) | 0.022 and **91.2%** at 179 lessons. The *direction* survives and the eigenmap stays refuted; the absolutes that were quoted do not |
| `metta-005`'s likelihood switches the treatment **off** — the knob fits to 0.0, the pre-registered refutation condition (6-lesson wiring check) | at 179 it lands **interior at 2.0**, on a monotone curve that rises 0.078 over five points and then turns. The likelihood *prefers* the treatment at twice the weight of the hand-built coordinates |

**Why:** lesson families differ enormously in which structure is available, so a
handful of them re-weights every model's strengths. The tokenizer case is the
same error wearing a fixture instead of a lesson set; the `I(d)` case is a third
form — a raw curve read without the null that says what the number is when no
signal exists.

**The rule, and it is absolute:** a slice or scratch script may form a hypothesis
and **may never appear** in a commit message, a docstring, `RESEARCH_LOG.md` or a
report. Only the full sweep reports. When a slice result is startlingly large,
expect the full run to cut it by roughly an order of magnitude — and say so
*before* running it.

**The guard is starting to work, and that is worth recording too.** The first
seven entries were caught by a *later sweep contradicting a published claim* —
the expensive way, and the only way anyone was catching them at first. Most of
the recent ones were caught **before the claim was published**, by re-measuring
at full scale on purpose: the +0.051 renaming drop was chased to 192 episodes and
evaporated; the temperature trap was registered as its own row precisely so the
full curriculum could price it, which is how it was found not to exist; and
`metta-005`'s knob was caught because the agent recorded the whole likelihood
curve instead of its argmax, which turned an argument into one glance.

The two that still cost full price are the ones where a *slice mechanism* was
written into a note as an explanation — abstention-below-chance and the
eigenmap's hop-parity. A number gets re-measured because it looks like a number;
a *mechanism* reads as understanding and nobody re-measures an explanation. That
is where the next one will come from.

**The variant that catches people twice:** do not pin a constant measured on one
slice into a test that runs on another fixture. A test asserting the curated
ontology's 0.68 imbalance failed on a three-lesson fixture where it is 0.47. The
imbalance is the invariant; its size is not.
