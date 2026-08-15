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

## The result to lead with: the type head moved, it was predicted, and it still does not clear the floor

Both halves of that sentence are load-bearing and neither survives alone.

The pre-registration named this head and named the mechanism, before anything
was built:

> **The type head, which nothing has attacked.** Floor 0.860, two of nineteen
> models positive, every VSA row parked at −0.486. `(: label type)` is a
> first-class atom here rather than a second head bolted on, and design rule 1
> (the heads do not share machinery) is satisfied by construction rather than by
> discipline.

| row | type acc | type lift | type bits | type bits lift |
|---|---:|---:|---:|---:|
| floor | 0.8601 | 0.000 | 2.3292 | 0.000 |
| every other `vsa_*` / `metta_*` row | 0.7922 | −0.4855 | 1.1806 | +0.4931 |
| **`metta_type-005`**, `metta_type_pure-005` | **0.8203** | **−0.2849** | **1.0110** | **+0.5660** |
| `corefer-001` | 0.9458 | +0.6123 | 0.3479 | +0.8506 |

**+0.201 of type lift and +0.073 of type bits lift** — and unlike everything else
in this line, the two metrics agree in direction, which they have not done
anywhere else in this repo's history for these models.

**It is the largest movement any VSA-family row has ever shown on the type head,
and it does not clear the floor.** −0.285 is below zero. The floor is 0.860 and
two of nineteen models beat it; this is not one of them. The honest claim is
"first movement on the head nothing had attacked", and the claim that is *false*
is "clears the type floor".

So the answer to *"is the type head unattacked because nobody looked down?"* is
**no**. Looking down — the multiset of a node's child types, which no key in this
repo has ever read, since `node_context` is `(parent type, slot, depth, has
children)` and entirely upward — helps a great deal and is not close to enough.
The floor's six-level backed-off upward ladder is genuinely strong, and the type
column is **saturated rather than unattacked**. That redirects effort away from a
whole class of ideas, which is worth more than the win would have been.

### Design rule 1, checked in the code and then in the arithmetic

`corefer` paid 0.174 → 0.004 for letting its heads share machinery, so a type
gain that leaked out of the label head would be that mistake in a new notation.
Checked, rather than asserted:

- `RuleBasedModel._forward_graph` fills **separate** confidence arrays `s_conf`
  and `t_conf` from separate `_collect` calls, and mixes them against
  **separate** back-offs (`symbol_backoff`, `type_backoff`).
- the `structural_fallback` prior is passed to the `symbol_logits` `_mix` call
  **only** — `prior=` appears once and it is on the label route;
- the post-hoc fitted `self.temperature` is applied to `symbol_logits`
  **only**;
- `DownwardTypes._type_vote` reads its own `type_rules` ladder with its own
  support threshold and its own confidence `min(0.15 + 0.8 n/total, 0.95)`,
  while the label vote goes through the fitted `MassCalibrator` gate. Different
  calibrators, not one shared one.

And then the arithmetic says the same thing without being asked. `metta_type-005`
differs from `metta-005` in the type head and nothing else:

| | label lift | label bits | copy acc |
|---|---:|---:|---:|
| `metta-005` | 0.0960 | 6.4905 | 0.1907 |
| `metta_type-005` | **0.0960** | **6.4905** | **0.1907** |
| `metta_pure-005` | 0.0780 | 6.6273 | 0.1907 |
| `metta_type_pure-005` | **0.0780** | **6.6273** | **0.1907** |

Identical to four decimals on every label and copy column while the type column
moves +0.201. A second confirmation falls out for free: the `_pure` switch moves
label numbers and leaves the type numbers **bit-identical** (0.8203 in both),
which is what a label-only fallback should do and is now measured rather than
read off the source.

## The knob: the likelihood wants the atomspace queries, and pays for them in bits rather than in accuracy

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

### This answers a question `RESEARCH_LOG.md` has had open for weeks

