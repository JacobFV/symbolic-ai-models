---
title: A certificate's coverage is not a measure of its reliability
date: 2026-08-19
status: lesson
---

## Twice in one day, in two domains

A certificate here asks *would a small perturbation change the answer?* — delete
one link, delete one member — and answers on the world **as read**. Both times it
was pointed at a surface with more corruption, its **coverage went up**:

- flood's role-independent certificate fires on **5.6%** of the clean adversarial
  surface and **12.7%** with `hard_distractors`, because the phantom links it is
  blind to add 2-edge-connectivity and make the answer *more* robust to deleting
  any one of them;
- solvency's membership certificate fires on **48.5%** of the uncued arm and
  **93.5%** once a spurious filing is added, because the spurious figure pushes
  the sum clear of the threshold so no member deletion can flip it — and accuracy
  among the certified falls from 1.000 to 0.481.

## The mechanism

Stability under perturbation is what these checks measure, and **a large error
makes the answer more stable**, not less. A wrong answer sitting far from the
decision boundary is exactly the shape a margin-based check is designed to
approve. The check is not malfunctioning; it is answering a question that stopped
being the useful one when a second channel opened.

## The two guards

**1. Never read coverage as reliability, and never compare it across surfaces.**
"The certificate fires more here" is not "the system is more trustworthy here" —
it can be, and twice today was, the opposite. Report coverage **with** the
accuracy among the certified, on the same surface, always.

**2. A rising coverage is a signal to look for a second channel.** That is the
useful reading of it. In both cases coverage rose exactly when a channel the
certificate does not cover was switched on, and in both cases the check's own
docstring already said which channel it covered. The number arrived before the
suspicion did, and it could have arrived the other way round.

## Related

- [[2026-08-19-a-detector-experiment-needs-a-baseline-arm-for-every-check]] — the
  same underlying error, that a rate means nothing without its counterfactual.
- The pairing law: soundness belongs to (channel, check), never to the check.
  This is what that law looks like when you only watch the check.
