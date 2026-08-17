---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-instances-per-pair-or-pool-width-a-prediction-with-a-number,
          2026-08-17-sixty-pairs-seen-three-times-each-and-the-lift-is-still-0614,
          2026-08-13-no-null-from-an-undertrained-budget,
          2026-08-15-a-floor-outside-the-models-hypothesis-class]
---

# Both matched predictions held, then the falsifier I designed broke the general claim

Pre-registered in
[[2026-08-17-instances-per-pair-or-pool-width-a-prediction-with-a-number]] with
**non-overlapping ranges**, because the two readings of the pair curve — a data
curve or a capacity curve — make different predictions and the previous finding
rests on the first.

## The two matched pairs

`acc | derived, not copyable`. The prediction was stated as a *match to an
existing rung*, not as "it goes up", so a bare improvement could not have
satisfied it:

| arm | pool | `n_train` | instances/pair | predicted | **measured** |
|---|---:|---:|---:|---|---:|
| `k24` | 24 | 20 | ~7.7 | — | 0.896 |
| **`k60`** | **60** | **40** | **~6** | **0.85–0.92** | **0.910** |
| `k12` | 12 | 20 | ~15 | — | 1.000 |
| **`k24`** | **24** | **40** | **~15** | **0.97–1.00** | **0.994** |

Both landed inside their ranges. The load-bearing comparison is the first pair:
**pool 60 and pool 24, two and a half times apart in width, score 0.910 and 0.896
when each pair is seen about as often.** The second pair says the same at the top
of the range, 0.994 against 1.000 at ~15 instances each.

**Instances-per-pair predicts the score; pool width does not.** The pair curve is
supervision, and the previous finding's interpretation stands as measured rather
than as argued. The alternative reading — "the model holds about twenty-four
pairs" — is dead: it holds sixty when sixty are shown often enough.

`notes/lessons/2026-08-13-no-null-from-an-undertrained-budget.md` is why this was
worth running: this repo has published a null before that was an undertrained
budget wearing an architecture's name, and the k=60 rung at 0.641 was exactly
that shape.

## A pre-registered refutation condition fired, and it was a bad condition

I wrote: *"Either control rises above its blind marginal. Then that rung is
admitting noise and nothing at it is readable."* Taken literally it fires:

| control | model | blind marginal | **the arm's own derivation floor** |
|---|---:|---:|---:|
| `k60-perm` @40 | 0.053 | 0.016 | **0.100** |
| `k24-perm` @40 | 0.123 | 0.041 | **0.173** |
| `k60-perm` @20 | 0.027 | 0.016 | 0.076 |
| `k24-perm` @20 | 0.072 | 0.057 | 0.136 |

Every control sits above its blind marginal — **including the two rungs I
published last round without flagging it.** So either four rungs are void, or the
condition I wrote is the wrong one. It is the wrong one, and the reason is
[[2026-08-15-a-floor-outside-the-models-hypothesis-class]]: the blind marginal is
not the ceiling in the control arm.

Under a per-episode permutation the value is still drawn from that episode's own
six, so a reader that sees the kind's *episode* is constrained to six candidates
even though the correspondence across episodes is noise. The quantity that bounds
a control-arm model is therefore the **control arm's own derivation floor** — a
lookup with the same information — and every model above sits **below** it. The
right condition was "the control rises to its own derivation floor", not "above
its blind marginal".

Recording it this way rather than quietly restating: the condition was written
before the numbers, it fired, and I am overriding it on an argument made after
seeing them. That is exactly the move this repo distrusts, so the argument has to
stand on the floor column being in the table above rather than on my say-so, and
a refuter should attack it there first.

## The confound, which was named in advance and is not removed

Raising `n_train` raises supervision for everything, so a rise is consistent with
"more instances per pair" *and* with "a better model overall". The design answers
it by predicting a **match to a rung with matched instances-per-pair and very
different pool width**, which a general improvement would not produce — a
uniformly better model would push k60@40 *past* k24@20, not onto it.

