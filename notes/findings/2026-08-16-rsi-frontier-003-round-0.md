---
date: 2026-08-16
author: rsi-loop
status: provisional
related: [2026-08-16-first-on-accuracy-eleventh-on-bits]
---

# RSI loop, `frontier-003`, round 0 — ranked by `equivariant`

Development split (`eval_seed0=500000`), **not** evaluation seeds. These numbers settle a design choice; they are not comparable with anything in `runs/full179`, where every row is scored at 1000000. The chosen candidate gets one evaluation run (`--final`) and that is the number that may be quoted.

```
tag                                         label_acc label_bits  renamed    drop type_acc
------------------------------------------------------------------------------------------
frontier-003[rank_tolerance=0.2]               0.3794      7.735   0.2245  0.1529   0.7448
frontier-003[min_precision=0.3]                0.4361      7.118   0.2203  0.2120   0.8540
frontier-003[rank_tolerance=0.1]               0.3955      7.514   0.2184  0.1785   0.7990
frontier-003[rank_tolerance=0.05]              0.4020      7.413   0.2169  0.1870   0.8486
frontier-003[rank_tolerance=0.02]              0.4034      7.387   0.2145  0.1870   0.8512
frontier-003                                   0.4080      7.337   0.2112  0.1929   0.8540
frontier-003[rank_tolerance=0.0]               0.4080      7.337   0.2112  0.1929   0.8540
frontier-003[keep_per_guard=2]                 0.4080      7.337   0.2112  0.1929   0.8540
frontier-003[keep_per_guard=3]                 0.4080      7.337   0.2112  0.1929   0.8540
frontier-003[min_precision=0.5]                0.4080      7.337   0.2112  0.1929   0.8540
frontier-003[min_precision=0.7]                0.3737      7.643   0.2048  0.1690   0.8540
frontier-003[keep_per_guard=1]                 0.4064      7.355   0.0320  0.3710   0.8573
------------------------------------------------------------------------------------------
ranked by `equivariant`. `renamed` is accuracy after permuting every symbol without refitting and `drop` is what that cost — a candidate that wins on acc and loses it all on drop bought vocabulary, not reasoning.
```

## What each candidate was for

- **`frontier-003[rank_tolerance=0.2]`** — one knob moved: rank_tolerance=0.2. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[min_precision=0.3]`** — one knob moved: min_precision=0.3. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[rank_tolerance=0.1]`** — one knob moved: rank_tolerance=0.1. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[rank_tolerance=0.05]`** — one knob moved: rank_tolerance=0.05. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[rank_tolerance=0.02]`** — one knob moved: rank_tolerance=0.02. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003`** — the registered defaults, as the baseline every other row is read against
- **`frontier-003[rank_tolerance=0.0]`** — one knob moved: rank_tolerance=0.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[keep_per_guard=2]`** — one knob moved: keep_per_guard=2. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[keep_per_guard=3]`** — one knob moved: keep_per_guard=3. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[min_precision=0.5]`** — one knob moved: min_precision=0.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[min_precision=0.7]`** — one knob moved: min_precision=0.7. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-003[keep_per_guard=1]`** — one knob moved: keep_per_guard=1. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.

## Read the two rankings against each other

Best on accuracy: **`frontier-003[min_precision=0.3]`** (0.4361). Best on the accuracy that survives renaming: **`frontier-003[rank_tolerance=0.2]`** (0.2245).

**They disagree, which is the finding of this round.** A ranking is a property of its metric, and the gap between these two columns is the part of the winner's score that is vocabulary.
