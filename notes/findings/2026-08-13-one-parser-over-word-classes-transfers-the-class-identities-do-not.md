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

**Script is the confound, exactly as predicted.** Retention for `polycky-001`
splits **0.780 for the 34 Latin-script languages against 0.470 for the 12 that
are the sole representative of their script**. Per language it is worse than the
average suggests: Arabic keeps 0.16, Mandarin 0.24, Korean 0.29; Aymara,
Western Apache and Ainu keep 0.94–0.96. When the script is in the mixture the
parser barely notices the language is new; when it is not, most of the score
goes. The abstraction helps most where it is hardest (Mandarin 0.24 against the
literal grammar's 0.12) and still does not rescue it.

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

`status: provisional`, because every control here was designed by the same agent
that wrote the parser. The two that most want an independent try:

- **The 1class result decides the interpretation.** If it is an artefact of the
  wildcard beam (`WILDCARD_BEAM = 6`, ordered by best reachable rule) then the
  full class induction is being starved at search time rather than losing on
  merit — one class means one wildcard child and no beam at all. That is a
  search bound doing the work of a finding, which is exactly the substitution
  this repo keeps making.
- **The retention statistic** divides out the language's own difficulty but not
  how much of the document that language translates. A language that leaves most
  of the frame in English will retain well for a reason that has nothing to do
  with the parser.
