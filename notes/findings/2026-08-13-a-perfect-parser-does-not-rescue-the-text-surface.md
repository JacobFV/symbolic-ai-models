---
date: 2026-08-13
author: agent-ae944e68
status: provisional
related: [a-parser-is-a-parameter-and-the-oracle-is-prefix-restricted,
          held-out-calibration-slices-are-whole-lessons, compositional-parser]
---

# A perfect parser does not rescue the text surface, and its renaming-invariant half does not beat a real one

Full 179-lesson sweep, `configs/full179.toml`, `runs/full179-gparse`. Not a
slice. One reasoner (`gparse`) registered five times against five readers of the
text, differing in nothing but the reader, plus one declared ablation of the
reasoner itself; `ngram-001` in the same sweep under the same floors, as the
existing text model to beat.

**`gparse-oracle` is a CEILING and not a system.** It is handed the episode's
true term graph, restricted to the symbols the reader has already read. There is
no oracle on real text and the row is not a claim about anything deployable.

## The hypothesis, and it was half wrong

Written before the numbers (`notes/decisions/2026-08-13-a-parser-is-a-parameter…`):
*with a perfect parse of the prompt a structure-conditioned reasoner can emit the
answer token; without one it cannot.* Refutation condition: the oracle row
scoring at or near its own floor.

The second half held emphatically. The first half did not: the oracle clears the
floor by a lot **and still gets 61% of answers wrong**, which is not what "can
emit the answer token" was meant to mean.

## The numbers

`answer_*` only. `token_*` is the boilerplate — about 98.6% of scored positions —
and every `gparse` row abstains there by construction, so its `token_lift` sits
at −0.001 to −0.007 and says nothing. Floor: a unigram over the *training
answers*, `answer_acc` 0.0579, `answer_bits` 7.9516, over 1,346 scored answer
positions.

| row | reader | discrete params | `answer_acc` | `answer_lift` | `answer_bits` | `answer_bits_lift` |
|---|---|---:|---:|---:|---:|---:|
| `gparse-oracle` | oracle — **CEILING** | 4,740 | 0.3871 | **+0.3494** | 7.169 | **+0.0984** |
| `gparse-retrieve` | `retrieve-001` | 1,838,708 | 0.3224 | +0.2808 | 7.804 | +0.0186 |
| `gparse-003` | `template-002` | 112,277 | 0.3053 | +0.2626 | 7.985 | −0.0042 |
| `gparse-nolex` | oracle, **symbol-free** — CEILING | 148 | 0.2994 | +0.2563 | 8.081 | −0.0163 |
| `ngram-001` | (no parser; counts) | 358,019 | 0.1426 | +0.0899 | **6.137** | **+0.2282** |
| `ctw-001` | (no parser; Bayesian mixture) | 819,616 | 0.0468 | −0.0118 | 8.646 | −0.0873 |
| `gparse-flat` | prefix words, no structure | 55 | 0.0297 | −0.0300 | 10.368 | −0.3039 |
| `gparse-none` | nothing | 1 | 0.0000 | −0.0615 | 10.608 | −0.3341 |

At n = 1,346 the standard error of a difference of proportions near 0.35 is about
0.018, so: oracle − `template-002` = 0.082 (≈4.5 SE, real), oracle −
`retrieve-001` = 0.065 (≈3.6 SE, real), oracle − `nolex` = 0.088 (≈4.9 SE,
real), **`retrieve-001` − `template-002` = 0.017 and `template-002` − `nolex` =
0.006 (≈1 SE and ≈0.3 SE — not distinguishable)**.

## Five readings, and three of them are uncomfortable

**1. Structure is the difference between working and not working.** The same
reasoner on the prefix's *words* scores 0.030 and on any structured parse
0.31–0.39 — a factor of ten, and the flat row is *below* its floor. This is not
a claim that parsing is easy; it is a claim that a bag of tokens is unusable to
a reasoner that this parse makes useful.

**2. A perfect parse leaves most of the task undone.** The ceiling is 0.387. At
most 84.5% of eval answers are namable by pointing at a graph node at all, so
even where the right node exists the reasoner picks it **under half the time**.
The bottleneck this measurement finds is *node selection*, not parsing — which
is the opposite of what motivated building the oracle, and is the answer to the
question the task set: **parsing is not where the remaining accuracy is.**

**3. The parser column is worth about a fifth of what is already there.** Of the
+0.349 lift the ceiling reaches, deployable parsers already deliver +0.26 to
+0.28. Perfect parsing buys +0.082 more accuracy. That is real and it is not
where a large gain lives.

**4. The best "parser" here does not parse.** `retrieve-001` hands back the
nearest *training* episode's graph verbatim — memorisation with no reading in it
at all — and is indistinguishable from `template-002` on accuracy while ahead of
it on bits. Its own docstring predicted this is what it was registered to catch,
and it caught it: whatever the parser column is buying over the flat control on
this measurement is **recognition of the lesson template**, not reading of the
episode. The leak audit says the same thing from the other side — 47% of the
nodes `retrieve-001` emits, and 37% of `template-002`'s, name symbols that do
not occur in the document at all.

