---
date: 2026-08-14
author: agent-refuter-spectral
status: measured
related: [2026-08-14-graph-derived-roles-structure-not-locality,
          2026-08-13-spectral-roles-preregistration,
          2026-08-14-a-boundary-optimum-is-not-a-fitted-value,
          2026-08-13-slices-have-inverted-results-eight-times,
          2026-08-13-a-control-that-could-fail]
---

# The graph roles survive the attack; the bandwidth they were measured at does not

An independent refutation of
`notes/findings/2026-08-14-graph-derived-roles-structure-not-locality.md`,
written by someone who did not write the models. **Full 179-lesson sweep**
(`configs/full179.toml`, `runs/vsa_role`) for every scored row; the two
diagnostics are labelled as diagnostics and neither carries a conclusion alone.

Floors, confirmed refitted rather than inherited: label **0.143**, type
**0.860**, copy **0.266**, copy ceiling **0.722** — byte-identical in all
twenty-seven `runs/vsa_role` summaries, in `runs/full179`, in `runs/ptrgen` and in
every `runs/vsa_dim/d*`, so every lift quoted here and there is against the same
denominator. `label_n` is **5,233** and `label_coverage` **0.8249** in every one
of the twenty-seven rows, so no accuracy comparison in this family is confounded
by a model abstaining more than another.

**The verdict in one line: the finding's four load-bearing conclusions all
survive, and its headline number is 0.053 too low.**

---

## What was attacked, and what happened

| # | claim | verdict |
|---|---|---|
| 1 | the shuffled control is load-bearing; the embedding's contribution is the correspondence | **survives, larger than claimed** — but two of its supporting statements die |
| 2 | graded beats partitioned with no graph at all | **survives**; the sentence quoting it mixes two columns |
| 3 | the pre-registered eigenmap is refuted | **survives**; its "mis-specified grid" reading and its slice mechanism numbers die |
| 4 | `vsa_perm_hks-004` is the repo's second-best pointer at +0.092 copy lift | **survives exactly** |
| 5 | the three heads disagree about the composition | numbers **verify exactly**, comparison **drawn at the wrong bandwidth** — see below |
| — | *not in the note*: the signature's bandwidth was pinned at the bottom of its grid | **the largest thing found here** |

---

## The largest thing found: `vsa_hks-004` was measured at a bandwidth the data does not want

All four registered heat-kernel rows fitted `knob = 0.5`, which is the **bottom**
of `knob_grid = (0.5, 1.0, 2.0, 4.0)`. That is the exact symptom
`notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value` was written
about — and the lesson was applied in the note to the **eigenmap**, which lost,
and not to the **signature**, which won. Nobody extended the winner's grid.

`vsa_hks_wide-004` extends it to `(0.0625, 0.125, 0.25, 0.5, 1, 2, 4)`. The fit
lands **interior at 0.25**, and it is worth a great deal:

| model | knob | grid | lbl acc | lbl lift | bits | bits lift | copy acc | copy lift | rename |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `vsa_hks_pure-004` (published) | 0.5 | bottom of (0.5 … 4) | 0.235 | +0.107 | 6.781 | 0.276 | 0.213 | −0.072 | +0.003 |
| `vsa_hks_wide_pure-004` | **0.25** | **interior** | **0.280** | **+0.160** | 6.634 | 0.292 | **0.256** | −0.014 | +0.006 |
| `vsa_hks-004` (published) | 0.5 | bottom | 0.242 | +0.115 | 6.643 | 0.291 | 0.213 | −0.072 | +0.009 |
| `vsa_hks_wide-004` | **0.25** | **interior** | **0.291** | **+0.173** | 6.499 | 0.306 | **0.256** | −0.014 | +0.019 |

**+0.053 of label lift on the equivariant row, +0.058 with the fallback on, and
+0.058 of copy lift, from one extra grid point.** The direction is toward a
*narrower* kernel — the graded signature Gram wants to be closer to a partition
on near-exact signature equality than the published fit allowed.

