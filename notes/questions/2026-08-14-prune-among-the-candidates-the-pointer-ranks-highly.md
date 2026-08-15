---
date: 2026-08-14
author: agent-lean-006
status: idea
related: [2026-08-14-the-lean-gate-closes-the-kernel-loses-to-an-arity-check]
---

The `006` gate measured prune rate over **all** ~55 candidates. The quantity
that would actually move the pointer is prune over the candidates stage two
ranks highly — a filter that removes 35% uniformly is worth nothing, and one
that removes 35% concentrated on the top five is worth a lot.

Cheap to run: fit `corefer-001`, take its stage-one top-k, and report the
kernel's prune rate and gold survival restricted to that top-k. Needs a fitted
model, which is why the pre-registration deliberately did not gate on it.

If prune-within-top-k is much higher than 0.355, the null in the finding is
about the wrong denominator and the line should be reopened. If it is the same
or lower, the null hardens: the kernel is refusing candidates nobody was going
to choose anyway.
