---
title: A test that passes a parameter the API does not take silently tests the empty case
date: 2026-08-18
author: lead
status: settled
tags: [testing, silent-failure, kernels]
---

## The mistake

Two tests for the new `Witness` field on the ASP kernel were written as

```python
proj = k.project(world, KernelRequest(params={"rules": ["p(a).", ":- p(a)."]}))
```

`AspKernel.project` takes `program`, `choices` and `constraints`. It does not
take `rules`. `KernelRequest.params` is a plain `Mapping`, so the unknown key was
accepted and ignored, the projection was **empty**, and clingo returned one
empty stable model. Both tests ran green paths that had nothing to do with what
they were named for: the "unique completion" test got the empty model and the
"unsatisfiable" test got the same empty model rather than an unsat.

They failed, which is the only reason this was caught — and they failed for the
*wrong reason*, on a `Witness` guard that refuses an empty fact tuple. Had that
guard not existed, both tests would have **passed** while testing nothing.

## Why it is the repo's recurring shape

This is `str.replace` again in a different costume, and the `pgrep` watcher, and
the backticks in `git commit -m`: **a permissive interface accepting something
plausible instead of refusing it**, so the damage is invisible at the moment it
is done. `params: Mapping[str, Any]` is deliberately open — kernels take
kernel-specific goals and a closed schema at the ABI would be worse — so the
looseness is a design choice and not a defect. The defect is trusting it in a
test.

## The guard

**A test of a non-trivial path must assert that the path was non-trivial.** Not
just the outcome: the shape. Both rewritten tests now assert

```python
assert res.ok and res.diagnostics["unique"]        # it really was a unique model
assert res.witness.size > 0 and not res.witness.vacuous
```

and the empty case gets its own test that says so in the name. Any of those
three assertions would have caught the original mistake immediately.

The general form: **when a test drives a component through a mapping it does not
validate, assert on a diagnostic that distinguishes the intended path from the
trivial one.** Kernels here already publish exactly that in `diagnostics` —
`unique`, `satisfiable`, `n_models`, `discarded` — and none of the original
tests read any of it.

## What it bought

The mistake produced the `vacuous` flag on `Witness`, which is a real
distinction the design had missed: a program whose unique stable model is
*empty* is satisfiable, and the empty set of atoms genuinely is its certificate.
Without the flag nothing can tell that from a kernel that left the field blank,
and one of those two is a lie. The flag stays.
