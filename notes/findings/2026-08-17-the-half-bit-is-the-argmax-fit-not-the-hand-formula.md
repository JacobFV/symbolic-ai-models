---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-third-point-on-the-half-bit-line,
          2026-08-17-two-thirds-of-softreasons-headline-is-the-gate-and-the-same-gate-pays-twice,
          2026-08-13-the-harness-moves-more-than-the-models]
---

# The third point lands at 0.16, not 0.55 — the half bit is the cost of an *argmax fit*, not of not using a calibrator

One round ago I measured the same gate change at **0.58 bits** on `ptrgen` and
**0.53** on `softreason`, and wrote that the gate's fitting method is worth "about
half a bit wherever it is applied", naming `corefer-001` as the checkable
consequence. `corefer-mass` is that check, pre-registered in
[[2026-08-17-the-third-point-on-the-half-bit-line]] with all four numbers stated.

## The four predictions

| # | predicted | measured | |
|---|---|---:|---|
| 1 | `label_bits` lands in **6.40–6.60** | **6.7933** | **refuted** |
| 2 | `label_acc` moves < 0.02 | 0.357157 → 0.357539 | held |
| 3 | `type_acc` unchanged at 0.9458 | **0.945776 → 0.945776**, bit-identical | held |
| 4 | renaming drop stays ≈ −0.003 | +0.0032 → +0.0019 | held |

Prediction 3 is the control that makes the row readable — the type head has its
own estimator and did not move by a single bit, so only the gate changed. And the
regression row reproduced `corefer-001` exactly on accuracy and type, at
`label_bits` 6.954734, which is the *documented post-drift* value from
[[2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable]] rather
than the 6.951829 in the published summary — an incidental re-confirmation of a
drift that lesson exists for.

## The claim, narrowed

The gain is **0.161 bits**, not 0.35–0.55. So:

| model | gate it replaced | gain from a mass-fitted gate |
|---|---|---:|
| `ptrgen` | argmax accuracy | 0.58 |
| `softreason` | argmax accuracy | 0.53 |
| **`corefer`** | **a hand formula**, `min(0.15 + 0.8·top, 0.9)` | **0.16** |

The pattern is not "a mass-fitted gate is worth half a bit wherever it is
applied". It is **"fitting the gate as an argmax accuracy costs about half a
bit"** — and `corefer` never made that mistake. Its formula is not an accuracy
estimate at all; it is roughly linear in the pointer's top share, which is much
closer to a mixture weight than an argmax accuracy is, and the calibrator finds
only 0.16 left to take.

That is a sharper statement than the one it replaces and it survives the same
evidence. `notes/lessons/2026-08-13-a-ranking-is-a-property-of-a-metric.md`
already explains why: an argmax accuracy answers "how often is the top vote
right?", which is *categorically* the wrong question for "how much mass has this
earned?", so a model asked the wrong question loses a fixed-ish amount. A hand
formula asked no question at all and happened to land closer.

**The generalisation I made from two points was wrong in its scope**, not in its
sign, and one more point was enough to see it. Two points made a line; the third
made it a different line.

## The defect this nearly shipped with

The first version of `corefer-mass` fitted the calibrator on the top-**label**
mass and applied it to the top-**node** share. Those differ whenever several
candidate nodes carry the same symbol, which on a coreference task is most of
the time — so it calibrated one quantity and spent the result on another. It
measured **6.968**, *worse* than the hand formula, and I nearly wrote that up as
"the pattern does not generalise at all".

What caught it was the number being wrong in a way a miscalibrated gate should
not be: a badly fitted gate should be somewhere between the formula and the
optimum, not past the formula in the wrong direction. The fix is a `_raw_gate`
flag that makes the fitting pass see exactly the number prediction is handed.

And a second guard earned its place: the repair patch tripped
`assert s.count(old) == 1` because `self.gate_map = MassCalibrator()` is a prefix
of `self.gate_map = MassCalibrator().fit(...)`. That is the **same prefix trap**
as [[2026-08-17-str-replace-hits-every-occurrence-including-the-subclass]], eight
hours later — and this time the assert that lesson prescribed stopped it before
anything was written.
