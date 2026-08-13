---
date: 2026-08-13
author: lead
status: intended
related: [2026-08-13-notes-are-one-file-per-note]
---

# Split a `symbolic_ai_core` out of `symbolic_ai_models`

**Intent recorded, deliberately not acted on yet.** Three agents are live in
separate worktrees; a refactor that moves shared modules would conflict with all
of them at once. This waits until the tree is quiet.

## Why

`symbolic_ai_models` is now three things wearing one name: the *harness* (floors,
lift, calibration, sweeps, invariance, registries), the *models*, and the
*data plumbing*. Two sibling packages already depend on the harness half —
`symbolic_ai_agents` imports the shortcut floors and the calibrator,
`symbolic_ai_parsers` needed the registry — and a third (`symbolic_ai_data`) is
being built.

The clearest evidence it should move is that **the registry has now been copied
three times**, and the versioned-name fix (a bare name must resolve over
*numbered* versions only, or `ptrgen` selects `ptrgen-argmax`) had to travel with
each copy by hand. This repo has already written down what copied code does —
see the note in `models/omegaclaw/base.py` about `routes.follow` being
reimplemented and the two copies being left to drift.

## Candidates for `symbolic_ai_core`

- `tasks/base.py` — `empirical_floor`, `ratio`, `lift`, `score_block`. The floor
  discipline is the repo's central methodological commitment and is not about
  models.
- `calibration.py` — `ScoreCalibrator`, `MassCalibrator`, `calibrate`.
- `registry.py` — the versioned-name resolution, *once*.
- `invariance.py` — renaming equivariance, which is a gate for every package.
- `asymptotics.py` — corpus observables, already used to judge the data and not
  any model.
- `report.py` / the compare table.

## What must not happen

A refactor is not a redesign. Every published number must be reproducible across
it, so this lands as **moves and re-exports with behaviour unchanged**, verified
by the existing suite, and any API change is a separate later commit. The
`Episode`/`Graph` types are contested — they may belong to `symbolic_ai_data`
instead — and that question should be settled before the move, not during it.
