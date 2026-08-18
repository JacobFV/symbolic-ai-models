---
title: Provenance.derivation shipped to eight kernels and none of them set it
date: 2026-08-18
status: provisional
tags: [architecture, kernels, provenance, fusion]
---

## The gap

`notes/findings/2026-08-18-the-registry-could-not-see-an-identity-conflict-and-load-order-rewrote-4992-facts.md`
added `Provenance.derivation` so a claim could say how it came to be known —
`measured`, `derived`, `simulated`, `synthetic`, `reconstructed`, `unresolved`
— and named the gap explicitly in its own "what would refute it" section:
**"`derivation` is unset on every claim the eight kernels produce. The field
exists and nothing populates it, which is the fourth instance this week of a
contract shipping ahead of its use."**

Checked directly: `grep -rn "Provenance(" symbolic_ai_kernels/` finds eight call
sites, one per kernel (`datalog`, `asp`, `smt`, `lean`, `geo`, `economy`,
`rigid`, `egraph`), and none of the eight passed `derivation`. Every claim a
kernel has ever produced in this repo was `derivation=""` — indistinguishable
from *unstated*, which `prefer_measured` treats as the lowest rank but does not
refuse, so a kernel claim fusing against a genuinely measured one would have
silently lost by rank rather than by an explicit "this was never a measurement"
statement. It never mattered yet because no kernel-vs-source fusion has been
exercised on real data (`ultimate_parent`'s conflicts are both `measured`,
filed by GLEIF itself) — but the invariant the registry finding built
(*derived can never become measured*) was resting on a field nobody had wired.

## Fix

Seven kernels get `derivation="derived"` — each computes a claim from a
projection of existing world facts via inference, search, arithmetic or proof,
none of it a new observation. `rigid@1` gets `derivation="simulated"`: it
integrates equations of motion forward in time, which is GLEIF's own vocabulary
distinction between "derived" (a logical consequence) and "simulated" (a
model run), not a style choice.

## Guard

`tests/test_kernel_conformance.py` already exists for exactly this pattern —
its own docstring: *"Three fields in this substrate have now been found
documented and never exercised... Three is a pattern rather than three
accidents."* `derivation` is the fourth. Added
`test_every_kernel_states_how_its_claims_were_derived`, parametrized over every
registered kernel, reading the kernel's module source (not just the class —
`datalog@1` and `rigid@1` build their claims in a module-level helper the class
calls, not a method, and a class-only check would have missed both) for
`"derivation="`. Same "declaring conformance is not conforming, read the
source" discipline the rest of the file uses.

291 tests pass across kernel conformance and all eight kernels' own suites, run
because they are exactly the tests that could notice a Provenance-construction
change.

## What would refute it

- A ninth kernel added later without a conformance table entry — caught
  already by `test_every_registered_kernel_appears_in_the_table`, unrelated to
  this change but the reason the new test is safe to add the same way.
- The static "derivation= appears somewhere in the module" check would pass if
  the string appeared in an unrelated, unreached branch. The real guard against
  that is `check_entitlement`-style: nobody has yet added a runtime assertion
  that every claim *actually returned* carries a derivation, only that the
  source states one exists. A kernel that computes `derivation` conditionally
  and misses a branch would not be caught here.
