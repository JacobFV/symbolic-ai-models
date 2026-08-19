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
recovers it, in two forms: `stolen` (an anchor named a different region as the
needs site) and `reassigned` (an anchor gave the adjacent region another role).

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

## The blind spot is the finding

**The check covers exactly the role that has a second signal.** Flooding
sentences misfiring onto depot cost 0.655 accuracy and fire **nothing**, because
neither depot nor flooding has any content-free corroboration on this surface —
vehicles are described in a paragraph that names no region, and a wrongly-named
depot is a real region that is usually still connected.

So this is the constructive form of the pairing law measured this morning
(*soundness is a property of the pairing (channel, check)*): **to make a failure
detectable, give the thing it corrupts a second, independent signal.** Not a
better check — a second reading of the same fact by different evidence. The needs
site has one because a quantity sits beside it; depot and flooding have none, and
nothing about the check can fix that.

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
