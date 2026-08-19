---
title: WordNet supplies the semantics; the ancestor's depth decides everything
date: 2026-08-19
status: measured
arm: verb-class-staleness
---

## The floor, and why nothing here could see it

The day's declared floor is the **uncued** stale sentence — *"sub_98 left the
group in April"* has the ownership signature exactly and carries no cancellation
cue. The signature-bits result says why nothing sees it: **a signature over
(entity counts, numbers, dates) never looks at the verb**, and the verb is where
the predicate lives.

WordNet is on disk. `symbolic_ai_generators/wordnet.py` reads it from the
distributed archive with the standard library only — `index.verb`, `data.verb`,
`lexnames`, `verb.exc`. No new dependency, and it is the first external standard
used here as a given rather than re-derived.

## 1. Supersenses cannot separate a transition from a state

| relation verbs | | transition verbs | |
|---|---|---|---|
| `owns` | possession | `left` | motion |
| `holds` | stative | `divested` | **possession** |
| `is` | stative | `ceased` | **stative** |
| `requires` | stative | `ended` | **stative** |
| `includes` | stative | `sold` | **possession** |

**WordNet's supersenses classify by subject matter, not by aspect.** `cease` is
*stative* because it is about states; `divest` is *possession* because it is
about possessions — exactly like `own`. Taking the union over senses is worse:
`left` carries *stative* among its six classes. No rule over supersenses can
tell a verb that **asserts** a relation from one that **ends** it.

## 2. The hypernym closure can, and the design set lies about how well

Ancestors that denote cessation, departure or loss: `change`, `end`,
`discontinue`, `leave`, `exit`, `deprive`, `transfer`, `remove`.

| root set | design recall | **held-out recall** | held-out FP |
|---|---:|---:|---:|
| all 8 | 0.86 | **0.42** | 0.08 |
| deep 6 (no `change`, `transfer`) | 0.64 | **0.33** | **0.00** |

The roots were chosen by "reached by stale verbs and not by my fifteen relation
verbs". **A fifteen-verb negative class inflated the recall about twofold.** The
held-out misses — *revoke*, *rescind*, *annul*, *abandon*, *forfeit*, *suspend*,
*disband* — could be caught by widening the roots, and doing so after seeing them
is fitting, not deciding.

## 3. At the sentence level it fires on half of English, and the reason is depth

| root set | real prose | + nominal filter |
|---|---:|---:|
| all 8 | **0.522** | 0.426 |
| deep 6 | **0.058** | 0.045 |
| *(`stale_by_cancellation`, same corpus)* | *0.003* | — |

Token fires per root, over 10,650 real sentences:

| `change` | `transfer` | `leave` | `end` | `remove` | `exit` | `deprive` |
|---:|---:|---:|---:|---:|---:|---:|
| **6,899** | **2,191** | 315 | 271 | 91 | 12 | 5 |

**Two shallow ancestors account for 95% of the firing.** `change` sits near the
root of the verb hierarchy, so *increase*, *add*, *process*, *update* all reach
it. That is the reusable statement:

> **An ancestor's usefulness as a feature is set by its depth, and depth must be
> measured against a large negative population, not a hand-listed one.**

And the nominal filter — skip a token after *the*, *of*, *in* — moves 0.522 →
0.426 and 0.058 → 0.045. It buys little, so **part of speech is not the dominant
problem; ancestor depth is.** That corrects my own framing from an hour earlier,
when I named POS tagging as the missing capability.

## 4. End to end, one word decides it

On solvency, with the consolidated reader:

| gate | clean | owns uncued | owns+filing uncued |
|---|---:|---:|---:|
| none | 1.000 | 0.485 | 0.450 |
| cancellation | 1.000 | 0.485 | 0.450 |
| **verb (deep roots)** | **0.650** | **0.635** | 0.530 |

It **lifts the floor** 0.485 → 0.635 — the first thing all day that moves the
uncued arm by reading — and **destroys the clean surface**, 1.000 → 0.650, on one
word: **`dated`**. A participial modifier in every filing sentence, whose first
WordNet sense is the romantic one, whose chain reaches *leave*. Both failure modes
in a single token: no part of speech, and the wrong sense taken by frequency.

## 5. And the theory already predicted the fallback would fail

The obvious repair for a noisy detector is not to delete but to **flag**, and let
the ambiguity machinery emit both worlds. That cannot work here, and this
afternoon's decision note says why before the experiment: solvency's decision is
a **sum**, every filing moves it, and an aggregating decision admits neither a
second reading nor insensitivity. A flagged claim would produce two worlds that
always disagree.

So the verb gate is **kept and marked**, not shipped as a gate:
`stale_by_verb` carries all of these numbers in its docstring, because a dead end
that is not written down gets re-derived.

## What would refute this

- The roots are eight words chosen by hand from WordNet's taxonomy. A principled
  selection — say, every ancestor whose corpus firing rate is below a threshold —
  is a different experiment and might do better.
- `first_sense_supersense` and the closure both take **the first sense**. That is
  word-sense disambiguation by prior, and `dated` is exactly where it fails.
- Recall is measured on 26 verbs total. That is a small sample for a 0.33 figure,
  and the rule-of-three bound on it is wide.