**5. A quarter of the ceiling is vocabulary, and the structural part of it does
not beat a real parser.** Two of the ten node features read a *symbol* — the
parent's and grandparent's labels. `gparse-nolex` is the identical row with them
removed, which makes the scorer exactly invariant under renaming every symbol in
the episode (checked directly on the feature set, not asserted). It scores
0.299, a drop of 0.088 from the ceiling — about the same size as the entire
oracle-versus-real-parser gap.

So the renaming-invariant ceiling is 0.299, and that is **indistinguishable from
`template-002`'s 0.305 and below `retrieve-001`'s 0.322**. Stated bluntly: the
part of a perfect parse's advantage that is genuinely about structure is worth
no more than what a real parser already delivers by reading words. Anyone
tempted to read the oracle row as "structure is the answer" has to explain that.

The other side of the same number is the parameter column. **148 discrete
features, none of which can name a symbol, get within 0.006 of a
112,277-parameter parser-plus-model and within 0.023 of a 1,838,708-parameter
memoriser.** Whatever this task rewards, almost none of it needs vocabulary and
almost none of it needs size.

## The two metrics disagree, and the disagreement is the finding

By `answer_acc` the ordering is oracle > retrieve > template ≫ ngram ≫ flat.
By `answer_bits` **`ngram-001` is the best row in the table** — 6.137 against the
ceiling's 7.169 — and `template-002` is at the floor (−0.004) while its accuracy
lift is +0.263.

Neither column is wrong. `gparse` decides: it puts spiky mass on a handful of
candidate spellings and abstains everywhere else, which is excellent for argmax
and poor for density. `ngram` estimates: it has a distribution everywhere and a
sharp opinion nowhere. Quoting only accuracy would say a perfect parse beats
counting by 2.7×; quoting only bits would say counting beats a perfect parse.
Anyone citing this table has to say which one they mean.

`token_*` settles what `gparse` is not: `ngram-001` scores `token_acc` 0.580 and
3.21 bits against `gparse`'s 0.05 and 8.47. **`gparse` is not a language model.**
It is an answer predictor sharing the LM head, and it does not touch the failure
that 11 of 19 models cannot emit a token of prose.

And `ctw-001` is the same trap from the other end, which is why it is in the
table. It is the strongest density estimator in the counting family, it holds
`token_lift` **+0.280** — and its `answer_lift` is **−0.012** and its
`answer_bits_lift` **−0.087**. It is *below the floor on the only 1.4% of
positions that carry the reasoning*, in both metrics, while looking respectable
in the undifferentiated one. That is the pathology `README.md` already warned
about, reproduced here on a model nobody had scored this way before, and it is
the reason `token_*` is not quoted as a result anywhere in this note.

## What would refute this

- **A stronger reasoner closing the gap to 0.845.** The ceiling measured here is
  a ceiling *for this reasoner* — naive Bayes over ten structural features, seven
  of them symbol-free. If a better reasoner on the same oracle reaches 0.6, reading 2 and 3
  above are about `gparse` and not about parsing.
- **The `retrieve-001` ≈ `template-002` tie separating at larger n.** It is one
  standard error. It is quoted as a tie, not as a win for memorisation.
- **A parser that beats `retrieve-001`.** That would make the parser column
  about reading rather than recognition, and would move reading 4.
- **`gparse-nolex` separating from `template-002`.** It is 0.006 apart, well
  inside noise, and reading 5 rests on that being a tie rather than a win for
  either. Larger `n_eval` would settle it; at four episodes per lesson it does
  not.

## An uncontrolled confound, stated rather than buried

The readers do not present the same number of candidates. Mean nodes per parse,
from the same audit: `flat` 78.6, `retrieve-001` 93.1, `oracle` 37.9,
`template-002` 28.1. The oracle is picking one node out of a smaller set than
`retrieve-001` is, and argmax over fewer candidates is easier.

It does not look like the driver — the ordering by node count (retrieve > flat >
oracle > template) bears no resemblance to the ordering by accuracy (oracle >
retrieve ≈ template ≫ flat), and `flat` has twice `template-002`'s candidates
and a tenth of its accuracy. But it is not controlled for, and a reader
comparing the oracle to `retrieve-001` specifically should know that the two
differ in candidate count by 2.5× as well as in structure.

## Caveats that belong on the number

- English only, the sweep's default. The oracle's availability rule is defined on
  words of the rendered text, so in a language where node labels are not written
  as words it reveals less and the ceiling falls. That is correct behaviour and
  it is untested here.
- The confidence calibration is fitted on a contiguous tail of a lesson-major
  episode list, i.e. on 36 lessons the weights never saw
  (`notes/questions/2026-08-13-held-out-calibration-slices-are-whole-lessons`).
  It affects the stated probabilities, not the argmax, so `answer_acc` is
  unaffected and `answer_bits` may be pessimistic for every `gparse` row equally.
- `gparse`'s `node` metrics are meaningless: it abstains on the graph task, and
  the type head has no structural fallback, so it lands on the type unigram at
  0.395 against a 0.860 floor. It is a text model in a two-task harness.
- Provisional by this repo's rule: every control here was designed by the same
  agent that wrote the model.
