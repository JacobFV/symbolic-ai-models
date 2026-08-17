---
date: 2026-08-17
author: lead
status: open
related: [2026-08-16-a-private-name-on-a-torch-module-is-not-private,
          2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property]
---

# Two published rows in `runs/full179` cannot be reopened

Found while crossing the renaming test with the copyable split, which needs to
load a fitted model:

* **`grammar-001`** — `ModuleNotFoundError: No module named
  `symbolic_ai_models.models.grammar``. Its checkpoint pickles a reference to a
  module path that no longer exists; the package is `grammar_001`.
* **`softreason-onehop`** — no `model.pt` at all, only `summary.json` and
  `rules.txt`. Weights under `runs/` are untracked by design, so this is a row
  whose numbers are published and whose model is simply gone from this checkout.

Neither is a wrong number. Both are rows that **cannot be re-analysed**, and the
repo's whole style of work is re-analysing published rows with new instruments —
the bits column, the copyable crossing, the derived split all needed to load
weights, and all of them silently dropped these rows.

## Why this is worth a note rather than a fix now

The `grammar-001` case is the same shape as
[[2026-08-16-a-private-name-on-a-torch-module-is-not-private]]: the model works,
the sweep was green, and only *reopening* it fails. The difference is that this
one was already broken before today and nothing noticed, because nothing had
reopened it.

The obvious guard — a test that every directory under `runs/` with a
`summary.json` can be loaded — is **not obviously right**, because weights are
deliberately untracked and a fresh clone would fail it for every row. A guard
that fails on a fresh clone is a guard that gets deleted.

What might work instead: a test that every **registered** model can be fitted,
saved and reloaded in-process, which catches the module-path rot without
depending on `runs/` at all. That is close to
`test_a_model_survives_module_to` and could extend it.

Left open rather than guessed at. Recorded so the next instrument that silently
drops two rows knows why.
