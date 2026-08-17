---
date: 2026-08-17
author: lead
status: measured
related: [2026-08-17-the-scope-is-in-the-path-and-the-guard-costs-045,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-15-a-floor-outside-the-models-hypothesis-class,
          2026-08-14-record-the-curve-not-the-argmax]
---

# Widening the conclusion language moves the ceiling; the condition language then binds, and it binds silently

## The mechanism

A guarded rule is scored on **every fill its guard admits**. So a rule that is
*perfect* on a rare sub-population cannot survive verification unless some guard
in the language **isolates that sub-population**. If the best available guard is
half something else, the rule's verified precision is capped near one half
however right it is on the part that matters, and it loses to a resolver that is
mediocre everywhere.

The failure is invisible from outside and looks like a search that tried hard:
thousands of guards proposed, hundreds kept, a residual that moves, and a model
that reads as *partially* understanding the phenomenon. Nothing reports that the
rule which would answer it is unreachable.

## What happened, and it took two refutations to find

`frontier-001` answers **55%** of the derived non-copyable bucket. Strip the
guard off its own winning rule and the same path and table answer **100%**. So
the guard is what limits recall — that much was measured in
[[2026-08-17-the-scope-is-in-the-path-and-the-guard-costs-045]]. That note then
named the wrong cause, and the two candidates died in order:

**Candidate 1 — the proposal gate.** A guard is proposed only if its residual
support clears `min_support = 12`, and the derived slot is ~170 of 86,805 fills,
so the guard specific to it can never be proposed. Plausible, and **false**.
`frontier-002` splits the proposal gate from the verification gate and drops it
to 2: **8,786 guards proposed in round 2 against 5,316**, 1,403 kept against
1,054 — and `acc | derived, not copyable` is **0.531546 in both**, identical to
six decimals. Thousands of extra hypotheses, not one derived fill changed.

**Candidate 2 — first-match-wins ordering.** Prediction fires the highest-ranked
matching rule, and a specific low-support rule cannot outrank a coarse rule with
n = 2,300 under a Wilson bound, so a correct rule might exist and never get a
turn. Also **false**: asking whether *any* rule in the model would have answered
the missed fills gives **0.0000**. The correct rules do not exist to be blocked.

**Candidate 3 — the guard language. Written here as holding, and it does not.**
Corrected within the day by
[[2026-08-17-an-average-cannot-see-a-sub-population]] and left standing so the
sequence is visible. The argument below is that a rule perfect on a rare
sub-population cannot verify because its guard admits too much else. Measured on
`[phead='obj', slot=1]`, which covers 80% of the derived slot, `map:sib@2` is
**1.000 on the derived members** and 0.179 on the rest — **0.625 overall**,
comfortably above the 0.5 threshold. It would have verified. Purity was not what
killed it.

Instrumenting the fit found what did: for that guard a resolver *is* chosen and
it is **`const` at score 0.993**, and `_verify` keeps **one resolver per guard**,
so the map is discarded for being 0.625 on average against a constant that is
0.993. The mechanism below is therefore right in its general form — a rule is
ranked by its average over the population its guard admits, and an average
cannot see a sub-population — and wrong about which stage of the search enforces
it. It is the *resolver* choice, not the guard's purity.

Fixing that (`frontier-003`, best rule per *form* per guard) did not move the
derived bucket either. Four candidates, three variants, zero fills. The honest
state is that what limits that bucket is still unidentified.

**The original candidate-3 argument, as written:** Over all 63 subsets of
the six guard atoms, the best guard covering at least half the derived fills is
`[phead='obj', slot=1]`, at **purity 0.531** and recall 0.799 — 147 derived
fills and **130 non-derived ones**. There is no guard that names the derived
slot. `obj` predicates occur across the curriculum and only some of them have a
derived attribute, because *derivedness is a property of the generator*, not of
the tree. So the perfect rule is verified on a population that is half something
else, scores ~0.53, and cannot win.

## Why this is the same shape as an old lesson, one level up

[[2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary]]
established that the derivability null was expressive rather than procedural: no
model could *state* `label(X) = m(label(Y))`, and adding that conclusion form
took the bucket from 0.000 to 0.532.

That was right, and it relocated the constraint rather than removing it. **The
conclusion language stopped binding and the condition language started.** The
remaining 0.468 is the same kind of failure about the other half of the rule,
and it was invisible until the first half was fixed — which is the general
pattern worth carrying:

> Expressiveness limits come in layers. Fixing the one you can see reveals the
> next one, and the next one will not announce itself; it will look like a
> search that nearly worked.

## The guard

There is no automated guard for this, and it should be said rather than
pretended. What there is, is a **cheap diagnostic that any guarded-rule model
can run**: for the sub-population you care about, enumerate the guard language
and report the best achievable *purity* at usable recall. If that number is near
0.5, no amount of search or support-tuning will help and the answer is a new
guard atom, not a better threshold. It cost one command here and it would have
saved two model variants and two refuted hypotheses.

`frontier-002` is kept registered despite being a null. It is the control that
makes "the proposal gate is not the cause" a measurement rather than an
assertion, and deleting it would leave that claim resting on nothing.
