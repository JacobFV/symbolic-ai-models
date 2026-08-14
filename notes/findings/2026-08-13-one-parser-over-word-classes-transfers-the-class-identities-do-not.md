---
date: 2026-08-13
author: agent-polyglot
status: provisional
related: [2026-08-13-one-parser-over-word-classes-and-many-languages,
          2026-08-13-the-language-representation-is-orthographic]
---

# One parser over word classes: abstraction transfers, the classes do not, and the lookup still wins

**Full 179 lessons, 46 WALS-coded languages, every language held out exactly
once.** Not a slice. `runs/polyglot/`, and `runs/polyglot/report.txt` is the
printed table. Pre-registration, written before any of it ran:
`notes/decisions/2026-08-13-one-parser-over-word-classes-and-many-languages.md`.

Protocol: **leave eight languages out, six folds stratified by script**, so the
training mixture is 38 languages rather than 45 — stricter than
leave-one-out, and named exactly rather than called LOLO. In-sample is the same
arms fitted on all 46. The graph is byte-identical in every language, so the
target never moves and every difference is attributable. Floors from
`fit_floor` on **English** training episodes only: the graph repeats 46 times in
a multilingual training set, so a floor fitted on the mixture would find its own
answer key in the other half. That trap is pinned by a test.

## The table

Held out — a language the parser was never fitted on. Macro over lessons, then
over the 46 languages.

| parser | uas | brack | label | edge | ted |
|---|---:|---:|---:|---:|---:|
| **polycky-1class** (control) | **0.229** | **0.103** | **0.450** | **0.195** | **0.443** |
| polycky-002 (lang-conditioned) | 0.218 | 0.101 | 0.436 | 0.188 | 0.430 |
| **polycky-001** (the parser) | 0.211 | 0.101 | 0.430 | 0.184 | 0.421 |
| polycky-hapax (control) | 0.213 | 0.093 | 0.416 | 0.181 | 0.426 |
| polycky-v1seg (control) | 0.207 | 0.099 | 0.419 | 0.180 | 0.419 |
| polycky-crc (nonsense split) | 0.186 | 0.079 | 0.397 | 0.158 | 0.400 |
| polycky-literal (control) | 0.177 | 0.080 | 0.385 | 0.152 | 0.370 |
| cky-001, mixture-fitted | 0.175 | 0.079 | 0.374 | 0.149 | 0.366 |
| *template-002* (lookup) | *0.462* | *0.157* | *0.635* | *0.539* | *0.692* |
| FLOOR (constant) | 0.078 | 0.004 | 0.116 | 0.054 | 0.315 |

In sample — the same arms fitted on all 46 and scored on all 46.

| parser | uas | brack | label | edge |
|---|---:|---:|---:|---:|
| polycky-002 | 0.264 | 0.134 | 0.473 | 0.236 |
| polycky-001 | 0.261 | 0.130 | 0.479 | 0.234 |
| polycky-v1seg | 0.255 | 0.126 | 0.466 | 0.228 |
| polycky-1class | 0.249 | 0.116 | 0.478 | 0.213 |
| polycky-literal | 0.246 | 0.130 | 0.455 | 0.224 |
| cky-001 | 0.239 | 0.124 | 0.442 | 0.216 |
| polycky-crc | 0.238 | 0.108 | 0.449 | 0.209 |
| *template-002* | *0.473* | *0.163* | *0.650* | *0.555* |

## What was confirmed

**Abstraction transfers, and it is the only factor that does.** Against
`polycky-literal` — identical segmentation, identical mixture, identical decode,
identical floors, literal words in the RHS — the class grammar gains **+0.021
bracket, +0.032 edge, +0.045 label, +0.033 uas on held-out languages, up in
6 folds of 6 on every metric**. Against `cky-001` fitted on the same mixture the
gain is the same size (+0.021 bracket, +0.034 edge). Retention — the held-out
score over that same language's in-sample score, which divides out "this
language is hard" — goes from **0.541 to 0.699**.

