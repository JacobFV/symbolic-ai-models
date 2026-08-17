---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-a-floor-a-rule-must-beat-is-the-guards-own-modal-rate,
          2026-08-17-the-channel-is-walked-and-it-took-a-conjunction-of-three,
          2026-08-15-a-floor-outside-the-models-hypothesis-class]
---

# All four predictions held, and the hand-chosen threshold is gone

> **Traced 2026-08-17 by `agent-refuter` — see
> [[2026-08-17-the-channel-is-walked-by-the-floor-alone]].** All four numbers
> reproduce from a clean refit; the `summary.json` is equal to this one field for
> field. Two things need amending. (1) **Prediction 2 could not have failed.** A
> rule fitted to noise on this bucket still emits one of the six values and is
> right ~1/6, which is what "the blind marginal" also reads — so the control
> lands near 0.14 whether or not the floor admits noise, and measurement says it
> *does*: in `-perm` the model fires on 623 of 623 fills through five map rules
> each right at ~1/7. The quantity that separates them is bits (2.36 treatment,
> 9.28 control, 10.09 for its own silenced back-off), not accuracy. (2) The two
> ingredients this model inherits from `frontier-006` are not needed and cost:
> `frontier-001` with **only** `relative_floor` scores 0.975 / **0.111** and beats
> this row on pooled accuracy, bits, type and `acc | rest, not copyable`.
> Registered as `frontier-floor`.

Pre-registered in
[[2026-08-17-a-floor-a-rule-must-beat-is-the-guards-own-modal-rate]] before the
run. `frontier-008` replaces `min_precision = 0.2` — a constant I picked after
logging that 0.5 excluded the rule the derived fills need — with a floor that is
a property of the population each guard admits: **a rule must beat that guard's
own out-of-fold modal rate**, the precision `const` achieves there.

## The four predictions

| # | prediction | measured | |
|---|---|---:|---|
| 1 | `acc \| derived, not copyable` ≥ 0.95 | **0.9890** | held |
| 2 | control `-perm` ≤ 0.20 | **0.1429** | held — it is the blind marginal, 0.1433 |
| 3 | `-shuffled` ties the treatment | **0.9890** | held, to four decimals |
| 4 | pooled `label_acc` ≥ 0.4376 | **0.4414** | held |

Prediction 2 was the void condition and the one that mattered: a relative floor
is *more* permissive at broad guards, so admitting rules that fit noise was the
live risk. The control sits on chance.

## The pooled table

| model | lbl acc | bits | renamed | drop | type | rules |
|---|---:|---:|---:|---:|---:|---:|
| **`frontier-008`** | **0.4414** | **7.141** | **0.2207** | 0.2249 | 0.8539 | 916 |
| `frontier-007` | 0.4376 | 7.180 | 0.2188 | 0.2226 | 0.8539 | 947 |
| `frontier-006` | 0.4091 | 7.397 | 0.2134 | 0.1979 | 0.8539 | — |
| `frontier-001` | 0.4042 | 7.433 | 0.0345 | 0.3716 | 0.8633 | 427 |
| `corefer-001` | 0.3572 | 6.952 | 0.3499 | 0.0032 | 0.9458 | — |

Better than `frontier-007` on accuracy, bits and renamed simultaneously, with an
identical type head — and with **fewer rules**, 916 against 947. That last number
is the one I did not expect and it is worth stating plainly: **the relative floor
is not more permissive overall, it is differently permissive.** It admits rules
at broad guards where a constant 0.2 was still too strict, and it excludes rules
at narrow guards where 0.2 was far too lax. The net is a smaller rule set that
scores better everywhere.

Regression-checked before any of this was believed: `frontier-007` refitted after
the `_sweep` rework scores 0.438 / 7.180 / 0.854, matching its published row.

## Why this matters more than the 0.0038 of accuracy

The derivability result now rests on **no threshold anyone chose**. Every knob in
the chain that walks the channel is either structural (`keep_by_path`,
`propose_support` — which round a guard may be proposed in) or derived from the
data (`floor_margin = 1.0`, "strictly better than doing nothing"; `abs_floor =
0.02` for `const`, which cannot beat itself).

That closes the weakness the previous finding named against itself. It does not
close the other two it named — six planted pairs is still a small map, and the
lookup floor still scores 1.000, so the ceiling was never in doubt.

## What would still make this hollow

**Tested on a provable null, 2026-08-17, and not triggered — see
[[2026-08-17-the-map-form-carries-the-kg-gap-and-the-per-guard-floor-does-not]].**
On the `kg:` arms, which are isomorphic by construction so anything found between
them is noise, `frontier-003` carries the *global* floor at the same level and
shows a gap of the same order (+0.012 against `-008`'s +0.018, level 0.285 against
0.326). The per-guard floor is not distinguishable from the global one there. A
null from a control is weaker than a failure, so this weakness is **untriggered,
not disproved**, and the paragraph below stands.

**The floor is `const`'s precision, and `const` is one of the resolvers being
floored.** So a guard where `const` happens to be weak is a guard where
everything is admitted. That is intended — it is the definition of "the
do-nothing baseline is weak here" — but it means a guard whose answers are simply
*noisy* looks identical to a guard whose answers are *structured but not modal*,
and the floor cannot tell them apart. `min_support` and the Wilson bound are what
stand between that and a rule set of noise, and neither was chosen with this
interaction in mind.

**Both new knobs were then measured on the development split**, per the
pre-registration and not on the derived bucket, and **both are inert**:

| | acc | bits | renamed |
|---|---:|---:|---:|
| `floor_margin` 1.0 (default) | 0.4384 | 7.111 | 0.2154 |
| `floor_margin` 1.5 | 0.4376 | 7.123 | 0.2154 |
| `floor_margin` 2.0 | 0.4365 | 7.137 | 0.2145 |
| `abs_floor` 0.0 | 0.4384 | 7.111 | 0.2154 |
| `abs_floor` 0.02 (default) | 0.4384 | 7.111 | 0.2154 |
| `abs_floor` 0.10 | 0.4386 | 7.109 | 0.2135 |

`floor_margin` moves accuracy by 0.002 and renamed by 0.001 across a doubling;
`abs_floor` at 0.0 and 0.02 is **bit-identical**, so it never binds. That is the
answer the section above asked for, and it is the good one: **the result rests on
the *shape* of the floor and not on either value.** 1.0 having been argued rather
than measured costs nothing, because any nearby value gives the same model.

An inert knob is worth reporting rather than quietly keeping. Both stay
registered with those defaults, and neither should be cited as a fitted
parameter — `notes/lessons/2026-08-14-record-every-fitted-parameter-or-a-drift-is-unattributable.md`
cuts both ways, and a knob recorded as fitted when it is inert is its own kind of
wrong.
