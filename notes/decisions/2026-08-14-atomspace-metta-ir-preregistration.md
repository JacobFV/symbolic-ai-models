---
date: 2026-08-14
author: lead
status: provisional
related: [2026-08-14-the-ir-is-a-knob, 2026-08-14-lean-ir-preregistration,
          2026-08-13-learn-or-seed-the-vsa-codebook,
          2026-08-13-compositional-parser]
---

# `005`: AtomSpace / MeTTa as the IR — pre-registration

Written **before any of it is built**, per `CLAUDE.md`. The prediction below is
one I expect to lose, which is the point.

## What gets built

`symbolic_ai_ir/atomspace.py` and friends, native and dependency-free:

- **Atoms.** Symbol, Variable, Expression, Grounded — the four MeTTa has. A
  curriculum `Graph` becomes an atomspace by the obvious structural map: a term
  node with children is an `Expression` whose head is the node's label and whose
  tail is its slots; a leaf is a `Symbol`; a `field` node becomes the named
  binding it already is. Node type rides as a typing atom `(: label type)`,
  which is how AtomSpace carries types anyway.
- **A MeTTa subset.** Unification with variables, pattern match over the space,
  and rewrite rules. Not the whole language — enough to express queries and
  transformations, with the deliberate omissions written down.
- **`atomspace_to_graph`**, asserted as the identity over **all 179 lessons'
  graphs**, on the node-type alphabet rather than a sampled fixture.
- **Models registered `metta-005`, …**, beside every existing row, never in
  place of one.

The real `hyperon` is an **outside conformance oracle**, not a dependency: it
publishes no wheel for this project's Python, and a C extension inside a sweep
breaks `APPROACH.md`'s cost budget. A separate out-of-band check writes our
atomspace out as MeTTa source, runs it under a real hyperon in its own
interpreter, and asserts the two agree. Skipped when absent, never in the hot
path.

## Why this IR might buy something, stated concretely

The claw vocabulary is **twelve routes somebody wrote down**. `ilp` is the one
model here whose hypothesis space is not a written-down list, and its strongest
discovered clause is a *typed, slot-selected sibling* which **`CLAWS` cannot
express** — there is `sibling0` and `prev_sibling` and no way to say which
sibling. That is a limitation of a hard-coded enum, and pattern-matching over a
hypergraph is exactly the calculus in which the missing route is one more
pattern rather than one more `if`.

Second, an atomspace **holds contradictory hypotheses at once**. This repo's
central metric tension — `label_acc` and `label_bits` ranking the models close to
inversely because one scalar `c` pushes deciding and estimating through the same
mixture — is a symptom of a representation that must commit. A space that can
carry several candidate fillers with weights does not face that trade-off at the
representation level, whatever it then does about it at the readout.

## The pre-registered prediction, and it is a loss

**`metta-005` will not beat `corefer-001` or `vsa_perm_pure-002` on label
accuracy, and the reason is already measured.** `omegaclaw_reach-001` added
`ilp`'s best discovered operator — `sibling_pred`, firing at 0.803 reliability
against `mirror`'s 0.232 — and **still lost**, +0.226 against +0.234. `ilp` is
uniquely right on only **2.2%** of nodes, because the existing claws reach the
same answer by another route nearly everywhere. Reach was never the constraint;
discrimination is, and candidate recall climbing 82.7% -> 98.7% moved accuracy by
0.000.

So "we can now express more patterns" predicts almost nothing on the head this
repo leads with. Writing that down first is what stops the eventual number being
read as whatever flatters the line.

**What it may legitimately buy, and where I would look first:**

- **Bits, not accuracy.** Superposed hypotheses are a density estimate. The best
  bits in the repo (`ensemble-001`, 4.77) came from *diversity*, and the honest
  reading of that result was that its gain was vocabulary memorisation which died
  under renaming. A pattern-matching IR's hypotheses are structural, so the same
  gain — if it appears — should **survive a renaming**. That is the sharp test
  and it is the one I would run first.
- **The type head, which nothing has attacked.** Floor 0.860, two of nineteen
  models positive, every VSA row parked at −0.486. `(: label type)` is a
  first-class atom here rather than a second head bolted on, and design rule 1
  (the heads do not share machinery) is satisfied by construction rather than by
  discipline.

## What would refute the line

- **The round trip is not the identity on all 179 lessons.** Fatal and cheap to
  check; do it before anything else.
- **The learned pattern set converges on the twelve claws.** Then the IR bought
  expressiveness nobody needed, `omegaclaw_reach` already told us so, and the
  line closes with a null worth one note.
- **Any bits gain dies under renaming**, the way `ensemble-001`'s 1.14 did. Then
  it is memorisation in a new notation. Permute all 2,105 symbols without
  refitting; the `_pure` convention for reporting it already exists.
- **Cost.** `APPROACH.md` targets ~200k tok/s and `vsa_sum-004` at d=256 does
  282k. Unification is not free and a pattern matcher over a space of thousands
  of atoms can be ruinous. Price it on the model's own inner loop the way
  `scripts/vsa_dim_curve.py` does — separating reasoning throughput from the
  `[B, L, V]` interface cost — and report it beside the quality, not instead.

## What stays learned

The MeTTa layer decides *where to look*; it does not decide *which symbol*. The
`vsa-003/004` extract/re-insert pair stays, now with atoms as the role source:
an atomspace query gives a far richer role than `(ptype, slot, depth, arity)`,
which is the one hand-built tuple `vsa_hks-004` already beat with a graph-derived
signature (+0.107 against +0.066).