And it is *specifically* a transfer effect: in sample the two are level on
bracket F1 (0.130 both). Abstraction costs nothing where the language is known
and pays only where it is not, which is what a claim about transfer should look
like.

**Script is a confound, and it is mostly a proxy for a bigger one.** Retention
for `polycky-001` splits **0.780 for the 34 Latin-script languages against 0.470
for the 12 that are the sole representative of their script**. Per language it
is worse than the average suggests: Arabic keeps 0.16, Mandarin 0.24, Korean
0.29; Aymara, Western Apache and Ainu keep 0.94–0.96.

But the alternatives had to be measured rather than argued about, and script
comes **third of three**. `scripts/polyglot_script_control.py`, 46 languages,
retention of `polycky-001` on bracket F1:

| correlate with retention | r |
|---|---:|
| **treebank clause coverage** (a harness heuristic) | **+0.886** |
| **untranslated share** (how little the language translates) | **+0.836** |
| novel script (1/0) | −0.493 |

They are heavily collinear — coverage against untranslated share is +0.849 —
so the partials are what decide it:

| | r |
|---|---:|
| coverage, untranslated share partialled out | **+0.609** |
| untranslated share, coverage partialled out | +0.339 |
| untranslated share, script partialled out | +0.800 |
| novel script, untranslated share partialled out | −0.313 |

So the best single predictor of whether this parser transfers to a language it
has never seen is **how many of that language's clauses `Treebank`'s span
heuristic could find at all** — a property of the harness, not of the grammar,
not of the conditioning, and not of the script. Script is real but largely
mediated: it drops from −0.49 to −0.31 once translation share is held, and
translation share is itself two thirds explained by coverage.

**And here is the part that stops this from being a causal claim.** The
segmentation arm is an *intervention* on exactly that variable. It raises
Chinese clause coverage from 0.466 to 0.627 and Cantonese from 0.491 to 0.685
— and moves the held-out parse score by +0.002 bracket, in 4 folds of 6. So
coverage predicts transfer across languages at +0.89 and yet manipulating
coverage within a language buys nothing. The correlation and the intervention
disagree, which means coverage is not the cause; it and retention are both
downstream of something else about how tractable a given rendering is.

That is the parser-side echo of the Mantel result on the graded language
representation (script +0.18, held-out WALS features null), with one extra
turn of the screw: here there was an intervention available, and taking it
showed the strongest correlate in the table to be a passenger.

## What was refuted, including by me

**H2 — the induced class identities carry nothing, and are a net negative out of
sample.** `polycky-1class`, which keeps the shared/translated split but collapses
every translated token into *one* symbol, **beats the full class induction on
held-out languages on every metric, in 5–6 folds of 6** (+0.011 edge, +0.020
label, +0.018 uas). It loses in sample (bracket 0.116 against 0.130). So the
class identity is a within-language memorisation that does not survive the
language changing, and what actually transfers is the far cruder fact
**"argument / frame / literal punctuation"** — a positional template with a
chart parser wrapped around it. That is `template-002`'s mechanism, and it has
to be reported as such rather than as grammar induction.

The countable translation-equivalence class was the interesting half of the
design. It is the half that does not work.

**H0 — segmentation is a null at the parser level, and I predicted it would
dominate.** The script-aware splitter fixes a real defect in the shared one:
`split_words` runs `alice和面包` together into a single token, so the argument
cannot be found, and Tamil shatters into graphemes because combining marks are
not `\w`. Treebank clause coverage, 179 lessons x 2 episodes:

| language | `split_words` | script-aware | mean clause length |
|---|---:|---:|---|
| english | 0.792 | 0.792 | 8.2 → 8.2 |
| cmn | 0.466 | **0.627** | 6.7 → 10.9 |
| jpn | 0.464 | **0.588** | 7.4 → 11.6 |
| yue | 0.491 | **0.685** | 7.0 → 8.8 |
| tha | 0.508 | **0.645** | 9.2 → 13.7 |
| khm | 0.528 | **0.664** | 12.4 → 11.9 |
| arb | 0.583 | 0.583 | **23.4 → 10.7** |
| tam | 0.755 | 0.755 | **13.4 → 7.7** |

