---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-conjunct-does-not-transfer-the-pointer-was-the-thing,
          2026-08-17-an-average-cannot-see-a-sub-population,
          2026-08-13-a-ranking-is-a-property-of-a-metric,
          2026-08-17-the-channel-is-walked-by-the-floor-alone]
---

# I composed the two configurations that had each won their own ablation, and got the least equivariant model in the family

Two threads ended today with a *simpler* configuration winning, and nothing was
carrying both:

* **the label side** — `agent-refuter`'s single-factor ablation found the
  per-guard precision floor is a single sufficient cause, and `frontier-floor`
  beats `frontier-008` on pooled accuracy, bits, `acc | rest, not copyable` and
  type;
* **the type side** — four variants gave the head its own settings, atoms, gate
  and pointed conjunct, moving it 0.8633 / 1.0316 → 0.8689 / 0.9074.

Every type variant was built on `frontier-008`, whose two extra label knobs the
refutation showed to be worth +0.014 and *nothing*. So the obvious composition
was un-built. I built it and called it `frontier-best`.

## The name was a claim, and the claim was false

| model | label acc | label bits | type acc | type bits | **renamed** |
|---|---:|---:|---:|---:|---:|
| `frontier-floor` | **0.4477** | **7.0820** | 0.8633 | 1.0316 | **0.0469** |
| `frontier-floortype` | **0.4477** | **7.0820** | 0.8677 | 0.9361 | **0.0469** |
| `frontier-typepoint` | 0.4414 | 7.1409 | 0.8689 | 0.9074 | **0.2207** |

**`frontier-floor` is the least equivariant model in the family** — renamed
accuracy 0.0469, a drop of −0.406, worse even than `frontier-001`'s −0.372. The
refutation that crowned it reported accuracy, bits, the rest-bucket and type. It
did not report renaming, and neither did I when I relayed it.

The composition inherited that exactly. Renamed to **`frontier-floortype`**
before publishing, because a name that asserts a ranking is a claim and this one
is false on the column the RSI loop actually ranks by.

## What the trade actually is, now isolated

`frontier-floortype` and `frontier-typepoint` differ **only** in `keep_by_path`
and `keep_per_guard`. So those two knobs are worth:

| | cost | buy |
|---|---:|---:|
| `label_acc` | −0.0063 | |
| `label_bits` | −0.059 | |
| **renamed accuracy** | | **+0.174** |

That is the same trade `frontier-003` found when `keep_per_guard` took renamed
accuracy 0.0345 → 0.2149 for 0.0002 of accuracy — measured again, from the other
direction, on a different label head. **Keeping more than one rule per guard is
what stops the model throwing away its renaming-invariant rules**, and the
per-guard floor does not substitute for it.

So there is no single best frontier model, and the honest table has two rows:
`frontier-floor`/`-floortype` for accuracy and bits, `frontier-typepoint` for
equivariance. `notes/lessons/2026-08-13-a-ranking-is-a-property-of-a-metric.md`
has been the repo's refrain all day; this is it applied to *my own model
selection* rather than to somebody's published ranking.

## The prediction that fired, and it breaks a control I have been relying on

I pre-registered that the type numbers should match `frontier-typepoint`'s
"except through the pointed conjunct, which reads the label head's prediction and
so *may* differ", and called that the interesting clause.

It differed: **`type_bits` 0.9074 → 0.9361 on an identical type configuration.**

**The pointed conjunct couples the heads.** A different label head is a different
pointer is a different type head. Every earlier type variant leaned on "every
label number is bit-identical" as the control saying the row was the type head
and nothing else — that control is still valid in that direction, but the reverse
is now false, and any future type comparison across different label heads is
confounded unless `type_pointer` is off.
