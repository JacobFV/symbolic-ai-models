---
title: Six arms priced determinacy and called it advantage — measured against a floor that shares its candidate sets, the symbolic resolver buys +0.9 points at entity level, zero at group level, and does not beat its floor at all
date: 2026-08-18
author: lead
status: provisional
tags: [cost, floors, north-star, self-correction, harness-trap, decisive]
---

## The item that had been standing, and what ignoring it cost

`HANDOVER.md` §7 item 10:

> **Put this session's work through `symbolic_ai_core/cost.py`.** Everything here
> was priced with hand-rolled arithmetic in scripts while the repo's own ledger
> sat unused... *a number on a different basis from the published ones is not
> comparable with them, which is most of what a ledger is for.*

This session then published **six arms** on a hand-rolled
`advantage(f) = M / (f·M + (1−f)·O)` and never opened the module. That formula is
a **cost ratio at assumed equal accuracy** — the assumption §6 records as having
put four earlier rows out of quotation.

`Capability` refuses to carry a rate without a floor, so running the arc through
it forces the measurement the arc never made: **is the answer right?** Every
number from `f` 14.66% down to 8.17% is a *determinacy* rate. Settling was
silently read as being correct.

## The answer key, and the ceiling nobody had computed

The wikidata CIK→LEI bridge resolves **1,015** matched filers by identifier at
both ends, so it is usable as ground truth — provided it is **excluded from the
system being scored**, which it is here.

> **CEILING: the true LEI is among the name join's candidates for 944/1,015 =
> 93.0% of filers.** No policy over those candidates can score above that, and no
> arm this session had established it.

## The result

The floor is **pick uniformly at random among the name candidates**. It is strong
by construction — an unambiguous filer has one candidate and the floor takes it
for free — which is exactly what this repo's standing rule demands of a floor.

| | settles | correct (fallback) | **floor** | **above floor** |
|---|---:|---:|---:|---:|
| **entity level** | 80.5% | 83.7% | 82.9% | **+0.9%** |
| **group level** | 84.6% | 87.3% | 87.4% | **−0.1%** |

And the ledger, `symbolic_ai_core/cost.py`, n = 1,015:

| system | rate | floor | $/solved | **$/solved above floor** |
|---|---:|---:|---:|---:|
| hybrid, escalating 15.4% | 0.965 | 0.874 | $9.80e-05 | **$1.04e-03** |
| frontier model only | 1.000 | 0.874 | $6.15e-04 | $4.88e-03 |
| **federated symbolic resolver** | **0.873** | **0.874** | $1.78e-11 | **inf** |

> *"aligned filer rate 0.8729 does not beat its floor 0.8739: cost per unit of
> capability is infinite, which is the honest entry and not a formatting bug."*
> — the module, unprompted.

## Why, and it is not a bug

At group level, closure determines the answer **because all candidates share a
root**. But if all candidates share a root, then picking a candidate at random
*also* lands on that root. The floor gets exactly the cases closure settles, for
free.

> **Determinacy is not accuracy.** Closure tells you the answer is determined; it
> does not tell you anything a guess could not. The **1.22×** published for
> closure, the **1.49×** for the crosswalk and the **1.80×** combined are cost
> ratios over an escalation policy, not capability gains — and measured against a
> floor holding the same candidate sets, the accuracy contribution is **+0.9
> points at entity level and zero at group level.**

## What the symbolic layer actually buys

Not the answer — **knowing when the answer is safe.** That is certification, and
it is worth something real: escalating the 15.4% it cannot settle reaches 96.5%
accuracy at **$1.04e-03 per unit of capability above floor**, against the model's
**$4.88e-03**.

> **The honest headline of the whole arc is 4.7× on cost per capability above
> floor** — not the 6.8×–12.2× cost ratios published across six commits, which
> price answers rather than capability and assume the opponent is perfect.

4.7× is a real number and it is the kind this repo says it exists to produce. It
is also an order of magnitude below what the arc read like.

## The harness trap, walked into with the sign posted

The first version of this script scored abstention as **zero** and reported the
symbolic layer at **−7.5% below floor**. That compares a system which refuses to
guess against a floor which always guesses, and the floor wins for that reason
alone. `CLAUDE.md` lists *"abstention falling back to the structural prior"*
among the largest measured effects in this repo's history. The fix is to score
both: abstain (−7.5%) and fall back (+0.9%), and the gap between them **is** the
effect.

## What would refute it

- **The ground truth is one bridge**, and it agrees with the name join only
  93.0% of the time. Where they disagree, the bridge is assumed right. If it is
  wrong at some rate, both system and floor move — but they move *together*, and
  the above-floor gap is a difference, so it is the more robust quantity.
- **The floor holds the candidate sets**, so it already contains the name join.
  This measures what the crosswalk, closure and ambiguity machinery add **on top
  of** the name join, which is the right question but not the only one. Against a
  floor with no name join, everything here looks excellent and means less.
- **n = 1,015 filers, one workload**, and only those the bridge covers — a
  population enriched 1.33× toward ambiguity, which if anything *favours* the
  symbolic layer.
- **The escalated share is assumed answered perfectly.** Blocked on credentials
  (§6); the assumption is generous to the opponent, so 4.7× is a lower bound.

## Reproduce

```bash
uv run python -u scripts/arc_through_the_ledger.py
```

`runs/arc_through_the_ledger.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `the-arc-through-the-ledger`.