Consequences, in the order they matter:

- **§3's headline is wrong low.** "+0.107 against the hand-built partition's
  +0.066" is really **+0.160 against +0.066**. The finding's own conclusion is
  strengthened: the gap between graph-derived roles and hand-built ones is
  **+0.094**, not +0.041, and it more than doubles.
- **§4's central sentence is refuted.** "A better role Gram is worth less than
  half of what a positional channel is worth" — the signature alone now reaches
  +0.160 against `vsa_perm_pure-002`'s +0.227, which is **70%**, not less than
  half. The sentence was true of the pinned fit and is false of the fitted one.
- **§5 was drawn at the wrong point** and is redrawn below.
- Equivariance survives the change: `vsa_hks_wide_pure-004`'s renaming drop is
  **+0.006**, still inside the family's ±0.003-ish band and nowhere near the
  fallback rows'.

`vsa_hks_wide-004` is a *new registered row beside* `vsa_hks-004`, not an edit to
it, so every published number keeping that name still means what it said.

## Claim 1 — the shuffled control: the conclusion survives and grows; two of its supports fall

### It survives, and the missing row makes it bigger

The family had **no row with no role information at all**, so "the gradedness of
the Gram … contributes nothing on its own" had nothing to be nothing *against*.
`vsa_null-004` supplies it: i.i.d. bipolar roles, one per node, drawn from the
model seed and an FNV digest of the tree's shape, so every off-diagonal Gram
entry is `0 ± 1/sqrt(d)` and the row is still exactly a function of the tree.

| row | what the Gram is | lbl acc | lbl lift | copy acc | copy lift |
|---|---|---:|---:|---:|---:|
| `vsa_null_pure-004` | i.i.d. — no gradedness, no correspondence | 0.036 | **−0.125** | 0.031 | −0.320 |
| `vsa_spec_shuf_pure-004` | eigenmap shuffled (refit to t=1) | 0.067 | −0.089 | 0.061 | −0.279 |
| `vsa_spec_shuf16_pure-004` | eigenmap shuffled, **matched at t=16** | 0.083 | −0.070 | 0.076 | −0.259 |
| `vsa_hks_shuf_pure-004` | signature shuffled | 0.083 | −0.071 | 0.075 | −0.260 |
| `vsa_hks_shuf_wide_pure-004` | signature shuffled, **pinned at the fitted 0.25** | 0.079 | −0.075 | 0.072 | −0.264 |
| `vsa_hks_wide_pure-004` | the signature, at its fitted bandwidth | 0.280 | **+0.160** | 0.256 | −0.014 |

Read against the true bottom, the embedding is worth **+0.285** of label lift and
the correspondence is **+0.235** of it — **82%**. The finding said the
correspondence was what mattered; with a bottom row to measure from, it matters
more than the finding could show.

### But "gradedness contributes nothing on its own" is refuted

Gradedness with the correspondence destroyed is worth **+0.055** of label lift
over i.i.d. roles (−0.070 against −0.125), and +0.051 at the corrected
bandwidth (−0.075 against −0.125) — which is larger than the entire
+0.041 gap the note's §3 headline was built on. It is not nothing.

And it is not noise. **Two structurally unrelated embeddings, shuffled, land
within 0.001 of each other** — `vsa_spec_shuf16_pure-004` at 0.0833 and
`vsa_hks_shuf_pure-004` at 0.0827 — which is what a shared mechanism looks like
and what an accident does not. The honest sentence is *"misattributed gradedness
is worth about a fifth of what correctly attributed gradedness is worth"*, not
*"nothing"*.

### And "the Gram's value multiset survives bit-identically (asserted in the tests)" is not asserted in the tests

`tests/test_vsa_spec.py::test_shuffling_keeps_every_gram_value_and_loses_the_correspondence`
contains, before it compares anything:

