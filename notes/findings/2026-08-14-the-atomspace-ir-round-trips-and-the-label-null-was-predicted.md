---
date: 2026-08-14
author: agent-005-atomspace
status: provisional
related: [2026-08-14-the-ir-is-a-knob,
          2026-08-14-atomspace-metta-ir-preregistration,
          2026-08-14-graph-derived-roles-structure-not-locality,
          2026-08-14-five-of-seventeen-node-types-are-dead]
---

# `005`: the atomspace round-trips, an outside MeTTa agrees with it, and the label head is the null the pre-registration ordered

Full 179-lesson sweep, `configs/full179.toml`, `runs/metta005`. Not a slice.
Floors, identical across every row and asserted to be by
`scripts/metta_table.py` before it prints: **label 0.143, type 0.860, copy
0.266, copy ceiling 0.722.**

## The headline: the likelihood wants the atomspace queries, and pays for them in bits rather than in accuracy

**A correction first, because it is the tenth time this has happened here.** The
six-lesson wiring check said the knob ran to **0.0** — "the extras contribute
nothing" — and that reading was written into this line's model docstrings as the
pre-registered expectation. On all 179 lessons it is **refuted**. The knob is
`extra_weight`, the share of a node's role given to the signature groups only an
atomspace can produce, fitted on held-out **training** episodes by the
log-likelihood of the calibrated mixture — the model that actually ships:

| `extra_weight` | hand-built share of role | held-out mixture LL |
|---:|---:|---:|
| 0.0 (= `metta_tuple-005`) | 100% | −4.1417 |
| 0.25 | 62.8% | −4.1145 |
| 0.5 | 47.5% | −4.0888 |
| 1.0 (= `metta-005`) | 32.3% | −4.0676 |
| **2.0** | **20.0%** | **−4.0639** |
| 4.0 | 11.4% | −4.0661 |

This is the one thing an argmax could not have told us and the curve does.
It is **monotone increasing from 0 to 2 and then turns down**, so it is none of
the three failure modes: not a truncated grid, not a flat objective with a noisy
argmax, and not a boundary. It is a **genuine interior optimum with a real
turnaround**, identical in both the `_pure` and non-`_pure` rows to four decimal
places. The likelihood does not merely tolerate the typed sibling, the child
types and the path — it prefers them at **twice** the weight of the four
coordinates `vsa-002` asserts, and it prefers each step toward them
monotonically.

Six lessons said zero; a hundred and seventy-nine say two. Slice number ten.

**And the gain is bits, not accuracy** — which is exactly, and only, where the
pre-registration said a legitimate win could appear.

## The bits gain is real, small, and survives renaming

The sharp test named in the pre-registration: *"if a pattern-matching IR gains
bits, that gain is structural and must survive a permutation of all 2,105
symbols without refitting."* The `_pure` rows are that test, because
`structural_fallback` is where every VSA row's renaming sensitivity lives.

| row (role channel only, `_pure`) | lbl acc | bits | bits lift | rename |
|---|---:|---:|---:|---:|
| `vsa_sum_pure-004` | 0.214 | 6.724 | +0.282 | −0.000 |
| `metta_tuple_pure-005` | 0.213 | 6.722 | +0.283 | −0.002 |
| `metta_pure-005` (share 1.0) | 0.210 | 6.627 | +0.293 | **+0.002** |
| `metta_gated_pure-005` (share 2.0) | 0.213 | **6.613** | **+0.294** | **+0.001** |

**+0.011 of bits lift over the identical machinery with only the query schedule
changed, at a renaming drop of +0.001.** All 2,105 symbols permuted, no
refitting. The gain is structural: no query in the schedule reads the `label`
relation, asserted on the schedule *and* empirically by permuting every label
and requiring the signatures to come out bit-identical.

For scale, this is a tenth of what `ensemble-001` claimed and did not keep. That
row reached 4.77 bits and lost 0.467 → 0.038 of it under renaming, because the
gain was vocabulary memorisation. This one is 0.011 and keeps essentially all of
it. **A small honest number and a large dishonest one are not on the same
scale**, and the whole point of running the permutation early was to find out
which kind this was.

**Accuracy does not move**: 0.213 against 0.213, and `metta_pure-005` is
*worse* at 0.210. So the atomspace roles improve the **density estimate** and not
the **decision** — this repo's oldest measured fact, `label_acc` and
`label_bits` ranking these models close to inversely, showing up one more time.
Quoting either number alone would misreport the line in opposite directions.

## Read the table with this in mind

## Read the table with this in mind

At the equal share `metta-005` pins, the four hand-built coordinates hold only
**32.3% of the role mass** — mean 4.0 hand-built signatures per node against
**14.3** atomspace-only ones (median 9, p90 23, max 237), measured over 12,734
nodes of 179 lessons.

So **`metta-005` is not "the four-tuple plus extras"; it is "extras dominating a
diluted four-tuple"**, and a row-against-row comparison with `vsa_sum-004` is
*not* the controlled swap it looks like. Two things change at once: which
signatures exist, and how much of the role the old ones keep. `metta_gated-005`
is the row that separates them, because its grid moves the hand-built share from
62.8% (`extra_weight` 0.25) through 32.3% (1.0) to 11.4% (4.0), and
`metta_tuple-005` is the 100% end.

