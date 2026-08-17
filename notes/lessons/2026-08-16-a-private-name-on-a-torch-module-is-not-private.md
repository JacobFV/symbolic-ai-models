---
date: 2026-08-16
author: lead
status: measured
related: [2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property,
          2026-08-14-a-sandboxed-test-reports-environment-faults-under-its-own-name]
---

# A model can run three green sweeps and be impossible to reopen

## The mechanism

`nn.Module` reserves a large namespace of underscore-prefixed methods, and
`_apply` is the one `.to(device)` dispatches through to walk a module's tensors.
A subclass that defines `_apply` for its own purposes overrides it, with a
different signature, and nothing complains until something calls `.to()`.

The failure is invisible along the whole path the work is actually done on.
Fitting does not call `.to()`. Evaluation inside the training process does not
call `.to()`. `train` writes `summary.json` and `rules.txt` and exits zero. The
model is broken and every artefact it produced is fine.

## What happened

`frontier-001` used `_apply(rule, idx, pv, fv)` for "this rule's prediction at
each of these fills". Three arms of the derivability sweep ran green — 179
lessons each, correct-looking numbers, renaming rows printed — and the analysis
script then died on the first line that reopened one:

    TypeError: FrontierModel._apply() missing 2 required positional arguments

`load_run` calls `make_model(...).to(device)`. So the cost was not a wrong
number; it was that **three completed sweeps could not be analysed**, and
finding out took the full round trip because nothing earlier could have told me.

## Why the existing test did not catch it

`tests/test_models.py::test_rule_based_survives_a_non_cpu_buffer` exists for a
neighbouring bug — buffers landing on cuda while confidences were built on cpu —
and it simulates the device move by assigning `buffer.to(torch.float64)`
**directly**. That is a deliberate choice, made so the test runs on a host with
no GPU, and it is why the test never goes through `nn.Module.to` and never
touches `_apply`. A test written to avoid needing a device also avoided the
code path where the device machinery lives.

That is the general shape and it is worth stating separately from this bug: **a
test that simulates the expensive half of an operation is not testing the
operation.** It tests the half you kept.

## The guard

`tests/test_models.py::test_a_model_survives_module_to` calls
`model.to(torch.device("cpu"))` — a no-op move, available on any host, that
still dispatches through `_apply` — for **every** registered rule-based model,
and then scores a batch. Verified to fail on the defect before being believed:
re-binding `_apply` to the old four-argument signature makes it raise, and
removing the rebinding makes it pass.

Parametrised over the whole registry rather than over the model that broke,
because the next collision will be a different private name on a different
model, and `nn.Module` has dozens of them.