The check named in advance was `acc | rest, not copyable`, and it did move:
0.243 → 0.274 at k60 and 0.263 → 0.283 at k24. So the model is ~0.02–0.03 better
on the rest of the curriculum at 40 seeds. That is real and it is an order of
magnitude smaller than the 0.27 the derived bucket moved, which is the argument
that the bucket's rise is not the general one — but it is an argument about
sizes, not a separation, and it is the weakest link in this note.

## The third point fits, the collapse claim does not, and the falsifier is why

`k60` at `n_train = 80` was predicted to reach ~12 instances/pair and land near
`k24`@40's 0.994. **Measured 0.962** — slightly below the point estimate, and
exactly where the relation puts it. Ordering every rung by instances-per-pair
rather than by pool width:

| instances/pair | pool | `n_train` | `acc \| derived, not copyable` |
|---:|---:|---:|---:|
| ~3 | 60 | 20 | 0.641 |
| ~6 | 60 | 40 | 0.910 |
| ~7.7 | 24 | 20 | 0.896 |
| ~12 | 60 | 80 | **0.962** |
| ~15 | 24 | 40 | 0.994 |
| ~15 | 12 | 20 | 1.000 |
| ~30 | 6 | 20 | 0.989 |

Reading those seven rows I wrote that four pool widths and three training
budgets **collapse onto one curve** in instances-per-pair. That claim is
**refuted**, by the point the note then nominated as the one most embarrassing to
miss.

**The falsifier.** `k6` at `n_train = 5` reaches ~7.7 instances/pair and, if the
collapse held, should *fall* to ≈0.896 — the score pool 24 gets at the same
supervision. **Measured 1.000.** No fall at all.

**The discriminator.** Holding instances-per-pair fixed at ~7.7 and varying only
the pool:

| pool | `n_train` | share of pool per episode | instances/pair | **acc** |
|---:|---:|---:|---:|---:|
| 6 | 5 | 1.00 | ~7.7 | **1.000** |
| 12 | 10 | 0.50 | ~7.7 | **0.956** |
| 24 | 20 | 0.25 | ~7.7 | **0.896** |

Monotone in pool width at identical supervision. **Both variables matter**: more
instances per pair helps, a wider pool hurts, and the pool penalty shrinks as
instances grow — at ~15 instances pools 12 and 24 agree to 0.006, while at ~7.7
they are 0.104 apart.

So the honest two-variable statement replaces the one-variable one. What made the
collapse look real is that the three points I had were consistent with it, and I
wrote it up as a collapse rather than as "consistent with". Seven points, one
tidy story, and the eighth point — chosen because it was the one that could
embarrass the story — killed it.

The third point itself was fine: predicted "near 0.994", measured 0.962, which is
where a two-variable surface puts pool 60 at ~12 instances.

Control at the third point: `k60-perm`@80 scores **0.063** against its own
derivation floor of 0.155 and a blind marginal of 0.016 — below its floor, like
every other control here.

## What survives, precisely

**The original claim survives in weakened form.** "The result is about table
size" is still wrong: pool 60 reaches **0.962**, so the model is not capped near
twenty-four pairs, and the derivability headline does not need hedging down to
"a six-pair correspondence".

**"Instances-per-pair is the variable" is wrong**, and it was mine, published an
hour before its falsifier ran. Pool width has an independent cost that is large
at thin supervision (0.104 between pools 12 and 24 at ~7.7 instances) and small at
thick supervision (0.006 at ~15).

**A mechanism is available and untested.** At pool 6 every episode draws all six
kinds — measured share of pool per episode 1.00 — so the map is *complete in every
episode*, while at pool 24 only a quarter of it is present. Completeness, not
width, may be the operative variable; pool 12 at 0.50 sitting between 6 and 24 is
consistent with that and does not establish it. The clean test is a pool-24 arm
that draws twelve kinds per episode instead of six, which holds width fixed and
moves completeness alone — and that needs a wider slot vocabulary, which is the
`COLORS`/`SHAPES` job
[[2026-08-17-the-parked-experiment-was-a-null-by-construction-and-nothing-would-have-said-so]]
already priced.