<!-- TABLE -->

## 1. The round trip is the identity, and covering the curriculum earned it twice

`Graph -> atomspace -> Graph` over **every graph of all 179 lessons at five
seeds — 895 graphs** — compared on `to_dict()`, so `depth` is included; and
`depth` is *recomputed* by the decoder rather than stored, which makes the check
stronger than comparing what was written down.

Covering rather than sampling paid immediately, twice:

**The encoding the pre-registration proposed is lossy.** It proposed the obvious
structural map — a term node becomes an `Expression` headed by its label. An
atomspace stores each atom once, so content-equal occurrences merge and the
parent's arity stops being recoverable. Measured over the same 895 graphs:
**26,351 of 62,253 nodes — 42.3% — would collapse, affecting 869 graphs
(97.1%).**

That is not a corner case, it is nearly half the corpus, and it is a property of
the representation rather than of this curriculum: a `Graph` is a tree of
*occurrences* and an atomspace is a set of *values*. The encoder therefore
**names** occurrences and carries five relations — `(node)`, `(:)`, `(label)`,
`(child)`, `(root)` — with `depth` deliberately not stored, because storing a
derived field would let a space hold a graph that `Graph` cannot represent.

The pre-registration's second proposal, `(: label type)`, fails for an unrelated
reason worth recording beside it: labels repeat across types, and the empty
label alone is carried by every `STRUCTURAL` type. The typing atom has to key on
the occurrence, not on the symbol.

**A digit-only label reparses as a grounded integer.** A `num` node's label
*is* `3`, so `Symbol("3")` printed unquoted and read back as `Grounded(3)`. The
object round trip passed; only the **source** round trip caught it — and the
source is what the conformance oracle consumes. Both are asserted separately now,
on the whole corpus, alongside a test that the corpus actually contains an empty
label, an underscore, both parens, whitespace and a digit-only label. That last
test is the one that makes the other two mean anything: it is the guard
`test_encoding_is_lossless` did not have when its fixture happened to contain no
underscore.

## 2. An outside MeTTa agrees, and the check can fail

`hyperon` publishes no wheel for this project's Python 3.13 and a C extension
inside a sweep would break `APPROACH.md`'s budget, so it is an **out-of-band
oracle, never a dependency and never in the hot path**. Our spaces are written
out as MeTTa source, the same queries are run under a real hyperon 0.2.10 in its
own 3.12 interpreter, and the binding sets are compared.

**12 curriculum graphs, 1,575 bindings, 0 disagreements.**

That number could have been vacuous — if hyperon had returned nothing and we had
recorded nothing, the counts would have agreed perfectly. So the run prints how
many bindings it compared, fails if that is zero, and `--selftest` deletes one
recorded binding and must exit non-zero. It does, with the counts off by exactly
one. This is the only assertion in the whole line that does not come from code
this repo also wrote.

## 3. What the MeTTa layer can express that `CLAWS` cannot

`CLAWS` is twelve routes somebody wrote down. Five things are expressible here
that are not expressible there, and only the first was the pre-registration's:

1. **A typed, slot-selected sibling.** `(child $p $k $q) (child $p $j $s)
   (: $s pred)`. `CLAWS` has `sibling0` and `prev_sibling` and no way to say
   *which* sibling — the offset `$j - $k` is a value in a query here and a case
   in an enum there. This is `ilp`'s strongest discovered clause, and reaching it
   is why `omegaclaw_reach-001` had to grow a branch.
2. **The downward direction at all.** `node_context` — the tuple the masked-node
   floor, the shared back-off, `OmegaClaw.perceive` and the VSA type head all key
   on — is `(parent type, slot, depth, has children)`: entirely upward, plus one
   bit of arity. `(child $q $k $c) (: $c $t)` names what a node *contains*, and
   nothing in this repo has ever had that feature.
3. **Joins of arbitrary length over a shared variable.** A claw is a fixed
   route; a query is a join, so "grandparent's type together with both slots on
   the path down" is one pattern rather than a new route kind.
4. **Derived relations as first-class atoms.** `chain` writes `(sibling ...)`
   back into the same space its premises came from, so a derived fact is
   queryable exactly as a given one is. That is what makes "one more pattern
   rather than one more `if`" literally true rather than a figure of speech.
5. **Bounded transitive closure.** Ancestry is two rules, not a loop — and
   `tests/test_metta.py` pins the hot path's depth against exactly that closure,
   so the fast path is a tested equality rather than a comment.

What was deliberately left out is written down in `symbolic_ai_atomspace/metta.py`:
grounded execution, non-determinism as an effect (`superpose`/`collapse`),
backward chaining, unbounded recursion, nested spaces, equality-as-reduction —
and **type checking**, which is `006`'s arm of the fork and would collapse the
comparison if implemented here.

## 4. The harness check, which licenses reading anything else

<!-- HARNESS -->

## 5. The label head

<!-- LABEL -->

## 6. The type head

<!-- TYPE -->

## 7. Cost

<!-- COST -->

## What would have refuted this, stated before the numbers

<!-- REFUTE -->
