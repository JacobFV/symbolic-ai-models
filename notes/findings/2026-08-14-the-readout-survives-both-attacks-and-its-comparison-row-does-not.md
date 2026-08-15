---
date: 2026-08-14
author: agent-refuter
status: measured
related: [the-action-readout-clears-the-repair-floor-on-179-lessons,
          abstention-on-repair-is-below-chance,
          pre-registering-the-two-attacks-on-the-action-readout,
          action-readout, readout-is-a-knob,
          slices-have-inverted-results-eight-times]
---

# The action readout survives both attacks. Its comparison row does not, and neither does a second published finding.

**Full curriculum**, not a slice: all 179 generatable lessons, 716 evaluation
episodes from seeds at 1,000,000, 2,632 scored fills, `repair` only,
`n_train=8`, `n_eval=4`, `configs/agents-readout179.toml`. Every number below is
`repair` `label_acc` from a `symbolic-ai-agents` run directory, named per row.
The floor is `context` at **0.2025** in every one of them — refitted inside each
run from its own training episodes and *run in the environment*, with `floor_by`
naming `context` in all seven runs made here and in the two published ones they
are read against.

Written by an agent that did not write the finding it was attacking. The
thresholds were fixed in
`notes/decisions/2026-08-14-pre-registering-the-two-attacks-on-the-action-readout.md`
and committed (`2058be1`) before any of these runs was started.

## The verdicts, first

1. **The headline survives both pre-registered attacks**, and the primary one by
   more than its threshold required. Reading `corefer-001`'s graph emission as a
   move clears the `repair` floor; nothing else in this package ever has.
2. **The confound the author flagged runs the *opposite* way to the worry.**
   Removing `wrap`'s truncation makes `wrap` slightly *worse*, so the published
   0.4229 gap was an understatement of the readout difference on equal candidate
   sets, not an inflation of it.
3. **The comparison row is not a measurement.** `wrap` scores 0.0851 and an
   agent that says nothing at all scores **0.0866** on the same 2,632 fills. The
   text readout of this model on `repair` is indistinguishable from silence, so
   the finding's inference that "the text readout is *actively* bad here" is
   unearned and should be struck.
4. **The two rows differed in three things, not one.** The candidate cap, the
   readout, and — unnamed by anyone until now — *where the confidence map was
   fitted*. All three are measured below. Equalising all of them at once leaves
   the gap at **0.4320**, the largest of the four ways of taking it.
5. **A different published finding is refuted outright.**
   `notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md` is a
   six-lesson slice, and at 179 lessons its headline **inverts**: abstention is
   0.032 *above* chance, not 0.06 below it.

## The ladder

Same fitted `corefer-001`, same 179 lessons, same 716 episodes, same 2,632
fills, same floor, same shared prior. Sorted by score.

`lift` is `(score − floor) / (1 − floor)` against the 0.2025 floor, the column
the harness prints; 0 is the floor and 1 is perfect.

| row | readout | cands | calibrated on | run directory | `label_acc` | lift |
|---|---|---:|---|---|---:|---:|
| `graphread` | graph | 24 | `repair` | `runs/agent-sweep/graphread/` | **0.5080** | **+0.383** |
| `graphread-capped` | graph | 8 | `repair` | `runs/agent-sweep/graphread-capped/` | **0.3609** | **+0.199** |
| *floor (`context`)* | — | 24 | — | (refitted in each) | *0.2025* | *0* |
| `abstain` | none | — | — | `runs/agent-sweep/abstain/` | 0.0866 | −0.145 |
| `wrap` | text | 8 | `choice` | `runs/agent-sweep/wrap/` | 0.0851 | −0.147 |
| `wrap` | text | 24 | `choice` | `runs/agents-readout179/wrap-24/` | 0.0767 | −0.158 |
| `wrap-envcal` | text | 24 | `repair` | `runs/agents-readout179/wrap-envcal-24/` | 0.0760 | −0.159 |
| `random` | none | — | — | `runs/agent-sweep/random/` | 0.0543 | −0.186 |

