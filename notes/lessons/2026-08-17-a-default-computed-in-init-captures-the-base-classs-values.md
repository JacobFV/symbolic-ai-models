---
date: 2026-08-17
author: lead
status: measured
related: [2026-08-14-a-guard-applied-only-to-the-arm-that-lost,
          2026-08-16-a-private-name-on-a-torch-module-is-not-private,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# Two ways I made a published model change without touching its definition

## One: a knob for one head, applied to both

`frontier-001` grew eight successors in a day and every one was tuned on
`label_acc`. `_induce` reads its knobs off the **model**, not off the head, so
each new knob went to the type head as well — a head whose column was not in the
table I was reading.

| model | type acc | type lift | what it added |
|---|---:|---:|---|
| `frontier-001` | 0.8633 | **+0.023** | — |
| `frontier-003` | 0.8607 | +0.004 | `keep_per_guard` |
| `frontier-004` | 0.8491 | **−0.079** | the tolerance band |
| `frontier-006/7/8` | 0.8539 | −0.045 | the rest |

The floor is 0.8601 and only two of nineteen models had ever cleared it. I took a
positive lift negative, over eight variants, while improving something else — and
`notes/lessons/2026-08-14-a-guard-applied-only-to-the-arm-that-lost.md` is exactly
the shape: the check gets applied where it costs nothing.

None of the knobs even had an argument for that head. `map` is not in its
resolver set, so `keep_by_path` has nothing to keep. A tolerance band resolves
near-ties toward the renaming-invariant `copy`, which matters because labels are
symbols and types are not. A floor asking a rule to beat its guard's modal answer
is near-unmeetable where the modal answer is already right 86% of the time — the
very property that made the *label* head need it.

**Guard:** the type head is induced under its own settings, and
`frontier-009` pins them.

## Two: the "no-op default" that was not one

The fix introduced a worse bug within minutes. The new field was written as the
obvious faithful default:

```python
self.type_head_settings = cfg.get("type_head_settings", None) or (
    self.rank_tolerance, self.keep_per_guard, self.keep_by_path,
    self.relative_floor)          # <- captured in the BASE __init__
```

That reads as "unless told otherwise, behave exactly as before". It does not.
**A subclass sets its knobs after `super().__init__()`**, so the tuple captures
the *base-class* values, and every subclass silently received the pinned type
head. Measured: `frontier-008`'s published `type_acc` moved **0.8539 → 0.8654**
with nothing in its own definition changed.

That is the silent redefinition `CLAUDE.md` names as having already happened
twice — *"editing a model in place silently redefines every published number
carrying its name"* — arriving by a route neither previous instance took. Nobody
edited `frontier-008`. A field was added to its base class with a default that
looked inert.

It was caught only because I ran the published model as a regression check
alongside the new one and read both rows. Had I run only `frontier-009`, its type
head would have looked like the fix working and `frontier-008`'s number would
have moved under a name that was not being printed.

## The guard

The field stays `None` and is resolved **at fit time**, where subclass values are
final. `tests/test_models.py::test_a_knob_added_for_one_model_does_not_change_another`
pins that for every registered `frontier` model: `None` everywhere except
`frontier-009`, which must pin it.

## The reusable part

**A default computed from `self` in a base `__init__` is not a no-op for
subclasses.** It freezes the base values at a point where the subclass has not
run. Any field whose default is "whatever the model is already doing" has to be
resolved where the model is finished being built — at use, not at construction.

And the process half, which is cheaper than any test: **when adding anything to a
shared base class, re-run one unchanged model that inherits from it and diff its
row.** That is one sweep. It caught this; nothing else would have.
