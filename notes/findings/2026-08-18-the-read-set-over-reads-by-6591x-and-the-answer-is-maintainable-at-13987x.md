---
title: The recorded read set over-approximates the claim's dependency by 6,591x — so the lever is not the logical form of the answer, and the complete answer is maintainable at 13,987x once the certificate is minimal
date: 2026-08-18
author: lead
status: provisional
tags: [certificates, cost, incremental, sec-13f, refuted-prediction, self-correction]
---

## What I set out to confirm, and did not

Two hours earlier
(`2026-08-18-an-optimum-is-two-claims-and-one-of-them-is-95x-cheaper-to-keep.md`)
I measured a 95x gap between the two halves of a clingo set-cover answer and
concluded:

> The lever is the logical form of the claim, not the size of the read set. An
> existential/monotone claim has a witness; a universal/negative claim has none.

That is the NP/coNP asymmetry, and if it were the mechanism it would replicate on
any optimisation. So: shortest co-holding path between two 13F filers
(`filer -> security -> filer`), same two filed snapshots, same 8,425-filing
stream, a BFS instead of a solver. Predicted: a *larger* gap, because the search
frontier is far bigger than twelve holder sets.

**The gap replicated at 8,932x, and the interpretation was wrong.**

## Measured

`scripts/cert_witness_path.py`. 300 paths, hops p50 1 / max 2, 173 ms/answer.

| certificate | dependency | P(hit) per filing | ceiling | advantage |
|---|---:|---:|---:|---:|
| witness (the path's edges) | 2.5 edges | 0.0034% | 29,390x | **29,182x** |
| optimality — **recorded** BFS frontier | 1,328.6 keys | 30.6067% | 3x | **3.3x** |
| optimality — **hand-derived minimal** | 0.5 keys | 0.0046% | 21,789x | **21,534x** |
| **full answer** `= d` (witness + minimal) | — | 0.0071% | 14,120x | **13,987x** |

The third row is the one that decides what the first two mean. The BFS's
*recorded* read set is the dependency of the **search**, not of the **claim**:

- for a 1-hop answer nothing can be shorter — the pair is distinct by
  construction — so optimality is **unconditional**, dependency ∅;
- for a 2-hop answer, "no 1-hop path exists" is exactly "the two portfolios do
  not intersect", which is **two facts**.

Either way it is not 1,328. Hand-deriving it collapses the witness-vs-optimality
gap from **8,932x to 1.4x**. The recording mechanism over-approximated the
claim's dependency by **6,591x**, and that over-reading — not the complexity
class — is what the first table measured.

**Control:** 222 of 300 witnesses are intact on the new snapshot and 0 fail to
chain from the source, so the witnesses are paths and the certificate is doing
what it says.

## The correction, stated plainly

**Retracted:** "the lever is the logical form of the claim".

**What replaces it:** the lever is the **true dependency of the claim**, and the
recorded read set can exceed it by four orders of magnitude. Logical form is
*one* way to get a small dependency — an existential claim comes with a witness —
but it is not the mechanism, and on shortest path it is worth 1.4x.

**Why set cover's 95x survives this attack.** There, the optimality read set
genuinely *is* the dependency: any filer in any of the twelve holder sets could
combine with others to give a `k−1` cover, so no smaller sound set exists.
Whether a recorded read set is tight is a property of the **problem**, not of the
recording mechanism. Two problems, two answers, and nothing in the mechanism
tells you which one you are in — which is the uncomfortable half of this.

**This is the same phenomenon a second agent measured independently on a
different graph the same day.** The dense-graph arm found a read set 66x larger
than the dependency on the route network (66 conflicts read across 23 queries, 0
of which change the answer when flipped alone). Same effect, two orders of
magnitude smaller. Two topologies, two kernels, one mechanism over-reading.

## The better result underneath the correction

The bound-maintenance headline is superseded by something stronger. Once the
certificate is minimal, the **complete answer** — `= d`, not `<= d` — is
maintained at **13,987x** against an opponent that re-derives it. The earlier
finding could only maintain half an answer because it never asked whether the
optimality half's dependency was really as big as the read set said.

## What this changes about what to build

- **Not** "every kernel reports its read set". Measured at 0.3x–1.0x per quarter,
  and now measured to over-read by up to 6,591x when it does.
- **Minimal certificates have to be derived, not recorded**, and the derivation is
  per-claim. For shortest path it is three lines and worth 6,591x. That is a bad
  trade to leave on the floor and a bad thing to promise generically.
- **The honest substrate contract** is therefore narrower than the one
  `HANDOVER.md` proposed: a kernel should be able to return a witness and, where
  it can, a minimal dependency — and where it cannot, say so, rather than
  returning a read set that reads like one.

## What would refute this

- **The hand-derived minimal certificate is only derived for hops ≤ 2**, which is
  every case in this sample (p50 1, max 2). The co-holding graph is nearly
  complete — any two filers holding one common large-cap are one hop apart — so
  this corpus cannot exercise deep paths at all. On a graph with real diameter
  the minimal optimality set is the ball of radius `d−1`, which grows, and the
  1.4x could open back up. **That is the experiment that would break this.**
- **The opponent** re-derives everything per update, as in the parent findings.
  No claim here is against incremental view maintenance.
- **A hand-derived certificate is hand-derived.** Its soundness here is an
  argument (a 1-hop answer cannot be beaten; a 2-hop answer is beaten only by a
  shared holding) checked by a control, not by a proof system. A wrong hand
  derivation produces a *silently* wrong maintained answer, which is strictly
  more dangerous than an over-read one — the over-read certificate is at least
  conservative.

## An error inside the run, kept

The FULL ANSWER row was wrong on its first computation and reported **exactly**
the minimal row's number. The witness is keyed on edges and the minimal
optimality set on adjacencies, and I replayed their union against the adjacency
stream alone, so the witness half matched nothing. It was caught because
`116 == 116` was too neat — the same shape as the trap already in `HANDOVER.md`
§8, "a control that confirms your prediction to three significant figures is
probably broken". Corrected to 179 invalidations (86 + 116 − 23 overlapping).

## Reproduce

```bash
uv run python -u scripts/cert_witness_path.py     # ~3 min, all four rows
```

`runs/cert_witness_path.json`; prediction and outcome in
`notes/autonomy/predictions.jsonl` under `cert-witness-generalises-path`.
