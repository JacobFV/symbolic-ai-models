---
date: 2026-08-14
author: agent-generation
status: open
related: [2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable]
---

`notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md`
records a live hazard: `corefer-001`'s `label_bits` moved 6.951829 → 6.954734 on
`master` while every accuracy held to nine decimal places, and the temperature
turned out **not** to be the cause. It is still open.

Re-running `node` at `mask_rate=0.15` under `configs/full179.toml` for the
infilling ladder reproduces that drift exactly and adds one fact to it.

| model | `runs/full179` | re-run today | Δ |
|---|---:|---:|---:|
| `corefer-001` `label_bits` | 6.951828893 | **6.954734342** | +2.91e-03 |
| `evidence-001` `label_bits` | 6.255003144 | 6.256926379 | +1.92e-03 |
| `routes-001` `label_bits` | 8.297689830 | 8.302012756 | +4.32e-03 |
| `routes-001` **`label_acc`** | 0.323523791 | **0.323332696** | **−1.91e-04** |

Three things narrow it:

1. **It is not nondeterminism in this checkout.** `routes-001` re-run a second
   time gives 0.323332696 and 8.302012756 — every digit.
2. **It is not the masking.** `label_floor` is bit-identical (0.143215189) in
   every row, and the floor draws its own masks under the same regime, so the
   hidden sets have not moved.
3. **It is not only bits.** The lesson's signature was "accuracies hold, bits
   move", which points at a monotone rescaling. `routes-001`'s accuracy moved by
   one fill in ~5,200. Whatever changed can reorder logits, so a post-hoc
   temperature cannot be the whole story — consistent with the lesson's own
   finding that forcing `T = 1.0` was a hundred times too large an effect.

So the drift lives in some model's *fit*, between `runs/full179` and today's
`master`. Bisecting it is a bounded job now that the floors are ruled out.
