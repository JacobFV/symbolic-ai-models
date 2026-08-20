---
title: 1 Bt/$ is cleared 5.7–17.7× on bounded tasks and missed on open prose — once throughput is charged for being right
date: 2026-08-19
status: measured
arm: pipeline-cost
---

Asked where the programme sits against **one billion tokens per dollar**, the raw
answer is "comfortably past it" and the raw answer is the wrong one.
`CLAUDE.md` has said so since before this arm: *a throughput number is an input
and never a headline, because a system can be arbitrarily fast and understand
nothing.* That was a rule with nothing enforcing it.

`Ledger.correct_tokens_per_usd` enforces it: throughput multiplied by the share of
attempts that clear the floor. **A system reading a billion tokens a dollar at its
floor earns exactly zero**, which is now a unit test.

| workload | tokens/$ | rate | floor | **correct tokens/$** | vs 1 Bt/$ |
|---|---|---|---|---|---|
| solvency (reader + kernels) | 37.8 B | 1.000 | 0.533 | **17.65 B** | **17.7×** |
| scheduling | 34.7 B | 1.000 | 0.642 | **12.43 B** | **12.4×** |
| flood (ASP + SMT) | 8.7 B | 1.000 | 0.342 | **5.69 B** | **5.7×** |
| real prose, `headquarters` | 3.8 B | 0.280 | 0.045 | **0.90 B** | 0.9× |
| real prose, `parent` | 3.8 B | 0.144 | 0.010 | **0.51 B** | 0.5× |
| real prose, `country` | 3.8 B | 0.390 | 0.298 | **0.35 B** | 0.4× |

## The two halves separate cleanly

**Bounded tasks clear the target by 5.7× to 17.7×.** Their rate is 1.000, so
almost all of the raw throughput survives the charge — the loss is only the floor,
and even solvency's 0.533 floor leaves 17.7 Bt/$.

**Open prose misses it, on every relation measured**, at 0.35–0.90 Bt/$. The raw
throughput is identical — 3.8 Bt/$ for reading, the same machinery — and the
charge removes 76% to 91% of it, because the reader is right about a seventh of
`parent` and its `country` accuracy sits close to a 0.298 floor.

**Same reader, same price sheet, same tokens. The difference is entirely
correctness**, which is what the metric was built to expose.

## What it does to the comparison with an API

Raw, a $3/Mtok API is 0.00033 Bt/$ and the ratio is **11,500×–113,000×**. Charged
for correctness the bounded ratio is unchanged in character (the API would also be
charged, and no accuracy has been measured for it) — but on prose the honest
statement changes shape: **the throughput advantage is intact and the capability
is not**, and quoting the first without the second is the exact failure the rule
exists to prevent.

## Why this belongs in `cost.py` rather than in a note

The number had been derived ad hoc twice from a price sheet. Both times the
derivation was correct and both times it was raw throughput, which is the number
the repo's own rule says not to lead with. Putting `tokens_per_usd` and
`correct_tokens_per_usd` side by side in the ledger makes the honest one as cheap
to quote as the flattering one.

## Limits

- `correct_tokens_per_usd` charges `rate − floor`, so it is a *above-floor*
  throughput and inherits every objection to the floor it is given. `country`'s
  0.298 floor is why its charged figure is the lowest despite the second-highest
  rate.
- The prose rows use one measured ingestion (2,502 articles, 566,513 tokens,
  26.6 s) applied to each relation's accuracy; reading is shared across relations
  in a real system, which would raise all three.
- No API accuracy is measured anywhere, so the ratio above is our cost and our
  accuracy against their published price.
