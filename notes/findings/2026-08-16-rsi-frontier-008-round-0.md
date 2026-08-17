---
date: 2026-08-16
author: rsi-loop
status: provisional
related: [2026-08-16-first-on-accuracy-eleventh-on-bits]
---

# RSI loop, `frontier-008`, round 0 — ranked by `equivariant`

Development split (`eval_seed0=500000`), **not** evaluation seeds. These numbers settle a design choice; they are not comparable with anything in `runs/full179`, where every row is scored at 1000000. The chosen candidate gets one evaluation run (`--final`) and that is the number that may be quoted.

```
tag                                         label_acc label_bits  renamed    drop type_acc
------------------------------------------------------------------------------------------
frontier-008[keep_paths=2]                     0.4478      7.020   0.2190  0.2254   0.8561
frontier-008[keep_paths=12]                    0.4290      7.201   0.2179  0.2090   0.8556
frontier-008                                   0.4384      7.111   0.2154  0.2203   0.8556
frontier-008[floor_margin=0.5]                 0.4384      7.111   0.2154  0.2203   0.8556
frontier-008[floor_margin=1.0]                 0.4384      7.111   0.2154  0.2203   0.8556
frontier-008[floor_margin=1.5]                 0.4376      7.123   0.2154  0.2201   0.8553
frontier-008[abs_floor=0.0]                    0.4384      7.111   0.2154  0.2203   0.8556
frontier-008[abs_floor=0.02]                   0.4384      7.111   0.2154  0.2203   0.8556
frontier-008[keep_paths=6]                     0.4384      7.111   0.2154  0.2203   0.8556
frontier-008[floor_margin=2.0]                 0.4365      7.137   0.2145  0.2201   0.8530
frontier-008[abs_floor=0.1]                    0.4386      7.109   0.2135  0.2226   0.8556
------------------------------------------------------------------------------------------
ranked by `equivariant`. `renamed` is accuracy after permuting every symbol without refitting and `drop` is what that cost — a candidate that wins on acc and loses it all on drop bought vocabulary, not reasoning.
```

## What each candidate was for

- **`frontier-008[keep_paths=2]`** — one knob moved: keep_paths=2. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[keep_paths=12]`** — one knob moved: keep_paths=12. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008`** — the registered defaults, as the baseline every other row is read against
- **`frontier-008[floor_margin=0.5]`** — one knob moved: floor_margin=0.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[floor_margin=1.0]`** — one knob moved: floor_margin=1.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[floor_margin=1.5]`** — one knob moved: floor_margin=1.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[abs_floor=0.0]`** — one knob moved: abs_floor=0.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[abs_floor=0.02]`** — one knob moved: abs_floor=0.02. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[keep_paths=6]`** — one knob moved: keep_paths=6. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[floor_margin=2.0]`** — one knob moved: floor_margin=2.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-008[abs_floor=0.1]`** — one knob moved: abs_floor=0.1. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.

## Read the two rankings against each other

Best on accuracy: **`frontier-008[keep_paths=2]`** (0.4478). Best on the accuracy that survives renaming: **`frontier-008[keep_paths=2]`** (0.2190).
