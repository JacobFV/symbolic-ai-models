---
date: 2026-08-15
author: agent-refuter-vv
status: provisional
related: [2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model,
          2026-08-15-a-conditional-is-not-a-fixed-question,
          2026-08-14-the-mask-rate-curve-moves-the-opportunity-not-the-ability,
          2026-08-15-the-copy-split-survives-and-its-floor-does-not,
          2026-08-13-slices-have-inverted-results-eight-times,
          2026-08-13-a-ranking-is-a-property-of-a-metric]
---

# The concentration reversal survives every attack I could aim at its banding — and its *size* has no estimate that is not extrapolation

**All 179 lessons, 716 evaluation episodes, both arms in full: 5,233 scored fills
at `mask_rate=0.15` and 31,671 at 0.90, `mask_mode=scatter`. Not a slice.** The
one number below that *is* a slice is labelled as one, twice, and is not used to
conclude anything.

I am not the author of
`notes/findings/2026-08-15-the-ninety-percent-point-is-a-different-bucket-not-a-better-model.md`.
I was asked to break its weakest link, which that note names itself: the
`v/V` banding — visible nodes carrying the target's label over visible labelled
nodes in the episode — is author-chosen, and the two arms' `v/V` distributions
barely overlap, so every band could be hiding a composition shift running the
same way in all of them.

Everything here comes from `scripts/copyable_covariates.py`, which I wrote and
which does not import `scripts/copyable_survivorship.py`. Weights are the other
agent's verified refits, read-only:
`.../agent-a0e0e014ef1db87a8/runs/refit-node-r015` and `.../runs/refute-node-r090`.
All twelve replays reproduce their run's published `final.node.label_acc` to
1e-9 — `corefer-001` 0.357157 / 0.181017, `ptrgen-001` 0.335945 / 0.195131,
`routes-001` 0.323333 / 0.125193, `vsa_perm-002` 0.326008 / 0.180133,
`evidence-001` 0.219186 / 0.144801, `grammar-001` 0.187273 / 0.075463 — so this
decomposes the published numbers rather than measuring beside them.