> Can anything reach the 0.722 copy ceiling? Four candidate-level features in a
> row have failed, and a discriminative re-ranker was worse than counting.
> `ptrgen`'s marginal-likelihood pointer is the fifth thing to not help, at
> +0.078 copy lift against `corefer`'s +0.096. The first thing that *did* move
> a pointer a long way is `vsa_perm-002`, and it moved it from far below the
> floor to +0.060 — **still third of the pointers, so the ceiling is
> untouched.**

`metta_perm_pure-005` is **first**, at +0.1091 against `corefer-001`'s +0.0959.
The ceiling is still a long way off — 0.346 of 0.722, so under half the
reachable signal — but "nothing has ever been first" is no longer true, and the
thing that did it is a role built from conjunctive queries over an atomspace.

### Both models are answering the same question, which is worth showing

A pointer is scored on **what it picked, not on which index it picked**:
`_source_counts` computes `label_group[picked] == label_group[asked]`, so
choosing any node that corefers with the hidden one is correct and choosing the
"wrong" node with the right label group is not penalised. A pointer may not
choose a padded position and may not choose itself. Scored over every masked
node that has a label — **including the 88.5% invented `ident` names the
vocabulary cannot name**, which is the point of the head, since those are
exactly where copying is the only available route.

The denominator is identical across every row of the sweep, **n = 5,785**, with
the same floor 0.2658 and the same ceiling 0.7216, and `corefer-001` reproduces
its published copy number to four decimals inside this run. So the two models
are being asked one question and not two differently-shaped ones.

### The same two models, on the type head, in the opposite order

Put the three columns side by side and this becomes the sharpest example in the
repo of `notes/lessons/2026-08-13-a-ranking-is-a-property-of-a-metric.md`:

| | `metta_perm_pure-005` | `corefer-001` |
|---|---:|---:|
| copy lift | **+0.109** | +0.096 |
| label lift | +0.140 | **+0.250** |
| **type lift** | **−0.486** | **+0.612** |

The same pair of models is first-and-second on the pointer, second-and-first on
label accuracy, and separated by **1.098** of type lift in the second direction.
There is no ordering of these two models that is not a statement about which
metric was chosen. A one-line summary of this line — "the atomspace IR beats
`corefer`" or "the atomspace IR loses to `corefer`" — is available in both
directions from the same run directory, and neither is a result.

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

## The sweep

All nineteen rows, one directory, `scripts/metta_table.py` asserting the floors
are identical across every row before it prints. `rename` is `summary.json`'s
`drop`: **positive means accuracy was lost** under a permutation of all 2,105
symbols with no refitting.