```python
control._knob, control._cache = treatment._knob, None   # one knob, not two
```

It overwrites the control's fitted bandwidth with the treatment's. What it
therefore asserts is that *permuting rows permutes the Gram* — true by
arithmetic, at any bandwidth, for any pair. It cannot see the case that actually
occurred in `runs/vsa_role`:

- `vsa_spec-004` fitted **t = 16**; `vsa_spec_shuf-004` refitted to **t = 1**.

Two different kernels. For the published eigenmap pair the bit-identical-multiset
property — the whole reason a shuffle is a *control* and not a different model —
**is false as run**. `vsa_hks-004` and `vsa_hks_shuf-004` both fitted 0.5, so the
pair the finding actually leans on is matched; that was luck, not construction,
and the test that was supposed to guarantee it could not have caught the failure.

`vsa_spec_shuf16_pure-004` pins the grid to the single value 16 and is the
matched control the eigenmap pair never had. Matched, it scores **−0.070**, not
the −0.089 the drifted control scored — so **the eigenmap beats its real control
by 0.026, not by 0.045**. My prediction here (that matching would make it worse)
was refuted; the direction of the correction narrows the eigenmap's margin over
its own control, which strengthens the refutation in §3.

### The shuffle also fails to destroy a fifth of the correspondence — and it turns out not to matter

*Diagnostic, structural, all 179 lessons, 357 views, 21,319 nodes — it reads the
feature matrices and the permutation the control actually draws, so no model is
fitted and no metric is involved.*

A heat-kernel signature is **identical on an automorphism class**, and a term
tree is full of them, so permuting rows inside a class is a no-op:

| embedding | fixed points | row unchanged by the shuffle | correspondence destroyed |
|---|---:|---:|---:|
| `vsa_hks-004` | 0.015 | **0.189** | 0.811 |
| `vsa_spec-004` | 0.015 | 0.018 | 0.982 |

So `vsa_hks_shuf-004` keeps its true role on 18.9% of nodes. That is a real
defect in the control — and it is *conservative*, understating the damage.
It is also, as it happens, not the explanation for the +0.055: the eigenmap
shuffle destroys 98.2% of the correspondence and scores the **same 0.083**. A
shuffled graded Gram converges to a common value regardless of how much
correspondence it happens to preserve.

The shuffle is drawn per episode, from `(seed + 5, len(view), FNV(view.parent))`,
identically at fit time and at prediction time — pinned by
`test_the_shuffle_is_the_same_permutation_every_time_it_is_asked`. That part is
sound and I could not break it.

## Claim 2 — graded beats partitioned: survives, but the sentence mixes two columns

§2 reads: "`*` → `+` is worth **+0.017 label lift**, +0.023 bits lift, +0.018
copy lift, and it *reduces* the renaming drop from +0.029 to +0.012."

Verified against the run directories, those are **two different model pairs**:

| pair | label lift | bits lift | copy lift | renaming |
|---|---:|---:|---:|---:|
| `vsa_sum_pure-004` − `vsa_pure-002` (equivariant) | **+0.0170** | +0.0230 | +0.0181 | +0.002 → −0.000 |
| `vsa_sum-004` − `vsa-002` (fallback on) | **+0.0096** | +0.0227 | +0.0181 | **+0.029 → +0.012** |

The +0.017 is the `_pure` column; the renaming halving is the fallback column,
where the label gain is +0.010. Both halves are true, neither pair shows both,
and no single row in the sweep is the sentence. The *claim* survives in both
columns — graded beats partitioned either way, and by more than noise — but the
quoted figure should name its column, which is this repo's own standing rule.

One arithmetic slip alongside it: the fallback is worth **+0.0132** for
`vsa_sum-004`, printed as +0.014. Everything else in that series checks
(+0.0195, +0.0067, +0.0069, −0.0115).

