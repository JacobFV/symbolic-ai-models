---
date: 2026-08-14
author: agent-refuter
status: measured
related: [the-action-readout-clears-the-repair-floor-on-179-lessons,
          abstention-on-repair-is-below-chance, action-readout,
          readout-is-a-knob]
---

# Pre-registration: the two attacks on the action-readout finding

> **Outcome, added after the fact and nothing above it edited:**
> `notes/findings/2026-08-14-the-readout-survives-both-attacks-and-its-comparison-row-does-not.md`.
> `C` = 0.3609 (threshold for "survives in the form claimed" was ≥ 0.2966);
> `W24` = 0.0767, which is *below* `wrap` at 8 rather than above it, so the
> primary test landed in the "stronger form" branch. `abstain` = 0.0866 against
> `random` 0.0543 — Attack 2's outcome (2) *and* (3) both landed, which the
> thresholds did not anticipate could happen together. The one thing this
> document got wrong is recorded as its own lesson:
> `notes/lessons/2026-08-14-an-unmeasured-confound-has-an-unknown-sign.md`.

Written **before any of the runs below were started**, by an agent that did not
write the finding it is attacking. Committed on its own so that the thresholds
are in git ahead of the numbers, which is the only defence this repo has found
against a reading drifting toward the write-up.

## What is being attacked

`notes/findings/2026-08-14-the-action-readout-clears-the-repair-floor-on-179-lessons.md`
(`status: provisional`). Same fitted `corefer-001`, same 179 lessons, same 716
episodes, same 2,632 fills, `runs/agents-full179-readout/`:

| row | `repair` `label_acc` | floor (`context`) | lift |
|---|---:|---:|---:|
| `graphread` (graph readout, all 24 candidates) | 0.5080 | 0.2025 | +0.383 |
| `wrap` (text readout, top 8 of 24) | 0.0851 | 0.2025 | −0.147 |

Gap **0.4229**. The finding attributes it to the readout. Its author names two
attacks and ran neither.

## The confound, restated precisely

The two rows differ in **two** things, not one. `wrap.max_actions` defaults to
8 (`symbolic_ai_agents/agents/wrapped/agent.py`, `self.get("max_actions", 8)`,
and the `extra` of both runs sets no such key — the `max_actions: 24` visible in
both `summary.json` files is the *environment's* candidate count, a different
setting with the same name). `graphread` has no cap at all. So `wrap` chooses
among 8 strings and `graphread` among 24, and the finding's own text concedes
that "some unknown part of the 0.423 is therefore truncation rather than
readout".

Write `G` = `graphread`, `W` = `wrap`, `F` = floor, `C` = the new
`graphread-capped` row — the graph readout under `wrap`'s own shortlist,
produced by `PolicyAgent.shortlist`, which is the method `wrap` calls, moved to
the base class so that there is one ranking rule and not two. Then

    G − W  =  (G − C)  +  (C − W)
    0.4229 =   the cap    the readout

and neither term has ever been measured.

## Attack 1 — thresholds, fixed in advance

`C` is the number that decides it. `F` = 0.2025 and `G − W` = 0.4229.

1. **The finding dies and becomes a `max_actions` artefact** if **`C` ≤ 0.2025**.
   The graph readout, handed the same candidate set as the text readout, would
   then fail to clear the floor, and the headline would not be "reading the
   emission as a move clears the floor" but "not being truncated clears the
   floor" — a fact about `wrap`'s cost model, which the repo already knew.
2. **The finding survives in the form claimed** if **`C` ≥ 0.2966** — that is,
   `C` clears the floor *and* the readout term `(C − W)` is at least half of the
   0.4229. The minimum defensible sentence is then intact: on identical
   candidate sets, the graph readout beats the text readout and clears the
   structural floor.
3. **The finding is wounded but alive** if **0.2025 < `C` < 0.2966**. It would
   still be true that the readout clears the floor, and false that the readout
   is worth 0.423; the headline number would have to be restated as the capped
   lift and the note's summary rewritten.

Chosen because "a majority of the gap" is the weakest claim that still makes the
readout the *principal* term. Nothing about the outcome is predicted here; I
expect (2) or (3) and would not bet between them.

**The handicap is deliberately a little harsher than `wrap`'s.** Where the cap
removes every vote the readout had, `graphread-capped` abstains onto the shared
prior, while `wrap` in that situation still ranks the eight it scored. That can
only push `C` down, which is the direction a control should err in. The rate is
counted (`CappedGraphReadAgent.truncated_out`) and will be reported, because if
it is large the asymmetry stops being a rounding error and `C` becomes a lower
bound rather than an estimate.

