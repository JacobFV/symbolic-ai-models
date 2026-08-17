---
date: 2026-08-16
author: rsi-loop
status: provisional
related: [2026-08-16-first-on-accuracy-eleventh-on-bits]
---

# RSI loop, `frontier-pointsoft`, round 0 — ranked by `equivariant`

Development split (`eval_seed0=500000`), **not** evaluation seeds. These numbers settle a design choice; they are not comparable with anything in `runs/full179`, where every row is scored at 1000000. The chosen candidate gets one evaluation run (`--final`) and that is the number that may be quoted.

```
tag                                         label_acc label_bits  renamed    drop type_acc
------------------------------------------------------------------------------------------
frontier-pointsoft[vote_sharpness=0.0]         0.3923      6.478   0.3070  0.0846   0.8760
frontier-pointsoft[vote_sharpness=0.125]       0.4007      6.471   0.3055  0.0933   0.8760
frontier-pointsoft[vote_sharpness=0.25]        0.4028      6.465   0.3055  0.0941   0.8760
frontier-pointsoft[vote_sharpness=0.5]         0.4085      6.448   0.3048  0.1026   0.8760
frontier-pointsoft[map_vote_weight=0.25]       0.4108      6.440   0.2976  0.1087   0.8760
frontier-pointsoft[vote_sharpness=1.0]         0.4187      6.429   0.2962  0.1217   0.8760
frontier-pointsoft[map_vote_weight=0.0]        0.3169      8.431   0.2957  0.0168   0.8760
frontier-pointsoft[vote_sharpness=2.0]         0.4286      6.405   0.2754  0.1526   0.8760
frontier-pointsoft[map_vote_weight=0.5]        0.4288      6.398   0.2754  0.1531   0.8760
frontier-pointsoft[max_voters=64]              0.4359      6.388   0.2603  0.1766   0.8760
frontier-pointsoft                             0.4376      6.392   0.2601  0.1787   0.8760
frontier-pointsoft[vote_sharpness=4.0]         0.4376      6.392   0.2601  0.1787   0.8760
frontier-pointsoft[map_vote_weight=1.0]        0.4376      6.392   0.2601  0.1787   0.8760
frontier-pointsoft[max_voters=24]              0.4376      6.392   0.2601  0.1787   0.8760
frontier-pointsoft[max_voters=8]               0.4422      6.462   0.2576  0.1838   0.8760
frontier-pointsoft[vote_sharpness=8.0]         0.4476      6.407   0.2559  0.1878   0.8760
------------------------------------------------------------------------------------------
ranked by `equivariant`. `renamed` is accuracy after permuting every symbol without refitting and `drop` is what that cost — a candidate that wins on acc and loses it all on drop bought vocabulary, not reasoning.
```

## What each candidate was for

- **`frontier-pointsoft[vote_sharpness=0.0]`** — one knob moved: vote_sharpness=0.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[vote_sharpness=0.125]`** — one knob moved: vote_sharpness=0.125. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[vote_sharpness=0.25]`** — one knob moved: vote_sharpness=0.25. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[vote_sharpness=0.5]`** — one knob moved: vote_sharpness=0.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[map_vote_weight=0.25]`** — one knob moved: map_vote_weight=0.25. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[vote_sharpness=1.0]`** — one knob moved: vote_sharpness=1.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[map_vote_weight=0.0]`** — one knob moved: map_vote_weight=0.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[vote_sharpness=2.0]`** — one knob moved: vote_sharpness=2.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[map_vote_weight=0.5]`** — one knob moved: map_vote_weight=0.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[max_voters=64]`** — one knob moved: max_voters=64. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft`** — the registered defaults, as the baseline every other row is read against
- **`frontier-pointsoft[vote_sharpness=4.0]`** — one knob moved: vote_sharpness=4.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[map_vote_weight=1.0]`** — one knob moved: map_vote_weight=1.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[max_voters=24]`** — one knob moved: max_voters=24. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[max_voters=8]`** — one knob moved: max_voters=8. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-pointsoft[vote_sharpness=8.0]`** — one knob moved: vote_sharpness=8.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.

## Read the two rankings against each other

Best on accuracy: **`frontier-pointsoft[vote_sharpness=8.0]`** (0.4476). Best on the accuracy that survives renaming: **`frontier-pointsoft[vote_sharpness=0.0]`** (0.3070).

**They disagree, which is the finding of this round.** A ranking is a property of its metric, and the gap between these two columns is the part of the winner's score that is vocabulary.