| model | lbl acc | lbl lift | bits | bits lift | typ acc | typ lift | cpy acc | cpy lift | rename | secs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `corefer-001` | 0.357 | +0.250 | 6.955 | +0.258 | **0.946** | **+0.612** | 0.336 | +0.096 | +0.003 | 359 |
| `vsa_perm_pure-002` | **0.337** | **+0.227** | 6.622 | +0.293 | 0.792 | −0.486 | 0.310 | +0.060 | −0.003 | 49 |
| `vsa_perm-002` | 0.326 | +0.213 | 6.491 | +0.307 | 0.792 | −0.486 | 0.310 | +0.060 | +0.010 | 52 |
| `metta_perm-005` | 0.274 | +0.153 | **6.338** | **+0.324** | 0.792 | −0.486 | **0.346** | **+0.109** | +0.009 | 402 |
| `metta_perm_pure-005` | 0.263 | +0.140 | 6.468 | +0.310 | 0.792 | −0.486 | **0.346** | **+0.109** | −0.007 | 355 |
| `vsa_hks-004` | 0.242 | +0.115 | 6.643 | +0.291 | 0.792 | −0.486 | 0.213 | −0.072 | +0.009 | 287 |
| `vsa_hks_pure-004` | 0.235 | +0.107 | 6.781 | +0.276 | 0.792 | −0.486 | 0.213 | −0.072 | +0.003 | 351 |
| `vsa_sum-004` | 0.228 | +0.098 | 6.583 | +0.297 | 0.792 | −0.486 | 0.194 | −0.097 | +0.012 | 37 |
| `metta_gated-005` | 0.227 | +0.098 | 6.477 | +0.309 | 0.792 | −0.486 | 0.193 | −0.100 | +0.018 | 591 |
| `metta_tuple-005` | 0.226 | +0.096 | 6.581 | +0.298 | 0.792 | −0.486 | 0.193 | −0.099 | +0.011 | 55 |
| `metta-005` | 0.225 | +0.096 | 6.490 | +0.307 | 0.792 | −0.486 | 0.191 | −0.102 | +0.018 | 319 |
| `metta_type-005` | 0.225 | +0.096 | 6.490 | +0.307 | **0.820** | **−0.285** | 0.191 | −0.102 | +0.018 | 324 |
| `vsa_sum_pure-004` | 0.214 | +0.083 | 6.724 | +0.282 | 0.792 | −0.486 | 0.194 | −0.097 | −0.000 | 37 |
| `metta_gated_pure-005` | 0.213 | +0.081 | 6.613 | +0.294 | 0.792 | −0.486 | 0.193 | −0.100 | +0.001 | 641 |
| `metta_tuple_pure-005` | 0.213 | +0.081 | 6.722 | +0.283 | 0.792 | −0.486 | 0.193 | −0.099 | −0.002 | 55 |
| `metta_pure-005` | 0.210 | +0.078 | 6.627 | +0.293 | 0.792 | −0.486 | 0.191 | −0.102 | +0.002 | 311 |
| `metta_type_pure-005` | 0.210 | +0.078 | 6.627 | +0.293 | **0.820** | **−0.285** | 0.191 | −0.102 | +0.002 | 332 |
| `metta_shuf-005` | 0.092 | −0.060 | 7.333 | +0.217 | 0.792 | −0.486 | 0.074 | −0.261 | +0.009 | 388 |
| `metta_shuf_pure-005` | 0.081 | −0.072 | 7.490 | +0.201 | 0.792 | −0.486 | 0.074 | −0.261 | −0.001 | 380 |

Requoted separately because they live in `runs/vsa_role` — same config, same
eval seeds, **`label_floor` 0.1432, identical**: `vsa_hks_wide_pure-004` 0.280 /
+0.160 / 6.634 / +0.292 / rename +0.006. The `vsa_hks-004` rows *in* the table
above are the **stale, bandwidth-pinned** ones and should not be used as the
graph-derived-role baseline.

### The control that could have failed, and did

`metta_shuf-005` is the identical schedule with the signature rows permuted
across nodes: the same multiset of signatures, the same Gram value distribution,
attached to the wrong nodes. It falls to **0.081 label accuracy** against
`metta_pure-005`'s 0.210 and **0.074 copy** against 0.191 — below the floor on
both, and below `vsa_null`-style abstention, because a shuffled role does not
merely fail to help: it asserts confidently that unrelated nodes are alike.

So the machinery is fully capable of producing a collapse, and the +0.011 bits
and +0.049 copy are not artefacts of a graded Gram being graded. What is doing
the work is the **correspondence between a query result and the node it
describes**.

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

`metta_tuple-005` re-expresses `vsa-002`'s four coordinates as conjunctive
queries over the atomspace and changes nothing else. Pre-registered to reproduce
`vsa_sum-004` to within crosstalk — the two draw independent random atoms per
coordinate, so they are not bit-identical, but the Gram has the same
distribution.

| | lbl acc | lbl lift | bits | bits lift | cpy acc | rename |
|---|---:|---:|---:|---:|---:|---:|
| `vsa_sum-004` | 0.228 | +0.098 | 6.583 | +0.297 | 0.194 | +0.012 |
| `metta_tuple-005` | 0.226 | +0.096 | 6.581 | +0.298 | 0.193 | +0.011 |
| `vsa_sum_pure-004` | 0.214 | +0.083 | 6.724 | +0.282 | 0.194 | −0.000 |
| `metta_tuple_pure-005` | 0.213 | +0.081 | 6.722 | +0.283 | 0.193 | −0.002 |