## Claim 3 — the eigenmap is refuted: survives; the reasons given for it do not

**The number is right.** `vsa_spec_pure-004` is 0.1055 / −0.0440, below the
0.143 floor, reproduced from `runs/vsa_role/vsa_spec_pure-004/summary.json`.

**The note's loosest claim is now measured, and it holds.**
`vsa_spec_wide_pure-004` extends the grid to `(4, 16, 64, 256, 1024)` and comes
out **bit-identical to `vsa_spec_pure-004`** — 0.1055 / −0.0440 / 7.3802 /
0.2123 / copy 0.0958, every digit. A wider diffusion grid does not rescue the
eigenmap. That was an argument in the note and it is a measurement now.

**But the reason the note gave for it is wrong.** The note, and
`notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value`'s second case
study, both read `t = 16` as a *mis-specified grid* whose pinned value meant
nothing. Extended, the fit **stays at 16 with 64, 256 and 1024 available**, which
makes it an **interior optimum and a genuine fitted value**. The lesson note's
"`vsa_spec_pure-004`, and here the boundary was the finding" needs amending: the
boundary was an artifact of the grid's top happening to be the optimum, and the
lesson's own guard — *"extend the grid past the optimum and refit; if it stays
pinned you have learned the direction"* — was never run on it. It has been now.

**And the mechanism's numbers do not survive the slice they came from.** The
note's table is labelled as a slice (550 masked nodes, three lessons), which is
honest, but the mechanism it supports is quoted in absolutes. Re-derived on all
179 lessons, 3,228 masked nodes with a gold label — *diagnostic on training
episodes, one masking pass at the harness's own 0.15 rate*:

| question | note (550 nodes, 3 lessons) | all 179 lessons (3,228 nodes) |
|---|---|---|
| the graph-nearest visible node carries the answer | **0.000** | **0.022** |
| no visible node carries the answer at all | **0.575** | **0.346** |
| hops to the nearest visible carrier | "always even: 2, 4, 6 or 7" | even on **91.2%**, hop 1 on 1.7% |

The nearest visible node is at hop 1 for 91% of queries, and hop 1 carries the
answer 2.2% of the time while 91% of the answers sit at even hops. **The
mechanism is real, strong, and correctly signed** — a diffusion kernel peaks
where the answer is not. Its *absolutes* are slice artifacts: "never at hop 1"
is 1.7% of the time, and "0.575 have no carrier" is 0.346. This is the tenth
time a small slice has produced a sharper number than the curriculum supports;
the note's own §5 confesses the ninth.

## Claim 4 — the second-best pointer: survives exactly

Every `summary.json` in the repo carrying a `copy_lift`, ranked:

| model | copy lift | floor | ceiling | run |
|---|---:|---:|---:|---|
| `corefer-001` | +0.0959 | 0.2658 | 0.7216 | `runs/full179/corefer-001` |
| **`vsa_perm_hks-004`** | **+0.0921** | 0.2658 | 0.7216 | `runs/vsa_role/vsa_perm_hks-004` |
| `ptrgen-001` | +0.0775 | 0.2658 | 0.7216 | `runs/ptrgen/ptrgen-001` |
| `vsa_perm-002` | +0.0599 | 0.2658 | 0.7216 | `runs/vsa_role/vsa_perm-002` |
| `routes-001` | +0.0509 | 0.2658 | 0.7216 | `runs/full179/routes-001` |

Same floor and same ceiling on every row, so the ordering is a real ordering.
`corefer-001` reproduces at +0.0959 in three independent run directories
(`runs/full179`, `runs/ptrgen`, `runs/full179-site`). Nothing to break here.

## Claim 5 — the three heads: the numbers verify, the comparison was drawn at the wrong bandwidth

All six published numbers verify against the run directories to three decimals:

