---
title: A certificate makes soundness free
date: 2026-08-19
status: measured
arm: insensitivity-certificate
---

## The problem it solves

Carrying at-most-one-spurious-link gives soundness 1.000 and costs **13.4× per
correct answer**, because proving that every candidate agrees means solving every
candidate. Ordering cannot help — the previous finding computed the ceiling at
25%, since a *decided* case must exhaust its candidates by construction.

The way below a ceiling like that is not to check faster but to **prove instead
of check**.

## The certificate

Flood admits a clean one, because **deleting a link is monotone**: it removes
routes and never creates them.

A vehicle qualifies iff `capacity ≥ demand` and some non-flooded route has
`min(bridge limits) ≥ mass + demand`. Under deletion:

- a vehicle that does **not** qualify cannot start qualifying — **safe for
  free**, no work at all;
- a vehicle that **does** qualify stops only if every admissible route used the
  deleted edge.

So the condition is: for each qualifying vehicle, depot and site stay connected
in *that vehicle's admissible subgraph* after removing any single edge. One DFS
per edge, against a full datalog + ASP + SMT solve sixteen times.

Monotonicity is what makes it cheap. Only the qualifying vehicles need proving.

## It is sound, and it appears exact

| | |
|---|---:|
| non-empty cases (150 seeds) | 95 |
| decided by enumeration | 50 |
| certificate fires | 50 |
| **unsound** (fired, not decided) | **0** |
| **incomplete** (decided, not fired) | **0** |

**Sufficiency is proved** by the monotonicity argument. **Necessity is measured**
— exact over 95 cases — and has an argument: if the certificate fails, some
qualifying vehicle has a cut edge whose deletion disconnects it from the site, so
that vehicle drops out and the answer changes.

The one assumption is that the flow's answer coincides with the graph condition.
ASP enumerates routes under a `max_routes` cap, which could in principle break
that, and empirically does not.

## The price

| policy | mean solves | price of soundness |
|---|---:|---:|
| enumerate every candidate | 16.0 | 13.4× |
| certificate, else enumerate (**proved** only) | 7.2 | **6.0×** |
| certificate alone (**measured converse** too) | 1.0 | **1.0×** |

Trusting only what is proved halves the cost twice over. Trusting the measured
converse makes soundness **free**: one solve for the answer, one DFS to decide
whether to give it — exactly what the collapsing reader spends, for the same
twenty correct answers. `$/correct` is unchanged.

**The difference between 13.4× and 1.0× is the difference between checking every
candidate and proving that none of them matters.**

## Why this matters beyond flood

The pattern is not flood-specific. It needs two things:

1. **A monotone perturbation** — one whose effect on the answer is one-directional,
   so half the objects are safe without any work.
2. **A structural invariant** standing in for the expensive computation —
   here 2-edge-connectivity for "a route survives".

Where both hold, an emit-rather-than-collapse policy costs nothing over
collapsing, and the pipeline gets to refuse instead of being silently wrong at no
price at all. That is a much stronger position than "soundness is affordable".

## What would refute this

- A case where the certificate fires and the enumeration disagrees. That is
  `test_the_certificate_agrees_with_the_enumeration`, asserted in **both**
  directions, and a failure is information about the flow/graph gap rather than
  a flaky test.
- A perturbation that is **not** monotone — corrupting a limit rather than
  deleting a link can push either way, and the free half of the argument
  disappears. The certificate as built covers deletions only.
- `test_the_certificate_needs_no_flow_solve` asserts it never calls the kernel,
  because its entire value is being cheap.