Four ways of taking the same comparison. **The gap grows as the differences are
removed**, which is the opposite of what a confounded result does:

| comparison | what is still unequal | gap |
|---|---|---:|
| `graphread` − `wrap`@8 | candidate set, calibrator | 0.4229 *(as published)* |
| `graphread` − `wrap`@24 | calibrator | **0.4312** |
| `graphread` − `wrap-envcal`@24 | *nothing but the readout* | **0.4320** |
| `graphread-capped` − `wrap`@8 | the handicap loaded onto the graph side | 0.2758 |

`graphread` reproduced the published `runs/agents-full179-readout/gr-corefer/`
to sixteen significant figures — 0.5079787234042553, lift 0.383039542639352,
`return` 0.4623453711093373, `success` 0.2011173184357542 — from a separate
process on a separate day. The re-run was itself a refutation attempt and it did
not land.

There is no copy ceiling to quote here and the reason matters. `Repair.reset`
only asks about a node when `tok.itos[ids[i]] in options`, so **the gold answer
is always among the 24 candidates** and the ceiling on this column is 1.0. That
is not the model harness's masked-node task, whose ceiling is 0.722; the two
numbers are not on one scale and must not be read against each other.

## Attack 1 — the `max_actions` confound, measured twice

The two published rows differed in **two** things, which the finding conceded
without quantifying: `wrap.max_actions` defaults to 8
(`self.get("max_actions", 8)`; the `max_actions: 24` in both `summary.json`
files is the *environment's* candidate count, a different setting with the same
name), and `graphread` has no cap at all.

### The secondary control: the same readout under the same shortlist

`graphread-capped` votes only within `PolicyAgent.shortlist(obs, obs.actions, 8)`
— literally the method `wrap` calls, moved to the base class so there is one
ranking rule and not two copies to drift apart, with
`tests/test_readout_controls.py` pinning that they agree, that the cap can only
narrow a vote, and that the cap switched off reproduces `graphread` exactly.

**0.3609.** The pre-registered thresholds were: dies at ≤ 0.2025, survives in
the form claimed at ≥ 0.2966. It cleared the survival threshold by 0.064. The
decomposition of the published gap is therefore

    G − W  =  (G − C)   +  (C − W)
    0.4229 =   0.1471       0.2758
               the cap       the readout
               34.8%         65.2%

and 65.2% is a **lower bound** on the readout's share, because the control was
built harsher than `wrap` on purpose: where the cap removed every vote the
readout had, `graphread-capped` abstains, and `wrap` never pays that. So part of
the 0.1471 attributed to the cap is the abstention tax rather than the candidate
set.

How much of it: `runs/agent-sweep/graphread-capped/policy.txt` instruments
**388 of 2,703** acting-time decisions losing every vote to the cap. Deriving
the same quantity from the two coverage lines instead — `graphread` spoke on
2,620 of 2,703, `graphread-capped` on 2,233 — gives 470 − 83 = **387**. The two
accountings disagree by one decision and I did not chase it; nothing here turns
on 0.04% of a column, but the disagreement is real and is recorded rather than
resolved by picking. Both say the cap silences roughly one decision in seven.

The whole run was repeated after a fix to that counter and reproduced
`label_acc` 0.3609422492401216 and lift 0.19866603144354456 unchanged, so the
determinism claim holds for this row as well as for `graphread`.

### The primary control: no handicap invented by anyone

Demoted the capped row to secondary before running it, for that reason, and ran
the direct thing instead: **`wrap` at `max_actions=24`**, so both readouts
choose among the same 24 strings and each behaves as it natively does. The
author skipped this on runtime grounds — "three times the forward passes on a
run that already took thirteen minutes". It took **395 s**
(`runs/agents-readout179/wrap-24/`), against 437 s for the 8-candidate run in
the published directory. The runtime argument was wrong.

