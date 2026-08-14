---
date: 2026-08-13
author: agent-synthex-balance
status: provisional
related: [2026-08-13-seeding-balance-not-provenance,
          2026-08-13-rebalancing-the-curated-class-layer]
---

# Rebalancing the curated ontology does not rescue it, and the 2x2 does not factor

**Full 179-lesson sweep**, `configs/full179.toml`, `runs/synthex_balance`,
`runs/synthex_balance_s1`, `runs/synthex_balance_s2` — 24 runs, one config, one
tokenizer, one set of floors (`label_floor` 0.1432 on every row, `label_coverage`
0.8249 on every row). No slice appears anywhere below. The rebalancing, the
hypothesis and the refutation condition were fixed in
`notes/decisions/2026-08-13-rebalancing-the-curated-class-layer.md` **before the
first score existed**; the one arm added afterwards is marked post-hoc where it
appears.

## The question

`synthex_class-002` (the curriculum's ground-truth node types) loses to
`synthex_random-002` (`sha256 % k`) at matched cardinality. It differs from it in
**two** things: provenance and balance. Hold provenance and vary balance, and see
which one the gap was.

## What was run

`k = 7` curated classes over 5,220 labelled symbols; `ident` holds 75.6% of them.
All arms differ from `SynthexClassModel` in `_assign_classes` and nothing else —
pinned by a test — so a gap between rows is the partition and can be nothing
else. Entropies are read back off each run's fitted `symbol_class`, not
re-derived.

| arm | provenance | H(type) | H(occurrence) | top | I(class; curated) |
|---|---|---:|---:|---:|---:|
| `synthex_class-002` | curated, skewed | 1.3517 | 1.9254 | 0.755 | **1.3517** |
| `synthex_skewrand-003` | none, curated skew | 1.3517 | 1.1446 | 0.755 | 0.0042 |
| `synthex_balanced-003` | curated, type-balanced | **2.8035** | 2.4823 | 0.156 | **0.8533** |
| `synthex_occbal-003` *(post-hoc)* | curated, occurrence-balanced | 2.4467 | **2.7909** | 0.267 | **1.1454** |
| `synthex_random-002` | none, uniform | **2.8066** | **2.8014** | 0.149 | 0.0054 |

`log2(7) = 2.8074`. Balance is matched to **0.003 bits** on the type measure
(`balanced` vs `random`) and to **0.011 bits** on the occurrence measure
(`occbal` vs `random`), and exactly on the skewed row. Provenance is 0.85–1.35
bits in the curated column against 0.004–0.005 in the random one. Every statistic
is stable to the third decimal across the three sha256 draws.

## The scores

Means over three sha256 draws (`""`, `"s1"`, `"s2"`); `+-` is the **full spread
across draws**, not a standard error. `synthex_class-002` is deterministic and has
one point. `synthex_random-003` at the default salt reproduces
`synthex_random-002`'s partition exactly and its rows are pooled.

| arm | n | lbl acc | **lbl lift** | +- | **lbl bits** | +- | renamed acc |
|---|--:|--:|--:|--:|--:|--:|--:|
| `synthex_class-002` | 1 | 0.079 | **-0.0750** | – | **+0.0317** | – | 0.0006 |
| `synthex_skewrand-003` | 3 | 0.086 | **-0.0672** | 0.0141 | **+0.0326** | 0.0207 | 0.0005 |
| `synthex_balanced-003` | 3 | 0.082 | **-0.0717** | 0.0056 | **+0.0278** | 0.0025 | 0.0009 |
| `synthex_occbal-003` | 2 | 0.096 | **-0.0550** | 0.0058 | **+0.0502** | 0.0014 | 0.0006 |
| `synthex_random-002/003` | 3 | 0.103 | **-0.0471** | 0.0078 | **+0.0731** | 0.0125 | 0.0006 |

and with the shared `structural_fallback` off:

| arm | n | lbl acc | **lbl lift** | +- | **lbl bits** | +- |
|---|--:|--:|--:|--:|--:|--:|
| `synthex_class_pure-003` | 1 | 0.049 | **-0.1101** | – | **+0.0168** | – |
| `synthex_skewrand_pure-003` | 3 | 0.052 | **-0.1066** | 0.0288 | **+0.0120** | 0.0382 |
| `synthex_balanced_pure-003` | 3 | 0.049 | **-0.1104** | 0.0158 | **+0.0130** | 0.0024 |
| `synthex_occbal_pure-003` | 2 | 0.074 | **-0.0805** | 0.0105 | **+0.0358** | 0.0018 |
| `synthex_random_pure-003` | 3 | 0.087 | **-0.0660** | 0.0205 | **+0.0582** | 0.0137 |

Type lift is **-1.3387 on all twenty-four rows**, to seven digits. That is the
experiment's own consistency check rather than a result: `_type_vote` keys on
`("d", depth, slot)` and never touches a class, so the type head is identical by
construction and any drift there would have meant something else was moving.

## The contrasts, and the pre-registered verdict

The refutation condition was `balanced-003 - random > +0.02` on `label_lift`.

| contrast | lift | bits | lift, pure | bits, pure |
|---|--:|--:|--:|--:|
| **provenance at matched balance** `balanced - random` | **-0.0246** | -0.0453 | **-0.0445** | -0.0453 |
| **provenance at matched balance** `occbal - random` *(post-hoc)* | **-0.0079** | -0.0229 | **-0.0145** | -0.0224 |
| **provenance at the curated balance** `class - skewrand` | **-0.0078** | -0.0009 | **-0.0035** | +0.0048 |
| **balance, no provenance** `random - skewrand` | **+0.0201** | +0.0404 | **+0.0406** | +0.0462 |
| **balance, with provenance** `balanced - class` | **+0.0033** | -0.0039 | **-0.0004** | -0.0039 |
| **balance, with provenance** `occbal - class` *(post-hoc)* | **+0.0201** | +0.0185 | **+0.0296** | +0.0190 |

**The refutation condition is not met on any arm, either metric, or either
fallback setting — and the sign is the opposite of the one that would have
rescued the seed.** Rebalancing the curated ontology to the control's entropy
leaves it 0.025 (0.045 without the fallback) of label lift *below* the meaningless
partition it was supposed to catch.

Two readings of the size, and the bracket is what separates them:

- **at matched type entropy** the curated arm is 0.025–0.045 below the control —
  three to five times the largest within-arm salt spread (0.0078–0.0205), so it
  is a real deficit rather than a draw;
- **at matched occurrence entropy** it is 0.008–0.015 below — **inside or at the
  edge of the spread**, i.e. a null.

So provenance is somewhere between *nothing* and *actively harmful*, and never
positive. The honest statement is the weaker one: **at matched balance, curated
semantics buy nothing.**

The third row is the cleanest single number in the table and it was not the one
being tested: `class - skewrand` is **-0.008 / -0.004** on lift and **-0.001 /
+0.005** on bits. Strip the semantics out of the ontology and keep only its
*shape* and the score does not move. The curated layer's whole contribution, at
its own balance, is its histogram.

## What did move: balance, but only where there is nothing to be redundant with

`random - skewrand` is **+0.020 / +0.041** — the same partition family, the same
zero provenance, 1.46 bits of entropy apart. Balance is worth about 0.014–0.028
lift per bit when the partition means nothing.

Hold provenance and the same 1.46 bits buys **+0.003** (`balanced - class`). The
2x2 does not factor: the interaction (+0.024 to +0.076 depending on cell and
metric) is as large as either main effect, and only one of the four cells —
meaningless **and** balanced — is any good. The other three sit within 0.008 of
each other.

**The mechanism this is consistent with, offered as a hypothesis and not as a
result.** The context key is `(parent_class, sibling_class, slot, depth)`. `slot`
and `depth` already largely determine a node's *type*, so a class layer that
encodes type is redundant with the key it is being added to, however much entropy
it is given. A hash partition is redundant with nothing: it is a three-bit
fingerprint of *which symbol* the neighbour is, which is a dimension the key does
not otherwise have. Rebalancing recovers entropy but not independence — the bins
stay organised by type. That predicts the ordering seen here, and it predicts
that the useful seed is one uncorrelated with the structural features already in
the key, which is the opposite of what a curated ontology is for. **Untested.**

## Three things that bound every number above

1. **Every arm is below its label floor.** The floor is 0.1432 and the best
   accuracy is 0.103. On the full curriculum this model family does not clear the
   prior at all, so the comparison is between degrees of failure. The twelve-lesson
   slice that motivated this work reported *positive* lifts (0.121 vs 0.175); the
   ordering survived the move to 179 lessons and the sign did not. That is the
   eighth time a slice in this repo has been contradicted at full scale, and the
   first where it kept the direction.
2. **The whole score is vocabulary.** Under renaming every arm falls from
   0.049–0.103 to **0.0004–0.0009**. Not one of them retains anything. So
   "which partition is better" is, in this family, entirely a question about which
   partition conditions a *memorising* lookup table better — it is not a question
   about reasoning, and no arm here has a structural component to lose.
3. **`label_acc` and `label_bits_lift` agree**, which in this repo is the unusual
   case and worth recording: they order the five arms identically and put
   `synthex_random-002` first on both. The usual warning that a ranking is a
   property of the metric does not bite here.

## What would refute this

- A curated seed that is **not** redundant with `slot`/`depth` — a lexical or
  distributional class layer rather than a syntactic-type one — beating the hash
  control at matched entropy. This result says nothing about that; it says the
  *curriculum's node type* specifically is the wrong thing to seed with.
- The same 2x2 on a model whose score survives renaming. Everything here is
  measured on a memoriser, and a partition that helps memorisation and a
  partition that helps binding need not be the same partition.
- A larger `k`. Cardinality was pinned at 7 because that is what the ontology has;
  the finding that balance is worth ~0.014–0.028 lift per bit suggests the
  cardinality knob may matter more than either axis tested here.

## What this does and does not retire

`APPROACH.md`: *what retires a method is a measured null with its control,
reproduced on the full curriculum.* This is that, for **one seed**: the
curriculum's own node types, used as a backoff class layer, at 179 lessons and 20
episodes each. It is now a fourth null, and the first with the *mechanism*
separated — the previous reading, that the ontology lost because it was skewed,
is **wrong**: unskewing it does not help.

It does **not** retire seeding. Nothing here tests a pretrained lexical seed, a
learned clustering at the measured effective rank, or a seed on a model that is
not a memoriser. It also does not license "any balanced partition is free": the
balanced partition that worked was balanced *and* independent of the structure
already in the key, and this experiment cannot say which of those two it needed.
