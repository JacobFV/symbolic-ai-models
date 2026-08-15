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

## The largest effect is on a head nobody predicted, and it is the copy head

The pre-registration named two places a win could legitimately appear: **bits**,
and **the type head**. It did not name the pointer. The largest effect in this
line is on the pointer, and because it was unpredicted it is the result most in
need of an independent refuter rather than the one to lead a claim with.

Permutation-channel rows, exactly equivariant (`_pure`), same floors, copy floor
**0.266** and copy ceiling **0.722**:

| row | lbl lift | bits lift | **copy acc** | **copy lift** | rename |
|---|---:|---:|---:|---:|---:|
| `vsa_perm_pure-002` | **+0.227** | +0.293 | 0.310 | +0.060 | −0.003 |
| `metta_perm_pure-005` | +0.140 | **+0.310** | **0.346** | **+0.109** | **−0.007** |
| `corefer-001` (best published pointer) | +0.250 | +0.258 | 0.336 | +0.096 | +0.003 |

Three things move at once and they do **not** move together:

- **copy lift +0.060 → +0.109**, an improvement of +0.049, which also clears
  `corefer-001`'s +0.096 — the best pointer this repo has published;
- **bits lift +0.293 → +0.310**, +0.017;
- **label lift +0.227 → +0.140**, a real **loss** of −0.087.

All of it at a renaming drop of **−0.007** — the model is slightly *better* after
every symbol is permuted, which is what exact equivariance plus noise looks like.

### A mechanism, offered as a hypothesis and not as a result

The label head and the pointer read the same roles through different operations,
and a richer role should help one and hurt the other:

- the pointer scores a node by `<Q_role(i), role(j)>` — a **cleanup against the
  role address codebook**. More signatures means more discriminative addresses,
  so pointing gets better.
- the label head unbinds the episode trace at the query's role. Every extra
  signature adds another term to a superposition that already carries every
  node, so **crosstalk rises** and symbol retrieval gets worse.

That predicts exactly the observed sign pattern. It is a story that fits, told
after the fact, and this repo has a lesson about those. What would test it: the
crosstalk account says the label loss should grow with the number of signatures
per node, so it should be worse on wide graphs and on high-arity nodes than on
narrow ones — a per-node breakdown nobody has run. **Not run here, and the
mechanism is therefore unconfirmed.**

## The result on the head the repo leads with, in one sentence with both columns

**The atomspace query schedule buys +0.011 of `label_bits` lift over identical
machinery and 0.000 of `label_acc`** — 0.213 against 0.213 — **and the bits gain
survives a permutation of all 2,105 symbols at a drop of +0.001.**

Neither half of that sentence may be quoted without the other. This repo's
entire published history was accuracy rankings that never said they were
accuracy rankings, and `label_acc` and `label_bits` rank these models close to
inversely. An "atomspace roles win" headline and an "atomspace roles are a null"
headline are both available here and both are misreporting.

### The bits gain, and the renaming test that is the load-bearing part

The sharp test named in the pre-registration: *"if a pattern-matching IR gains
bits, that gain is structural and must survive a permutation of all 2,105
symbols without refitting."* The `_pure` rows are that test, because
`structural_fallback` is where every VSA row's renaming sensitivity lives.

| row (role channel only, `_pure`) | lbl acc | lbl lift | bits | bits lift | rename |
|---|---:|---:|---:|---:|---:|
| `vsa_sum_pure-004` | 0.214 | +0.083 | 6.724 | +0.282 | −0.000 |
| `metta_tuple_pure-005` | 0.213 | +0.081 | 6.722 | +0.283 | −0.002 |
| `metta_pure-005` (share 1.0) | 0.210 | +0.078 | 6.627 | +0.293 | **+0.002** |
| `metta_gated_pure-005` (share 2.0) | 0.213 | +0.081 | **6.613** | **+0.294** | **+0.001** |

`metta_tuple_pure-005` and `metta_gated_pure-005` differ in **one thing only** —
which conjunctive queries produce the signatures — so the +0.011 is attributable
to the query schedule and to nothing else.

**Why the renaming column is the whole result and not a footnote.** A bits gain
is the easiest thing in this repo to fake, and this repo has faked it. The best
bits ever recorded here, `ensemble-001` at **4.77**, turned out to be vocabulary
memorisation: permute the symbols without refitting and **0.467 collapsed to
0.038**, keeping 8% of what it claimed. That is why the pre-registration made
the permutation the *first* thing to run rather than a check at the end.

This gain is **a tenth the size and keeps essentially all of it.** +0.011 of
bits lift at a +0.001 drop, against +1.14 at a −0.429 collapse. The comparison
is the point: a small number that is real is worth more than a large one that is
not, and the only way to tell them apart is the control that could have failed.
It could have failed here — `metta_shuf_pure-005` is the same schedule with the
signatures on the wrong nodes and it lands at **0.086 label accuracy** against
0.210, so the machinery is fully capable of producing a collapse.

The structural claim is also closed at the source rather than inferred from the
number: **no query in the schedule reads the `label` relation**, asserted on the
schedule itself *and* empirically by permuting every label in a view and
requiring the signatures to come out bit-identical.

### Against the right baseline, which is not the one this line was designed against

`vsa_hks-004`'s bandwidth was pinned at the bottom of its grid; an independent
refuter refitted it, and the fitted-bandwidth rows are the real ones. Requoted
from `runs/vsa_role`, whose `label_floor` is **0.1432 — identical to this
sweep's**, same config and same evaluation seeds:

| role-only `_pure` row | lbl acc | lbl lift | bits | bits lift | rename |
|---|---:|---:|---:|---:|---:|
| `vsa_hks_wide_pure-004` | **0.280** | **+0.160** | 6.634 | +0.292 | +0.006 |
| `metta_gated_pure-005` | 0.213 | +0.081 | **6.613** | **+0.294** | **+0.001** |

**This is the honest comparison and it is unflattering in the column this repo
leads with.** The heat-kernel signature — a spectral quantity of the graph, no
queries, no atomspace — reaches **+0.160** of label lift where the atomspace
schedule reaches **+0.081**, twice as much. On bits the two are level, with the
atomspace row ahead by 0.002 of lift, which is inside anything worth calling a
difference.

So the graph-derived role that already existed is a **much better classifier**
and an **equal density estimate**, at a slightly worse renaming drop. The
atomspace's contribution is not that it found structure the spectrum could not;
it is that it found structure the *hand-built four-tuple* could not, and the
spectrum had already found more of it by another route.

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
