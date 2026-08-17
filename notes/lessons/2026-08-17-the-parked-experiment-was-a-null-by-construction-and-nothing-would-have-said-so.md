---
date: 2026-08-17
author: lead
status: measured
related: [2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control,
          2026-08-15-give-the-control-a-floor-so-its-failure-is-provable-without-a-model,
          2026-08-17-the-per-guard-floor-keeps-the-channel-and-drops-the-chosen-constant,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# A parked idea can be a null by construction, and the parking note is where it hides

## The mechanism

An experiment gets noticed mid-run, written into `notes/questions/` as a
three-line idea, and left. The note is a *design*, not a run — nothing has
executed, so nothing has checked whether the design can produce a signal at all.
Months later somebody picks it up, implements exactly what it says, gets a flat
curve, and writes it up as a finding about the models.

The parking lot is meant to make capture cheap, and it should stay that way. But
a design that has never been executed has also never been *checked for a null by
construction*, and the flat curve it produces is indistinguishable from a real
one in every artefact.

## What happened

`notes/questions/2026-08-15-how-many-pairs-can-a-model-here-hold.md` asks for the
curve behind the derivability result: register `derive:wordnet-k12`, `-k24`,
`-k60`, widening the corpus-wide map from six pairs to k, and read where the
derived-slot accuracy falls off. It is the right question — the derivability
headline's biggest remaining threat is that it is about **table size** rather
than induction, and this is the measurement that separates them.

It cannot be run the way it is written. `DeriveBinder.vocabulary` applies the map
only when the slot asks for exactly as many words as the map holds:

```python
if slot == KIND_SLOT and len(default) == len(self.kinds):
    return list(self.kinds)
```

and the scene vocabularies are **six words each** —
`COLORS = ["red", "blue", "green", "yellow", "purple", "orange"]`,
`SHAPES = ["cube", "sphere", "cone", "prism", "disc", "rod"]` — imported by 57
lesson modules. Measured directly:

| map width | what the kind slot gets back | fallback recorded |
|---:|---|---|
| 6 | **the map** | none |
| 12 | the curriculum's own list | yes |
| 24 | the curriculum's own list | yes |

So a widened arm falls back at every slot, derives nothing, and scores its
baseline. The curve would have been flat at every rung, and the reading —
"the models hold about six pairs and no more" — would have been a fact about the
binder.

## Why it would not have been caught

The fallback **is** counted; `DeriveBinder._fallback` exists precisely so a
half-filled slot is visible, which is good design by whoever wrote it. But
nothing surfaces that count: not the sweep, not `summary.json`, not
`scripts/derived_split.py`. The run completes, the table prints, the floors
reproduce — the derivation floor would even still be 1.000, because it is fitted
on the same episodes and *nothing derived is nothing to get wrong*.

That is the same shape as
[[2026-08-15-a-degree-preserving-scramble-is-an-isomorphism-not-a-control]]: a
manipulation that cannot produce a difference, wearing the artefacts of one that
could.

## The guard

`_check_derive_width` raises at **registration**, where the message can say what
the real change is rather than what the symptom looks like: widening the pool
means widening `COLORS` and `SHAPES`, which moves every scene in every lesson and
therefore the substrate of every published number. That is a much larger and more
honest piece of work than adding a curriculum name, and the point of failing here
is that whoever tries finds that out in one second instead of after a sweep.

Two tests: one that the guard refuses a width the slots cannot take, and one that
pins the *behaviour it exists for* — a wide binder returning the curriculum's list
and recording a fallback. The second matters more, because the guard is only
correct while that behaviour is what it claims.

## The reusable part

**Before running a parked experiment, check that its treatment can move at all.**
Not the control — the *treatment*. The repo already has the habit of asking
whether a control could fail; the mirror question is whether the manipulation
could succeed, and a design that has sat unexecuted has never been asked it.

Cheapest version: construct the manipulated thing and assert it differs from the
unmanipulated one, before any model is fitted. Here that was one call to
`vocabulary()` and it took a second.
