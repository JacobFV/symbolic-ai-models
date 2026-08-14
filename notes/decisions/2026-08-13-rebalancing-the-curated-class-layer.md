---
date: 2026-08-13
author: agent-synthex-balance
status: measured
related: [2026-08-13-seeding-balance-not-provenance]
---

# Which rebalancing, and what would refute the balance hypothesis

**Written before the sweep ran.** Everything below the line was fixed before any
of the four cells had a score; the only numbers in it are properties of the class
*partition*, which is what "matched balance" has to be measured as.

## The confound

`synthex_class-002` (curated node types) loses to `synthex_random-002`
(`sha256 % k`) at matched cardinality. The two rows differ in **two** things at
once, so the gap is unattributable:

- **provenance** — the curriculum's own ground-truth ontology vs. no meaning;
- **balance** — on the full 179-lesson curriculum, 5,258 labelled symbols fall
  into **7** curated classes of which `ident` holds **75.6%**, giving 1.35 bits,
  against the control's 2.81.

## The design: fill in the other two cells of the 2x2

|                    | skewed (H = 1.35 bits)  | balanced (H = 2.81 bits) |
|--------------------|-------------------------|--------------------------|
| curated provenance | `synthex_class-002`     | `synthex_balanced-003`   |
| no provenance      | `synthex_skewrand-003`  | `synthex_random-002`     |

- **balance effect** = (balanced + random) - (class + skewrand)
- **provenance effect** = (class + balanced) - (skewrand + random)

All five models differ from `SynthexClassModel` in `_assign_classes` and in
nothing else, so a gap between rows is the partition and can be nothing else.

## The rebalancing chosen, and why, *before* seeing any score

**Equal-frequency binning that respects curated boundaries.** Of the three
defensible options, only this one can reach the target:

- **merge-to-target-entropy is arithmetically unable.** Merging never splits the
  giant class, so entropy is capped at `H(0.756, 0.244) = 0.80` bits against a
  target of `log2(7) = 2.81`.
- **recursive split on a structural feature is disqualified.** Depth, frequency
  or parent type is information the ontology does not contain; using it would
  make a win unattributable all over again, which is the failure this experiment
  exists to fix.
- **equal-frequency binning splits only inside a curated class and merges only
  whole curated classes**, so every bin is a subset of one class or a union of
  several. That is the most curated information any partition of this cardinality
  and this entropy can carry.

Concretely, with `k` = the number of distinct curated classes: apportion `k` slots
by symbol count (Hamilton, ties by class id); split a class holding `s >= 1` slots
into `s` sub-buckets by `sha256(salt|symbol) % s`; drop a class holding no slot,
**whole and uncut**, into whichever bin is smallest, largest leftover first.

**The caveat, stated in advance because it limits the conclusion either way.** A
partition where 75.6% of symbols share one class *cannot be balanced from inside
the ontology*. The sub-bucket index is arbitrary by necessity, so
`synthex_balanced-003` is curated-where-it-can-be and hash-where-it-must-be. How
much provenance survived is reported as `I(assignment; curated type)` rather than
asserted.

`synthex_skewrand-003` completes the square from the other side: symbols ordered
by digest and handed out in blocks whose sizes are exactly the curated class
sizes. Identical size profile, identical entropy, no semantics.

## Matched balance, as a number

Measured on the full curriculum's training split (179 lessons, 20 episodes each,
`vocab_size = 8192`), 5,258 labelled symbols, `k = 7`:

| arm | classes | H(class) | top class | I(class; curated) |
|---|---:|---:|---:|---:|
| `synthex_class-002` curated, skewed | 7 | **1.3468** | 0.756 | **1.3468** |
| `synthex_balanced-003` rebalanced curated | 7 | **2.8044** | 0.156 | **0.8517** |
| `synthex_skewrand-003` skew-matched random | 7 | **1.3468** | 0.756 | 0.0024 |
| `synthex_random-002` uniform hash | 7 | **2.8067** | 0.147 | 0.0035 |

`log2(7) = 2.8074`. Balance is matched to **0.002 bits** across the balanced pair
and **exactly** across the skewed pair. Provenance is 0.85 bits in the rebalanced
arm — 63% of `H(curated)` — against ~0.003 in both random arms. The square is
clean: each axis moves one thing.

## Hypothesis, and what refutes it

**H1 (the balance reading).** The `-002` gap is balance, not semantics.
Predictions, on `label_lift` over the full 179-lesson sweep:

- balance effect **> +0.05**;
- provenance effect **within the salt-to-salt spread** — `|balanced-003 -
  random-002| <= 0.02` and `|class-002 - skewrand-003| <= 0.02`.

**Refuted by** `balanced-003 - random-002 > +0.02` and beyond the salt spread:
the semantics were real and were masked by skew, and the leapfrog's high-level
seed is salvaged.

**Also refuted, the other way**, by a balance effect near zero: then the `-002`
gap was neither of these two things and the mechanism written into
`tests/test_synthex.py` is wrong.

**Noise band.** The three hash-driven arms are re-drawn at salts `""`, `"s1"`,
`"s2"`. A difference smaller than the spread across draws is not a difference.
`synthex_class-002` is deterministic and has one point.

**Metrics, fixed in advance.** `label_lift` is the headline. `label_bits_lift` is
reported beside it, never instead of it, because this repo has documented that
the two rank models close to inversely. Renaming drop and the four
`structural_fallback = False` rows are reported for every cell — the fallback is
a *shared* memoriser identical across all four, so it can compress the
differences but cannot create one.