| | label lift | bits lift | copy lift |
|---|---:|---:|---:|
| `vsa_perm_pure-002` | +0.2267 | 0.2932 | +0.0599 |
| `vsa_perm_hks_pure-004` | +0.1614 | 0.3080 | +0.0921 |

and the differences the note quotes are +0.065 label (printed +0.066), +0.015
bits, +0.032 copy. Two rounding slips of 0.001, nothing more. The note reports
the disagreement evenhandedly, names the metric each time, and refuses to pick a
winner — which is what this repo asks for, and I could not find a place where it
resolves toward the flattering reading.

**But both signature rows in that table fitted the pinned 0.5.** The comparison
is between `vsa_perm_pure-002` and a signature measured at a bandwidth worth
0.053 less than the fitted one, so the table cannot be quoted as it stands.
`vsa_perm_hks_wide-004` was registered to redraw it, with its prediction written
down first — and the redrawn table below leaves §5's conclusion standing.

## What I could not break

- The identity the module rests on — that the candidate score *is* the role Gram.
  Pinned by `test_the_candidate_score_is_the_role_gram` and true by the bipolar
  algebra; every comparison in the family really is one operator swapped.
- Equivariance. Every `_pure` row is within 0.003 of zero renaming drop and the
  two new pure rows are within 0.006, and roles are asserted per node to be a
  function of the tree alone.
- The floors, the ceiling, the denominators. Identical everywhere, in this sweep
  and in every other run directory the note compares against. There is no `rgt`
  here.
- The `-002` rows reproducing: `vsa-002` at 0.2194 / +0.0889 / 6.7956 / 0.1812 /
  +0.0292 is bit-identical to `runs/vsa/vsa-002`, and `vsa_perm_pure-002` at
  0.337 / +0.227 / 0.310 / −0.003 matches `RESEARCH_LOG.md` line 688.
- The shuffle's determinism between fitting and prediction.
- The dimension/quality half of the curve — 0.178/0.215/0.219/0.217/0.218 for
  `vsa-002` and the `vsa_sum-004` and `vsa_hks-004` series all check out of
  `runs/vsa_dim/d*`. **The throughput half was not re-measured and must not be:**
  the machine was under a parallel load during this work, and a sibling agent
  measured `vsa_sum-004` at 1,391 tok/s against its published 18,995 under the
  same contention. Timing is the one column here that needs replicating on a
  quiet box, and it remains the note's least-attacked claim.

## One thing the note does not say and should

Every row in the family — all twenty-seven, including `vsa_null-004` — has
`type_acc = 0.7922` against a **type floor of 0.8601**, a type lift of
**−0.486**. The type head is completely independent of the role construction and
is far below its own floor in every row. The note quotes the type floor in its
header and never returns to it. "The three heads disagree" is really two heads
disagreeing and one head that no model in this family beats.

## What would have refuted this refutation

- The null row landing level with the shuffled rows. It does not: −0.125 against
  −0.070, and **this refuted my own written prediction**, which was that the null
  would land *above* the shuffled rows. It landed below, and the correction runs
  in the finding's favour.
- The wide bandwidth grid staying pinned at 0.5. It moves interior to 0.25.
- The wide diffusion grid rescuing the eigenmap. It does not — bit-identical row.
- The matched eigenmap control landing below the drifted one. It lands above
  (−0.070 against −0.089), refuting my second prediction.
- The floors differing between `runs/vsa_role` and the rows it is compared with.
  They do not.

**Four of my five written predictions were wrong**, every one of them in the
direction that helps the note: the null landed below the shuffled rows instead of
above, the matched eigenmap control landed above the drifted one instead of
below, and the corrected composition failed to overtake `vsa_perm_pure-002` on
label. Only the wide-grid prediction (that the signature's bandwidth fit was a
boundary artifact) came in as written, and it is the one that moved a number.
The predictions are in the model docstrings and in git, committed before the
sweeps ran.

## The composition, redrawn at the fitted bandwidth — and §5 survives it