**0.0767.** Pre-registered: survives in the stronger form if `G − W24` ≥ 0.21
and `W24` < 0.2025. Both hold — `G − W24` = **0.4312**, larger than the
published 0.4229, and `W24` is 0.126 below the floor.

**Removing the truncation made `wrap` worse.** Not by much — 0.0084, which is
about 22 fills of 2,632 and inside what a paired binomial would call noise — so
the honest statement is that the cap was costing `wrap` nothing at all. The
same cap costs `graphread` 0.147. One handicap, opposite effects.

The likely mechanism is readable off the code and is **not** measured here, so
it is a hypothesis: `Repair._nearby` orders candidates by `abs(j - i)` in the
pre-order linearisation, nearest visible label first, and
`PolicyAgent.shortlist` breaks its near-ties on `opts.index(a)`. With the shared
prior almost flat over `repair`'s label space, the "top 8" is therefore close to
"the 8 nearest visible labels" — a locality heuristic `wrap` was getting for
free and paying nothing for the loss of, while the graph readout has real
information about the other sixteen. That would be worth measuring and has not
been.

**What this does to the finding.** Nothing bad. The confound was real, its size
is now known, and its sign is the reverse of the worry every reader would have
had. The pre-registered kill conditions for Attack 1 were not met.

## Attack 2 — the abstention baseline at 179 lessons

Measured by a registered `abstain` agent whose `prefer` returns `ABSTAIN`
unconditionally, rather than through a model that happens to emit nothing — a
control reached by way of a broken model stops being that control the moment
someone fixes the model. `tests/test_readout_controls.py` pins the explicit
agent move-for-move against the accidental route the slice note used.

### The slice inverts

| | six lessons, 116 fills | 179 lessons, 2,632 fills |
|---|---:|---:|
| `abstain` | 0.0431 | **0.0866** |
| `random` (chance) | 0.1034 | **0.0543** |
| floor (`context`) | 0.3966 | 0.2025 |
| abstention vs chance | **−0.060** | **+0.032** |

`notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md` names this
exactly as its live risk — *"a bigger slice reversing it. **Untested, and this
is the live risk**: 116 fills over six lessons, and this repo has had a small
slice invert a result six times."* It reverses. The note's title claim is false
at full scale and **has been marked `refuted`** in this branch; its *mechanism*
section — that
`action_prior` is counted over `Episode.answer` while `repair`'s actions are
node labels, so the base distribution is near-uniform and `shortcut_purity` of
the mass is then moved by a cheat fitted for a different action space — survives
and is still worth having. `runs/agent-sweep/abstain/policy.txt` confirms the
shape at scale: **515 prior counts, 0.254 of the mass on `shortest`**.

What changed is which side of chance that lands on. **Both rows moved**, in
opposite directions and by similar amounts — abstention 0.0431 → 0.0866, chance
0.1034 → 0.0543 — so this is not one row drifting past a fixed other, and I have
measured no mechanism for either move. (Chance falling as the lesson set grows
is what larger candidate sets would do, and that is a guess.) What is measured
is that the direction of the comparison is a property of the lesson mix, which
is exactly what a slice cannot report.

Ninth inversion;
`notes/lessons/2026-08-13-slices-have-inverted-results-eight-times.md` needs its
title incremented, which is left to whoever owns that file — appending to a
shared lessons file from a worktree is what the workflow rules forbid.

### The reading that bites the finding

Pre-registered as outcome (3), and it landed:

> If **`abstain` ≳ 0.0851** — that is, if silence scores what `wrap` scores —
> then `wrap`'s row is indistinguishable from saying nothing, and the finding's
> inference that "the text readout is *actively* bad here" is unearned.

`abstain` = **0.08662614**. `wrap` = **0.08510638**. Silence beats the text
readout by 0.00151976, which is **exactly four fills of 2,632**. On `success`
the two are identical to sixteen significant figures — 0.019553072625698324 in
both run directories — so across 716 episodes the text readout did not change
which ones came out solved even once.

