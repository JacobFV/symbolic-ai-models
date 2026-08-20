---
title: The in-scope path turned out larger than the blocked one — components nobody was measuring
date: 2026-08-19
kind: status
---

A programme-level assessment after the reading arm reopened. Every number is cited
from a note under `notes/findings/`; this introduces no measurements. It
supersedes `notes/status/2026-08-19-supervision-is-cheap-and-the-ceiling-did-not-move.md`,
which concluded that the ceiling would not move without the excluded component.
**That conclusion was wrong**, and this says by how much.

## What changed

The previous assessment closed twelve interventions on the reader and concluded
the remaining route was a learned representation — the one thing the scope keeps
as a control. It was measuring the wrong components.

Every decomposition then in use was **ceiling × classifier × ranker**. Adding the
**proposer** — how often the candidate the answer needs is even generated —
produced a four-factor model whose product reproduces the measured rate to within
**0.019 across ten rows**, and revealed that on `industry` the proposer was
**0.006**: the reader could not represent the answer at all, and every previous
number for that relation was a statement about a component nobody had looked at.

Acting on that, entirely inside the scope:

| relation | before | after | above its floor |
|---|---|---|---|
| `industry` | **0.000** (impossible) | **0.238** | +0.177 |
| `country` | 0.182 | **0.390** | +0.092 |
| `headquarters` | 0.254 | 0.280 | **+0.235** |

Three steps, each identified by a measurement rather than guessed: a **phrase
proposer** for lowercase values, **supervision routed through the proposer** so
the reader trains on the sentences it can actually answer (3.9× on `industry`
alone), and **aliases induced by label association** so a relation stated only in
a derived form becomes visible.

**Half of `country`'s gain and four fifths of `industry`'s is genuine paraphrase
reading**, measured where guessing is impossible: on articles that never state the
answer literally, the base arm scores a structural 0.000 and the alias arm reaches
0.219 and 0.209.

## What this does to the critical path

The advice given when this was last asked — *the classifier is binding, and the
decisive experiment is the excluded component* — was **half right and badly
incomplete**.

- **Still true:** an oracle classifier is worth **1.9× to 6.6×** on every relation
  measured. That prize is real and Path A would collect it.
- **Newly true, and it was not visible before:** a comparable prize was sitting in
  the proposer and the supervision, in scope, unblocked, and unmeasured. Nobody
  had looked because the decomposition did not have a term for it.

The general lesson is sharper than either: **the components that were not in the
decomposition were the ones with headroom.** Twelve interventions were spent on
the two factors that were being measured.

## Trajectory

**Do:** finish the in-scope path before spending the blocked one. Three of the
five relations still have obvious untried work — `founder` induces zero aliases
and sits at +0.092 above floor, `parent`'s proposal is 0.871 and its classifier
0.351. The four-factor table says which component to attack for each, and the
screening statistic (`containment × proposal`, no model, seconds) says whether a
new relation is worth attempting at all.

**Stop:** quoting real-text accuracy without its floor. `country` looked
second-best on raw accuracy and is **weakest of five** above floor, because
answering *United States* every time is right 29.8% of the time. That inversion
was found once and would have been published twice.

**Keep:** the four-factor decomposition, and the discipline of splitting a gain by
whether the answer was visible. Both turned an ambiguous number into a specific
claim this week.

## How this fits the narrative

The symbolic tradition's post-mortem blames the knowledge-acquisition bottleneck.
This week priced it — ~385,000 articles or **$0.03 and a machine-day** for a
relation a public KB curates, and about **200 seed articles** for one it does not.
What this assessment adds is that the bottleneck was never only *acquisition*: for
`industry` the blocker was that the system had no way to **express** the answer,
which is a representation-of-values problem the literature does not usually
separate from extraction.

Against the scaling position the position is unchanged and quantified: the
reasoning substrate costs **$1.6e-08 to $9.7e-08 per solved episode** against an
API's 25,597×–112,395× at *perfect* accuracy, and a persistent world beats
iterative retrieval **from the first query**. The reading half remains far behind
hand-written rules on open prose, and this week narrowed that gap by a factor of
two to ten on three of five relations without leaving the scope.

## What should make an outside reader sceptical

- **One corpus, one genre**, five relations, all company intros.
- **The floor inverted a ranking once already**, and only `headquarters` clears
  its floor by more than 0.18.
- **Three headlines were withdrawn this week** and two lesson notes written about
  the mechanisms that produced them — small numerators, prefix sampling, and hash
  randomisation.
- **Some induced aliases are priors** (`ftse→London`); the split is measured but
  the mechanism cannot yet refuse them at induction time.
- **No LLM accuracy anywhere.** Every cost comparison is a price sheet plus our
  own accuracy.
