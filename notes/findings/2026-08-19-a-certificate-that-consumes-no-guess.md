---
title: A certificate that consumes no guess
date: 2026-08-19
status: measured
arm: role-independent-certificate
---

## Building the thing the last finding named

`certifies_insensitive` reads the roles to build its graph, so on a world whose
depot was guessed it certifies the wrong question — which is why replacing the
role flag with enumeration broke the pair's soundness. The named fix: require
insensitivity for **every** candidate assignment rather than for one arbitrary
collapse.

| policy | answers | coverage | wrong | accuracy |
|---|---:|---:|---:|---:|
| answer everything | 252 | 1.000 | 81 | 0.679 |
| flag + certificate | 120 | 0.476 | **0** | 1.0000 |
| enumeration + certificate | 130 | 0.516 | **1** | 0.9923 |
| **role-independent certificate** | 123 | **0.488** | **0** | **1.0000** |

Sound, at 1.19 candidate worlds per case on average. **0 wrong in 123 bounds the
error at 2.44%**, not zero.

## The mechanism, on the case that broke enumeration

Seed 83, three candidates:

| depot | certifies | answer |
|---|---|---|
| region_2 | **True** | (truck_0, truck_1, truck_2) |
| **region_0** (true) | **False** | (truck_0, truck_1, truck_2) |
| region_1 | **True** | (truck_0, truck_1, truck_2) |

All three agree, so agreement alone admits it — and the answer is wrong; the
truth is (truck_0, truck_2). The **true**-depot candidate is the one that fails
to certify. Requiring all of them refuses the case.

**A check that consumes no guess cannot be misled by one.**

## What it is actually worth

**+1.2 points of coverage — marginal, and not the reason to prefer it.**

The reason is structural: the flag-plus-certificate pairing works only because
the flag is a *precondition*, guaranteeing the certificate is asked about the
right graph. That is a composition that has to be got right in the correct order
and cannot be checked locally. The role-independent form is **one check with no
precondition**, and it is slightly cheaper in coverage terms as well.

Where a finding says "these two must be applied together, in this order", a
version that needs no ordering is worth having even at equal numbers.

## Consolidation

The certificate had become load-bearing across four findings while living in
`scripts/insensitivity_certificate.py`. It is now
`symbolic_ai_generators/flood/certificate.py`, with both forms and the
distinction documented on each. The script imports it rather than defining it.

Three tests pin the difference: the role-independent form is sound; it refuses
seed 83 **where the collapsed form is misled**, asserted as a gap that must
exist; and the collapsed form's verdict provably changes when only the roles are
swapped, which is the property that makes it need a precondition at all.

## What would refute this

- 123 answers bounds the error at 2.44%. A larger sample can only tighten it,
  and nothing here says it stays clean.
- Coverage is still under half. Both certificates refuse whenever any qualifying
  vehicle's admissible subgraph has a cut edge, which is common — a sharper
  sufficient condition would recover more, and the deletion-dependency work
  suggests most of those cuts are inert.
