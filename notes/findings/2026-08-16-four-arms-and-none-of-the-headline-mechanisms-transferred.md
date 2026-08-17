---
date: 2026-08-16
author: lead
status: provisional
related: [2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-16-first-on-accuracy-eleventh-on-bits,
          2026-08-16-a-soft-consequence-fixpoint-buys-bits-and-the-iteration-costs-them,
          2026-08-16-infilling-errors-clump-but-do-not-cascade-and-cart-is-a-null,
          2026-08-16-premise-selection-is-free-inside-the-object-and-costs-0714-outside-it]
---

# Four arms in one day, and in every one the paper's headline mechanism was not the part that worked

Four 2026 neurosymbolic papers, four arms, all on the 179-lesson curriculum
against the same floors. The point of running them together rather than one
properly was to find out which direction is live before committing a deep pass
to it. That worked, and it produced a pattern nobody was looking for.

| paper | headline mechanism | did the headline transfer? | what actually moved |
|---|---|---|---|
| Hypothesis Frontier | verifier-guided **search** over formulas | **no** — the search was never the constraint | the hypothesis **form** (a verified symbol map): +0.109 acc, and 0.000 → 0.532 on the derived bucket |
| SoftReason | differentiable **`T_P` closure** to a fixpoint | **no** — iterating is *worse* than one hop, −0.012 acc / +0.169 bits | emitting the closure as a **distribution**: 2nd of 26 on bits at a −0.004 renaming drop |
| CART | constraint propagation + **backtracking** | **no** — −0.0012 acc, negative on both metrics | nothing; the reusable part is its **cascade metric**, which killed it |
| CoTu | delegate deduction, **premise selection** is the residual | **half** — a residual exists but is not relevance ranking | **argument binding**: 1.000 scoped to the object, 0.286 over the graph |

Three of four headline mechanisms are nulls here, and in each case a *component*
of the paper carried whatever moved. That is worth stating as a pattern rather
than four times as a coincidence: **the transferable unit of one of these papers
is a component, not the architecture**, and an arm that adopts the architecture
wholesale will report the architecture's name against a number some other part
of it earned. Every one of these four arms would have done exactly that without
the control that separated them — and in three of the four, the separating
control was one the agent built because the brief demanded one, not one the
paper suggested.

## The live direction, and it is not the one that got built first

**Premise selection, and specifically the reframe it produced.** Neither
pre-registered reading won. At whole-graph scope the selector picks one of the
six kind labels on **99.9%** of positions — it identifies what *sort* of fact
answers the question, out of 23.6 candidates and a vocabulary of thousands — and
picks the right **object's** kind only **23.3%** of the time. That is 1/4, and
there are four objects in a scene. It retrieves a true corpus fact about the
wrong entity.

So the 0.833-wide channel is not about hypothesis language and not about search.
It is about **relevance scope** — knowing which object the question is about.
That reinterprets the day's other result: `frontier-001`'s winning rule is
guarded `[slot=1, nsib=4]`, and a guard is exactly a scope restriction. The map
may be getting credit for what the guard is doing.

**The pre-registered discriminator already exists** and is falsifiable in one
run: widen scenes to eight objects. If the whole-graph rung moves to ~1/8 while
the object-scoped rung stays at 1.000, binding is the constraint and scene size
is its denominator. If both hold, it is not.

That is the deep pass, and it goes in front of everything else here.

## Second: the readout, not the closure

`softreason-onehop` is Pareto-optimal at 6.1479 bits / 0.3193 accuracy with a
renaming drop of **−0.004** — near-equivariant, which no other high-bits row
here is. Against `corefer-001` it trades 0.038 accuracy for 0.804 of a bit.
`RESEARCH_LOG.md`'s interface argument — that collapsing to an argmax throws
away about 3.3 bits — is cashed out, and the acc/bits inversion turns out not to
be a law of these models but an artefact of the readout.

The missing control is named and cheap: **`softreason-argmax`**. The 0.804 bits
moves distribution-output and mass-fitted gate at once and nothing separates
them yet.

## Dead, and cleanly

CART. Errors clump (0.7705 conditional against a 0.6251 marginal, the paper's
shape) and do not cascade (oracle headroom **+0.0066**). The tell is that
receivers do *worst* — 0.3721 — when the model **abstained** on the donor, and
an abstention cannot cause anything downstream, so that column is ranking
episode difficulty. An observational number that looked exactly like a
publishable headline was worth 0.005 interventionally.

Keep the instrument. Any future proposal here that depends on one fill informing
another clears the interventional cascade test first.

## What this says about how to run the next day

The fan-out cost roughly one arm's worth of wall clock and returned three
directions with numbers instead of one direction with a write-up. The ranking it
produced is not the ranking anyone would have guessed: the arm built first and
deepest (`frontier-001`) is the one whose result the *fourth* arm may have just
reinterpreted.