### `wrap` at 24 is the *primary* test, and the capped row is the secondary

Amended after the wiring check and before any 179-lesson run. On
`configs/agents-small.toml` — six lessons, a wiring check and not a result —
`graphread-capped` lost every vote to the cap on 61 of 140 decisions. If that
rate holds at scale, the harshness the paragraph above waves at is not a
rounding error: `C` would be dominated by the abstention tax rather than by the
readout, and outcome (1) could be reached for a reason that is a property of my
control rather than of the finding. A control that can fail for its own reasons
is a weak control, so it is demoted.

The clean version needs no invented handicap at all: **run `wrap` at
`max_actions=24`.** Then `wrap` and `graphread` choose among the *same 24
strings*, both mechanisms behave as they natively do, and the only surviving
difference between the two rows is what the model's output is read as — which is
exactly the claim. It costs 3x the forward passes of the 8-candidate run and is
affordable, which is the reason the author's runtime argument does not stand.

Fixed in advance, writing `W24` for that row and `F` = 0.2025:

* **The finding dies** if `W24` ≥ 0.2025 and `G − W24` < 0.21 — the text readout
  would clear the floor once untruncated, and the readout gap would be less than
  half the headline. The published 0.423 would then be mostly `max_actions`.
* **The finding survives, and in a stronger form than it was written in**, if
  `G − W24` ≥ 0.21 *and* `W24` < 0.2025: both the size and the sign hold on
  identical candidate sets, with no handicap invented by anyone.
* **The sign claim alone dies** if `W24` ≥ 0.2025 while `G − W24` ≥ 0.21. The
  note's sentence that "reading the identical model as text loses to that table"
  would be false and truncation all along; "the graph readout is worth ~0.2 to
  ~0.4 label_acc over the text readout" would stand.

`C` remains worth having as the third rung of the ladder — it is the only row
that prices the cap at a fixed readout — but the verdict is `W24`'s.

## Attack 2 — the abstention baseline, thresholds fixed in advance

`notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md` measures the
abstain-everywhere control at **0.0431** against chance at 0.1034 and a floor of
0.3966 — on six lessons, 116 fills, 3% of the curriculum, and this repo has had
a slice invert a result six times. It has never been taken at 179 lessons, and
every coverage-weighted reading of an agent column assumes it.

Measured here by a registered `abstain` agent whose `prefer` returns `ABSTAIN`
unconditionally, rather than through a model that happens to emit nothing — a
control reached by way of a broken model stops being that control the moment
someone fixes the model. `random` is in the same sweep so that "below chance"
is a comparison inside one config rather than across two.

1. If **`abstain` < `random` < `F`** at 179 lessons, the slice result replicates
   and the `graphread` finding is *helped*: `graphread` abstains on 3.1% of
   decisions and `wrap` on none, so the abstention tax falls on `graphread` and
   its 0.5080 is a slight understatement.
2. If **`abstain` ≥ `random`**, the six-lesson finding was a slice artefact and
   should be marked `refuted` — a separate result, and one worth having.
3. **The reading that would bite.** If **`abstain` ≳ 0.0851** — that is, if
   silence scores what `wrap` scores — then `wrap`'s row is indistinguishable
   from saying nothing, and the finding's inference that "the text readout is
   *actively* bad here" is unearned. Being below the floor would be what
   everything that is not the structural table gets on `repair`, not a fact
   about text. The gap `G − W` would survive as arithmetic and its
   *interpretation* would not.

## What is being built, and why beside rather than in place

Two new registered agents, both additions: `graphread-capped`
(`symbolic_ai_agents/agents/graphread/capped.py`) and `abstain`
(`symbolic_ai_agents/agents/abstain/`). `graphread` and `wrap` are untouched in
behaviour — `wrap._shortlist` now delegates to the base-class method it used to
inline, with the ranking unchanged — so every number already published under
those names still means what it meant.

`configs/agents-readout179.toml` writes down the settings
`runs/agents-full179-readout/` was produced at (`n_train=8`, `n_eval=4`,
`repair` only), so the new rows are the same run and not a reconstruction.
`graphread` and `wrap` are re-run inside it rather than quoted from the existing
directory: a re-run that does not reproduce 0.5080 and 0.0851 is itself a
refutation, and it is 11 minutes.
