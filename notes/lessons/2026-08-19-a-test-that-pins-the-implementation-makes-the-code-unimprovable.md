---
title: A test that pins the implementation makes the code unimprovable
date: 2026-08-19
status: lesson
---

## The mistake

`test_the_oracle_is_exhaustive_rather_than_heuristic` asserted:

```python
src = inspect.getsource(W.feasible_by_search)
assert "itertools.product" in src
```

The intent was right and important — a heuristic ground-truth oracle that
occasionally missed a feasible packing is indistinguishable from a kernel bug.
The mechanism was wrong. **Exhaustiveness is behaviour; the test asserted a
substring.**

## What it cost

The brute force it pinned was costing **53 seconds on a single 18-job instance**
against milliseconds for the kernel it was checking, and it capped the whole
scheduling domain at toy sizes. Replacing it with a pruned *exact* search — same
verdicts, 2.7 million times faster — failed a test whose stated subject was
correctness, while changing nothing about correctness.

A test like this inverts its own purpose. It was written to protect a property
and ended up protecting the one implementation that had it, including the part
of that implementation nobody wanted.

## The guard

**Assert the property, against a reference, not the source text.** Keep the slow
obviously-correct version as an executable specification and test agreement with
it. That gets you *more* confidence than the substring did, because it would also
catch a brute force that was subtly wrong.

Source-level assertions are legitimate for properties that genuinely live in the
source. The same test's other half — that the oracle does not import `clingo`,
`get_kernel` or `build_program` — is a real independence property that no
behavioural test can establish, and it correctly stayed a source check.

The discriminator: **could a different, better implementation have this
property?** If yes, the test must be behavioural. If the property *is* "does not
depend on X", source is the only place to look.

## Related

- [[2026-08-19-the-ground-truth-cost-2.7-million-times-the-system-it-checked]]
- The neighbouring test `test_the_expensive_kernel_really_is_the_expensive_part`
  passed throughout and was never wrong — it measures cost inside the flow, and
  the runaway cost was in the harness outside it. A correct test with a scope
  that stops short of the problem reads exactly like a clean bill of health.