Sixteen points of clause coverage in Chinese, and Arabic clauses less than half
as long. The parser barely moves: `polycky-001` over `polycky-v1seg` is
**+0.002 bracket, +0.004 edge, up in only 4 of 6 folds**. Under the *English-fit*
protocol it is worse than null — Chinese `size_ratio` goes 1.36 → 3.84 and every
score falls, because every unseen ideograph becomes its own token and the
English-fitted lexicon calls all of them arguments.

So: the harness defect is real, large, in the direction claimed, and does not
matter. That is the opposite of this repo's standing prior and it is recorded
because it is.

**H3 — language conditioning is a null, and on a held-out language it is a null
by construction.** In sample, `polycky-002` gains **+0.0031 bracket** over the
unconditioned `polycky-001`; the same-cardinality crc32 split *loses* **0.0220**.
Read carefully, that is not "conditioning beats the control by +0.025": it is
"splitting the rule weights 46 ways costs 0.022 when the split is meaningless,
and knowing the split is real buys almost all of that back and nothing more."

On held-out languages the gain is **+0.0001**, and that is a property of the
design rather than a measurement: the Dirichlet backoff makes an unseen
condition score *exactly* the global rule set, pinned by a test. So the entire
held-out difference between the conditioned and unconditioned arms is the one
other thing conditioning provides — the parser can tell that the language is
novel and switch its out-of-vocabulary rate. **What language conditioning buys
on a language you have never seen is knowing that you have never seen it.**

## The result that overshadows all of the above

`template-002` — punctuation-shape lookup, retrieve the nearest training
prompt, copy its graph, refill the content words — scores **0.539 edge F1 on
held-out languages against 0.184** for the best compositional arm, and keeps
**0.964** of its in-sample score. It is almost language-invariant already.

The gap is much smaller on `bracket_f1` (0.157 against 0.103), which is the
metric that demands the exact yield under a node rather than credit for local
triples — the usual disagreement, and it is the compositional parsers' best
showing. It does not change the ranking. The multilingual grammar is a 28%
relative improvement on a family that is still losing to a lookup table by 3x.

## The oracle, priced

The conditioned arms are handed the language from episode metadata. A
nearest-centroid head on `shape_features` recovers it at **0.073 against a
0.022 floor** over 46 languages — 3.3x chance and useless. The reason is
coherent: the derived grammars are tier 4 (word order from WALS, no morphology)
and keep the punctuation, so the features that identify the *lesson* barely move
between languages. Nothing here rests on the oracle, because conditioning is a
null; but any future conditioned result does, and this is what it would cost.
Measured on 368 probe episodes over 8 lessons, so it is indicative rather than
settled.

## An accident worth keeping

`Grammar._fit_lexicon` estimates `P(ARG | unseen token)` from training hapaxes
and gets ~0.9 monolingually, on the sound reasoning that a token seen once is a
nonce symbol and nonce symbols are arguments. **On a parallel corpus that
reasoning inverts.** An argument is copied verbatim into all 46 renderings, so
it is never a hapax; a rare *translated frame word* is a hapax in exactly one
language. The same estimator returns **0.009** on the mixture, and
`polycky-hapax` — which keeps it — loses 0.008 bracket held out. The replacement
is a held-out-language simulation over training seeds, which gives 0.672 for a
known language and 0.222 for a novel one.

## What would have refuted this, and what still might

Stated in the decision note before the run: abstraction was to be refuted if
`polycky-001` failed to beat `polycky-literal` held out (it did not fail, 6/6);
the class identities were to be refuted if `polycky-1class` matched (it did more
than match); conditioning was to be refuted if `polycky-crc` gained as much (it
lost outright, which refutes the *machinery* rather than the signal).

## Two refutation attempts, run rather than parked