**Agreement to 0.002 on every column.** Saying the old thing in the new notation
reproduces the old number, so the harness did not move and everything else in
this note is attributable to the IR rather than to a changed contract.

Six reference rows were re-run into this directory rather than cited from their
original sweeps, and **all six reproduce their published numbers to three
decimals** — `vsa_sum-004`, `vsa_sum_pure-004`, `vsa_hks-004`,
`vsa_hks_pure-004`, `vsa_perm-002`, `vsa_perm_pure-002`, plus `corefer-001`
matching to four on the copy column. That is what licenses reading the table at
all, and it is why the sweep re-ran rows whose answers were already known.

## 5. The label head

The numbers are above; what belongs here is the verdict on the
pre-registration's central claim.

**Pre-registered:** *"`metta-005` will not beat `corefer-001` or
`vsa_perm_pure-002` on label accuracy, and the reason is already measured"* —
`omegaclaw_reach-001` added `ilp`'s best discovered operator and still lost,
because `ilp` is uniquely right on only 2.2% of nodes and candidate recall
climbing 82.7% → 98.7% moved accuracy by 0.000. Reach was never the constraint;
discrimination is.

**Confirmed, and by a wide margin.** Best `-005` label accuracy is
`metta_perm-005` at 0.274 against `corefer-001`'s 0.357 and
`vsa_perm_pure-002`'s 0.337. Not close. The prediction was right and it was
right *for the stated reason*: the atomspace demonstrably reaches further —
`metta_shuf-005`'s collapse proves the extra signatures carry real information,
and the likelihood curve proves the model wants them — and reaching further
still does not decide better.

This is the third independent confirmation of the same fact in this repo
(`omegaclaw_reach-001`, the candidate-recall experiment, and now this), and it
is the most expensive one, so it should probably be the last. **Expressiveness
is not the binding constraint on this curriculum's label head.** Any future line
proposing to win on label accuracy by representing more should have to say what
it does about *discrimination*, not about *reach*.

## 6. The type head — the numbers are at the top of this note

Led with, because it was the pre-registered one. Two things belong here rather
than up there:

**The narrower prediction inside it was refuted.** `MettaTypes`' docstring said
*"**positive type lift**"*. It is −0.285. Predicting the head correctly and the
sign wrongly is worth separating from predicting nothing.

**The guard against the flattering reading was written first and turned out not
to be needed.** The design note said a type head landing near 1.0 would be a
*definition* rather than a result — the encoding would be carrying the answer,
which is the trap `symbolic_ai_parsers` fell into when it reported UAS 0.95 for a
parser that did no parsing. It landed at 0.820, so nothing here is trivially
correct by construction, and the check cost nothing to have made in advance.

## 7. Cost: the ratios, and a refusal to quote the absolute rate

**The absolute throughput numbers from this pass are not reportable, and the
instrument said so rather than me.** `scripts/metta_cost.py` carries a
calibration control: `vsa_sum-004` is in the same directory, timed by the same
code, and has a published rate of **18,995 tok/s** at this `d = 4096` from the
dimension curve. It measured **9,493 — 0.50x**, outside the 0.7–1.4x band, so
the script printed `THE BOX WAS NOT QUIET` and exited non-zero. Load average was
12–18 on 20 cores with a parallel sweep and real training on the machine.

A missing number with a reason beats a contaminated one. What survives is the
**ratios between rows measured in the same pass**, which share the contamination:

| contrast | reasoning tok/s (contaminated) | ratio | what it prices |
|---|---:|---:|---|
| `vsa_sum-004` | 9,493 | 1.00x | four dict lookups per node |
| `metta_tuple-005` | 3,613 | **0.38x** | the *same four features*, via encode-to-atomspace + conjunctive query |
| `metta-005` | 1,003 | **0.11x** | the full six-query schedule |
| `vsa_perm-002` | 1,170 | — | permutation channel, hand-built roles |
| `metta_perm-005` | 275 | **0.24x of `vsa_perm-002`** | permutation channel, query roles |

