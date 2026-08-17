---
date: 2026-08-16
author: cart scouting arm
status: pre-registration
related: [2026-08-16-constraint-anchored-infilling-and-the-backtrack,
          2026-08-13-the-harness-moves-more-than-the-models]
---

# CART: what the three arms are, and what each is predicted to score

Written **before** anything ran. Adapting arXiv:2607.16727 (Cheng, Dai, Sun) to
masked-node infilling: fill the most-constrained hole first, propagate the
consequences of each fill, backtrack when the partial graph goes inconsistent.

## The gap this is aimed at

`RuleBasedModel._forward_graph` calls `node_votes(view)` **once**, and the view
it passes has every hidden node still hidden. So each of an episode's ~10 holes
is answered against the same masked context; nothing a fill implies ever reaches
the other holes and nothing is ever un-filled. That is the whole of the decode
order in this repo today: there isn't one.

## Why this is a harness change and must be arm'd before it is read

`notes/lessons/2026-08-13-the-harness-moves-more-than-the-models.md`: harness
decisions here span 0.15 to 2.0 lift where models span 0.1. A sequential decoder
that lets hole *j* read hole *i*'s committed fill is a **contract change** — it
gives the reasoner strictly more visible context — and it will move the number
whether or not any constraint logic works. So the arms are built so that the
constraint logic is the only thing that varies at the top.

The reasoner is held fixed: all three arms wrap **`frontier-001`** (best
`label_acc` on `runs/full179`, 0.404) and change the decoder alone. Every arm
inherits frontier's fitted rules, gate, calibrator and back-off unchanged.

## The three arms

| arm | fill order | committed fills visible to later holes | learned domains + backtracking |
|---|---|---|---|
| `cart-001` | most-constrained first | yes | **yes** |
| `cart-order` | most-constrained first | yes | no |
| `cart-noop` | most-constrained first | yes | machinery runs, assertion is a tautology |

`cart-order` is the propagation-free control the parked note asks for: the same
decode order and the same sequential context, with the constraint logic removed.
`cart-noop` is the no-op-constraint control: the *identical* code path to
`cart-001` — domains computed, checked, backtracking armed — with the domain set
to the whole vocabulary so no assertion can ever fail.

The reference point is `frontier-001` itself, already on `runs/full179`
(`label_acc` 0.404, `label_bits` 7.433, `type_acc` 0.863; floor 0.143, copy
ceiling 0.722). It is the fourth arm and it is already run.

## Predictions, and what refutes what

1. **`cart-noop` ≈ `cart-order`**, to within about 0.005 `label_acc`. They differ
   only in machinery that cannot bite. If they separate, there is a bug, and the
   whole table is unreadable until it is found.
2. **`cart-order` > `frontier-001`** by roughly +0.01 to +0.04 `label_acc`. The
   sequential context is free extra information: frontier's `copy:` and `map:`
   resolvers decline whenever their path is masked, and a committed fill turns
   some of those declines into answers. This is the *decode order* effect and it
   is not the claim.
3. **`cart-001` > `cart-order`** is the claim, and I put it at maybe +0.00 to
   +0.02. I do not expect much: frontier already picks the argmax of a
   cross-fitted rule, and a domain constraint can only change an answer when the
   argmax is *outside* the domain and some in-domain candidate has a positive
   vote — which needs the model to be both wrong and to have kept the right
   answer in its vote table.

**What refutes the claim that the constraint logic is doing the work**: if
`cart-001 - cart-order` is smaller than `cart-order - frontier-001`, the gain is
decode order and not logic, and that is the honest headline whatever the top
line says. If `cart-001 == cart-order` to three decimals, the constraints never
bit and the arm should be reported as a null, not as "the full system scores X".

**What refutes the whole direction before any of it is built**: the cascade
measurement below.

## The cascade measurement, which comes first and can stop the build

CART's headline is the cascade rate — given one wrong step, how often the next
is wrong — falling 0.65 -> 0.14. This repo has never measured whether errors
cascade in infilling, and it is a property of the **task**, not of any model.

Two forms, on `frontier-001` over `runs/full179`'s eval episodes:

* **Observational**: order an episode's holes in the CART fill order, and
  compare P(hole *k* wrong | hole *k-1* wrong) against the marginal P(wrong).
  This is confounded by episode difficulty and is reported as such.
* **Interventional**, and this is the decisive one. For each ordered pair of
  holes (*i*, *j*), score *j* three ways: (a) with *i* left masked, (b) with *i*
  filled with the **true** label and type, (c) with *i* filled with the model's
  own prediction. Then
  * (b) - (a) is the **headroom** a perfect propagator could reach,
  * (c) - (a) is what the real sequential decoder actually gets, and
  * (b) - (c) is the **cascade cost** — how much of the headroom a wrong fill
    burns.

Pre-registered reading: if (b) - (a) is under ~0.01, there is nothing for a
propagator to propagate, no constraint machinery can help, and the correct
report is "the CART premise does not transfer to this task" — stop, do not go
deep. If (b) - (a) is large but (c) - (a) is negative, errors cascade and CART's
backtracking is aimed at a real problem here.

## Addendum, written after the cascade run and before the sweep

The cascade measurement finished first, as intended, and it moves prediction 2
before any sweep number existed. The oracle headroom is **+0.0066** — filling a
neighbouring hole with the *true* label and type buys the receiving holes 0.7
accuracy points. That is the ceiling on everything a decoder can gain from
sequential context, propagation included, because a perfect propagator cannot do
better than knowing the answer. So prediction 2 is revised **down** from "+0.01
to +0.04" to "**+0.000 to +0.005**", and prediction 3 correspondingly to "not
distinguishable from zero".

Recording the revision rather than editing prediction 2 in place: the original
guess was wrong by a factor of about five and that is worth leaving visible.

## What was rejected

* **Writing a new reasoner.** The arms have to differ in the decoder alone or
  the comparison confounds decoder with model, which is the mistake
  `notes/lessons/2026-08-15-a-floor-outside-the-models-hypothesis-class.md` is
  about.
* **A hand-written constraint list.** The domains are *learned* from the
  training episodes — which labels occur at slot *s* under a parent labelled
  *L*, which arities a label has been seen with, which types a label takes. A
  hand-written list of constraints is a fitted parameter with no error bar, and
  `frontier-001`'s own docstring levels exactly that criticism at `ruleinduce`.
* **Coreference propagation.** `relation_matrix` withholds the coreference edges
  of hidden nodes, so hidden-hidden coreference is not readable from a
  `GraphView` and a propagator that used it would be reading the answer.
