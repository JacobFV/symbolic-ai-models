---
date: 2026-08-17
author: lead
status: measured
related: [2026-08-17-a-default-computed-in-init-captures-the-base-classs-values,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# Editing code with `str.replace` hit a line I did not know was a prefix of another

## The mechanism

Patching a file by `s.replace(old, new)` replaces **every** occurrence, not the
one being looked at. When `old` is also a *prefix* of a longer line elsewhere,
the longer line is rewritten into something that still parses, still runs, and
means something different.

Here the base class had

```python
self.type_head_settings = cfg.get("type_head_settings", None)
```

and a subclass had the same text continued:

```python
self.type_head_settings = cfg.get("type_head_settings", None) or (0.0, 1, False, False)
```

Replacing the first with "that line, plus a new `self.type_atoms = ...` line"
turned the subclass into

```python
self.type_head_settings = cfg.get("type_head_settings", None)
self.type_atoms = bool(cfg.get("type_atoms", False)) or (0.0, 1, False, False)
```

so the subclass stopped pinning its type head **and** assigned a truthy tuple to
a boolean flag. Both silently: the tuple is truthy, so the flag read as "on", and
the model quietly became something nobody had registered — the eight-atom type
head *with* the label head's settings.

## What it cost, and what caught it

`frontier-009`'s `type_acc` went **0.8652 → 0.8540**, undoing the fix committed
half an hour earlier, while `frontier-010` — the model actually under test —
also read 0.854 and looked like a failed experiment.

It was caught by the regression check from
[[2026-08-17-a-default-computed-in-init-captures-the-base-classs-values]]:
re-running an unchanged model alongside the new one and diffing its row. That
lesson was written to catch a base-class default; it caught a text-editing
accident instead, which is the better argument for it.

Two false trails were taken first, and both were cheap only because they were
*measurements* rather than guesses: the number was checked for non-determinism
(0.854 twice — deterministic, so the change was the cause), and the diff was read
before anything was rewritten. The thing that finally located it was printing the
attributes:

    frontier-009: type_atoms=(0.0, 1, False, False)  type_head_settings=None

A boolean holding a tuple is not subtle once printed, and printing it took one
command against twenty minutes of reading the diff.

## The guards

* **Assert the count before replacing.** `assert s.count(old) == 1` was used for
  most edits in this session and was omitted for this one, which is exactly the
  edit that needed it. It costs one line and turns this failure into an exception.
* **Print the constructed object's fields when a knob does not do what it should.**
  Before re-reading the code, ask the object what it thinks its settings are.
* The standing one it re-earns: **re-run an unchanged model and diff its row**
  after touching anything shared.

## The wider point

Three of the day's worst hours went to defects introduced by *how the code was
edited*, not by what the edit intended — a `__slots__` addition that broke
unpickling, a base-class default that captured pre-override values, and this. All
three were invisible to the test suite and visible in one re-run of an unchanged
model. **The cheapest guard in this repo is not a test, it is a control row.**
