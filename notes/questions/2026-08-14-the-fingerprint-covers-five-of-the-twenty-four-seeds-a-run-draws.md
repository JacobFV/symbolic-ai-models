---
date: 2026-08-14
author: agent-kg-seam
status: open
related: [2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property,
          2026-08-14-what-share-of-the-curriculum-a-knowledge-graph-can-reach]
---

# The corpus fingerprint hashes 5 seeds; a published run is drawn from 24

`symbolic_ai_core/data/fingerprint.py` is the repo's central guard — "nothing
else in this repo can notice that generation moved" — and its grid is

```python
SEEDS = (0, 1, 7, 1_000_000, 1_000_003)
```

`configs/full179.toml` draws `n_train = 20` from seed 0 and `n_eval = 4` from
1,000,000. So a published number rests on seeds **0-19** and
**1,000,000-1,000,003**, of which the fingerprint hashes **five**. A generator
change that touched only seeds 2-6 or 8-19 would move every published number and
leave the guard green.

Nothing has ever exploited that, and it is not obviously exploitable — a
generator is a pure function of a seed and few changes are seed-selective. But
"not obviously exploitable" is the description of every silent property in
`notes/lessons/2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property.md`,
and the cost of the gap is that the guard's *claim* is wider than its coverage.

## Measured today, because the KG seam needed it

The binding hook in `symbolic_ai_data/binding.py` had to be proved inert, and
the five-seed fingerprint was not enough to prove it on the episodes a sweep
actually draws. So the wider hash was taken by hand: **179 lessons x 24 seeds**
(0-19 and 1,000,000-1,000,003), English, full `Episode.to_dict()`, run once
against the generator at `8f7c167` (before the hook) and once against the
current tree.

```
old  5174ab631fa1478a
new  5174ab631fa1478a
```

Identical. The hook is inert on every seed a training run touches, not only on
the five the golden file pins.

That also settles a smaller question it raised. Re-running the base curriculum
reproduces `runs/full179` **exactly** on `label_acc`, `type_acc` and
`copy_ceiling` for 8 of 10 models, and differs by one label in 5,233
(±0.000191) on `routes-001` and `workspace-001`, with `label_bits` moving up to
0.0043 on all of them. With the corpus proved byte-identical at every seed those
runs used, that drift cannot be the data. `routes-001` re-run a third time
reproduces the *new* number to nine decimals, so it is not nondeterminism
either. It is harness or model commits landing between `runs/full179` and now —
the same unattributed `label_bits` drift
`notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md`
records, now with the data half of the hypothesis eliminated.

## What to do about it

Not "re-record the fingerprint" — the grid is the thing that is pinned and
widening it would rewrite the golden file, which is the move that file's own
failure message warns against. Two options that do not:

* a **second** golden file over the full 24-seed grid, added beside the existing
  one, so both are checkable and the published one keeps its meaning. Costs one
  more file and about a minute of suite time;
* or a test that hashes the wide grid for a *named subset* of lessons — cheaper,
  and closes the gap for the lessons most likely to move.

Parked rather than done: it is a change to the repo's central guard and belongs
in its own commit with the lead's attention, not appended to a KG branch.
