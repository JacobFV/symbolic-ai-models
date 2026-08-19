---
title: Decidedness is (1−d)ⁿ, and pooling inverts the conclusion
date: 2026-08-19
status: measured
arm: decidedness-law
---

## A derivation instead of a fourth slogan

Three formulations of *when is carried ambiguity cheap* had failed or been
thinned: hypothesis size (wrong), collision cost (a different quantity that
agreed by accident), dependency under the carried perturbation (right variable,
two points, no form).

There is a derivation available. Carrying **at most one spurious claim of kind
K** decides exactly when no single deletion of a K claim changes the answer. With
`d` the per-deletion dependency and `n` the number of K claims:

> **decided = P(all n deletions inert) = (1 − d)ⁿ**, under independence

**No free parameter** — `d` and `n` are both measured. So this is a test *of
independence*, not a fit, and the residual has a specific meaning.

## It holds, on the right population

Non-empty cases, 60 seeds, nine claim kinds:

| kind | n | d | (1−d)ⁿ | observed | residual |
|---|---:|---:|---:|---:|---:|
| link | 8.0 | 0.243 | 0.108 | 0.059 | −0.049 |
| bridge_on | 5.0 | 0.118 | 0.535 | 0.588 | +0.053 |
| load_limit | 5.0 | 0.118 | 0.535 | 0.588 | +0.053 |
| mass | 3.0 | 0.765 | 0.013 | 0.000 | −0.013 |
| capacity | 3.0 | 0.765 | 0.013 | 0.000 | −0.013 |
| flooded | 1.5 | 0.162 | 0.767 | 0.794 | +0.027 |
| depot / needs / demand | 1.0 | 1.000 | 0.000 | 0.000 | 0.000 |

Mean absolute residual **0.036**, signs both ways, no systematic bias.

The three singleton kinds are **exact by construction** — at n=1 the identity
reduces to a definition — so they validate the measurement code and test nothing.
The real content is the six multi-claim rows, mean signed residual **+0.006**.

## Pooled, it says the opposite

Run over all 60 cases instead of the 34 non-empty ones:

| population | mean signed residual on multi-claim kinds | conclusion it supports |
|---|---:|---|
| **pooled** | **+0.131** | independence fails; (1−d)ⁿ is a lower bound |
| **non-empty** | **+0.006** | independence holds; (1−d)ⁿ is a point estimate |

I predicted the pooled answer, with a mechanism — positive correlation from
structural redundancy — and it was an **artefact of the case mix**. On a case
whose answer is already empty, almost every deletion is inert, so decidedness
floors at the empty-answer share.

**The tell was five kinds reading exactly 0.433**, which is flood's empty share.
`depot`, `needs`, `demand`, `mass` and `capacity` all landed on the same number
with different `n` and different `d`, which no real mechanism produces.

This repo has a standing rule about exactly this, and the rule earned its place
again.

## Re-checking the earlier result for the same trap

[[2026-08-19-refusing-to-collapse-costs-nothing-and-flags-every-error]] reports
carrying spurious links at **0.383 decided, giving up nothing**, over the pooled
population. Split:

| population | n | decided | collapse correct |
|---|---:|---:|---:|
| empty | 26 | 0.115 | 0.115 |
| non-empty | 34 | **0.588** | **0.588** |

The identity between the two sets holds **within each population**, and the
non-empty rate is **higher** than the pooled figure. That result was
**understated** by pooling, not inflated. The check was worth running and the
answer went the other way.

## Scope, stated so it is not overreached

The law is measured on **true worlds**, so it characterises the *domain*: given a
claim kind, how often would carrying one spurious instance of it decide. It does
**not** predict a particular reader's decidedness, because the enumeration then
runs over the *read* world, whose `d` and `n` differ — the read world here
carries extra links from bridges, the phantom, and a distractor. Applying the law
there requires measuring `d` and `n` on the read world, which needs a reader and
gives up the offline property that makes the rest of the audit useful.

So: **offline, about the domain.** The true-world link row reads 0.059 while the
read-world carrying experiment reads 0.588; those are different worlds and
comparing them directly would be the next mistake on this thread.

## What is now established

- The controlling variable is dependency under the carried perturbation.
- The functional form is `(1 − d)ⁿ`, derived and unfitted, mean absolute error
  **0.036** over six non-trivial kinds in one domain.
- Both `d` and `n` are computable from the world alone, so decidedness of an
  emit-rather-than-collapse policy can be forecast before any reader exists.

Still one domain. That remains the weakness, and scheduling and solvency cannot
test it because neither has an ambiguity worth carrying.