So the sentence in the finding that has to go is this one:

> A pure truncation story would put `wrap` somewhere between a shortlisted
> reader and a full one, not **below the structure-only baseline** — so the
> honest reading is that the text readout is actively bad here.

Being below the structure-only baseline is not evidence of anything. On
`repair` at 179 lessons *everything* that is not the structural lookup table
sits between 0.045 and 0.087, in both configs this repo has run it at:

| | `runs/agent-sweep/` (`n_train=8`, 716 eps, 2,632 fills) | `runs/agents-full179/` (`n_train=20`, 1,432 eps, 5,407 fills) |
|---|---:|---:|
| `context` = floor | **0.2025** | **0.2643** |
| `careful` | — | 0.2643 |
| `abstain` | 0.0866 | — |
| `wrap` | 0.0851 | — |
| `recall` | — | 0.0725 |
| `random` | 0.0543 | 0.0601 |
| `shortcut` | — | 0.0451 |

The two columns are not comparable to each other — different depth, different
floor, different episode count — and neither needs to be for the point: within
each, the lookup table is alone above 0.09 and everything else is bunched at the
bottom, `graphread` excepted. `wrap` is not actively bad. `wrap` is *inert*, and
an inert row is not a comparison.

**This makes the headline stronger and its stated form weaker.** The finding
presents 0.423 as "the same fitted model, one thing swapped", implying a
contrast between two readouts. What is actually measured is a contrast between
one readout and *nothing*: the graph readout clears the floor by a third of the
headroom, and the text readout of the same model contributes no measurable
signal at all on this environment. "The readout is a knob" is confirmed. "Text
loses to the structural table" is a statement about the abstention path, not
about text.

## The third difference, which nobody had named

The finding says of the two rows: *"same model, same 179 lessons, same 716
episodes, same 2,632 fills, same floor, same shared prior and calibrator. One
thing differs."* The calibrator is not the same. That was worth a run — this
repo's standing lesson is that harness decisions span 0.15 to 2.0 while models
span 0.1 — and it turned out to be worth 0.0007.

`WrappedModel._calibrate` builds a **fresh `choice` environment** and fits its
confidence map there — on a run configured `envs = ["repair"]`, an environment
the run does not contain, whose action space is the curriculum's
multiple-choice answers rather than node labels. `GraphReadAgent._calibrate`
fits through the environments the run was fitted with, and says why in its own
docstring: `mask_rate` and `max_actions` change how separable a decision is, so
a map fitted at one and applied at another is a map for a different question.
`graphread` was right about the hazard and `wrap` was left carrying it.

That map is the weight on the mixture between an agent's votes and the prior. A
map that returns near-zero on `repair` reduces `wrap` to the prior — which is
precisely the number `wrap` scores. `wrap-envcal` is `wrap` with `graphread`'s
calibration and nothing else, pinned both ways in
`tests/test_readout_controls.py` (it must *be* `wrap` exactly on a
`choice`-only run, and must not be on a `repair` one).

Run at 24 candidates, so that it is `graphread`'s equal in everything a row can
be equal in — same model, same episodes, same prior, same 24 strings, same
calibration environment — it scores **0.0760**
(`runs/agents-readout179/wrap-envcal-24/`, `policy.txt` confirming
"scores at most 24 actions per decision / calibrated in: repair", 466 s).

So the calibrator is *not* the explanation, and the negative result is the
informative half. The hypothesis was that `wrap` collapses onto the prior
because a map fitted on `choice` returns near-zero confidence on `repair` — a
mis-set dial. Fit the map on `repair` and `wrap` still collapses onto the prior,
by 0.0007 more. **A correctly fitted calibrator assigning near-zero confidence
to these votes is the calibrator working**, not failing: it has measured, on
held-out training episodes and through the environment the agent acts in, that
`corefer-001`'s text ranking of `repair`'s candidates carries no information,
and it has priced it accordingly. The inertness is in the votes.

