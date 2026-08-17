---
date: 2026-08-17
author: lead
status: provisional
related: [2026-08-17-the-non-copyable-gain-is-entirely-vocabulary-measured-at-last,
          2026-08-17-the-conjunct-does-not-transfer-the-pointer-was-the-thing,
          2026-08-16-the-derivability-channel-is-taken-and-the-price-is-the-vocabulary,
          2026-08-17-a-rule-is-verified-on-the-population-its-guard-admits]
---

# Frontier's ten paths can reach the answer on 41% of copyable fills, and `corefer` scores 49%

The previous finding showed the equivariance difference between `frontier`
variants lives entirely in the copyable bucket — it is about how much of the
model's **pointing** survives — and left `frontier-typepoint` at 0.306 renamed
against `corefer-001`'s 0.492. Before building anything to close that, the
question is whether frontier's copy resolver *can* close it.

## The ceiling

On renamed evaluation episodes, 3,817 copyable fills:

| | |
|---|---:|
| answer reachable by **any** of the ten fixed paths | **0.4124** |
| answer on any visible node (the copy ceiling, by definition of the bucket) | 1.0000 |
| `frontier-typepoint` achieves | 0.3060 |
| **`corefer-001` achieves** | **0.4920** |

**`corefer` scores above frontier's ceiling.** Its pointer reaches answers that
frontier's path vocabulary cannot express at all, so the 0.186 gap is not a
search failure. Improving rule selection over the same paths can buy at most
**0.106**; the remaining 0.080 requires paths frontier does not have.

And frontier is already at **74%** of its own ceiling (0.3060 of 0.4124), which
is the part of this that is *not* a criticism of the search.

## Which paths carry it

Share of copyable fills each path reaches, when any does:

| path | share |
|---|---:|
| `prev` — nearest earlier visible node | **0.288** |
| `sib@1` | 0.236 |
| `sib@2` | 0.222 |
| `sib@0` | 0.218 |
| `sib@3` | 0.209 |
| `parent` | 0.009 |

`gparent` and the three `psib@k` do not appear at all in the top six. So of ten
paths, **four sibling slots and `prev` do essentially all the work**, they
overlap heavily (the shares sum to far more than 0.4124), and four are nearly
dead weight. A fixed path set is both redundant and insufficient at once.

## The third time the same answer has come back

- **Label head:** the derivability null was expressive, not procedural — no model
  could *state* `label(X) = m(label(Y))`.
- **Type head:** four variants of knobs, atoms, gate and conjunct moved it 0.0053
  in accuracy; what it lacks is a *pointer*, and the conjunct does not transfer
  from a bad one.
- **Copy head, here:** the search reaches 74% of what its paths allow, and the
  paths allow 41% of what a pointer would.

Three heads, three rounds of tuning, and the same diagnosis each time: **the
hypothesis language is the constraint, and in two of the three cases the missing
piece is specifically the ability to point at an arbitrary node.** `corefer` is
that ability and nothing else, and it is why it leads the type column, the
renamed column, and now this ceiling.

## What this licenses, and what it does not

It licenses building a pointer resolver into `frontier` — a rule form that ranks
*all* visible nodes rather than reading a fixed offset — because that is the only
change that can pass 0.4124. It is the thing I said two rounds ago would be
"building `corefer` inside it", and the ceiling says that is not a reason not to:
the two models would then differ in what selects among candidates, which is a
real comparison, rather than in whether candidates exist at all.

It does **not** say frontier would then reach 0.492. `corefer`'s pointer is a
fitted naive-Bayes over pairwise relational features with a reranking stage, and
[[2026-08-17-the-conjunct-does-not-transfer-the-pointer-was-the-thing]] already
measured what a *bad* pointer is worth: +0.002 where a good one gives +0.095.
A pointer resolver whose ranking is poor would lift the ceiling and not the
score.
