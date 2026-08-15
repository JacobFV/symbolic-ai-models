---
date: 2026-08-14
author: lead
status: measured
related: [2026-08-13-a-guard-is-the-only-thing-that-catches-a-silent-property,
          2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable]
---

# A test that builds its own sandbox will report environment faults under its own name

## The mechanism

A test that needs to control one environment variable is tempted to construct
the child environment from scratch, because that is the airtight way to control
it. Doing so drops every *other* variable too — including the ones nothing in the
test is about, like the dynamic loader's. When the child then fails for that
unrelated reason, the failure surfaces as **the test's own name**, and the name
is a claim about the subject.

So a broken sandbox and a genuine violation of the property produce the same
summary line. The reader's first hypothesis is the one the test is named for,
which is the wrong one.

## What happened

`test_fitting_is_stable_across_processes` exists to catch a real and nasty class
of bug: iterating a `set` of strings gives an order that depends on hash
randomisation, fixed within a process and different between them, so a tie-break
depending on iteration order would flap every published number while looking
perfectly reproducible inside one interpreter. It fits the same model in two
subprocesses under `PYTHONHASHSEED=1` and `999` and compares a hash of the
logits. Good test.

It built the child env as `{PATH, PYTHONHASHSEED, HOME, CUDA_VISIBLE_DEVICES}`.
That dropped the loader environment, `torch` failed to import in the child with
`ImportError: libcusparseLt.so.0`, and the suite reported:

    FAILED tests/test_models.py::test_fitting_is_stable_across_processes[vsa-002]

which reads as *`vsa-002`'s fit is not reproducible*. It reproduced only under
load — three agents were running — and passed cleanly in isolation four times,
which is the worst possible signature: intermittent, and pointing at the
architecture instead of at the harness.

**And this repo's standing lesson is "suspect the harness before the
architecture".** It still took a look at the actual stderr to apply it. The
saving grace was that the assertion already carried `out.stderr` as its message,
so the real cause was one scroll away rather than lost.

## The cost

Fifteen minutes, and a moment of believing that the model family with the
repo's most-quoted equivariance property had a nondeterministic fit. Cheap only
because the assertion message had been written well.

## The guards

1. **Inherit the environment; override only what the test is about.**
   `{**os.environ, "PYTHONHASHSEED": seed, …}`. Hash order is controlled by one
   variable and nothing else needed removing. The GPU mask stays, because
   several subprocesses initialising CUDA at once genuinely did make the suite
   flaky — that part of the original reasoning was right.
2. **An assertion about the child's *exit* must say it is about the exit.** The
   message now begins "the child failed to run at all, which is an environment
   fault and not a determinism result". A test with two failure modes should
   name which one fired, in the message, every time.
3. **Full-suite green means the run that ends the series**, not a subset and not
   a run from before the machine was loaded. This failure was only ever visible
   in a full run under concurrency.

## The general form, for the next one

**Any test that constructs a sandbox — a stripped env, a temp `HOME`, a fake
clock, a cut network — can fail because the sandbox is wrong rather than because
the property is violated.** Every one of them needs an assertion that
distinguishes "the subject misbehaved" from "the scaffolding did", or it is a
test whose red state means two incompatible things.