`vsa_perm_hks_wide-004` and `vsa_perm_hks_wide_pure-004` fit **0.25**, interior,
like the plain signature. Redrawing §5's table:

| | label lift | bits lift | copy lift |
|---|---:|---:|---:|
| `vsa_perm_pure-002` | **+0.2267** | 0.2932 | +0.0599 |
| `vsa_perm_hks_pure-004` (published, knob 0.5) | +0.1614 | 0.3080 | +0.0921 |
| `vsa_perm_hks_wide_pure-004` (knob **0.25**) | +0.1873 | **0.3155** | **+0.0926** |

**The disagreement narrows and does not collapse.** The label gap falls from
0.065 to **0.039**, and `vsa_perm_pure-002` still leads on label while the
signature composition still leads on bits and on copy. My written prediction —
that the corrected bandwidth would put the composition at or above +0.227 and
leave one model ahead on all three heads — is **refuted**. §5's conclusion, that
*"there is no single ranking of these two models; which one is better is a
property of the metric"*, survives the correction that invalidated the numbers it
was drawn from. That is the strongest thing in the original note and it is now
independently confirmed at the right operating point.

Two smaller things fall out:

- **The gain does not fully transfer through the permutation channel.** The
  signature alone gains +0.053 of label lift from the wider grid (+0.107 →
  +0.160); composed with permutation it gains **+0.026** (+0.161 → +0.187). The
  two mechanisms are partial substitutes, which is exactly the reading
  `VSAPermHKS`'s own docstring wrote down in advance.
- **Claim 4's margin narrows.** `vsa_perm_hks_wide-004`'s copy lift is
  **+0.0926**, still second in the repo and now **0.0033** behind
  `corefer-001`'s +0.0959 rather than 0.0038.

## The control, re-matched at the corrected bandwidth

`vsa_hks_shuf_wide_pure-004` is the shuffled signature **pinned** to 0.25 — the
treatment's fitted value — so the bit-identical-multiset property holds by
construction and cannot drift the way the eigenmap pair's did. It scores
**0.0791 / −0.0748**, essentially where it scored at 0.5 (−0.0706). It did not
rise with its treatment.

So at the bandwidth the data actually wants, with a properly matched control and
a real bottom row:

| | label lift | share of the embedding |
|---|---:|---:|
| `vsa_null_pure-004` (no roles at all) | −0.1254 | — |
| `vsa_hks_shuf_wide_pure-004` (graded, correspondence destroyed) | −0.0748 | **+0.051 = 17.7%** |
| `vsa_hks_wide_pure-004` (the signature) | **+0.1598** | **+0.235 = 82.3%** |

**Claim 1's conclusion is confirmed in its strongest form**: four fifths of what
a graph-derived role embedding is worth is the correspondence between a
coordinate and the node it describes. The remaining fifth is gradedness, which is
not the "nothing" the note claimed but is not much either.

## The full family, `_pure` rows, at the end of this attack

