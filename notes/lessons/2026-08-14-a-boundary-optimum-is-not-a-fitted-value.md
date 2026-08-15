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
