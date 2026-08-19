---
title: Refusing to collapse costs nothing here, and flags every error
date: 2026-08-19
status: measured
arm: carry-distractor-ambiguity
---

## The gap this fills

[[2026-08-19-grounded-means-consistent-with-what-was-read-not-true]] closed off
the obvious defence: nothing downstream of a reader can see the true world, so no
grounding check catches an invented claim. On the hard-distractor surface the
reader answers **0.383** and cannot say which answers are the wrong ones.

The remaining response is directive 19's: **decline to collapse.** The audit
already says, offline and without a reader, that flood's `(2 regions, 0 number)`
signature is shared with prose. A reader cannot tell *which* link sentence is the
distractor, but it knows the kind is suspect.

Bounded hypothesis, matching the generator's actual situation: **at most one link
is spurious.** That gives `k + 1` candidate worlds — the read world, and each
single link deletion. Median **16** per case, so the enumeration is cheap.

## The result

| policy | accuracy | soundness | decided |
|---|---:|---:|---:|
| collapse (answer regardless) | **0.383** | — | 1.000 |
| carry at-most-one-spurious | — | **1.000** | **0.383** |

Decidedness equals the collapsing accuracy — and the sets are **identical**:

| | |
|---|---:|
| decided | 23 |
| collapse correct | 23 |
| decided **and** correct | **23** |
| decided but wrong | **0** |
| correct but undecided | **0** |

**The policy gives up nothing and flags every error.** Same answers, and now you
know which to trust.

## One half is provable, the other is not

This distinction is the finding, not a caveat.

- **decided ⟹ correct** follows by construction. If the true world is among the
  candidates and every candidate agrees, the common answer *is* the true answer.
  Soundness is exact, and `test_the_truth_is_always_among_the_candidates` pins
  the premise it rests on.
- **correct ⟹ decided** is **empirical**. A collapsing reader could be
  accidentally right while the candidates disagree; on 60 cases it never was.
  Nothing guarantees that, and on a surface with less redundant road networks it
  would fail — the policy would still be sound, it would just start paying
  coverage for soundness, which is the normal case.

`test_it_gives_up_no_coverage_here_which_is_the_fragile_half` says so in its
name, and its docstring instructs a later session to treat a failure as
information rather than a regression.

## Why this is worth more than the accuracy number

0.383 correct with no way to tell which is a **silent** error rate. 0.383 decided
at soundness 1.000 is a **bounded** one — the system answers less often and is
never wrong when it does. For a pipeline whose whole argument is that its
reasoning is inspectable rather than inferred, that is the difference between a
component you can build on and one you cannot.

It also completes an arc. Carrying **role** ambiguity was measured earlier as
"sound and rapidly vacuous" — 72 worlds deciding 0.0%. Carrying **distractor**
ambiguity is sound and, here, free. The difference is the bound: role permutation
enumerates a combinatorial space with no structure, while at-most-one-spurious is
a single bounded hypothesis the generator actually satisfies. **Ambiguity is
cheap to carry when the hypothesis about it is small.**

## What would refute this

- A generator whose networks are less redundant, where deleting a real link
  changes the answer more often. Decidedness would fall and the identity between
  the two sets would break. Soundness would not.
- More than one spurious claim. The hypothesis is stated as exact and the test
  checks the premise directly, so this would show up as a soundness failure
  rather than quietly.
- The same policy applied to a claim kind that is not a link. Nothing here is
  specific to links except that the audit named that signature; the machinery
  takes the suspect kind as input and has not been tried on another.
