---
date: 2026-08-13
author: agent-a11dfe7b
status: measured
related: [2026-08-13-split-symbolic-ai-core, 2026-08-13-vendor-verbatim-rather-than-rename]
---

# `symbolic_ai_core` owns the episode types; `symbolic_ai_data` stays upstream's

The fork `2026-08-13-split-symbolic-ai-core.md` left open — "the `Episode`/`Graph`
types are contested, they may belong to `symbolic_ai_data` instead, and that
question should be settled before the move" — taken, plus what the survey
corrected in that note.

## Decided

**1. A thin core owns the types; the generator package is not touched.**
Rejected: folding `symbolic_ai_models/data/` into `symbolic_ai_data/` as a
subpackage. The decisive argument is not taste, it is a test.
`tests/test_vendored_generator.py` walks every `.py` under `symbolic_ai_data`,
subtracts `_vendor.ADDED`, and asserts the remainder is upstream's byte for byte;
`_vendor.py` states it is the only file in that package written here. Putting
harness code there means either growing `ADDED` until "is this still upstream?"
stops being answerable, or having the vendoring tests audit our own code as
though it were upstream's. The split is therefore by **authorship and
direction** — `symbolic_ai_data` generates and is upstream's, `symbolic_ai_core`
reads and is ours — not by subject matter.

**2. Old import paths survive as re-export shims.** Rejected: a clean break.
`symbolic_ai_agents` exists only on the `omegaclaw` branch and imports
`symbolic_ai_models.data.*`, `.calibration`, `.shortcuts` and `.tasks.base` in
about twenty places. CLAUDE.md records that a modify/delete conflict resolves
toward the delete **silently**, so a break would surface as that package's work
vanishing from a merge that looked green. `test_layering.py` now walks every
moved path and asserts identity, not equality, so a copy cannot pass while
breaking `isinstance` downstream.

**3. Moved only on "more than one consumer, or plainly not about models".**
What stayed, and why:

- `report.py` — its columns are model rows.
- `tasks/base.py`'s `Task` protocol — typed in terms of `ModelOutput`, so moving
  it would make the core import the models package and invert the dependency the
  core exists to straighten. Only the pure half (`lift`, `empirical_floor`,
  `score_block`, `ratio`, `Totals`) moved, to `symbolic_ai_core/floors.py`.

## What the survey corrected in the intent note

**The registry had been copied twice, not three times.** The note says three.
`symbolic_ai_data/registry.py` and `symbolic_ai_data/grammar/registry.py` are the
vendored curriculum's own and are untouched; our copies were
`symbolic_ai_models/models/registry.py` and `symbolic_ai_parsers/base.py`.

**The cross-package coupling is data types, not harness code.** 24 of 25
cross-package imports were `Episode`, `Graph` or `SymbolTokenizer`. The intent
note leads with the registry, which is the sharpest *symptom* but by volume the
smaller move.

**`symbolic_ai_parsers.floors` is not a second copy of the floor machinery.** It
looked like one from the module names. It is a genuinely different floor — one
constant graph per metric, found by search over held-out training episodes — for
a different codomain, and it shares no code with `tasks/base.py`. It quotes the
same argument for needing a floor at all, which is the part worth having once.

**Two modules the note did not list clear its own bar more cleanly than most
that it did.** `asymptotics.py` and `shortcuts.py` import nothing from this repo
and measure the corpus rather than any model; `asymptotics.py` had no consumer in
`symbolic_ai_models` at all, only tests.

**One module the note listed is thinner than it reads.** `invariance.py` has a
single consumer on `master` (`train.py`). It moved on "plainly not about models"
plus the `omegaclaw` branch, not on consumer count — recorded here so the
justification is not remembered as stronger than it was.

## The check that says this was a refactor and not a redesign

`tests/test_curriculum_fingerprint.py` holds the global digest `68be4d098db17e28`
over 179 lessons x 5 seeds x 7 languages. It was verified before the first move
and after the last, and did not move. The golden JSON travelled with
`fingerprint.py`; its entry point is now
`python -m symbolic_ai_core.data.fingerprint --write`, which supersedes the path
given in `2026-08-13-vendor-verbatim-rather-than-rename.md`.

## Known loose end

`symbolic_ai_core.invariance.__all__` omits `label_accuracy`, and always has,
while `train.py` and three test files import it. The shim names it by hand rather
than fixing `__all__`, because adding a name changes what `import *` means and an
API change was out of scope. Worth fixing in a commit of its own.