**The 1class result could have been a search bound, and is not.** An unknown
token is tried against at most `WILDCARD_BEAM = 6` class symbols; the one-class
control has exactly one class and therefore no beam at all, so a bound tight
enough to starve the full induction would look identical to "the class
identities carry nothing". `polycky-wide` was registered afterwards, with the
beam at 64 — wider than the class count at any state this grammar builds, i.e.
exhaustive. All six folds again:

| contrast | brack | edge | label | uas | ted |
|---|---:|---:|---:|---:|---:|
| wide − 001 (the beam was costing this) | +0.0007 | +0.0023 | +0.0033 | +0.0038 | +0.0030 |
| 1class − wide (the gap that remains) | +0.0018 | +0.0090 | +0.0165 | +0.0141 | +0.0193 |

Taking the beam off recovers about a fifth of the gap on `edge_f1` and a
quarter on `uas`, and `polycky-1class` still leads on 6 folds of 6 on every
metric but bracket. The bound was not binding; the finding stands.

**The abstraction gain does not go where the mechanism says it should, and
that is a null against my own story.** The account of *why* classes transfer is
that a held-out language's frame words are all unseen, so a literal RHS has
nothing to match while a wildcard does — which predicts the gain should be
largest in the languages that translate most. It is not. The gain in retention
averages **+0.158** and correlates with untranslated share at **r = +0.027** —
flat. Against novel script it is +0.19, weak and noisy. So abstraction buys a
roughly uniform amount of retention everywhere rather than rescuing the hard
languages, and the mechanism is more likely "a smaller, better-generalising rule
set" (28,046 rules against the literal grammar's 55,010) than "the wildcard
catches untranslated frames". The effect is real and reproduces 6/6; the
explanation for it does not survive its own prediction.

## What would have refuted this

Stated in the decision note before the run: abstraction was to be refuted if
`polycky-001` failed to beat `polycky-literal` held out (it did not fail, 6/6);
the class identities were to be refuted if `polycky-1class` matched (it did more
than match); conditioning was to be refuted if `polycky-crc` gained as much (it
lost outright, which refutes the *machinery* rather than the signal).

**The translation correlation is not an artefact of the retention statistic.**
That was the third thing worth attacking — retention is a ratio of two small
numbers (bracket F1 in the 0.05–0.17 range), so a correlation could be a
property of the statistic rather than of the corpus. Recomputed on three
metrics and on the raw held-out score, which does not divide by anything:

| read-out | untranslated share | novel script |
|---|---:|---:|
| retention, bracket_f1 | +0.836 | −0.493 |
| retention, edge_f1 | +0.862 | −0.467 |
| retention, label_f1 | +0.843 | −0.531 |
| raw held-out bracket_f1 | +0.826 | −0.575 |
| raw held-out edge_f1 | +0.853 | −0.554 |

It holds everywhere, between +0.83 and +0.86, and script stays second in every
row. The section survives.

**And it is not an artefact of the instrument that measures it.** Untranslated
share is counted in tokens, and the two splitters here count tokens very
differently for exactly the languages the analysis is about — one emits a token
per ideograph, the other emits whole runs. Measured with the shared
`split_words` instead of the script-aware one, the covariate agrees with itself
at **r = 0.986**, correlates with retention at **+0.828** (against +0.836), and
survives partialling script out at **+0.777** (against +0.800). The covariate
is not carrying the new splitter's fingerprint.

`status: provisional`, because every control here was designed by the same agent
that wrote the parser, and the ones that passed passed against controls I chose.
What most wants an independent try now:

**The correlation/intervention dissociation is the load-bearing claim and it
rests on one intervention.** Segmentation is the only handle on clause coverage
that was tried. A second, independent way of moving coverage — loosening the
greedy one-node-per-segment assignment in `Treebank._add`, or scoring anchors by
substring rather than whole-token match — would either reproduce the null and
make "coverage is a passenger" solid, or move the score and make the
segmentation arm the odd one out. Until then "coverage is not causal" is one
experiment's worth of evidence against a +0.886 correlation, and that is not
much.