| model | role Gram | lbl acc | lbl lift | bits lift | copy lift | rename |
|---|---|---:|---:|---:|---:|---:|
| `vsa_null_pure-004` | i.i.d. — **new bottom** | 0.036 | −0.125 | 0.201 | −0.320 | +0.003 |
| `vsa_hks_shuf_wide_pure-004` | signature shuffled, pinned 0.25 | 0.079 | −0.075 | 0.166 | −0.264 | +0.000 |
| `vsa_hks_shuf_pure-004` | signature shuffled | 0.083 | −0.071 | 0.159 | −0.260 | −0.002 |
| `vsa_spec_shuf16_pure-004` | eigenmap shuffled, **matched** | 0.083 | −0.070 | 0.192 | −0.259 | −0.003 |
| `vsa_spec_shuf_pure-004` | eigenmap shuffled (drifted) | 0.067 | −0.089 | 0.203 | −0.279 | −0.002 |
| `vsa_spec_pure-004` = `vsa_spec_wide_pure-004` | eigenmap | 0.105 | −0.044 | 0.212 | −0.232 | −0.001 |
| `vsa_pure-002` | product of atoms | 0.200 | +0.066 | 0.259 | −0.115 | +0.002 |
| `vsa_sum_pure-004` | sum of atoms | 0.214 | +0.083 | 0.282 | −0.097 | −0.000 |
| `vsa_hks_pure-004` | signature, pinned 0.5 | 0.235 | +0.107 | 0.276 | −0.072 | +0.003 |
| `vsa_hks_wide_pure-004` | **signature, fitted 0.25** | 0.280 | **+0.160** | 0.292 | −0.014 | +0.006 |
| `vsa_perm_hks_pure-004` | signature + perm, pinned 0.5 | 0.281 | +0.161 | 0.308 | +0.092 | −0.002 |
| `vsa_perm_hks_wide_pure-004` | **signature + perm, fitted 0.25** | 0.304 | **+0.187** | **0.316** | **+0.093** | −0.002 |
| `vsa_perm_pure-002` | partition + permutation | 0.337 | **+0.227** | 0.293 | +0.060 | −0.003 |

## One more arithmetic slip, in the dimension section

"`vsa-002` moves 0.215 → 0.218 from 1k to 64k; `vsa_sum-004` 0.227 → 0.226;
`vsa_hks-004` 0.244 → 0.241 — **all three decline slightly**." From
`runs/vsa_dim/d1024` and `runs/vsa_dim/d65536`: `vsa-002` moves **0.2146 →
0.2180**, which is a rise of +0.003, not a decline. Two of the three fall, by
0.000 and 0.004. The right sentence is that all three move by ≤0.004 in either
direction, which is the saturation the section claims; "all three decline" is not
what the numbers say and reads as a curve that was expected to bend before it was
plotted, which is the failure mode `CLAUDE.md` names by name.

## What should happen to the note

`status: provisional` → I would promote it, with these edits:

1. **Requote every `vsa_hks*` number from the `_wide` rows.** +0.107 becomes
   +0.160; the gap over the hand-built partition doubles; §4's "worth less than
   half of what a positional channel is worth" has to go.
2. **Replace "gradedness contributes nothing on its own"** with the measured
   17.7% / 82.3% split against `vsa_null_pure-004`.
3. **Drop "asserted in the tests"** from the multiset claim, and say which pair
   is matched and which is not.
4. **Correct §3's mechanism table** to the 179-lesson numbers, and delete the
   "mis-specified grid" reading of `t = 16` — it is an interior optimum.
5. **Name the column** in §2's `*` → `+` sentence.
6. **Fix "all three decline"** in the dimension section.
7. Keep §5 exactly as it is. It was right, and it stayed right after the ground
   moved under it.

`notes/lessons/2026-08-14-a-boundary-optimum-is-not-a-fitted-value` also needs
its second case study amended: `vsa_spec_pure-004`'s `t = 16` was not a
mis-specified grid, and the lesson's own guard — *extend and refit* — had not
been applied to it. The lesson is unharmed; its example was.

## What would refute *this* note

- `vsa_hks_wide_pure-004` failing to reproduce +0.160 on a re-run. It is one
  sweep row; the `-002` rows in the same sweep reproduce bit-identically, which
  is the reason to believe the harness was stable, but nobody has run it twice.
- The 0.25 fit itself sitting on a boundary. It does not: the grid is
  `(0.0625, 0.125, 0.25, 0.5, 1, 2, 4)` and 0.25 is interior with two points
  below it. This is the guard I accused the note of skipping, so it is stated.
- The 17.7% / 82.3% split moving if the null row is built differently. It is one
  construction of "no roles"; an all-ones role matrix (an episode unigram) is the
  other degenerate end and was not run.
- The throughput column. Not re-measured, and not re-measurable under the load
  this ran on.

