---
date: 2026-08-14
author: agent-refuter
status: open
related: [the-readout-survives-both-attacks-and-its-comparison-row-does-not,
          abstention-on-repair-is-below-chance]
---

# Is `wrap`'s top-8 shortlist just "the 8 nearest visible labels"?

Falling out of the readout refutation, unmeasured, and it would explain the
oddest number in it: capping the candidate set at 8 costs `graphread` 0.147
`label_acc` and costs `wrap` **nothing** (0.0851 at 8, 0.0767 at 24; floor
0.2025; `runs/agent-sweep/wrap/`, `runs/agents-readout179/wrap-24/`).

Read off two functions, never run:

* `Repair._nearby` orders candidates by `abs(j - i)` over the pre-order
  linearisation — **nearest permanently-visible label first**.
* `PolicyAgent.shortlist` sorts by `(-prior.get(a, 0.0), opts.index(a))`, so
  wherever the prior is flat the surviving key is the environment's own order.
* `notes/findings/2026-08-13-abstention-on-repair-is-below-chance.md`'s mechanism
  section establishes the prior *is* near-flat on `repair`: `action_prior` is
  counted over `Episode.answer` and `repair`'s actions are node labels, so
  almost every legal action falls to `prior_floor`. Confirmed at 179 lessons in
  `runs/agent-sweep/abstain/policy.txt`: 515 prior counts, 0.254 of the mass on
  one shortcut pick.

If that composes as it looks like it does, "the top 8 by the shared prior" is
"the shortcut's pick, then the 8 nearest visible labels" — a **locality
heuristic given to `wrap` for free**, which would explain why taking the cap
away does not help it: at 24 it has to rank sixteen more candidates with a text
scorer that carries no information here, and it loses the free ordering.

## What would answer it

One run of `wrap` at `max_actions=8` with the shortlist replaced by a *random*
8 of the 24 at a fixed seed. If the locality reading is right that row drops
well below 0.0851; if it lands at 0.0851 the shortlist was never doing anything
and the whole idea is wrong.

## Why it matters beyond `wrap`

Because `graphread-capped` faces the same shortlist, and if the shortlist is a
locality prior then the 0.199 lift that row clears the floor by is *partly the
shortlist's*, not the readout's. It would not touch the uncapped comparison —
`graphread` at 24 against `wrap-envcal` at 24 is 0.4320 with no shortlist
anywhere — but it would mean the capped row is measuring two things and should
stop being quoted as a clean decomposition of the cap.

`notes/findings/2026-08-14-graph-derived-roles-structure-not-locality.md` found
locality to be *worse than nothing* as a feature on the model side. If it is
worth something here, that is a difference between the two harnesses worth
having.
