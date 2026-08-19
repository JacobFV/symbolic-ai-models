---
title: An optimum is two claims and one of them is 95x cheaper to keep — the lever on a maintenance certificate is the logical form of the claim, not the size of the read set
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, cost, incremental, sec-13f, asp, bounds]
---

## Where this starts

The finding it extends
(`2026-08-18-the-certificate-is-worth-nothing-per-quarter-and-1342x-per-filing.md`)
measured a ceiling on what a dependency certificate can be worth:

```
advantage  <=  1 / P_hit,     P_hit  ~  r x keys_per_update / total_keys
```

so the mechanism is governed by `r`, the size of the dependency, and the cost of
the computation only decides whether the ceiling is reached. That put the clingo
set-cover answer **last** of four query classes at 37x, purely because it read
the most facts — twelve holder sets against the intersection's two portfolios.

The obvious next move is to shrink `r`. The dense-graph scout found the same
lever from the other side on the route network: 66 conflicts read across 23
queries, **0** of which change the answer when flipped alone — a read set 66x
larger than the dependency. So: can a kernel report a *minimal* dependency, and
does the ceiling rise with it?

**It cannot, in general, and the reason is more useful than the answer.**

## The structure that was in the way

"The optimal cover has size k" is not one claim. It is two, and they have
different logical forms:

| | claim | rests on | form |
|---|---|---|---|
| upper | a cover of size k **exists** | a **witness**: one edge per item, from k filers | existential, monotone |
| lower | no cover of size k−1 exists | every item's **whole holder set** | universal, negative |

The upper bound is monotone: adding holdings can only make covering easier, so a
witness that still exists still proves `<= k`. The lower bound is a claim about
*absence* — any filer anywhere in those holder sets could have been the one that
made `k−1` reachable — so reading all of them is not over-approximation, it is
**correct**, and there is no smaller sound set.

This also kills the idea the experiment was originally designed around. A
solver's **unsat core is not a sound stability certificate** for the lower half:
the core proves infeasibility under the facts present, and infeasibility is not
preserved when facts are added. The core is minimal with respect to the *current*
world and says nothing about the next one.

## Measured

`scripts/cert_bound_asymmetry.py`, on the same two filed 13F snapshots. 8,425
filings; 411,122 edges opened and 333,014 closed of 2,282,570; 300 covers of 12
securities, 7.9 ms/answer.

| certificate | P(hit) per filing | ceiling `1/P` | measured advantage | $/quarter maintained |
|---|---:|---:|---:|---:|
| **optimality** (12 holder sets) | 2.8589% | 35x | **35.0x** | 3.2e-03 |
| **witness** (12 edges) | **0.0300%** | 3,334x | **3,309.4x** | **4.0e-05** |
| opponent (re-derive per filing) | — | — | 1.0x | 1.3e-01 |

**The split is worth 95x.** And it buys **half an answer**: a maintained `<= k`,
not a maintained `= k`.

**Control.** The optimality row must reproduce the number already on disk or this
is not the same measurement. 2.8589% against 2.71%, 35.0x against 37.3x —
different random sample, same quantity.

**Anchor A** (n=300, not sample-limited): every witness is real edges in the old
snapshot, covers every item, and names no more filers than the optimum claims.
300/300.

**Anchor B**: re-solve every witness that survived the whole quarter. 13/300
survive — which is itself the freshness lesson again, 99.97% per filing and 4.3%
per quarter — and **0** of the 13 had a maintained bound that was wrong.

## Two things I got wrong inside this run, kept rather than tidied

**The decomposition row is ill-posed.** I built a row to separate "how much of
the saving is monotonicity" from "how much is the smaller dependency". It
returned 1.0x, and the reason is that the question is malformed: a witness edge
exists in the old snapshot, so it can only ever be *deleted* and no addition can
touch it — the row is identical to the deletions-only row by construction. The
small dependency is *licensed by* the monotonicity. They are one effect and no
measurement here separates them. The row stays in the script labelled degenerate.

