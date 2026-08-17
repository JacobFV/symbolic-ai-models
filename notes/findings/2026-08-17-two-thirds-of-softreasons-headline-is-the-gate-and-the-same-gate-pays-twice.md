---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-16-a-soft-consequence-fixpoint-buys-bits-and-the-iteration-costs-them,
          2026-08-13-the-harness-moves-more-than-the-models,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The missing control says two thirds of SoftReason's advantage is the calibrator, and the same method is worth the same on an unrelated model

`softreason-onehop` was written up at **6.148 bits**, second of twenty-six, and
read as the *distribution readout* paying — SoftReason's transferable part. The
agent that built it named the gap against itself and called it "the single most
important missing control": the comparison against `corefer-001` moves **two
things at once**, the output being a distribution *and* the gate being fitted by
held-out likelihood rather than as an argmax accuracy. It was never run. This
runs it.

## The row

`runs/full179`, everything identical but the one method — same closure, same
conclusion mass emitted whole, same rules, same type head:

| model | gate fitted by | label acc | **label bits** |
|---|---|---:|---:|
| `softreason-onehop` | held-out likelihood (`MassCalibrator`) | 0.319 | **6.148** |
| **`softreason-argmax`** | argmax accuracy (`ScoreCalibrator`) | 0.258 | **6.680** |
| `corefer-001` | a hand formula, `0.15 + 0.8·top` | 0.357 | 6.952 |

Both existing rows reproduced exactly (0.3071/6.3165 and 0.3193/6.1479), so the
refactor that made the gate overridable is a no-op.

## The headline was two thirds a calibrator

The published claim is that `softreason-onehop` beats `corefer-001` by **0.804
bits** and that the distribution readout is why. Decomposing that 0.804:

| | bits | share |
|---|---:|---:|
| the **mass-fitted gate** (6.680 → 6.148) | **0.532** | **66%** |
| the **distribution readout** (6.952 → 6.680) | **0.272** | 34% |

So the distribution is worth a third of what was claimed for it. The rest is a
calibration method that `ptrgen-001` / `ptrgen-argmax` had already measured and
published, which makes two thirds of the headline a **restatement of an existing
result on a new model** rather than a new one.

The 0.272 that is genuinely the readout is real and still worth having — it is
the difference between emitting a closure and emitting its argmax — but the note
should say 0.27, not 0.80.

## The part I did not expect: the same method pays almost identically twice

| model | mass-fitted | argmax-fitted | **difference** |
|---|---:|---:|---:|
| `ptrgen` | 5.91 | 6.49 | **0.58** |
| `softreason` | 6.148 | 6.680 | **0.53** |

Two architectures with nothing in common — a gated pointer over node pairs and a
soft consequence operator iterated over weighted implications — and one shared
method is worth **0.58 and 0.53 bits** on them. That is a fact about the
*harness*, not about either model, and it is
[[2026-08-13-the-harness-moves-more-than-the-models]] arriving with a second data
point: the list of shared parts that move more than the architectures now has the
gate's *fitting method* on it, priced at about half a bit wherever it is applied.

**It predicted something checkable**, and the check narrowed it — see
[[2026-08-17-the-half-bit-is-the-argmax-fit-not-the-hand-formula]].
`corefer-mass` gains only **0.161 bits** (6.9547 → 6.7933), not 0.35–0.55. So the
pattern is **not** "a mass-fitted gate is worth half a bit wherever it is
applied"; it is **"fitting the gate as an argmax accuracy costs about half a
bit"**. `corefer` never made that mistake — its hand formula is not an accuracy
estimate but is roughly linear in the pointer's top share, already much closer to
a mixture weight, and only 0.16 was left to take. The generalisation above was
wrong in its **scope**, not its sign, and one more point was enough to see it.

## Where my own prediction failed

I pre-registered *"accuracy should move little either way: a gate scales every
vote equally and cannot reorder them."* Accuracy moved **0.319 → 0.258**, a drop
of 0.061.

The claim was too strong and this repo had already documented why. A gate cannot
reorder votes *within* the vote set, but it does move the boundary between a
voted symbol and the back-off — `RESEARCH_LOG.md` records exactly this for
`ptrgen`, where the argmax gate cost 0.015 of accuracy for the same reason. What
is new is the **size**: 0.061 is four times ptrgen's, because a closure spreads
its mass over more candidates than a pointer does, so a lower `c` hands more of
it back to the structural prior.

So the control is still a control — the only thing that changed is the gate — but
my reason for saying accuracy would hold was wrong, and the refutation condition
I wrote ("refuted as a control if accuracy moves materially") would have thrown
away a valid measurement had I applied it literally. **A refutation condition
stated on a mechanism I had not checked is worse than none**, because it licenses
discarding the result on the strength of my own error.
