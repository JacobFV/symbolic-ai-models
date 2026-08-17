---
date: 2026-08-16
author: rsi-loop
status: provisional
related: [2026-08-16-first-on-accuracy-eleventh-on-bits]
---

# RSI loop, `frontier-soft`, round 0 — ranked by `bits`

Development split (`eval_seed0=500000`), **not** evaluation seeds. These numbers settle a design choice; they are not comparable with anything in `runs/full179`, where every row is scored at 1000000. The chosen candidate gets one evaluation run (`--final`) and that is the number that may be quoted.

```
tag                                         label_acc label_bits  renamed    drop type_acc
------------------------------------------------------------------------------------------
frontier-soft[vote_sharpness=8.0]              0.4039      6.951   0.2141  0.1891   0.8540
frontier-soft[max_voters=64]                   0.4009      6.957   0.2171  0.1817   0.8540
frontier-soft                                  0.4009      6.959   0.2169  0.1811   0.8540
frontier-soft[vote_sharpness=4.0]              0.4009      6.959   0.2169  0.1811   0.8540
frontier-soft[max_voters=24]                   0.4009      6.959   0.2169  0.1811   0.8540
frontier-soft[vote_sharpness=2.0]              0.3957      6.972   0.2186  0.1732   0.8540
frontier-soft[vote_sharpness=1.0]              0.3909      6.982   0.2179  0.1694   0.8540
frontier-soft[vote_sharpness=0.5]              0.3883      6.984   0.2177  0.1664   0.8540
frontier-soft[max_voters=8]                    0.4018      7.030   0.2156  0.1853   0.8540
------------------------------------------------------------------------------------------
ranked by `bits`. `renamed` is accuracy after permuting every symbol without refitting and `drop` is what that cost — a candidate that wins on acc and loses it all on drop bought vocabulary, not reasoning.
```

## What each candidate was for

- **`frontier-soft[vote_sharpness=8.0]`** — one knob moved: vote_sharpness=8.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft[max_voters=64]`** — one knob moved: max_voters=64. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft`** — the registered defaults, as the baseline every other row is read against
- **`frontier-soft[vote_sharpness=4.0]`** — one knob moved: vote_sharpness=4.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft[max_voters=24]`** — one knob moved: max_voters=24. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft[vote_sharpness=2.0]`** — one knob moved: vote_sharpness=2.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft[vote_sharpness=1.0]`** — one knob moved: vote_sharpness=1.0. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft[vote_sharpness=0.5]`** — one knob moved: vote_sharpness=0.5. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.
- **`frontier-soft[max_voters=8]`** — one knob moved: max_voters=8. A coordinate sweep says which knobs move anything at all before any pair of them is tried together.

## Read the two rankings against each other

Best on accuracy: **`frontier-soft[vote_sharpness=8.0]`** (0.4039). Best on the accuracy that survives renaming: **`frontier-soft[vote_sharpness=2.0]`** (0.2186).

**They disagree, which is the finding of this round.** A ranking is a property of its metric, and the gap between these two columns is the part of the winner's score that is vocabulary.