**Anchor A failed 300/300 on its first run, and the bug was in the anchor.** I
compared `|witness|` — 12 edges, one per item — against `k`, which is 4 to 9
distinct filers. The witness was correct the whole time. Worth recording because
the reflex on a 300/300 failure is to distrust the mechanism, and the anchor is
the newer and less-tested code of the two.

## What this changes

- **The lever is the logical form of the claim, not the size of the read set.**
  An existential/monotone claim has a witness, and a witness is a small stable
  dependency. A universal/negative claim has no witness and must read the
  complement. "Push kernels toward smaller read sets" was the right instinct
  aimed at the wrong quantity: you cannot shrink an optimality claim's
  dependency, but you can often **split the answer** into a half that has a
  witness and a half that does not.
- **A maintained bound is a real product.** For the question this query models —
  *how few managers must I talk to to reach every one of these positions* — the
  witness is the actionable half: it is a **plan**, and it stays valid through
  99.97% of filings for 1/95th of the cost. Optimality is a guarantee you can
  re-establish on a slower clock. This is the same shape as this repo's two
  earlier results, `additive_bounds` and the solver rung where the maximum is
  closed-form and the minimum is NP-hard, and that is now three times the cheap
  half of a problem has been the useful half.
- **It narrows what to build.** Not "every kernel reports its read set" — that
  was measured at 0.3x–1.0x per quarter. Kernels should report **witnesses**
  where their answers have them, and say plainly where they do not.

## The direction of corpus drift was the obvious attack, and it is second-order

This finding's own "what would refute it" said: *13F grows — 411,122 opened
against 333,014 closed — so a corpus that mostly **shrinks** inverts the
asymmetry, the witness becoming the fragile half. That is a cheap experiment
nobody has run.* It was also recorded in `state.yml` as a belief at **confidence
0.8**.

Run, by reading the same two filed snapshots in the opposite order — so
"shrinking" is made of real filings rather than a simulation:

| | forward (growing) | **reversed (shrinking)** |
|---|---:|---:|
| per filing | 48.8 opened, 39.5 closed | 39.5 opened, **48.8 closed** |
| witness P(hit) | 0.0305% | **0.0351%** |
| optimality P(hit) | 2.8589% | 2.5509% |
| witness advantage | 3,253.9x | 2,813.3x |
| optimality advantage | 35.0x | 39.2x |
| **the split** | **93x** | **72x** |

**The belief was false.** The asymmetry does not invert; it narrows by 23%, which
is exactly the rise in the deletion rate (39.5 → 48.8 closures per filing). The
optimality certificate is invalidated by a change in *either* direction so its
P(hit) barely moves; the witness is hit only by deletions, so it moves in step
with them, and the gap narrows by that ratio and nothing else.

**So the dominant term is dependency size** — twelve edges against twelve whole
holder sets — and corpus direction is second-order. Anchors held in both
directions: 300/300 witnesses well-formed, 0 wrong maintained bounds, and the
forward run reproduces the published 93x, so the two are the same measurement.

## What would refute it

- **The opponent.** As in the parent finding: it re-derives everything per
  update, which is what an LM must do and is not what a database would do. No
  claim here is against incremental view maintenance.
- **The witness is not minimal, only small.** Twelve edges for twelve items is
  minimal at edge granularity for *this* problem shape; a problem whose witness
  is large would show none of this.
- ~~13F grows, and a shrinking corpus would invert the asymmetry.~~ **Run — see
  above. It does not invert; it narrows 93x → 72x.**
- **Anchor B is thin.** 13 re-solutions. The witness's soundness is structural
  rather than empirical (the k edges *are* a cover), so anchor B is testing the
  implementation, not the theorem; anchor A at n=300 is the load-bearing one.

## Reproduce

```bash
uv run python -u scripts/cert_bound_asymmetry.py     # ~2 min, both anchors
```

Row in `runs/cert_bound_asymmetry.json`; prediction and outcome, written before
and after, in `notes/autonomy/predictions.jsonl` under `cert-bound-asymmetry-13f`.