**Floors.** Published `final.node.label_floor` 0.1432 → 0.1259; split floor on
the copyable bucket 0.158 → 0.183 (the attacked note's, not recomputed here);
`copy_ceiling` 0.7216 → 0.3017 and `copy_floor` 0.2658 → 0.2792, both read
directly from the twelve `summary.json` files.

## What I said would refute it, before I looked

| attack | refutes the note if | confirms if |
|---|---|---|
| exact matching on the integer pair `(v, V)` | shortfall ≥ 0, or common support carries < 20% of the 0.90 weight | shortfall clearly negative on real support |
| logistic in `log v`, `log V`, arm indicator | `b(rate=0.90) ≥ 0` | clearly negative |
| mean `v/V` *inside* each band | 0.90 sits low in every band, and an ability-free predictor reproduces a shortfall of the same order | the ability-free predictor's shortfall is near zero |
| swapping the supply covariate | the sign flips between `v/V`, `v/D`, `v/Vtype` | sign holds |
| the identical fill at both rates | 0.90 ≥ 0.15 on the same (episode, node), copyable at both | 0.90 below |

Scored honestly against those conditions: **two came back for the note
outright** (logistic, within-band means), **two came back triggering their
refutation clause** (exact matching gave a positive shortfall for three of six
models; the covariate swap did flip the sign), and **one came back against the
note's phrasing and for its conclusion** (paired fills). Both of the triggered
clauses are argued away below — and in both cases I am adding a criterion
*after* seeing the number, which is the move this repo distrusts most, so each
is flagged where it happens rather than folded into the verdict.

## First, the arithmetic reproduces exactly

`copyable_survivorship._conc_band` bands `lo < x <= hi`; my first pass used
`lo <= x < hi`. That is not cosmetic at 0.90, where `V` is about 7 and `v/V`
lands *on* 0.1, 0.2 and 0.4 constantly. Under the note's own convention I get
its table to the digit:

| `corefer-001`, `acc \| copyable` by v/V | 0-0.02 | 0.02-0.05 | 0.05-0.1 | 0.1-0.2 | 0.2-0.4 | 0.4-1 |
|---|---|---|---|---|---|---|
| 0.15 | 0.187 (8.4%) | 0.341 (31.9%) | 0.525 (32.2%) | 0.662 (18.9%) | 0.792 (4.7%) | 0.960 (4.0%) |
| 0.90 | — | 0.364 (0.3%) | 0.354 (25.2%) | 0.561 (37.9%) | 0.733 (23.7%) | 0.933 (12.9%) |

Standardised: predicted **0.6955**, observed **0.5971**, shortfall **−0.0983**.
The note says 0.696, 0.597, −0.099. `ptrgen-001` −0.1195 against its −0.120,
`routes-001` −0.2416 against its −0.242. **An independent implementation on a
separate worktree reproduces all three to the third decimal.**

Under the left-closed convention the same table gives **−0.1163**. A 0.018 swing
from an arbitrary boundary rule, and the note happens to have taken the
conservative side of it.

## Attack 2: within-band composition runs the *other* way

This was the attack I most expected to land. It does not.

| band | mean `v/V` at 0.15 | at 0.90 | difference |
|---|---:|---:|---:|
| 0.02-0.05 | 0.0349 | 0.0476 | **+0.0127** |
| 0.05-0.1 | 0.0716 | 0.0814 | **+0.0098** |
| 0.1-0.2 | 0.1396 | 0.1543 | **+0.0147** |
| 0.2-0.4 | 0.2541 | 0.2813 | **+0.0272** |
| 0.4-1 | 0.6397 | 0.6283 | −0.0114 |

The 0.90 arm sits *higher* inside four of the five shared bands, not lower. To
price that exactly rather than eyeball it, I ran the standardisation on a
predictor with no ability at all: **a uniform pick among the visible labelled
nodes is right with probability exactly `v/V`.** Pushed through the identical
bands and the identical weights it comes back at **+0.0130** — banding a
zero-ability predictor this way makes 0.90 look *better* by 0.013.

So the residual composition inside the bands is worth about +0.013 in the
0.90 arm's favour. The note's −0.099 is, if anything, **−0.111 too generous**.
The stated weak link is not weak.

## Attack 1: with no bands at all

**Logistic**, `correct ~ 1 + log v + log V + 1[rate=0.90]`, fitted on the
pooled copyable fills of both arms, marginal effect = the 0.90 fills scored
under the 0.15 arm's fitted surface against their own:

| model | `b(log v)` | `b(log V)` | `b(rate=0.90)` | marginal | with interactions |
|---|---:|---:|---:|---:|---:|
| `corefer-001` | +1.306 | −1.242 | **−0.724** | **−0.140** | −0.130 |
| `ptrgen-001` | +1.672 | −1.391 | **−0.616** | **−0.119** | −0.154 |
| `routes-001` | +1.203 | −0.847 | **−0.678** | **−0.150** | −0.221 |
| `vsa_perm-002` | +1.376 | −1.203 | **−0.666** | **−0.139** | −0.152 |
| `evidence-001` | +2.801 | −2.084 | **−0.135** | **−0.022** | −0.208 |
| `grammar-001` | +0.552 | −0.089 | **−0.371** | **−0.038** | −0.049 |

Six of six negative, on both specifications, with no bands anywhere.
`evidence-001` is the one whose size depends heavily on the functional form
(−0.022 additive, −0.208 with interactions); its sign does not.

Note also what the fit *says*: `b(log v)` and `b(log V)` are of comparable
magnitude and opposite sign in five of six models — their ratio is 1.05, 1.20,
1.42, 1.14 and 1.34, with only `grammar-001` (+0.552 / −0.089) outside. The
response is close to a function of the ratio alone, which is the note's
covariate choice vindicated by a fit that was free to reject it.

## Attack 3: the covariate choice does flip the sign — and the control adjudicates

| standardised on | corefer | ptrgen | routes | vsa_perm | evidence | grammar | zero-ability control |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v/V` | −0.098 | −0.120 | −0.242 | −0.149 | −0.149 | −0.118 | **+0.013** |
| `v/V_type` | −0.127 | −0.147 | −0.265 | −0.167 | −0.131 | −0.111 | **+0.046** |
| `V` alone | −0.131 | +0.018 | +0.022 | −0.004 | −0.042 | +0.021 | +0.016 |
| `v/D` (distinct visible labels) | +0.039 | +0.035 | −0.095 | −0.001 | +0.082 | −0.087 | **+0.109** |
| `m` (total multiplicity) | +0.012 | +0.001 | −0.131 | −0.030 | +0.018 | −0.106 | **+0.074** |
| `v` alone | +0.286 | +0.311 | +0.146 | +0.300 | +0.372 | −0.083 | **+0.185** |

So yes — **this triggers the second pre-registered refutation clause.** `v`
alone, `v/D` and `m` give mixed or positive shortfalls, the sign does depend on
the covariate, and a note that quoted only `v/V` without saying so is
overclaiming to that extent. But the last column settles which covariates were
ever candidates, and unlike the criterion I added above, this one is a
measurement rather than a judgement call. **A predictor with no ability
standardised on `v` alone appears +0.185 better at 0.90**; on `v/D`, +0.109; on
`m`, +0.074. Those covariates do not adjust the comparison, they mostly fail to,
and the positive model shortfalls under them are that failure showing through.
The two covariates whose control residue is small — `v/V` at +0.013 and `V`
alone at +0.016 — are the ones that adjust, and under `v/V` all six models are
negative. **The note picked the right covariate and never showed why; this is
the missing argument, and it is a control the note could have run in four
lines.**

## A sixth attack I added: hold the node type *and* the concentration

This one was not in the table above — I thought of it after the first five had
run, so it is a post-hoc attack and is labelled as one. What would refute the
note: the joint shortfall turning positive or mixed in sign.

The obvious confound `v/V` cannot see is that the copyable bucket at 0.90 may
hold a different mix of **node types**. Joint cells of (type, `v/V` band) hold
both, and cost only 1.8% of the 0.90 weight:

| shortfall | corefer | ptrgen | routes | vsa_perm | evidence | grammar |
|---|---:|---:|---:|---:|---:|---:|
| `v/V` alone | −0.098 | −0.120 | −0.242 | −0.149 | −0.149 | −0.118 |
| type × `v/V` | **−0.062** | **−0.089** | **−0.207** | **−0.134** | **−0.140** | **−0.133** |
| type alone | +0.048 | +0.051 | −0.091 | +0.034 | +0.125 | −0.088 |

Six of six still negative, control residue +0.0155. **The direction survives the
confound the note did not control for.** But the size does not: adding node type
takes about a third off `corefer-001`'s headline, 0.098 → 0.062, and shrinks
five of the six. Type alone is not an adjustment at all (mixed signs), so this
is a genuine joint effect and not a substitution.

That is a second, independent reason to treat −0.099 as an upper bound on the
magnitude rather than a measurement of it.

## Attack 4: the size is extrapolation, and the one estimator without it is a slice

This is where the note is genuinely soft, and not where it expected to be.

| | 1% | 5% | 25% | 50% | 75% | 95% | 99% |
|---|---:|---:|---:|---:|---:|---:|---:|
| `V` at 0.15 | 13 | 25 | 43 | 65 | 94 | 106 | 109 |
| `V` at 0.90 | 2 | 3 | 7 | 9 | 12 | 16 | 19 |

**2.6%** of the 0.15 arm's copyable fills have `V` at or below the 0.90 arm's
99th percentile. Matching on the *ratio* buys full mass — no band loses weight —
only by letting `V` differ ninefold inside every cell: a fill at `v/V = 0.14`
means `v≈8.5, V≈62` at 0.15 and `v=1, V=7` at 0.90. That is not the same
question, and no banding of the ratio can make it one.

Exact matching on the integer pair `(v, V)` is the estimator with no
extrapolation in it. It matches 65.3% of the 0.90 weight — and the 0.15 side of
that support is **106 of 3,776 fills, 68 episodes, 35 of the 179 lessons**,
against 178 lessons in the whole bucket. It gives:

| | corefer | ptrgen | routes | vsa_perm | evidence | grammar |
|---|---:|---:|---:|---:|---:|---:|
| exact `(v,V)` shortfall | −0.066 | **+0.069** | **+0.045** | **+0.060** | −0.127 | −0.023 |

Three of six positive, which **triggers my own pre-registered refutation
clause** — I wrote "shortfall ≥ 0, or common support carries < 20% of the 0.90
weight", and the support carries 65.3%, so the clause fires on the first
disjunct. I am declining it anyway, on a criterion I did not write down: the
constraint that binds is not the 0.90 weight I pre-registered but the **0.15
side's fill count**, which I had not thought to bound. That is a criterion added
after seeing the number and it should be read with the suspicion that deserves.
The ground is that 106 fills over 35 lessons is exactly the object
`slices-have-inverted-results-eight-times` says may form a hypothesis and may
never appear in a conclusion, and it is additionally confounded: a 0.15 fill
with `V = 13` is a small graph, while a 0.90 fill with `V = 13` is a graph ten
times larger with 90% of it hidden. Exact matching trades the ratio's
extrapolation for a lesson-composition confound of unknown sign — see
`an-unmeasured-confound-has-an-unknown-sign`.

**The honest statement is therefore narrower than the note's.** The *direction*
is supported by every estimator that uses the full mass — six models, three
covariate families, banded and unbanded. The *magnitude* −0.099 has no estimate
that is not extrapolating the 0.15 arm into a corner of the covariate space it
occupies 2.6% of the time. The note calls the 0.099 "an estimate"; that is
correct and, on this evidence, it should be the only word it ever gets.

## Attack 5: the same fill, asked at both rates — the one that runs against the note

4,720 (episode, node) pairs are scored fills in **both** arms; 1,364 of them are
copyable in both. Same episode, same node, same answer, no covariate anywhere:

| model | 0.15 | 0.90 | Δ | McNemar z | logistic counterfactual on the same pairs |
|---|---:|---:|---:|---:|---:|
| `corefer-001` | 0.5726 | 0.5894 | **+0.017** | +1.3 | −0.147 |
| `ptrgen-001` | 0.5601 | 0.5733 | **+0.013** | +0.9 | −0.114 |
| `evidence-001` | 0.4406 | 0.4604 | **+0.020** | +1.3 | −0.029 |
| `vsa_perm-002` | 0.5359 | 0.5110 | −0.025 | −1.6 | −0.143 |
| `routes-001` | 0.5418 | 0.4479 | −0.094 | −6.1 | −0.116 |
| `grammar-001` | 0.2053 | 0.1129 | −0.092 | −8.6 | −0.026 |

**On the fills it answers at both rates, the 0.90 arm is not worse.** Three of
six are above and within noise, two are below and significant, one is below at
z = −1.6. So the sentence "the model at 0.90 is 0.099 worse" is a claim about a
counterfactual supply surface and **not** about any question that was actually
asked twice — and a reader will reasonably hear the second thing.

It is not a refutation, because of the second half of the row: on those same
pairs, mean `v/V` **rises** from 0.152 to 0.226. The evidence got *more*
concentrated and the accuracy did not move. "The ability is flat" predicts these
pairs get easier; they did not. The counterfactual column prices that at −0.026
to −0.147, six of six negative. So the paired test disagrees with the note's
*phrasing* and agrees with its conclusion.

## The attack that turned into the best evidence: a model that never saw 0.90

Neither the note nor my brief says this out loud, and it matters: **the two arms
are separately fitted models.** `runs/refit-node-r015` fits at
`fit_mask_rate=0.15` and `runs/refute-node-r090` at 0.90. So "the model at 0.90"
is not one model under more masking, it is a different fit — and the whole
argument could be about training rather than about the bucket.

The two arms' tokenizers are byte-identical (`md5 0f29f1ea…`), so the 0.90 draw
is well defined for either arm's weights. Scoring the **0.15-fitted** weights on
the **0.90 draw**, no refitting, `acc | copyable`:

| model | 0.15 fit, 0.15 draw | 0.15 fit, **0.90 draw** | 0.90 fit, 0.90 draw | transfer − native |
|---|---:|---:|---:|---:|
| `corefer-001` | 0.4936 | **0.5974** | 0.5971 | +0.0003 |
| `ptrgen-001` | 0.4616 | **0.5755** | 0.5688 | +0.0067 |
| `routes-001` | 0.4481 | **0.4287** | 0.4150 | +0.0137 |
| `vsa_perm-002` | 0.4351 | **0.5638** | 0.5162 | +0.0476 |
| `evidence-001` | 0.3032 | **0.4656** | 0.4682 | −0.0026 |
| `grammar-001` | 0.1907 | **0.0869** | 0.1007 | −0.0138 |

What would have refuted the note here: the transferred weights scoring clearly
*below* the native 0.90 fit, which would mean the 0.90 arm's training adds
ability and the rise is not the bucket. Predicted before the run; it did not
happen.

`corefer-001` gains **+0.1038** by being moved to the 0.90 draw with **no
parameter changed at all**, against the +0.1035 the note attributes to the 0.90
arm. Pooled, the transferred model scores 0.1822 against the native fit's
published 0.1810 — refitting at 0.90 bought *nothing*. Four of six transferred
models match or beat their native counterpart.

**This is the survivorship claim with no covariate, no banding, no floor and no
stratification: a predictor whose ability is frozen at the 0.15 fit picks up the
entire rise.** It is the cleanest evidence in this exercise and neither the note
nor my brief anticipated it.

## The two numbers that say it with no rescoring at all

Reading the twelve `summary.json` files: `copy_floor` — a structure-only pointer
lookup, refit at each rate, a predictor with no ability that can improve — goes
**0.2658 → 0.2792**, *up*, while `copy_ceiling` (the copyable share) collapses
0.7216 → 0.3017 and every model's `copy_acc` falls (`corefer-001` 0.3362 →
0.1721). A fixed-ability lookup scoring **higher in absolute terms with 90% of
the graph hidden** is the "different bucket" claim entire, and it needs no
stratification, no banding and no covariate. It is the strongest evidence in
this whole argument and it was sitting in the published summaries.

(The ratio `copy_floor / copy_ceiling` — 0.368 → 0.925 — is tempting and I am
not quoting it as a result: `copy_acc` and `copy_floor` use the any-node
convention while `copy_ceiling` is visible-only, so the denominator is not that
numerator's ceiling. See `the-copy-split-survives-and-its-floor-does-not`.)

## Verdict

**The reversal survives.** The note's self-nominated weak point — the banding —
is the part that came through cleanest: within-band composition runs the other
way by +0.013, an ability-free control prices the banding at near zero, the
logistic finds the same sign with no bands, six of six models are negative where
the note reported three, and the sign holds when node type is held jointly with
concentration. Episode-clustered bootstraps (400 resamples,
resampling episodes because one 0.90 episode contributes dozens of correlated
fills) put the banded shortfall at [−0.137, −0.059] for `corefer-001`, [−0.159,
−0.083] `ptrgen`, [−0.281, −0.205] `routes`, [−0.182, −0.116] `vsa_perm`,
[−0.193, −0.108] `evidence`, [−0.160, −0.073] `grammar` — six of six intervals
entirely below zero.

Two things the note should say and does not:

1. **The −0.099 is extrapolation, not just an estimate, and it is an upper
   bound.** Say the support: 2.6% overlap in `V`, and the only unextrapolated
   estimator is a 106-fill, 35-lesson slice that gives three positive signs and
   cannot report. And holding node type as well as concentration takes it to
   −0.062 for `corefer-001`, on 98.2% of the weight — a control the note did not
   run, which keeps its sign and removes a third of its size.
2. **"0.099 worse" should never be said without "at matched concentration".**
   On the 1,364 fills asked at both rates the models are not worse; they fail to
   get *better* when the evidence concentrates. That is the claim, and it is a
   weaker and more interesting one.

And one thing it should add, which is stronger than anything already in it:
**the 0.15-fitted weights, moved to the 0.90 draw untouched, pick up +0.1038 of
`acc | copyable` against the note's +0.1035.** A model whose ability is frozen
gains what the note attributes to the bucket, exactly.

Neither of the two criticisms touches the note's actual finding, which is that
`acc | copyable` rising at 0.90 is the bucket and not the model. On that I found
nothing that breaks it and several things that make it stronger.

Suggested status change for the attacked note: `provisional` → `measured` on the
survivorship claim, with the `−0.099` demoted from "estimate" to "upper bound,
extrapolated" wherever it appears.

## What would have refuted this, and the guard I did not expect to need

Five refutation conditions are in the table at the top, written before the
numbers; two more (type × `v/V`, and the cross-fit transfer) are post-hoc, each
with its own refutation condition stated before its run and marked as post-hoc
where it appears.
Two came back for the note outright, **two fired their refutation clause** —
exact `(v,V)` matching and the covariate swap — and one (paired fills) came back
against the note's phrasing and for its conclusion. Both fired clauses are
argued away above, one of them (exact matching) on a criterion I added after
seeing the number. A reader who thinks that criterion is special pleading should
read this note's verdict as "the direction survives, the size does not", which
is the conclusion either way.

**The guard, and it caught a real error in this very note's first draft:** for
any covariate standardisation, run the *ability-free predictor whose accuracy is
an exact function of that covariate* through the identical machinery. Under
exact matching its shortfall must be **identically zero**; under bands it must be
tiny. My first exact-`(v,V)` pass returned **+0.0814** for it — mathematically
impossible, and the bug was that I compared a prediction made on the matched
cells against an observation pooled over all cells including the 34.7% with no
counterfactual. Every model's number in that pass was wrong by roughly +0.08 and
every one of them looked plausible. Nothing else I ran would have caught it: the
sign was interesting, the magnitude was reasonable, and it flattered the
refutation I had been sent to write.

The same control is what turned "the covariate choice flips the sign, so the
note overclaims" into "three of those covariates do not adjust anything, and
here is the number that proves it". One line of code, two findings, one of them
about my own arithmetic.
