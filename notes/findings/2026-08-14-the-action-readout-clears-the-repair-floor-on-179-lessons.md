---
date: 2026-08-14
author: agent-readout
status: provisional
related: [action-readout, readout-is-a-knob,
          abstention-on-repair-is-below-chance]
---

# Reading the graph head as an action clears the `repair` floor on 179 lessons

**Full curriculum**, not a slice: all 179 generatable lessons, 716 evaluation
episodes from seeds at 1,000,000, **2,632 scored fills**. Depth is `n_train=8`,
`n_eval=4` — shallower than `configs/agents-full.toml`'s 20/8, and why that
matters is in the caveats.

## The standing claim this bears on

`df40011` ("The interactive half, measured: only `repair` discriminates, and
nothing clears it") records that **no agent in `symbolic_ai_agents` clears its
floor**, and that `repair` is the only environment that separates agents at all
(spread 0.29, against `choice`'s 0.014).

## What was measured

One agent, `graphread(corefer-001, channel=symbol)` — the `action` readout of
`notes/findings/2026-08-13-action-readout.md`, which reads a model's
`node_votes` emission as a move instead of scoring the rendered s-expression as
text.

`runs/agents-full179-readout/gr-corefer/`:

| metric | agent | floor | lift |
|---|---:|---:|---:|
| `label_acc` (per filled node) | **0.5080** | 0.2025 | **+0.383** |
| `return` | 0.4623 | 0.1963 | +0.331 |
| `success` (every node in the episode right) | 0.2011 | 0.0698 | +0.141 |

`floor_by: context` on all three — the strongest of `random`/`shortcut`/`context`,
fitted on the training episodes and **run in the environment**, which is the only
floor that cannot be wrong about what the policy scores.

## It is not a coverage artifact

The standing worry about every `graphread` number
(`notes/questions/2026-08-13-coverage-versus-accuracy-in-an-agent-column.md`) is
that an agent's column mixes *how often it spoke* with *how good it was*, and
that abstaining on `repair` lands **below chance**. Here it does not apply:

    spoke on 2,620 of 2,703 decisions (96.9%)

read straight off `policy.txt`. The agent answered essentially everything, so
0.5080 is a reasoning number and not a selection effect.

## The caveat that has to be stated first, because it moves the floor

This run is `n_train=8`; the published `runs/agents-full179` is `n_train=20`.
The floor is refitted inside each run, so a **shallower run has a weaker floor**
— `context` scores 0.2025 here and 0.2643 there. The lift above is therefore
measured against a floor fitted on less data than the published one.

Both readings, so nobody has to take the flattering one on trust:

* against **its own** floor, fitted at the same depth as the agent: +0.383;
* against the **published** `n_train=20` floor of 0.2643, which the agent did
  not get to train against: `(0.5080 − 0.2643) / (1 − 0.2643)` = **+0.331**.

The conclusion is the same either way, which is the only reason it is worth
stating: **this is the first agent in the package to clear the `repair` floor,
and it does so by a third of the headroom.**

## Why it is a fact about the readout and not about `corefer`

`corefer-001` is not new and has been in `runs/agents-full179`'s reach the whole
time — through `wrap`, which reads the same fitted model as *text*. On the
six-lesson slice `wrap` spans 0.0086–0.0603 across twelve architectures, a range
that **straddles the abstain-everywhere baseline of 0.0431**: reading these
models as text on `repair` is indistinguishable from saying nothing.

So the model was always able to do this and the harness could not ask it. What
changed is the readout. That is the claim
`notes/decisions/2026-08-13-readout-is-a-knob.md` was written to test —
*a representation that only works for one readout has been short-circuited* —
and this is the strongest form of it the repo has: the same fitted model, the
same environment, the same prior and calibrator, one thing swapped.

## The refutation was attempted and did not land

The condition written down before the control ran: *if `wrap(corefer-001)` at
these exact settings clears the floor too, the gain is depth or configuration
and not the readout.* It does not clear it. It does not come near it.

`runs/agents-full179-readout/wrap-corefer/` — same model, same 179 lessons, same
716 episodes, same 2,632 fills, same floor, same shared prior and calibrator.
**One thing differs: what the model's output is read as.**

| | `label_acc` | `return` | `success` |
|---|---:|---:|---:|
| `graphread` — read as a move | **0.5080** (+0.383) | 0.4623 (+0.331) | 0.2011 |
| `wrap` — read as text | **0.0851** (−0.147) | 0.0726 (−0.154) | 0.0196 |
| floor (`context`) | 0.2025 | 0.1963 | 0.0698 |

The two sit on **opposite sides of the floor**, 0.423 apart on the same fitted
model. Reading `corefer-001`'s output as a move beats a structure-only lookup
table by a third of the headroom; reading the identical model as text loses to
that table.

### The confound in it, unquantified and stated anyway

`wrap` **scores at most 8 of `repair`'s 24 candidates** (`max_actions=8`, read
off its own `policy.txt`), shortlisted by the shared prior. Where the answer
falls outside that shortlist, `wrap` cannot pick it at any quality of reading.
Some unknown part of the 0.423 is therefore truncation rather than readout, and
I did not measure how much: `wrap` at 24 candidates is three times the forward
passes on a run that already took thirteen minutes, and it would not fit the
box's kill window.

What the confound does **not** explain is the sign. The floor picks from all 24
and scores 0.2025; `wrap` scores 0.0851. A pure truncation story would put `wrap`
somewhere between a shortlisted reader and a full one, not **below the
structure-only baseline** — so the honest reading is that the text readout is
actively bad here and truncation makes it worse by an amount nobody has
measured. The clean version of this control is `graphread` restricted to the
same top-8 shortlist, which is cheap and was not built.
2. **The abstain-everywhere control does not land at the floor here.** The
   agents-side abstention path is measured to score *below chance* on `repair`
   at slice scale, and if that holds at 179 lessons then part of any gap between
   two agents is the abstention machinery rather than either agent. `graphread`
   abstains on 3.1% of decisions, so this can move the number a little and
   cannot produce it.
3. **`floor_by` is not `context` at `n_train=20`.** The floor is a maximum over
   three policies and a different winner at a different depth would mean the
   floor family, not the depth, is what moved.

## Refutation status

**Still `provisional`, and the control landing does not change that.** The
reason is the one this repo keeps relearning: every control here was designed by
the agent that built the readout, and an author-designed control that passes is
exactly the shape of a hollow one. What can honestly be said is that the
refutation condition was written down first, attempted, and not met.

The two an independent refuter should take, in order:

1. **`graphread` on the same top-8 shortlist `wrap` gets.** The cheap version of
   the control above, and the one that removes the confound it still carries.
   If the gap collapses, the finding is about `max_actions` and not about the
   readout.
2. **The abstain-everywhere baseline at 179 lessons.** It is measured to sit
   *below chance* on `repair` at slice scale. `graphread` abstains on 3.1% of
   decisions and `wrap` on none, so this can shift the comparison a little and
   cannot manufacture 0.423 — but the number has not been taken at this scale
   and every coverage-weighted reading here assumes it.
