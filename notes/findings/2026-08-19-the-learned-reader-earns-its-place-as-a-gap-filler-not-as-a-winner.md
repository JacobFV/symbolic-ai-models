---
title: The learned reader earns its place as a gap-filler, not as a winner — and composition multiplies reader error
date: 2026-08-19
status: measured
arm: reader-union
---

The learned reader loses to four hand-written patterns on every relation. That is
settled and not in dispute. This asks the useful question instead: the two
readers fail on **different articles**, so does a system with both answer more?

168 Wikipedia intros, the same corpus and the same composed query as
`scripts/multi_relation_world.py`:

    parent(c, p) JOIN country(c, X)  ->  which groups control companies in X?

stated in no sentence of any article. The learned reader is 4-fold
cross-validated so no article is read by a model fitted on it.
`runs/reader_union_join.json`.

## 1. The correct sets are not nested

Articles each reader gets right, by relation:

| relation | hand | learned | **learned-only** | hand-only | both |
|---|---|---|---|---|---|
| `parent` | 55 | 25 | **5** (20% of its correct) | 35 | 20 |
| `country` | 136 | 30 | **7** (23%) | 113 | 23 |
| `headquarters` | 39 | 37 | **15** (41%) | 17 | 22 |

On `headquarters` the two readers are nearly disjoint in strength: 15 articles the
classifier gets and the patterns do not, against 17 the other way, and only 22
shared. **A fifth to two fifths of the learned reader's correct answers are on
articles the patterns miss**, which is what a different inductive bias looks like
rather than a worse copy of the same one.

## 2. Filling gaps helps; overriding does not

| arm | `parent` | `country` | `hq` | JOIN precision | recall | F1 |
|---|---|---|---|---|---|---|
| hand (published) | 0.327 | 0.819 | 0.241 | 0.207 | 0.119 | 0.138 |
| learned alone | 0.149 | 0.181 | 0.228 | 0.046 | 0.004 | **0.007** |
| **union** (hand, else learned) | **0.345** | **0.855** | **0.327** | 0.197 | 0.124 | **0.142** |
| union+ (learned may override) | 0.315 | 0.729 | 0.321 | 0.154 | 0.103 | 0.112 |

**Union improves every relation** — `headquarters` most, 0.241 → 0.327, **+36%
relative**. Letting the learned reader *override* the patterns where they
disagree makes everything worse, so its confidence is not calibrated well enough
to arbitrate; it is only good enough to speak when nothing else does.

The composed query barely moves (0.138 → 0.142) for a structural reason worth
stating: it joins `parent` with `country`, and `country` is the relation where the
hand reader is already at 0.819. There is little gap left to fill on the query as
published.

**Not run, and the reason:** a query joining `parent` with `headquarters` would
show a much larger union gain, because `headquarters` is where the union gains.
Choosing the query after seeing which relation improved would be selecting the
result, and the outcome is predictable — union recall up roughly in proportion to
the +36% on `hq`. The prediction is recorded here instead of being run.

## 3. Composition multiplies reader error, on real text

The learned reader alone scores **0.007 F1** on the composed query while scoring
0.149 and 0.181 on its two constituent relations. A join needs *both* relations
right on the *same* article, so per-article joint accuracy is roughly the product,
and a query over two relations converts a middling reader into a useless one.

That is the `r^k` picture the generated domains produced, appearing on real text
without being looked for: the hand reader at 0.327 × 0.819 keeps enough joint
mass to score 0.138, and the learned reader at 0.149 × 0.181 does not. **The
number that matters for composed queries is the product, and it punishes a
balanced-but-mediocre reader far more than an uneven one.**

## What would have refuted this

The learned reader's correct set being contained in the hand reader's — it would
have meant the classifier had found the same few high-frequency frames and added
only noise. It is not contained in any relation, and least of all in the one
where the union gains most.