So, stated as multipliers rather than as rates:

- **The IR machinery alone costs 2.6x.** `metta_tuple-005` computes exactly
  `vsa-002`'s four coordinates and differs only in getting them by building an
  atomspace and running two conjunctive queries over it. That is the price of the
  representation with the expressiveness held fixed, and it is the honest
  denominator for "was the IR worth it".
- **The full query schedule costs 9.5x**, and 4.2x on top of the IR itself. Six
  queries, ~14 extra signatures per node, and a sibling join that is quadratic in
  arity.
- **In the permutation channel the tax is 4.3x.**

**Against `APPROACH.md`'s budget**, and the honest framing is that this line is
not where the budget is lost: `vsa_sum-004` at `d = 256` does 282,170 tok/s and
is comfortably inside the ~200k target, while the same model at the `d = 4096`
every row here uses does 18,995 — already **15x below target before any
atomspace exists**. The dimension is the dominant cost and the IR is a
multiplier on top of it. A `005` row at `d = 256` has never been run, and by the
dimension curve's own finding — quality saturates at `d = 1,024` and the last
64x buys nothing — that is the obvious cheap experiment this line did not do.

**Interface share.** 49–74% of deployed cost is the harness's `[B, L, V]`
assembly rather than any reasoning, which is independent of everything above and
is why the two clocks are reported separately.

**What would settle it:** re-run `scripts/metta_cost.py` on an idle box. It is
one command, it self-checks, and it will refuse again if the box is busy.

## What would have refuted this, stated before the numbers

The pre-registration listed four. All four were checked and two fired.

| condition | outcome |
|---|---|
| the round trip is not the identity on all 179 lessons | **passed** — identity on 895 graphs, and it caught two encoding bugs on the way |
| the learned pattern set converges on the twelve claws | **did not fire** — the likelihood curve rises monotonically to `extra_weight` 2.0, so the model actively wants the atomspace-only patterns |
| any bits gain dies under renaming | **did not fire** — +0.011 bits lift at a +0.001 drop, all 2,105 symbols permuted, no refitting |
| cost | **fired** — 2.6x for the IR alone, 9.5x for the full schedule; and the absolute rate is unquotable from this pass |

Plus the two predictions written into the model docstrings, which are a stricter
bar because they name a number:

| prediction | outcome |
|---|---|
| `metta_tuple-005` reproduces `vsa_sum-004` to within crosstalk | **confirmed**, 0.002 on every column |
| `metta-005` does not beat `corefer-001` or `vsa_perm_pure-002` on label accuracy | **confirmed**, 0.274 vs 0.357 and 0.337 |
| `metta_gated-005`'s knob lands at or near 0.0 | **refuted** — interior at 2.0; this came off a six-lesson slice and is inversion number thirteen |
| `metta_type-005` shows positive type lift | **refuted** — −0.285, a +0.201 move that does not clear the floor |

## What this line should and should not be cited for

**Cite it for:** the type head is *saturated, not unattacked* — the downward
direction is worth +0.201 and still loses to the floor's upward ladder;
expressiveness is not the binding constraint on the label head, now on a third
independent measurement; and a `Graph` cannot be content-addressed into an
atomspace without losing 42.3% of its nodes.

**Do not cite it for:** the copy result, until an independent refuter has been
at it. It is the largest effect here, it was **not** pre-registered, and an
unpredicted large effect is the single most likely thing in this repo to be a
harness artefact rather than reasoning. The mechanism offered for it is an unrun
story and is labelled as one.

**Status is `provisional`** on the definition in `notes/README.md`: every
control in this note was designed by the same agent that wrote the treatment.
The one exception is the `hyperon` conformance check, which is the only
assertion here that does not come from code this repo wrote.
