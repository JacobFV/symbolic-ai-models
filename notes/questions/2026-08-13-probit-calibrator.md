---
date: 2026-08-13
author: lead
status: idea
---
`ScoreCalibrator` uses isotonic regression on binary outcomes, and its own
docstring notes the top bin is often a handful of examples -- exactly where
isotonic is noisiest. A parametric probit link `P(correct) = Phi(a + b*s)` has two
parameters instead of a step function. This is a *data-efficiency* argument, not
a multiple-truths one: expect it to help small-slice runs and do nothing on 179
lessons. See ROADMAP design rule 4.
