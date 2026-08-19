---
title: What a wrong answer must cost, before refusing pays
date: 2026-08-19
status: measured
arm: break-even-wrong-cost
---

## The gap, named by the module itself

`usd_per_solved_above_floor` counts **answers**. A certificate that refuses half
of them makes the row *worse* however sound it is, and `cost.py`'s own header
already says so — it "prices getting the answer right and prices knowing you are
right at zero". Three certificates were measured today whose entire value is
soundness, and the north star sees none of them.

The fix is not another denominator. It is to make the caller's decision a
**number** rather than a hedge:

> answering earns `rate − W(1 − rate)` per case at compute `c₀`; certifying earns
> `coverage` at `c₁`. So certifying pays iff
> **W > [rate − coverage/m] / (1 − rate)**, with `m = c₁/c₀`.

`W` is what **one wrong answer costs in units of one right answer**. Shipped as
`symbolic_ai_core.cost.break_even_wrong_cost`.

## The three certificates, priced

| certificate | accuracy | coverage | compute | break-even `W` |
|---|---:|---:|---:|---:|
| solvency, membership | 0.485 | 0.485 | 1.00× | **free** |
| flood, role-independent | 0.679 | 0.488 | 1.00× | **0.60×** |
| scheduling, capability | 0.790 | 0.525 | 3.07× | **2.95×** |

Three different verdicts, and none of them is a matter of taste any more:

- **Solvency: take it, always.** The certified set *is* the correct set, at the
  same compute — it converts 103 silent errors into 103 refusals and gives up
  nothing.
- **Flood: take it if a wrong answer costs more than 0.6 of a right one.** Which
  it usually does.
- **Scheduling: only if a wrong answer costs ~3 right ones.** That is a real
  trade, and the reason is visible in the row: 3.07× compute, and a coverage that
  keeps only two-thirds of the correct answers.

## A correction to my own reasoning

I predicted flood and solvency would both come out **free**, on the grounds that
each certificate's certified set is a subset of what the collapsing reader
already got right. That is true and it is **not sufficient**. Free requires
`coverage/m ≥ rate` — the certificate must keep *most* of the correct answers,
not merely a subset of them. Flood's keeps 0.488 of 0.679, so 28% of its correct
answers are given up, and something has to pay for them.

Solvency's is free because its coverage **equals** its accuracy exactly: on that
arm, certified ⟺ correct.

## Scope

- It prices soundness against **accuracy**, not against the floor, so it is a
  companion to `usd_per_solved_above_floor` and not a replacement. A system below
  its floor has bought nothing whatever a wrong answer costs.
- Every input is measured on the honest surface, and the compute multiples are
  measured rather than assumed — but coverage and accuracy both carry the
  distractors those surfaces use, which are ones I wrote.
- `W` treats a refusal as worth zero. A pipeline that can escalate a refusal to a
  more expensive arm is a different calculation, and `cost.Targeting` is the
  place for it.
