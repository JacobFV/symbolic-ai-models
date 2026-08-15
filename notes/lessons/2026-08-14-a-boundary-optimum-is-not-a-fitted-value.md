---
date: 2026-08-14
author: lead
status: measured
related: [2026-08-14-graph-derived-roles-structure-not-locality,
          2026-08-13-spectral-roles-preregistration,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# A fit that lands on the edge of its grid has not fitted anything

## The mechanism

Fit a knob by search over a grid, land on the first or last point of that grid,
and report the value as though the data chose it. It did not. A boundary optimum
is the search saying **"I wanted to keep going and you stopped me"**, and it
cannot distinguish two completely different worlds:

- this really is the best setting, and the curve turns around just past it;
- the grid was too narrow, and the true optimum is somewhere you never looked.

Those have opposite implications and identical printouts. The value looks like a
measurement — it came out of a likelihood fit on held-out data, it has decimal
places — and it is an artefact of where the author stopped typing.

## It has happened twice here, in opposite directions, three weeks apart

**`vsa_full_gated-002`, and it wasted a whole experiment.** The question was
whether superposing two channels loses to the better one alone because the
weaker channel is *mis-weighted* rather than *subsumed*. The defence was to fit
the share on held-out training episodes by held-out likelihood. The grid stopped
at 1.0, the fit landed on 1.0, and the model came out **bit-identical to the
unweighted `vsa_full-002`**. A row that reproduces another row to every digit is
not a control, it is the same model with a longer name. Re-run with the grid
extended, it lands **interior at 1.25**, which is a real fit — and the
pre-registered claim was then refuted properly.

**`vsa_spec_pure-004`, and here the boundary was the finding.** The fitted
diffusion time ran to the **top** of its grid (`t = 16`). At that end a diffusion
kernel is smeared toward "every node has the same role" — so the likelihood was
asking for the embedding to be *erased as far as the grid allowed*. That is a
mis-specified grid by the same rule, and reporting `t = 16` as the chosen
diffusion time would have been meaningless. But the **direction** of the boundary
is informative: extending the grid can only move further toward "the embedding
contributes nothing", which is the refutation the pre-registration asked for.

The two cases are the whole lesson. The same symptom means "your experiment did
not run" in one case and "your hypothesis is dead" in the other, and **only the
direction of the boundary tells you which**.

### Amendment, 2026-08-14: the second case study was wrong, and this lesson's own guard is why

An independent refuter did what guard 1 below says to do and never got done for
`vsa_spec_pure-004`: extended the grid to `(4, 16, 64, 256, 1024)` and refit.
**The fit stays at `t = 16`** and `vsa_spec_wide_pure-004` comes out bit-identical
to `vsa_spec_pure-004` (0.105 / −0.044 / 7.380 / 0.212 / copy 0.096, every digit).
So `t = 16` was **an interior optimum all along**, not a mis-specified grid, and
the paragraph above describing it as one is wrong. The conclusion it supported —
the eigenmap is refuted — is untouched, and "a wider grid cannot rescue it" has
gone from an argument to a measurement.

Worse, and the reason this amendment matters more than the correction: the same
sweep's *winning* arm, `vsa_hks-004`, fitted `knob = 0.5` — the **bottom** of
`(0.5, 1, 2, 4)` — in all four registered rows, and nobody applied this lesson to
it. Extended to `(0.0625 … 4)`, it lands **interior at 0.25 and gains +0.053 of
label lift**. The guard was invoked on the arm that lost, where it was not needed
and gave the wrong reading, and skipped on the arm that won, where it was worth
0.053. See `notes/lessons/2026-08-14-a-guard-applied-only-to-the-arm-that-lost.md`
and `notes/findings/2026-08-14-the-graph-roles-survive-the-attack-and-their-bandwidth-does-not.md`.

The lesson below is unharmed. Its example was.

## The cost

One registered model, one sweep, and one write-up that would have reported a
null as a null while measuring nothing at all. Cheap this time only because the
bit-identical rows were noticed before publication.

## The guards

1. **A boundary fit is a failed fit until re-run wider.** Extend the grid past
   the optimum in the direction it ran and refit. If it moves interior, the first
   number was noise. If it stays pinned, you have learned the direction and
   should report *that*, never the pinned value.
2. **Two rows identical to every printed digit are one row.** That is the cheapest
   available detector and it caught this. Any variant that reproduces its
   predecessor exactly has not varied anything — say so and find out why before
   writing a word about it.
3. **State the grid in the note, not just the fitted value.** `t = 16` means
   nothing without "over `[1 … 16]`". A fitted parameter reported without its
   search range is unauditable, which is the same defect as
   [[2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable]].

## The general form, for the next one

**Every fitted scalar in this repo should be checked for where it sits in its own
search range before it is believed** — the mixture weight `c`, the softmax
temperature, `top_k`, the diffusion time, `FRAME_THRESHOLD`. Interior is a fit.
Edge is a question.
