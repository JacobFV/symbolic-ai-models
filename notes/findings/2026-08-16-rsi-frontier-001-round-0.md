---
date: 2026-08-16
author: rsi-loop
status: provisional
related: [2026-08-16-first-on-accuracy-eleventh-on-bits]
---

# RSI loop, `frontier-001`, round 0 — ranked by `equivariant`

Development split (`eval_seed0=500000`), **not** evaluation seeds. These numbers settle a design choice; they are not comparable with anything in `runs/full179`, where every row is scored at 1000000. The chosen candidate gets one evaluation run (`--final`) and that is the number that may be quoted.

```
tag                                         label_acc label_bits  renamed    drop type_acc
------------------------------------------------------------------------------------------
frontier-001[resolver_forms=const+copy]        0.2960      8.587   0.2224  0.0755   0.8573
frontier-001[min_precision=0.3]                0.4357      7.128   0.0375  0.3931   0.8573
frontier-001[min_support=6]                    0.4116      7.287   0.0322  0.3763   0.8580
frontier-001[frontier_repeats=2]               0.3986      7.462   0.0322  0.3644   0.8454
frontier-001                                   0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[min_support=12]                   0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[min_support=24]                   0.4005      7.427   0.0320  0.3651   0.8514
frontier-001[min_precision=0.5]                0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[max_rules=400]                    0.4045      7.377   0.0320  0.3695   0.8404
frontier-001[max_rules=2000]                   0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[max_rules=6000]                   0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[frontier_repeats=3]               0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[resolver_forms=const+copy+map]    0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[resolver_forms=copy+map]          0.4064      7.355   0.0320  0.3710   0.8573
frontier-001[min_support=48]                   0.3919      7.519   0.0318  0.3560   0.8247
frontier-001[frontier_repeats=5]               0.4154      7.257   0.0312  0.3816   0.8641
frontier-001[min_precision=0.7]                0.3728      7.649   0.0307  0.3422   0.8573
------------------------------------------------------------------------------------------
ranked by `equivariant`. `renamed` is accuracy after permuting every symbol without refitting and `drop` is what that cost — a candidate that wins on acc and loses it all on drop bought vocabulary, not reasoning.
```

## What each candidate was for

- **`frontier-001[resolver_forms=const+copy]`** — one knob moved: resolver_forms=const+copy. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[min_precision=0.3]`** — one knob moved: min_precision=0.3. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[min_support=6]`** — one knob moved: min_support=6. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[frontier_repeats=2]`** — one knob moved: frontier_repeats=2. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001`** — the registered defaults, as the baseline every other row is read against
- **`frontier-001[min_support=12]`** — one knob moved: min_support=12. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[min_support=24]`** — one knob moved: min_support=24. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[min_precision=0.5]`** — one knob moved: min_precision=0.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[max_rules=400]`** — one knob moved: max_rules=400. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[max_rules=2000]`** — one knob moved: max_rules=2000. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[max_rules=6000]`** — one knob moved: max_rules=6000. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[frontier_repeats=3]`** — one knob moved: frontier_repeats=3. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[resolver_forms=const+copy+map]`** — one knob moved: resolver_forms=const+copy+map. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[resolver_forms=copy+map]`** — one knob moved: resolver_forms=copy+map. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[min_support=48]`** — one knob moved: min_support=48. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[frontier_repeats=5]`** — one knob moved: frontier_repeats=5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-001[min_precision=0.7]`** — one knob moved: min_precision=0.7. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.

## Read the two rankings against each other

Best on accuracy: **`frontier-001[min_precision=0.3]`** (0.4357). Best on the accuracy that survives renaming: **`frontier-001[resolver_forms=const+copy]`** (0.2224).

**They disagree, which is the finding of this round.** A ranking is a property of its metric, and the gap between these two columns is the part of the winner's score that is vocabulary.
