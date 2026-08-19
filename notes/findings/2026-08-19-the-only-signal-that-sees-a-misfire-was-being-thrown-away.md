---
title: The only signal that sees a misfire was being thrown away
date: 2026-08-19
status: measured
arm: contradicting-evidence
---

## The gap this fills

A **misfire** — an anchor firing on a sentence it was not written for — costs
**0.290** against having no vocabulary at all, and is invisible to every check
this repo has built:

- it reads as `role_assignment_forced`, so `read_content_roles_worlds` emits one
  world and agreement is vacuous;
- its sentence **is** consumed, so `audit.unconsumed` sees nothing;
- `certifies_insensitive` builds its graph from the roles, so it inherits the
  error.

But the reader already has **two independent signals** for the needs site — the
lexical anchor, and positional adjacency to the bare demand quantity, which is
content-free and survives interleaving. It consults the second only when the
first stayed silent:

```python
if not needs and adjacent and adjacent in unresolved:
```

so whenever they disagree, **the disagreement is discarded**. `evidence_conflict`
recovers it — as `stolen` (an anchor named a different region as the needs site)
and `reassigned` (an anchor gave the adjacent region another role) — and a third
form, `arity`, falls out of the same question asked once more.

## Measured, 400 seeds, 252 non-empty, interleaved

| surface | accuracy | fire rate |
|---|---:|---:|
| published (original phrasings) | 0.988 | **0.000** |
| evading (anchors silent by construction) | 0.710 | 0.000 |
| misfire: depot sentences trip `require` → needs | 0.865 | **0.774** |
| misfire: flooding sentences trip `origin` → depot | 0.655 | **0.000** |
| misfire: needs sentences trip `water` → flooded | **0.151** | **0.976** |
| misfire: all three | 0.421 | 1.000 |

**Zero false alarms in normal operation** (0 of 252, bound 1.2%), and it catches
two of the three misfire directions at 0.774 and 0.976.

The `reassigned` form is what makes the second of those work, and it was worth
building: a needs sentence tripping the flooding vocabulary marks **the
destination impassable** — accuracy 0.151, the worst single arm measured, worse
than all three misfiring at once — and it does not take the needs slot, so the
`stolen` form is silent on it. The first version of this check scored 0.000
there.

## The blind spot named a third signal, and it closed

Flooding sentences misfiring onto depot cost 0.655 accuracy and fired
**nothing**: neither depot nor flooding has content-free corroboration on this
surface. But **depot and needs are single-valued**, and the reader takes the
first claimant silently (`if role == "depot" and not depot`). Two regions
claiming one single-valued role is a contradiction the domain's own **arity**
supplies, with no second evidence source at all.

| surface | accuracy | any | `stolen` | `reassigned` | `arity` |
|---|---:|---:|---:|---:|---:|
| published | 0.988 | **0.000** | 0.000 | 0.000 | 0.000 |
| evading | 0.710 | 0.000 | 0.000 | 0.000 | 0.000 |
| depot → needs | 0.865 | **0.988** | 0.774 | 0.000 | 0.492 |
| flooding → depot | 0.655 | **0.833** | 0.000 | 0.000 | **0.833** |
| needs → flooding | 0.151 | **0.976** | 0.000 | **0.976** | 0.000 |
| all three | 0.421 | **1.000** | 0.988 | 0.976 | 0.452 |

**All three misfire directions are covered, at zero false alarms**, and each form
is the unique coverer of one of them. They are complementary rather than nested:
on depot → needs neither `stolen` (0.774) nor `arity` (0.492) reaches the 0.988
they reach together.

`arity` is silent on needs → flooding because **`flooded` is multi-valued** — an
extra flooded region violates no arity, which is exactly why that direction needs
the adjacency signal instead. And `arity` reaches only 0.492 on depot → needs
because it needs the *true* needs sentence to claim the role too, and only **two
of the four** original needs phrasings trip an anchor at all (`outstanding call`
and `asking for resupply` are the documented misses — `supply` does not reach
*resupply*). Checked by inspection, not inferred from the number.

## The general shape

This is the constructive form of the pairing law measured this morning
(*soundness is a property of the pairing (channel, check)*): **to make a failure
detectable, give the thing it corrupts a second, independent reading.** The three
sources here are of three different kinds and that is the point —

- a **positional** signal (a quantity sits beside its site),
- a **cross-role** signal (that site was given away to something else),
- a **structural** signal (the domain says this role holds one region).

None is a better check than the others; each covers what the others cannot,
because each reads a different fact. Asking "what else knows this?" is a cheaper
question than "what stronger check exists?", and on this surface it was answerable
three times without adding a single word of vocabulary.

## A non-monotonicity worth recording

All three roles misfiring (0.421) is **better** than needs alone misfiring
(0.151). Misfires interact through elimination: when the depot sentence also
steals the needs slot, the needs site is no longer marked impassable, so the
destination survives. More corruption, less damage. Any model that treats reader
errors as independent and multiplicative gets this backwards.

## What would refute this

- The fire rates are measured with a *whole role's* phrasings misfiring. A real
  vocabulary misfires on a minority of sentences; the rate at which the alarm
  accrues is not measured.
- 0 false alarms over 252 published cases bounds the rate at 1.2%, not at zero.
- It detects the **condition**, not the consequence. A misfire changes the answer
  on 146 of 252 cases in the all-three arm, so firing does not mean wrong and
  precision against wrongness is 0.58 — barely above the base rate. Named in the
  docstring for what it computes.