Removing all three differences at once leaves

    graphread        (graph, 24 candidates, calibrated on repair)   0.5080
    wrap-envcal      (text,  24 candidates, calibrated on repair)   0.0760
                                                            gap    0.4320

which is the **largest** of the four ways of taking this comparison, and the
only one in which the readout is the sole surviving difference. The three text
rows — 0.0851, 0.0767, 0.0760 — span 0.009 between them and all three sit below
`abstain`'s 0.0866. `wrap-envcal` is 28 fills of 2,632 below silence.

The finding claimed one difference and had three. All three are now measured,
two of them run the wrong way for the finding's own story, and the effect
survives every one of them at close to full size. That is a better result than
the note was written to claim.

## What was checked against the run directories

Every number the attacked finding quotes, because four numbers in a recent
finding here were wrong until someone checked. All of these verify:
`label_acc` 0.5080 / 0.0851, floor 0.2025, lifts +0.383 / −0.147, `return`
0.4623 / 0.0726 against floor 0.1963, `success` 0.2011 / 0.0196 against 0.0698,
716 episodes, 2,632 fills, "spoke on 2,620 of 2,703 decisions (96.9%)", the
0.4229 gap, and the `n_train=20` restatement `(0.5080 − 0.2643)/(1 − 0.2643)` =
0.331 against `runs/agents-full179/context/summary.json`'s floor of 0.2643.

One of the finding's three open caveats is settled in passing. It worried that
"`floor_by` is not `context` at `n_train=20`". It is: `runs/agents-full179/`
records `floor_by: context` at 0.2643 on `repair` for all five agents there. The
floor family does not move with depth, so the depth caveat is about the floor's
*value* only.

## What would still refute this, and has not been tried

* **One model.** Everything here is `corefer-001`. If the graph readout clears
  the floor only for this architecture, "the readout is a knob" is a claim about
  one model's emission and not about the readout. `runs/agent-sweep/` is set up
  to answer this — one more sweep with a different `extra.model`.
* **The channel.** `channel=symbol` throughout. `node` and `both` are knobs the
  readout was built to expose and neither has been taken at 179 lessons.
* **The locality hypothesis above**, parked in
  `notes/questions/2026-08-14-is-the-top-8-shortlist-just-locality.md` with the
  run that would answer it. It is read off two functions, not measured. If it
  holds, the `graphread-capped` row is measuring the shortlist as well as the
  readout and should stop being quoted as a clean decomposition — though the
  uncapped comparison, where no shortlist appears anywhere, is untouched.
* **`n_train=20`.** Everything here is the shallow config. The floor is
  0.2025 rather than the published 0.2643, and `graphread` clears both, but no
  agent-side row at `n_train=20` exists for the graph readout.

## Status

`measured`, for the two attacks that were pre-registered and run — and only for
those. Everything in "what would still refute this" is untried.

Two other agents' notes were edited in this branch rather than left as
recommendations, because both invite it in their own text and leaving a struck
paragraph standing in a `provisional` note is worse than touching someone else's
file:

* `2026-08-14-the-action-readout-clears-the-repair-floor-on-179-lessons.md` →
  `measured`, with a banner recording the three corrections and the "actively
  bad" paragraph struck in place. Its own "Refutation status" section asked for
  exactly these two attacks, in this order.
* `2026-08-13-abstention-on-repair-is-below-chance.md` → `refuted`, with a
  banner. Its own "What would refute this" section named a bigger slice
  reversing it as the live risk.

What has *not* been done, and is the lead's call rather than mine: `RESEARCH_LOG.md`
records that no agent in `symbolic_ai_agents` clears its floor (`df40011`). That
is now false — `graphread` clears it at `n_train=8` by +0.383, and by +0.331
restated against the published `n_train=20` floor. Promoting it needs the
`n_train=20` row that does not exist yet, and rewriting a shared file from a
worktree is the one thing this repo's workflow rules forbid outright.
